#!/bin/bash
cd "$(dirname "$0")"
uv run streamlit run app.py --server.port 8505 --server.headless true
