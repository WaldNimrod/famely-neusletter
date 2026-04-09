#!/bin/bash
set -e

# Famely Neuslettr — Runner Script
# Usage: ./run.sh daily-build | daily-send | daily-survey | health-check

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Load .env if it exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Run the command
python3 -m src.orchestrator "$@" 2>&1 | tee -a logs/famely-$(date +%Y-%m-%d).log
