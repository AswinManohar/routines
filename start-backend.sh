#!/bin/bash

# Routine Tracker Backend - Persistent Runner
# Keeps the backend running in a tmux session

SESSION_NAME="routine-backend"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR/backend"

# Function to start the backend
start_backend() {
    echo "🚀 Starting Routine Tracker Backend..."
    
    # Create virtual environment if needed
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        source venv/bin/activate
        pip install -q -r requirements.txt
    else
        source venv/bin/activate
    fi
    
    # Run uvicorn with auto-reload
    export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/routine_tracker"
    exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir .
}

# Check if tmux session exists
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "⚠️  Backend is already running in tmux session: $SESSION_NAME"
    echo "   Attach: tmux attach -t $SESSION_NAME"
    echo "   View logs: tmux capture-pane -t $SESSION_NAME -p"
    exit 0
fi

# Create new tmux session and run backend
echo "Creating tmux session: $SESSION_NAME"
tmux new-session -d -s "$SESSION_NAME" -n "backend" "$(readlink -f "$0")" internal

echo "✅ Backend started in tmux session: $SESSION_NAME"
echo ""
echo "Commands:"
echo "  View logs:  tmux attach -t $SESSION_NAME"
echo "  Detach:     Ctrl+B, then D"
echo "  Stop:       tmux kill-session -t $SESSION_NAME"
echo "  Status:     tmux ls"
echo ""
echo "API: http://localhost:8000"
echo "App: http://localhost:8080"

# If called with 'internal' argument, start the backend
if [ "$1" = "internal" ]; then
    start_backend
fi
