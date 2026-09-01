#!/bin/bash
WORKSPACE_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_DIR="$WORKSPACE_DIR/tools"
PID_DIR="$WORKSPACE_DIR/.pids"
mkdir -p "$PID_DIR"

echo "  [..] Arrêt des services précédents..."
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile")
    kill "$pid" 2>/dev/null
    rm -f "$pidfile"
done

# Free the workspace ports regardless (catches orphaned processes)
for port in 8500 8501 8502 8503 8505; do
    pid=$(lsof -ti tcp:$port 2>/dev/null)
    [ -n "$pid" ] && kill $pid 2>/dev/null
done

sleep 2

echo "  [..] Lancement du workspace..."

(cd "$TOOLS_DIR/job-tracker" && uv run streamlit run app.py --server.port 8501 --server.headless true) &
echo $! > "$PID_DIR/job-tracker.pid"; disown $!
echo "  [ok] Job Tracker    -> http://localhost:8501"

(cd "$TOOLS_DIR/todolist" && python3 -m http.server 8502 2>/dev/null) &
echo $! > "$PID_DIR/todolist.pid"; disown $!
echo "  [ok] To Do List     -> http://localhost:8502/dashboard.html"

(cd "$TOOLS_DIR/email-reader" && uv run streamlit run app.py --server.port 8503 --server.headless true) &
echo $! > "$PID_DIR/email-reader.pid"; disown $!
echo "  [ok] Email Reader   -> http://localhost:8503"

(cd "$TOOLS_DIR/calendar" && uv run streamlit run app.py --server.port 8505 --server.headless true) &
echo $! > "$PID_DIR/calendar.pid"; disown $!
echo "  [ok] Calendar       -> http://localhost:8505"

cd "$WORKSPACE_DIR"
echo "  [ok] Portal         -> http://localhost:8500"
uv run streamlit run portal.py --server.port 8500

# Portal exited — clean up background services
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile")
    kill "$pid" 2>/dev/null
    rm -f "$pidfile"
done
