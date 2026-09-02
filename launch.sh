#!/bin/bash
WORKSPACE_DIR="$(cd "$(dirname "$0")" && pwd)"
TOOLS_DIR="$WORKSPACE_DIR/tools"
PID_DIR="$WORKSPACE_DIR/.pids"
mkdir -p "$PID_DIR"

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

    if [ "$tool_type" = "streamlit" ]; then
        (cd "$TOOLS_DIR/$tool_dir" && uv run streamlit run app.py --server.port "$tool_port" --server.headless true) &
    else
        (cd "$TOOLS_DIR/$tool_dir" && PORT="$tool_port" uv run python app.py) &
    fi
    echo $! > "$PID_DIR/$slug.pid"; disown $!
    printf "  [ok] %-18s -> http://localhost:%s\n" "$tool_name" "$tool_port"
done

# Portal (foreground)
cd "$WORKSPACE_DIR"
echo "  [ok] Portal             -> http://localhost:8500"
PORT=8500 uv run python portal.py

# Portal exited — clean up
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    kill "$(cat "$pidfile")" 2>/dev/null
    rm -f "$pidfile"
done
