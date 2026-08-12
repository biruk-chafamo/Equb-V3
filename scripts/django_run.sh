#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
source equb_venv/bin/activate
export $(grep -v '^#' .env | xargs)
python3 manage.py runserver 0.0.0.0:8000
