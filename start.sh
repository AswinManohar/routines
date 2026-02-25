#!/bin/bash

# Routine Tracker Startup Script
# Starts PostgreSQL (if needed), initializes DB, starts FastAPI backend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Routine Tracker Backend..."

# Check if PostgreSQL is running
if ! pg_isready -q 2>/dev/null; then
    echo "⚠️  PostgreSQL doesn't seem to be running. Please start it:"
    echo "   sudo service postgresql start"
    echo "   or"
    echo "   sudo systemctl start postgresql"
    exit 1
fi

# Create database if it doesn't exist
echo "📊 Checking database..."
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname='routine_tracker'" | grep -q 1 || {
    echo "Creating database..."
    sudo -u postgres psql -c "CREATE DATABASE routine_tracker;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE routine_tracker TO postgres;"
}

# Run schema
echo "🏗️  Setting up schema..."
sudo -u postgres psql -d routine_tracker -f database/schema.sql 2>/dev/null || {
    echo "Schema may already exist, continuing..."
}

# Install Python dependencies if needed
if [ ! -d "backend/venv" ]; then
    echo "📦 Setting up Python environment..."
    python3 -m venv backend/venv
fi

source backend/venv/bin/activate
pip install -q -r backend/requirements.txt

# Start FastAPI server
echo "🌐 Starting API server on http://localhost:8000"
echo "📱 Frontend available at http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd backend
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/routine_tracker"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
