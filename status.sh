#!/bin/bash

echo "🖥️  Routine Tracker Status"
echo "=========================="
echo ""

# Check backend
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Backend: RUNNING on http://localhost:8000"
else
    echo "❌ Backend: STOPPED"
fi

# Check frontend (static server)
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "✅ Frontend: RUNNING on http://localhost:8080"
else
    echo "❌ Frontend: STOPPED"
fi

# Check tmux session
if tmux has-session -t "routine-backend" 2>/dev/null; then
    echo "✅ Tmux Session: ACTIVE (routine-backend)"
else
    echo "❌ Tmux Session: NOT FOUND"
fi

echo ""
echo "Commands:"
echo "  ./start-backend.sh    - Start backend (persistent)"
echo "  ./start.sh            - Start everything with DB setup"
echo "  ./monitor.sh          - Auto-restart monitor"
echo "  tmux attach -t routine-backend  - View backend logs"
echo "  tmux kill-session -t routine-backend  - Stop backend"
