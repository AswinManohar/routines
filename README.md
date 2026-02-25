# Routine Tracker - PostgreSQL Backend

A full-stack habit tracking app with PostgreSQL backend, FastAPI, and React frontend.

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   React     │──────▶│   FastAPI    │──────▶│  PostgreSQL │
│  Frontend   │◀──────│   Backend    │◀──────│   Database  │
└─────────────┘      └──────────────┘      └─────────────┘
     ▲                                              ▲
     │                                              │
     └──────────────────────────────────────────────┘
              Telegram Bot (via API)
```

## Quick Start

### 1. Start PostgreSQL
```bash
sudo service postgresql start
# or
sudo systemctl start postgresql
```

### 2. Start the Backend
```bash
cd routine-tracker-react
./start.sh
```

This will:
- Create the `routine_tracker` database if it doesn't exist
- Run the schema (tables, indexes, triggers)
- Install Python dependencies
- Start FastAPI on http://localhost:8000

### 3. View the App
Open http://localhost:8080 in your browser.

## Database Schema

### Tables

**habits** - Stores routine definitions
- `id` (PK), `habit_id` (unique slug), `name`, `icon`
- `is_recurring`, `duration`, `target_days`
- `created_at`, `archived_at`

**completions** - Daily completion tracking
- `id` (PK), `habit_id` (FK)
- `completion_date`, `completion_percent` (0-100)
- `status` (auto-calculated: completed/partial/missed)
- `notes`

**streaks** - Streak tracking per habit
- `habit_id` (FK), `current_streak`, `longest_streak`
- `last_completed`, `updated_at`

### Auto-Calculated Status
```sql
completion >= 75% → 'completed'
completion >= 30% → 'partial'
completion < 30%  → 'missed'
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/habits` | List all habits with week data |
| POST | `/api/habits` | Create new habit |
| PUT | `/api/habits/{id}/completion/{date}` | Update completion |
| GET | `/api/habits/{id}/monthly` | Get monthly heatmap data |
| DELETE | `/api/habits/{id}` | Archive habit |

### Example API Calls

```bash
# List habits
curl http://localhost:8000/api/habits

# Create habit
curl -X POST http://localhost:8000/api/habits \
  -H "Content-Type: application/json" \
  -d '{"name":"Drink Water","icon":"💧","is_recurring":true,"duration":"30 days"}'

# Update completion
curl -X PUT http://localhost:8000/api/habits/1/completion/2024-02-24 \
  -H "Content-Type: application/json" \
  -d '{"completion_percent":100}'

# Get monthly data
curl http://localhost:8000/api/habits/1/monthly
```

## Frontend Features

- **Weekly bars** - 7-day view with click-to-toggle completion
- **Consistent colors** - Same green scale in bars and heatmap
- **Monthly heatmap** - Click routine to see GitHub-style grid
- **Add habits** - FAB button with recurring options
- **Delete habits** - Trash icon in each card
- **Auto-refresh** - Updates every 30 seconds

## Telegram Bot Integration

When you say "Add a habit" in Telegram, I'll:

1. **Ask for the habit name**
2. **Ask if recurring** (Yes/No)
3. **Ask for duration** (if recurring)
4. **Save via API** and confirm

### Quick Add via CLI
```bash
python3 ~/.openclaw/skills/telegram-habit-bot/scripts/add_habit_api.py \
  "Morning Meditation" "🧘" --recurring --duration "30 days"
```

## File Structure

```
routine-tracker-react/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── requirements.txt     # Python deps
│   └── venv/                # Python environment
├── database/
│   └── schema.sql           # PostgreSQL schema
├── src/
│   ├── App.js               # React components
│   └── App.css              # Styling
├── build/                   # Compiled frontend
├── start.sh                 # Startup script
└── package.json
```

## Environment Variables

```bash
# Backend
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/routine_tracker

# Frontend
REACT_APP_API_URL=http://localhost:8000/api
```

## Troubleshooting

**Backend won't start?**
```bash
# Check PostgreSQL
sudo service postgresql status

# Check if port 8000 is free
lsof -i :8000
```

**Frontend shows "Loading..."?**
- Make sure backend is running on port 8000
- Check browser console for CORS errors

**Database connection failed?**
```bash
# Test connection
sudo -u postgres psql -d routine_tracker -c "SELECT 1;"
```
