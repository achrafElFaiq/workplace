#!/bin/bash
WORKSPACE_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_DIR="$WORKSPACE_DIR/tools"
PID_DIR="$WORKSPACE_DIR/.pids"
LOG_DIR="$WORKSPACE_DIR/logs"
TODAY=$(date +%Y-%m-%d)
mkdir -p "$PID_DIR"

# Clean logs older than 3 days
find "$LOG_DIR" -name '*.log' -mtime +3 -delete 2>/dev/null

echo "  [..] Stopping previous services..."
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid=$(cat "$pidfile")
    kill "$pid" 2>/dev/null
    rm -f "$pidfile"
done

# Free known ports
for port in 8500 8501 8502 8503 8504 8505 8506 8507 8508 8509; do
    pid=$(lsof -ti tcp:$port 2>/dev/null)
    [ -n "$pid" ] && kill $pid 2>/dev/null
done
sleep 2

echo "  [..] Discovering tools..."

# Simple YAML field reader (no python dependency)
yaml_get() {
    grep "^${2}:" "$1" 2>/dev/null | sed "s/^${2}: *//" | tr -d '"' | tr -d "'"
}

PORT=8501
for manifest in "$TOOLS_DIR"/*/tool.yaml; do
    [ -f "$manifest" ] || continue
    tool_dir=$(basename "$(dirname "$manifest")")
    slug=$(yaml_get "$manifest" "slug")
    tool_type=$(yaml_get "$manifest" "type")
    tool_name=$(yaml_get "$manifest" "name")

    [ -z "$slug" ] && continue
    [ -z "$tool_type" ] && tool_type="streamlit"
    [ -z "$tool_name" ] && tool_name="$slug"

    # Get port from config.yaml by matching the tool directory name
    cfg_port=$(grep -A4 "path:.*/${tool_dir}$" "$WORKSPACE_DIR/config.yaml" 2>/dev/null \
        | grep "port:" | head -1 | sed 's/.*port: *//')
    if [ -n "$cfg_port" ]; then
        tool_port=$cfg_port
    else
        tool_port=$PORT
        PORT=$((PORT + 1))
    fi

    tool_log_dir="$LOG_DIR/$slug"
    mkdir -p "$tool_log_dir"
    if [ "$tool_type" = "streamlit" ]; then
        (cd "$TOOLS_DIR/$tool_dir" && uv run streamlit run app.py --server.port "$tool_port" --server.headless true) >> "$tool_log_dir/$TODAY.log" 2>&1 &
    else
        (cd "$TOOLS_DIR/$tool_dir" && PYTHONUNBUFFERED=1 PORT="$tool_port" uv run python app.py) >> "$tool_log_dir/$TODAY.log" 2>&1 &
    fi
    echo $! > "$PID_DIR/$slug.pid"; disown $!
    printf "  [ok] %-18s -> http://localhost:%s\n" "$tool_name" "$tool_port"
done

# MCP Server (background)
cd "$WORKSPACE_DIR"
mkdir -p "$LOG_DIR/mcp"
MCP_PORT=8510 PYTHONUNBUFFERED=1 uv run python mcp_server.py >> "$LOG_DIR/mcp/$TODAY.log" 2>&1 &
echo $! > "$PID_DIR/mcp.pid"; disown $!
echo "  [ok] MCP Server         -> http://localhost:8510"

# Portal (foreground)
mkdir -p "$LOG_DIR/portal"
echo "  [ok] Portal             -> http://localhost:8500"
PYTHONUNBUFFERED=1 PORT=8500 uv run python portal.py 2>&1 | tee -a "$LOG_DIR/portal/$TODAY.log"

# Portal exited — clean up
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    kill "$(cat "$pidfile")" 2>/dev/null
    rm -f "$pidfile"
done
