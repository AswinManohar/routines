#!/bin/bash

# Routine Tracker Monitor
# Checks if backend is running, restarts if needed

API_URL="http://localhost:8000/api/health"
SESSION_NAME="routine-backend"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

check_backend() {
    curl -s "$API_URL" > /dev/null 2>&1
    return $?
}

restart_backend() {
    echo "$(date): Backend not responding, restarting..."
    
    # Kill existing session if stuck
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    
    # Start fresh
    cd "$SCRIPT_DIR"
    ./start-backend.sh
    
    echo "$(date): Backend restarted"
}

# Main loop
while true; do
    if ! check_backend; then
        restart_backend
    fi
    # Check every 30 seconds
    sleep 30
done
