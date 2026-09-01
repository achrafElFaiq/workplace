#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
exec uv run streamlit run app.py --server.port 8503 --server.headless true
