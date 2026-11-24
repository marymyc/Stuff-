#!/usr/bin/env bash
# One-time setup on macOS / Linux. Needs Node 18+, Python 3.9+ and ffmpeg already installed.
set -e
cd "$(dirname "$0")"
npm install
python3 -m pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
python3 tools/check_env.py || true
echo "Next: add the Kenney props (public/bridge/kenney/README.md) and choose a voice engine in .env"
