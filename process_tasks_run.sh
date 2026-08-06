#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
source equb_venv/bin/activate
export $(grep -v '^#' Equb/.env | xargs)
python3 Equb/manage.py process_tasks
