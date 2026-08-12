#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
source equb_venv/bin/activate
export $(grep -v '^#' .env | xargs)
python3 manage.py process_tasks
