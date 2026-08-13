# Backend tests

## Run the tests

To run all tests:

```bash
./scripts/run_tests.sh
```

One folder or one file:

```bash
./scripts/run_tests.sh moneypool/tests/[[folder or file path]]
```

The script starts the two Docker containers it needs. To create them when
absent:

```bash
set -a; source .env; set +a

docker run -d --name equb-test-pg -p 5433:5432 \
  -e POSTGRES_DB="$POSTGRES_DB" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  postgres:16

docker run -d --name equb-test-redis -p 6379:6379 redis:7-alpine
```

## Run the backend to test manually

```bash
source equb_venv/bin/activate
POSTGRES_HOST=localhost REDIS_URL=redis://localhost:6379
# seeding data for reproducible testing data
python3 manage.py seed_dev          # --list to describe, --reset to remove
python3 manage.py runserver 0.0.0.0:8000
```

Every seeded account uses the password `equbtest123`. `alice` belongs to every seeded equb group, so use her account.

## Pre-deploy check

```bash
python3 manage.py check
python3 manage.py makemigrations --check --dry-run    # must say "No changes detected"
```

## Tests in the CI pipeline

`.github/workflows/backend-tests.yml`, on every pull request and every push to
`main`. It starts a fresh Postgres and Redis, installs `requirements.txt` and
`requirements-dev.txt`, then runs the full suite with a coverage report.

Pushing to main will autodeploy to Heroku.
