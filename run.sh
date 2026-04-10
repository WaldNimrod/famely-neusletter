#!/bin/bash
set -e

# Family Newsletter — Runner Script
# Usage: ./run.sh weekly-build | weekly-send | weekly-survey | health-check
# Note: daily-build/send/survey still work as backward-compat aliases.

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
python3 -m src.orchestrator "$@" 2>&1 | tee -a logs/newsletter-$(date +%Y-%m-%d).log
