from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="Routine Tracker API")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/routine_tracker"
)

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# ==================== MODELS ====================

class HabitCreate(BaseModel):
    name: str
    icon: str = "✨"
    is_recurring: bool = False
    duration: Optional[str] = None

class HabitResponse(BaseModel):
    id: int
    habit_id: str
    name: str
    icon: str
    is_recurring: bool
    duration: Optional[str]
    created_at: datetime
    streak: int = 0

class CompletionUpdate(BaseModel):
    completion_percent: int
    notes: Optional[str] = None

class DayData(BaseModel):
    day: str
    completion: float
    status: str
    is_today: bool
    is_future: bool

class RoutineWithWeek(BaseModel):
    id: int
    habit_id: str
    name: str
    icon: str
    is_recurring: bool
    duration: Optional[str]
    streak: int
    week_data: List[DayData]

class MonthlyDay(BaseModel):
    date: date
    day: int
    completion: float
    status: str
    is_future: bool

# ==================== HELPERS ====================

def get_bar_class(percentage: float) -> str:
    if percentage >= 75:
        return "completed"
    elif percentage >= 30:
        return "partial"
    return "missed"

def generate_week_data(habit_id: int, conn) -> List[DayData]:
    """Generate week data for a habit from database."""
    today = date.today()
    day_of_week = (today.weekday() + 7) % 7  # Monday = 0
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    week_data = []
    
    with conn.cursor() as cur:
        for i in range(7):
            day_date = today - timedelta(days=day_of_week - i)
            is_future = i > day_of_week
            is_today = i == day_of_week
            
            if is_future:
                week_data.append(DayData(
                    day=day_names[i],
                    completion=0,
                    status="future",
                    is_today=False,
                    is_future=True
                ))
            else:
                # Get completion from database
                cur.execute("""
                    SELECT completion_percent FROM completions 
                    WHERE habit_id = %s AND completion_date = %s
                """, (habit_id, day_date))
                
                result = cur.fetchone()
                completion = result['completion_percent'] if result else 0
                
                week_data.append(DayData(
                    day=day_names[i],
                    completion=completion,
                    status=get_bar_class(completion),
                    is_today=is_today,
                    is_future=False
                ))
    
    return week_data

def get_streak(habit_id: int, conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT current_streak FROM streaks WHERE habit_id = %s",
            (habit_id,)
        )
        result = cur.fetchone()
        return result['current_streak'] if result else 0

# ==================== ENDPOINTS ====================

@app.get("/api/habits", response_model=List[RoutineWithWeek])
def get_habits(conn = Depends(get_db)):
    """Get all habits with their weekly data."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT h.*, COALESCE(s.current_streak, 0) as streak
            FROM habits h
            LEFT JOIN streaks s ON h.id = s.habit_id
            WHERE h.archived_at IS NULL
            ORDER BY h.created_at DESC
        """)
        habits = cur.fetchall()
    
    result = []
    for habit in habits:
        week_data = generate_week_data(habit['id'], conn)
        result.append(RoutineWithWeek(
            id=habit['id'],
            habit_id=habit['habit_id'],
            name=habit['name'],
            icon=habit['icon'],
            is_recurring=habit['is_recurring'],
            duration=habit['duration'],
            streak=habit['streak'],
            week_data=week_data
        ))
    
    return result

@app.post("/api/habits", response_model=HabitResponse)
def create_habit(habit: HabitCreate, conn = Depends(get_db)):
    """Create a new habit."""
    habit_id = habit.name.lower().replace(' ', '-').replace('/', '-')
    
    # Calculate target days from duration
    target_days = None
    if habit.is_recurring and habit.duration:
        duration_map = {
            '7 days': 7, '14 days': 14, '21 days': 21, '30 days': 30,
            '60 days': 60, '90 days': 90, '365 days': 365
        }
        target_days = duration_map.get(habit.duration)
    
    with conn.cursor() as cur:
        try:
            cur.execute("""
                INSERT INTO habits (habit_id, name, icon, is_recurring, duration, target_days)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (habit_id, habit.name, habit.icon, habit.is_recurring, 
                  habit.duration, target_days))
            new_habit = cur.fetchone()
            
            # Initialize streak
            cur.execute(
                "INSERT INTO streaks (habit_id, current_streak, longest_streak) VALUES (%s, 0, 0)",
                (new_habit['id'],)
            )
            
            conn.commit()
            
            return HabitResponse(
                id=new_habit['id'],
                habit_id=new_habit['habit_id'],
                name=new_habit['name'],
                icon=new_habit['icon'],
                is_recurring=new_habit['is_recurring'],
                duration=new_habit['duration'],
                created_at=new_habit['created_at'],
                streak=0
            )
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            raise HTTPException(status_code=400, detail="Habit with this name already exists")

@app.put("/api/habits/{habit_id}/completion/{completion_date}")
def update_completion(
    habit_id: int, 
    completion_date: date, 
    update: CompletionUpdate,
    conn = Depends(get_db)
):
    """Update completion for a specific date."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO completions (habit_id, completion_date, completion_percent, notes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (habit_id, completion_date)
            DO UPDATE SET completion_percent = EXCLUDED.completion_percent, 
                          notes = EXCLUDED.notes
        """, (habit_id, completion_date, update.completion_percent, update.notes))
        conn.commit()
    
    return {"status": "success", "completion_percent": update.completion_percent}

@app.get("/api/habits/{habit_id}/monthly")
def get_monthly_data(habit_id: int, conn = Depends(get_db)):
    """Get monthly completion data for a habit."""
    today = date.today()
    year = today.year
    month = today.month
    
    # Get all days in current month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    with conn.cursor() as cur:
        cur.execute("""
            SELECT completion_date, completion_percent, status
            FROM completions
            WHERE habit_id = %s 
            AND completion_date >= %s 
            AND completion_date <= %s
        """, (habit_id, first_day, last_day))
        
        completions = {r['completion_date']: r for r in cur.fetchall()}
    
    # Build monthly data
    monthly_data = []
    current = first_day
    while current <= last_day:
        is_future = current > today
        comp = completions.get(current, {})
        completion = comp.get('completion_percent', 0) if not is_future else 0
        
        monthly_data.append({
            "date": current.isoformat(),
            "day": current.day,
            "completion": completion,
            "status": comp.get('status', 'missed') if not is_future else 'future',
            "is_future": is_future
        })
        current += timedelta(days=1)
    
    # Calculate stats
    completed_days = sum(1 for d in monthly_data if d['completion'] >= 75 and not d['is_future'])
    tracked_days = [d for d in monthly_data if not d['is_future']]
    avg_completion = sum(d['completion'] for d in tracked_days) / len(tracked_days) if tracked_days else 0
    
    # Get current streak
    streak = get_streak(habit_id, conn)
    
    return {
        "days": monthly_data,
        "stats": {
            "completed_days": completed_days,
            "avg_completion": round(avg_completion, 1),
            "current_streak": streak
        }
    }

@app.delete("/api/habits/{habit_id}")
def delete_habit(habit_id: int, conn = Depends(get_db)):
    """Soft delete a habit."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE habits SET archived_at = CURRENT_TIMESTAMP WHERE id = %s",
            (habit_id,)
        )
        conn.commit()
    return {"status": "deleted"}

# Telegram bot endpoints
@app.post("/api/telegram/habits")
def create_habit_from_telegram(habit: HabitCreate, conn = Depends(get_db)):
    """Special endpoint for Telegram bot to create habits."""
    return create_habit(habit, conn)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "database": "connected"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
