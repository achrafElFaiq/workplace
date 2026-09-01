#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "  [..] Setting up email-reader..."

# Install dependencies
cd "$DIR"
uv sync
echo "  [ok] Dependencies installed"

# Symlink .env from job-tracker (shared credentials)
if [ ! -f "$DIR/.env" ]; then
    if [ -f "$DIR/../job-tracker/.env" ]; then
        ln -sf "../job-tracker/.env" "$DIR/.env"
        echo "  [ok] .env linked from job-tracker"
    else
        echo "  [!] No .env found — create $DIR/.env with:"
        echo "      OPENROUTER_API_KEY=sk-or-v1-..."
        echo "      OPENROUTER_MODEL=google/gemini-2.5-flash"
        echo "      GMAIL_1_ADDRESS=your@gmail.com"
        echo "      GMAIL_1_APP_PASSWORD=xxxx xxxx xxxx xxxx"
    fi
fi

# Create data dirs
mkdir -p "$DIR/data/syncs"
echo "  [ok] Data directories ready"

echo "  [ok] Setup complete — run ./run.sh to start"
