#!/usr/bin/env bash
# Runs the backend test suite. Arguments are passed through to pytest:
#   ./scripts/run_tests.sh moneypool/tests/settlement -q
set -euo pipefail
cd "$(dirname "$0")/.."

# 5433 is the test database container. Development uses 5432, so tests never
# touch development data.
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export REDIS_URL=redis://localhost:6379

for container in equb-test-pg equb-test-redis; do
  if [ -n "$(docker ps -q -f "name=^${container}$")" ]; then
    echo "==> $container found"
    continue
  fi

  if [ -n "$(docker ps -aq -f "name=^${container}$")" ]; then
    echo "==> Starting $container"
    docker start "$container" >/dev/null
  else
    echo "The container $container does not exist yet."
    echo "See moneypool/tests/README.md for the command that creates it."
    exit 1
  fi
done

until docker exec equb-test-pg pg_isready -q 2>/dev/null; do
  sleep 1
done

exec equb_venv/bin/python3 -m pytest "$@"
