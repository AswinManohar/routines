from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime, timedelta
import sqlite3
import json
import os
from pathlib import Path

app = FastAPI(title="Routine Tracker API")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://pop-os.tailf0835c.ts.net:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite database path
DB_PATH = Path.home() / ".openclaw/workspace-general/routine-tracker-react/data.db"

def get_db():
    """Get SQLite database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with schema."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Habits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '✨',
            is_recurring BOOLEAN DEFAULT 0,
            duration TEXT,
            target_days INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            archived_at TIMESTAMP
        )
    """)
    
    # Completions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
            completion_date DATE NOT NULL,
            completion_percent INTEGER DEFAULT 0 CHECK (completion_percent >= 0 AND completion_percent <= 100),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(habit_id, completion_date)
        )
    """)
    
    # Streaks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER REFERENCES habits(id) ON DELETE CASCADE,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_completed DATE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Daily routines table (separate from habits)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            routine_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            time_slot TEXT, -- e.g., "7:00-8:00 AM"
            days TEXT, -- e.g., "Mon-Fri" or "Daily"
            description TEXT,
            icon TEXT DEFAULT '📋',
            order_index INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# ==================== MODELS ====================

class HabitCreate(BaseModel):
    name: str
    icon: str = "✨"
    is_recurring: bool = False
    duration: Optional[str] = None

class CompletionUpdate(BaseModel):
    completion_percent: int
    notes: Optional[str] = None

# ==================== HELPERS ====================

def get_bar_class(percentage: float) -> str:
    if percentage >= 75:
        return "completed"
    elif percentage >= 30:
        return "partial"
    return "missed"

def generate_week_data(habit_id: int, cursor) -> List[dict]:
    """Generate week data for a habit."""
    today = date.today()
    day_of_week = (today.weekday() + 7) % 7
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    week_data = []
    
    for i in range(7):
        day_date = today - timedelta(days=day_of_week - i)
        is_future = i > day_of_week
        is_today = i == day_of_week
        
        if is_future:
            week_data.append({
                "day": day_names[i],
                "completion": 0,
                "status": "future",
                "is_today": False,
                "is_future": True
            })
        else:
            cursor.execute(
                "SELECT completion_percent FROM completions WHERE habit_id = ? AND completion_date = ?",
                (habit_id, day_date.isoformat())
            )
            result = cursor.fetchone()
            completion = result['completion_percent'] if result else 0
            
            week_data.append({
                "day": day_names[i],
                "completion": completion,
                "status": get_bar_class(completion),
                "is_today": is_today,
                "is_future": False
            })
    
    return week_data

def get_streak(habit_id: int, cursor) -> int:
    cursor.execute("SELECT current_streak FROM streaks WHERE habit_id = ?", (habit_id,))
    result = cursor.fetchone()
    return result['current_streak'] if result else 0

# ==================== ENDPOINTS ====================

@app.get("/api/habits")
def get_habits():
    """Get all habits with their weekly data."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT h.*, COALESCE(s.current_streak, 0) as streak
        FROM habits h
        LEFT JOIN streaks s ON h.id = s.habit_id
        WHERE h.archived_at IS NULL
        ORDER BY h.created_at DESC
    """)
    habits = cursor.fetchall()
    
    result = []
    for habit in habits:
        week_data = generate_week_data(habit['id'], cursor)
        result.append({
            "id": habit['id'],
            "habit_id": habit['habit_id'],
            "name": habit['name'],
            "icon": habit['icon'],
            "is_recurring": bool(habit['is_recurring']),
            "duration": habit['duration'],
            "streak": habit['streak'],
            "week_data": week_data
        })
    
    conn.close()
    return result

@app.post("/api/habits")
def create_habit(habit: HabitCreate):
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
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO habits (habit_id, name, icon, is_recurring, duration, target_days)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (habit_id, habit.name, habit.icon, habit.is_recurring, 
              habit.duration, target_days))
        new_habit_id = cursor.lastrowid
        
        # Initialize streak
        cursor.execute(
            "INSERT INTO streaks (habit_id, current_streak, longest_streak) VALUES (?, 0, 0)",
            (new_habit_id,)
        )
        
        conn.commit()
        
        return {
            "id": new_habit_id,
            "habit_id": habit_id,
            "name": habit.name,
            "icon": habit.icon,
            "is_recurring": habit.is_recurring,
            "duration": habit.duration,
            "streak": 0
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Habit with this name already exists")
    finally:
        conn.close()

@app.put("/api/habits/{habit_id}/completion/{completion_date}")
def update_completion(habit_id: int, completion_date: date, update: CompletionUpdate):
    """Update completion for a specific date."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO completions (habit_id, completion_date, completion_percent, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(habit_id, completion_date)
        DO UPDATE SET completion_percent = excluded.completion_percent,
                      notes = excluded.notes
    """, (habit_id, completion_date.isoformat(), update.completion_percent, update.notes))
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "completion_percent": update.completion_percent}

@app.get("/api/habits/{habit_id}/monthly")
def get_monthly_data(habit_id: int):
    """Get monthly completion data for a habit."""
    today = date.today()
    year = today.year
    month = today.month
    
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT completion_date, completion_percent
        FROM completions
        WHERE habit_id = ? AND completion_date >= ? AND completion_date <= ?
    """, (habit_id, first_day.isoformat(), last_day.isoformat()))
    
    completions = {row['completion_date']: row for row in cursor.fetchall()}
    
    # Build monthly data
    monthly_data = []
    current = first_day
    while current <= last_day:
        is_future = current > today
        date_str = current.isoformat()
        comp = completions.get(date_str, {})
        completion = comp.get('completion_percent', 0) if not is_future else 0
        
        monthly_data.append({
            "date": date_str,
            "day": current.day,
            "completion": completion,
            "status": get_bar_class(completion) if not is_future else 'future',
            "is_future": is_future
        })
        current += timedelta(days=1)
    
    # Calculate stats
    completed_days = sum(1 for d in monthly_data if d['completion'] >= 75 and not d['is_future'])
    tracked_days = [d for d in monthly_data if not d['is_future']]
    avg_completion = sum(d['completion'] for d in tracked_days) / len(tracked_days) if tracked_days else 0
    
    streak = get_streak(habit_id, cursor)
    
    conn.close()
    
    return {
        "days": monthly_data,
        "stats": {
            "completed_days": completed_days,
            "avg_completion": round(avg_completion, 1),
            "current_streak": streak
        }
    }

@app.delete("/api/habits/{habit_id}")
def delete_habit(habit_id: int):
    """Soft delete a habit."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE habits SET archived_at = CURRENT_TIMESTAMP WHERE id = ?",
        (habit_id,)
    )
    conn.commit()
    conn.close()
    return {"status": "deleted"}

# ==================== DAILY ROUTINES ====================

class RoutineCreate(BaseModel):
    name: str
    time_slot: Optional[str] = None
    days: Optional[str] = "Daily"
    description: Optional[str] = None
    icon: str = "📋"
    order_index: int = 0

class RoutineUpdate(BaseModel):
    name: Optional[str] = None
    time_slot: Optional[str] = None
    days: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None

@app.get("/api/routines")
def get_routines():
    """Get all daily routines ordered by order_index."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM daily_routines 
        WHERE is_active = 1 
        ORDER BY order_index, created_at
    """)
    
    routines = []
    for row in cursor.fetchall():
        routines.append({
            "id": row['id'],
            "routine_id": row['routine_id'],
            "name": row['name'],
            "time_slot": row['time_slot'],
            "days": row['days'],
            "description": row['description'],
            "icon": row['icon'],
            "order_index": row['order_index'],
            "is_active": bool(row['is_active']),
            "created_at": row['created_at']
        })
    
    conn.close()
    return routines

# ==================== BATCH ROUTINES ====================

class BatchRoutines(BaseModel):
    routines: List[RoutineCreate]

@app.post("/api/routines/batch")
def create_routines_batch(batch: BatchRoutines):
    """Create multiple routines at once."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Get max order
    cursor.execute("SELECT MAX(order_index) FROM daily_routines WHERE is_active = 1")
    result = cursor.fetchone()
    order_index = (result[0] or 0) + 1
    
    created_routines = []
    
    for routine in batch.routines:
        routine_id = routine.name.lower().replace(' ', '-').replace('/', '-')
        
        # Check if exists
        cursor.execute("SELECT id FROM daily_routines WHERE routine_id = ?", (routine_id,))
        if cursor.fetchone():
            created_routines.append({
                "routine_id": routine_id,
                "name": routine.name,
                "status": "skipped (exists)"
            })
            continue
        
        cursor.execute("""
            INSERT INTO daily_routines (routine_id, name, time_slot, days, description, icon, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (routine_id, routine.name, routine.time_slot, routine.days, 
              routine.description, routine.icon, order_index))
        
        order_index += 1
        
        created_routines.append({
            "routine_id": routine_id,
            "name": routine.name,
            "status": "created"
        })
    
    conn.commit()
    conn.close()
    
    return {
        "added": sum(1 for r in created_routines if r['status'] == 'created'),
        "skipped": sum(1 for r in created_routines if r['status'] != 'created'),
        "routines": created_routines
    }
    """Create a new daily routine."""
    routine_id = routine.name.lower().replace(' ', '-').replace('/', '-')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM daily_routines WHERE routine_id = ?", (routine_id,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Routine with this name already exists")
    
    # Get max order_index
    cursor.execute("SELECT MAX(order_index) FROM daily_routines WHERE is_active = 1")
    result = cursor.fetchone()
    order_index = routine.order_index or (result[0] or 0) + 1
    
    cursor.execute("""
        INSERT INTO daily_routines (routine_id, name, time_slot, days, description, icon, order_index)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (routine_id, routine.name, routine.time_slot, routine.days, 
          routine.description, routine.icon, order_index))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "id": new_id,
        "routine_id": routine_id,
        "name": routine.name,
        "time_slot": routine.time_slot,
        "days": routine.days,
        "description": routine.description,
        "icon": routine.icon,
        "order_index": order_index,
        "is_active": True
    }

@app.put("/api/routines/{routine_id}")
def update_routine(routine_id: str, update: RoutineUpdate):
    """Update a routine."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build update query dynamically
    updates = []
    values = []
    
    if update.name is not None:
        updates.append("name = ?")
        values.append(update.name)
    if update.time_slot is not None:
        updates.append("time_slot = ?")
        values.append(update.time_slot)
    if update.days is not None:
        updates.append("days = ?")
        values.append(update.days)
    if update.description is not None:
        updates.append("description = ?")
        values.append(update.description)
    if update.icon is not None:
        updates.append("icon = ?")
        values.append(update.icon)
    if update.order_index is not None:
        updates.append("order_index = ?")
        values.append(update.order_index)
    if update.is_active is not None:
        updates.append("is_active = ?")
        values.append(1 if update.is_active else 0)
    
    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(routine_id)
    query = f"UPDATE daily_routines SET {', '.join(updates)} WHERE routine_id = ?"
    
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    
    return {"status": "updated", "routine_id": routine_id}

@app.delete("/api/routines/{routine_id}")
def delete_routine(routine_id: str):
    """Soft delete a routine."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE daily_routines SET is_active = 0 WHERE routine_id = ?",
        (routine_id,)
    )
    
    conn.commit()
    conn.close()
    return {"status": "deleted", "routine_id": routine_id}

@app.post("/api/routines/reorder")
def reorder_routines(order: List[str]):
    """Reorder routines by routine_id list."""
    conn = get_db()
    cursor = conn.cursor()
    
    for index, routine_id in enumerate(order):
        cursor.execute(
            "UPDATE daily_routines SET order_index = ? WHERE routine_id = ?",
            (index, routine_id)
        )
    
    conn.commit()
    conn.close()
    return {"status": "reordered"}

# ==================== HABIT UPDATE MODELS ====================

class HabitUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    is_recurring: Optional[bool] = None
    duration: Optional[str] = None

class HabitFullUpdate(BaseModel):
    name: str
    icon: str = "✨"
    is_recurring: bool = False
    duration: Optional[str] = None

# ==================== FULL HABIT UPDATE ====================

@app.put("/api/habits/{habit_id}")
def update_habit_full(habit_id: int, update: HabitFullUpdate):
    """Update all fields of a habit."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Calculate target days from duration
    target_days = None
    if update.is_recurring and update.duration:
        duration_map = {
            '7 days': 7, '14 days': 14, '21 days': 21, '30 days': 30,
            '60 days': 60, '90 days': 90, '365 days': 365
        }
        target_days = duration_map.get(update.duration)
    
    cursor.execute("""
        UPDATE habits 
        SET name = ?, icon = ?, is_recurring = ?, duration = ?, target_days = ?
        WHERE id = ?
    """, (update.name, update.icon, update.is_recurring, update.duration, target_days, habit_id))
    
    conn.commit()
    conn.close()
    return {"status": "updated", "habit_id": habit_id}

@app.patch("/api/habits/{habit_id}")
def update_habit_partial(habit_id: int, update: HabitUpdate):
    """Partially update a habit (only provided fields)."""
    conn = get_db()
    cursor = conn.cursor()
    
    # Build update query dynamically
    updates = []
    values = []
    
    if update.name is not None:
        updates.append("name = ?")
        values.append(update.name)
    if update.icon is not None:
        updates.append("icon = ?")
        values.append(update.icon)
    if update.is_recurring is not None:
        updates.append("is_recurring = ?")
        values.append(update.is_recurring)
    if update.duration is not None:
        updates.append("duration = ?")
        values.append(update.duration)
        # Update target_days too
        duration_map = {
            '7 days': 7, '14 days': 14, '21 days': 21, '30 days': 30,
            '60 days': 60, '90 days': 90, '365 days': 365
        }
        target_days = duration_map.get(update.duration)
        updates.append("target_days = ?")
        values.append(target_days)
    
    if not updates:
        conn.close()
        raise HTTPException(status_code=400, detail="No fields to update")
    
    values.append(habit_id)
    query = f"UPDATE habits SET {', '.join(updates)} WHERE id = ?"
    
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return {"status": "updated", "habit_id": habit_id}

# ==================== TELEGRAM BOT ENDPOINTS ====================

@app.post("/api/telegram/habits/{habit_id}/complete")
def telegram_complete_habit(habit_id: int):
    """Mark a habit as complete for today (100%) via Telegram."""
    today = date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO completions (habit_id, completion_date, completion_percent, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(habit_id, completion_date)
        DO UPDATE SET completion_percent = 100, notes = 'Completed via Telegram'
    """, (habit_id, today, 100, 'Completed via Telegram'))
    
    conn.commit()
    
    # Get habit name for response
    cursor.execute("SELECT name FROM habits WHERE id = ?", (habit_id,))
    habit = cursor.fetchone()
    conn.close()
    
    return {
        "status": "completed",
        "habit_id": habit_id,
        "habit_name": habit['name'] if habit else None,
        "date": today,
        "completion_percent": 100
    }

@app.post("/api/telegram/habits/{habit_id}/skip")
def telegram_skip_habit(habit_id: int):
    """Skip a habit for today via Telegram."""
    today = date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO completions (habit_id, completion_date, completion_percent, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(habit_id, completion_date)
        DO UPDATE SET completion_percent = 0, notes = 'Skipped via Telegram'
    """, (habit_id, today, 0, 'Skipped via Telegram'))
    
    conn.commit()
    
    cursor.execute("SELECT name FROM habits WHERE id = ?", (habit_id,))
    habit = cursor.fetchone()
    conn.close()
    
    return {
        "status": "skipped",
        "habit_id": habit_id,
        "habit_name": habit['name'] if habit else None,
        "date": today
    }

@app.post("/api/telegram/habits/{habit_id}/partial")
def telegram_partial_habit(habit_id: int, percent: int = 50):
    """Mark a habit as partially complete via Telegram."""
    today = date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO completions (habit_id, completion_date, completion_percent, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(habit_id, completion_date)
        DO UPDATE SET completion_percent = excluded.completion_percent, notes = 'Partial via Telegram'
    """, (habit_id, today, percent, f'{percent}% via Telegram'))
    
    conn.commit()
    
    cursor.execute("SELECT name FROM habits WHERE id = ?", (habit_id,))
    habit = cursor.fetchone()
    conn.close()
    
    return {
        "status": "partial",
        "habit_id": habit_id,
        "habit_name": habit['name'] if habit else None,
        "date": today,
        "completion_percent": percent
    }

@app.get("/api/telegram/habits")
def telegram_get_habits():
    """Get all habits formatted for Telegram."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT h.id, h.habit_id, h.name, h.icon, h.is_recurring, h.duration,
               COALESCE(s.current_streak, 0) as streak
        FROM habits h
        LEFT JOIN streaks s ON h.id = s.habit_id
        WHERE h.archived_at IS NULL
        ORDER BY h.created_at DESC
    """)
    
    habits = []
    for row in cursor.fetchall():
        habits.append({
            "id": row['id'],
            "habit_id": row['habit_id'],
            "name": row['name'],
            "icon": row['icon'],
            "display": f"{row['icon']} {row['name']}",
            "command": f"done {row['habit_id']}",
            "is_recurring": bool(row['is_recurring']),
            "duration": row['duration'],
            "streak": row['streak']
        })
    
    conn.close()
    return {"habits": habits, "count": len(habits)}

@app.get("/api/telegram/habits/incomplete")
def telegram_get_incomplete_habits():
    """Get habits not yet completed today (for reminders)."""
    today = date.today().isoformat()
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT h.id, h.habit_id, h.name, h.icon, h.is_recurring, h.duration
        FROM habits h
        WHERE h.archived_at IS NULL
        AND h.id NOT IN (
            SELECT habit_id FROM completions 
            WHERE completion_date = ? AND completion_percent >= 75
        )
        ORDER BY h.created_at DESC
    """, (today,))
    
    habits = []
    for row in cursor.fetchall():
        habits.append({
            "id": row['id'],
            "habit_id": row['habit_id'],
            "name": row['name'],
            "icon": row['icon'],
            "display": f"{row['icon']} {row['name']}",
            "quick_complete": f"/complete_{row['id']}",
            "quick_skip": f"/skip_{row['id']}"
        })
    
    conn.close()
    return {"habits": habits, "count": len(habits), "date": today}

# ==================== ROUTINE TELEGRAM ENDPOINTS ====================

@app.post("/api/telegram/routines")
def telegram_create_routine(name: str, time_slot: Optional[str] = None, days: Optional[str] = "Daily", icon: str = "📋"):
    """Create a routine via Telegram (simple params)."""
    routine_id = name.lower().replace(' ', '-').replace('/', '-')
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM daily_routines WHERE routine_id = ?", (routine_id,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Routine already exists")
    
    # Get max order
    cursor.execute("SELECT MAX(order_index) FROM daily_routines WHERE is_active = 1")
    result = cursor.fetchone()
    order_index = (result[0] or 0) + 1
    
    cursor.execute("""
        INSERT INTO daily_routines (routine_id, name, time_slot, days, icon, order_index)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (routine_id, name, time_slot, days, icon, order_index))
    
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "status": "created",
        "routine_id": routine_id,
        "name": name,
        "time_slot": time_slot,
        "days": days,
        "message": f"✅ Added routine: {icon} {name}"
    }

@app.get("/api/telegram/routines")
def telegram_get_routines():
    """Get all routines formatted for Telegram."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT routine_id, name, time_slot, days, icon
        FROM daily_routines
        WHERE is_active = 1
        ORDER BY order_index, created_at
    """)
    
    routines = []
    for row in cursor.fetchall():
        time_str = f" ({row['time_slot']})" if row['time_slot'] else ""
        days_str = f" [{row['days']}]" if row['days'] else ""
        routines.append({
            "routine_id": row['routine_id'],
            "name": row['name'],
            "display": f"{row['icon']} {row['name']}{time_str}{days_str}",
            "time_slot": row['time_slot'],
            "days": row['days'],
            "delete_command": f"/delete_routine {row['routine_id']}"
        })
    
    conn.close()
    return {"routines": routines, "count": len(routines)}

@app.delete("/api/telegram/routines/{routine_id}")
def telegram_delete_routine(routine_id: str):
    """Delete a routine via Telegram."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM daily_routines WHERE routine_id = ?", (routine_id,))
    routine = cursor.fetchone()
    
    if not routine:
        conn.close()
        raise HTTPException(status_code=404, detail="Routine not found")
    
    cursor.execute(
        "UPDATE daily_routines SET is_active = 0 WHERE routine_id = ?",
        (routine_id,)
    )
    
    conn.commit()
    conn.close()
    
    return {
        "status": "deleted",
        "routine_id": routine_id,
        "name": routine['name'],
        "message": f"🗑️ Deleted routine: {routine['name']}"
    }

@app.get("/api/health")
def health_check():
    return {"status": "ok", "database": "sqlite", "path": str(DB_PATH)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
