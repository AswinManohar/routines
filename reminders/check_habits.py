#!/usr/bin/env python3
"""
Check for incomplete habits and send Telegram reminders.
Called by OpenClaw cron job (isolated session) so it can use the message tool.
"""

import json
from datetime import datetime, date
from pathlib import Path

SCHEDULE_FILE = Path.home() / ".openclaw/workspace-general/routine-tracker-react/reminders/schedule.json"
SENT_FILE = Path.home() / ".openclaw/workspace-general/routine-tracker-react/reminders/sent_today.json"
DATA_FILE = Path.home() / ".openclaw/workspace-general/data.json"

# Default schedule (habit_id -> reminder time)
DEFAULT_SCHEDULE = {
    "hydrate-wake": "07:00",
    "bright-light": "08:00",
    "morning-supps": "08:30",
    "protein-breakfast": "09:00",
    "morning-hygiene": "08:00",
    "stability": "10:00",
    "zone2": "10:00",
    "strength": "10:00",
    "vo2max": "10:00",
    "hydrate-3l": "17:00",
    "protein-target": "18:00",
    "nature": "19:00",
    "protein-dinner": "20:00",
    "evening-walk": "21:00",
    "mindfulness": "21:30",
    "evening-hygiene": "22:00",
    "screens-off": "22:30",
    "sleep-7-9": "23:00",
    "no-alcohol": "21:00",
    "no-sugar": "20:00",
    "healthy-fats": "20:00",
    "fermented": "20:00",
}

def load_schedule():
    """Load reminder schedule."""
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE) as f:
            return json.load(f)
    return DEFAULT_SCHEDULE

def load_sent():
    """Load already-sent reminders for today."""
    today = date.today().isoformat()
    if SENT_FILE.exists():
        with open(SENT_FILE) as f:
            data = json.load(f)
            if data.get("date") == today:
                return set(data.get("sent", []))
    return set()

def save_sent(sent):
    """Save sent reminders."""
    SENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SENT_FILE, "w") as f:
        json.dump({"date": date.today().isoformat(), "sent": list(sent)}, f)

def get_habits():
    """Fetch habits from local JSON."""
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            data = json.load(f)
            return data.get("habits", [])
    return []

def get_completions():
    """Get today's completions."""
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            data = json.load(f)
            return data.get("completions", {})
    return {}

def is_habit_complete(habit_id):
    """Check if habit is completed today (in completions and count > 0)."""
    completions = get_completions()
    today = date.today().isoformat()
    
    # Check if there's a completion entry for today
    if today in completions:
        return habit_id in completions[today] and completions[today][habit_id] > 0
    return False

def get_incomplete_habits_due_now():
    """Get habits that need reminders right now."""
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    
    schedule = load_schedule()
    sent = load_sent()
    habits = get_habits()
    
    reminders = []
    
    for habit in habits:
        habit_id = habit.get("habit_id")
        if not habit_id or habit_id not in schedule:
            continue
        
        # Skip if already reminded today
        if habit_id in sent:
            continue
        
        # Check if it's time to remind
        remind_time = schedule[habit_id]
        if current_time < remind_time:
            continue  # Too early
        
        # Check if habit is already completed today
        if is_habit_complete(habit_id):
            continue  # Already completed
        
        reminders.append(habit)
        sent.add(habit_id)
    
    save_sent(sent)
    return reminders

if __name__ == "__main__":
    reminders = get_incomplete_habits_due_now()
    
    # Output as JSON for the agent to process
    output = {
        "current_time": datetime.now().strftime("%H:%M"),
        "reminders_count": len(reminders),
        "reminders": reminders
    }
    print(json.dumps(output))
