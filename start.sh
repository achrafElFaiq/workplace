#!/bin/bash
# Start MCP server in background, portal in foreground
uv run python mcp_server.py &
MCP_PID=$!
echo "  [ok] MCP server         -> port ${MCP_PORT:-8510}"

echo "  [ok] Portal             -> port ${PORT:-8501}"
uv run python portal.py

kill $MCP_PID 2>/dev/null
