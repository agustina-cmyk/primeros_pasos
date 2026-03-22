#!/bin/bash
set -e
cd "$(dirname "$0")/.."
source "/Users/agusalvarez/Documents/Proyectos Vaas/.venv/bin/activate" 2>/dev/null || source .venv/bin/activate 2>/dev/null || true
python -m pytest tests/ -v "$@"
