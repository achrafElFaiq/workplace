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

# Read tool ports from config.yaml (local dev mode)
get_port() {
    local slug="$1"
    local tool_dir="$2"
    python3 -c "
import yaml, re, sys
def slugify(n): return re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')
try:
    cfg = yaml.safe_load(open('$WORKSPACE_DIR/config.yaml'))
    for t in cfg.get('tools', []):
        s = slugify(t['name'])
        path_dir = t.get('path','').rstrip('/').split('/')[-1]
        if s == '$slug' or path_dir == '$tool_dir':
            url = t['url']
            port = url.split(':')[-1].split('/')[0]
            print(port)
            sys.exit(0)
except: pass
print('')
" 2>/dev/null
}

PORT=8501
for manifest in "$TOOLS_DIR"/*/tool.yaml; do
    [ -f "$manifest" ] || continue
    tool_dir=$(basename "$(dirname "$manifest")")
    slug=$(python3 -c "import yaml; print(yaml.safe_load(open('$manifest')).get('slug',''))" 2>/dev/null)
    tool_type=$(python3 -c "import yaml; print(yaml.safe_load(open('$manifest')).get('type','streamlit'))" 2>/dev/null)
    tool_name=$(python3 -c "import yaml; print(yaml.safe_load(open('$manifest')).get('name','$slug'))" 2>/dev/null)

    [ -z "$slug" ] && continue

    # Get port from config.yaml, or assign next available
    cfg_port=$(get_port "$slug" "$tool_dir")
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
