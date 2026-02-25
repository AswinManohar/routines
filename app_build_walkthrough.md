# Routine Tracker - App Build Walkthrough

A full-stack habit and routine tracking application with React frontend, FastAPI backend, and SQLite database.

---

## Table of Contents
1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Database Architecture](#database-architecture)
4. [Backend Architecture](#backend-architecture)
5. [Frontend Architecture](#frontend-architecture)
6. [How to Run](#how-to-run)
7. [API Reference](#api-reference)
8. [Deployment Notes](#deployment-notes)

---

## Overview

**Tech Stack:**
- **Frontend:** React 18, CSS3
- **Backend:** FastAPI (Python)
- **Database:** SQLite (single file, zero-config)
- **Network:** Tailscale for remote access

**Features:**
- Track daily habits with weekly progress bars
- Plan daily routines with time slots
- Mark completions (0%, 50%, 100%)
- Monthly heatmap view
- Telegram bot integration via API
- Works on local network and remotely via Tailscale

---

## Project Structure

```
routine-tracker-react/
├── backend/
│   ├── main_sqlite.py          # FastAPI server + SQLite backend
│   ├── main_csv.py             # Alternative CSV backend (deprecated)
│   ├── requirements.txt        # Python dependencies
│   └── venv/                   # Python virtual environment
├── src/
│   ├── App.js                  # Main React app + Habits view
│   ├── App.css                 # Main styles
│   ├── DailyRoutines.js        # Routines view component
│   ├── Routines.css            # Routines styles
│   └── index.js                # React entry point
├── database/
│   └── schema.sql              # PostgreSQL schema (deprecated)
├── reminders/
│   ├── check_habits.py         # Cron job script for reminders
│   └── schedule.json           # Reminder timing configuration
├── public/
│   └── index.html              # HTML template
├── package.json                # Node dependencies
├── start.sh                    # Startup script (legacy)
├── backend.log                 # Backend output log
├── frontend.log                # Frontend output log
└── data.db                     # SQLite database (created at runtime)
```

---

## Database Architecture

**Database:** SQLite (`data.db`)

### Tables

#### 1. habits
Stores habit/routine definitions.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| habit_id | TEXT UNIQUE | URL-friendly slug (e.g., "sleep-7-9") |
| name | TEXT | Display name |
| icon | TEXT | Emoji icon (e.g., "💤") |
| is_recurring | BOOLEAN | True for ongoing habits |
| duration | TEXT | "30 days", "90 days", "365 days" |
| target_days | INTEGER | Calculated from duration |
| created_at | TIMESTAMP | Creation time |
| archived_at | TIMESTAMP | Soft delete timestamp |

#### 2. completions
Tracks daily completion percentages.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| habit_id | INTEGER FK | References habits.id |
| completion_date | DATE | YYYY-MM-DD format |
| completion_percent | INTEGER | 0-100 |
| notes | TEXT | Optional notes |
| created_at | TIMESTAMP | Record creation |

**Unique constraint:** (habit_id, completion_date)

#### 3. streaks
Tracks current and longest streaks per habit.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| habit_id | INTEGER FK | References habits.id |
| current_streak | INTEGER | Consecutive days completed |
| longest_streak | INTEGER | All-time longest |
| last_completed | DATE | Most recent completion |
| updated_at | TIMESTAMP | Last update |

#### 4. daily_routines
Separate from habits - for time-based daily planning.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PRIMARY KEY | Auto-increment ID |
| routine_id | TEXT UNIQUE | URL-friendly slug |
| name | TEXT | Display name |
| time_slot | TEXT | e.g., "7:00-8:00 AM" |
| days | TEXT | e.g., "Mon-Fri", "Daily" |
| description | TEXT | Optional details |
| icon | TEXT | Emoji icon |
| order_index | INTEGER | Display order |
| is_active | BOOLEAN | Soft delete flag |
| created_at | TIMESTAMP | Creation time |

### Database Operations

```python
# Get database connection
conn = sqlite3.connect('data.db')
conn.row_factory = sqlite3.Row  # Enables dict-like access

# Initialize tables (auto-run on startup)
init_db()
```

---

## Backend Architecture

**Framework:** FastAPI
**File:** `backend/main_sqlite.py`

### Key Components

#### 1. Database Connection
```python
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn
```

#### 2. Auto-Initialization
Database and tables created automatically on first startup.

#### 3. CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://pop-os.tailf0835c.ts.net:3000"  # Tailscale
    ],
    ...
)
```

### API Structure

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/habits` | GET | List all habits |
| `/api/habits` | POST | Create new habit |
| `/api/habits/{id}` | PATCH | Partial update |
| `/api/habits/{id}` | PUT | Full update |
| `/api/habits/{id}` | DELETE | Soft delete |
| `/api/habits/{id}/completion/{date}` | PUT | Update completion % |
| `/api/habits/{id}/monthly` | GET | Monthly heatmap data |
| `/api/routines` | GET/POST | List/create routines |
| `/api/routines/batch` | POST | Create multiple routines |
| `/api/routines/{id}` | PUT/DELETE | Update/delete routine |
| `/api/telegram/*` | Various | Telegram bot endpoints |

### Data Flow

```
Frontend (React)
      ↓ HTTP/JSON
FastAPI Backend
      ↓ SQL
SQLite Database
```

---

## Frontend Architecture

**Framework:** React 18
**Styling:** CSS3 with custom properties

### Component Structure

```
App.js (Main container)
├── Habits View (default)
│   ├── RoutineCard (grid of habit cards)
│   │   ├── ProgressBar (weekly completion bars)
│   │   └── RoutineStats (counts)
│   ├── MonthlyModal (heatmap view)
│   └── AddHabitModal (create form)
├── Routines View
│   ├── RoutineItemCard (todo-style list)
│   ├── AddRoutineModal
│   └── EditRoutineModal
└── Navigation Bar
```

### State Management
- **Local state:** React `useState` for UI state
- **Data fetching:** `useEffect` with `fetch` API
- **Auto-refresh:** 30-second polling interval

### Key Features

#### Weekly Progress Bars
- 7-day view (Mon-Sun)
- Color coding: green (≥75%), yellow (≥30%), gray (<30%)
- Click to toggle: 0% → 50% → 100% → 0%
- "TODAY" badge on current day

#### Monthly Heatmap
- GitHub-style contribution graph
- 5 intensity levels (0-4)
- Hover for date + completion %

#### Responsive Grid
- Desktop: 2-4 cards per row
- Mobile: 1 card per row (stacked)

---

## How to Run

### Prerequisites
- Python 3.10+
- Node.js 16+
- npm or yarn

### Step 1: Install Dependencies

**Backend:**
```bash
cd routine-tracker-react/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Frontend:**
```bash
cd routine-tracker-react
npm install
```

### Step 2: Start Backend

```bash
cd routine-tracker-react/backend
source venv/bin/activate
uvicorn main_sqlite:app --host 0.0.0.0 --port 8000

# Or background mode:
nohup uvicorn main_sqlite:app --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
```

Backend runs at:
- Local: http://localhost:8000
- Tailscale: http://pop-os.tailf0835c.ts.net:8000

### Step 3: Start Frontend

```bash
cd routine-tracker-react
npm start

# Or background mode:
nohup npm start > frontend.log 2>&1 &
```

Frontend runs at:
- Local: http://localhost:3000
- Tailscale: http://pop-os.tailf0835c.ts.net:3000

### Step 4: Verify

```bash
# Check backend
curl http://localhost:8000/api/health
# Expected: {"status": "ok", "database": "sqlite", ...}

# Check habits
curl http://localhost:8000/api/habits
```

### Auto-Start on Boot (Optional)

Create systemd service files (see `backend/routine-tracker-backend.service` template).

---

## API Reference

### Habits

#### List All Habits
```bash
GET /api/habits
```

**Response:**
```json
[
  {
    "id": 1,
    "habit_id": "sleep-7-9",
    "name": "Sleep 7-9 Hours",
    "icon": "💤",
    "is_recurring": true,
    "duration": "365 days",
    "streak": 5,
    "week_data": [...]
  }
]
```

#### Create Habit
```bash
POST /api/habits
Content-Type: application/json

{
  "name": "Morning Meditation",
  "icon": "🧘",
  "is_recurring": true,
  "duration": "30 days"
}
```

#### Update Completion
```bash
PUT /api/habits/1/completion/2026-02-25
Content-Type: application/json

{"completion_percent": 100}
```

#### Delete Habit
```bash
DELETE /api/habits/1
```

### Routines

#### List Routines
```bash
GET /api/routines
```

#### Create Routine
```bash
POST /api/routines
Content-Type: application/json

{
  "name": "Morning Writing",
  "time_slot": "7:00-8:00 AM",
  "days": "Mon-Fri",
  "icon": "✍️"
}
```

#### Batch Create
```bash
POST /api/routines/batch
Content-Type: application/json

{
  "routines": [
    {"name": "Gym", "time_slot": "6:00 PM", "days": "Mon-Wed-Fri"},
    {"name": "Read", "time_slot": "10:00 PM", "days": "Daily"}
  ]
}
```

### Telegram Endpoints

Designed for bot integration:

```bash
# Quick complete
POST /api/telegram/habits/1/complete

# Quick skip
POST /api/telegram/habits/1/skip

# List with commands
GET /api/telegram/habits

# Get incomplete (for reminders)
GET /api/telegram/habits/incomplete
```

---

## Deployment Notes

### Local Development
- Use `localhost` URLs
- Hot reload enabled (npm start)

### Tailscale Access
1. Ensure both devices on same Tailscale network
2. Use Tailscale machine name in URLs:
   - Frontend: `http://pop-os.tailf0835c.ts.net:3000`
   - API: `http://pop-os.tailf0835c.ts.net:8000`
3. CORS already configured for Tailscale domain

### Production Considerations
- **Database:** SQLite is fine for single-user; migrate to PostgreSQL for multi-user
- **Security:** Add authentication (JWT tokens)
- **HTTPS:** Use reverse proxy (nginx) with SSL
- **Backup:** Regular backups of `data.db` file

### File Locations
- **App:** `~/.openclaw/workspace-general/routine-tracker-react/`
- **Database:** `~/.openclaw/workspace-general/routine-tracker-react/data.db`
- **Logs:** `backend.log`, `frontend.log`

---

## CLI Tool

Quick commands via Python script:

```bash
# List habits
python3 habit_cli.py list

# Mark complete
python3 habit_cli.py done 5

# Add routine
python3 habit_cli.py add-routine "Morning Run" "7:00 AM" "Mon-Fri"

# Batch add from JSON
python3 habit_cli.py add-routines-batch routines.json
```

Location: `~/.openclaw/skills/habit-tracker-api/habit_cli.py`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to backend" | Check if backend running: `lsof -i :8000` |
| CORS errors | Verify CORS origins in `main_sqlite.py` |
| Port already in use | Kill existing process: `pkill -f uvicorn` |
| Database locked | Wait and retry; check for concurrent access |
| Frontend not updating | Check `frontend.log` for compile errors |

---

## Future Enhancements

- [ ] User authentication
- [ ] Data export (CSV/JSON)
- [ ] Push notifications
- [ ] Analytics dashboard
- [ ] Habit categories/tags
- [ ] Shared/group habits

---

**Built with ❤️ for personal productivity**
