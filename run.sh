#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

PY_BIN="python3.12"
if ! command -v "$PY_BIN" &> /dev/null; then
    PY_BIN="python3"
fi

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment using $PY_BIN..."
    "$PY_BIN" -m venv .venv
fi

source .venv/bin/activate

echo "Checking dependencies..."
pip install -q -r requirements.txt

echo "Starting Disney Infinity Creator..."
python src/main.py "$@"
