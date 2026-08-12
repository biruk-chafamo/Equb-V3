# Equb Finance API

Backend REST API for [Equb Finance](https://app.equbfinance.com), a platform for managing rotating savings groups.

**Base URL:** `https://api.equbfinance.com`

## API Endpoints

| Resource              | Endpoint                       | Description                               |
| --------------------- | ------------------------------ | ----------------------------------------- |
| Users                 | `/users/`                      | User registration, profiles, friend lists |
| Equbs                 | `/equbs/`                      | Create and manage savings groups          |
| Bids                  | `/bids/`                       | Place bids to win the current round       |
| Join Requests         | `/equbjoinrequests/`           | Request to join an equb                   |
| Invite Requests       | `/equbinviterequests/`         | Invite users to your equb                 |
| Friend Requests       | `/friendrequests/`             | Send and manage friend requests           |
| Payment Confirmations | `/paymentconfirmationrequest/` | Confirm payments to round winners         |
| Payment Methods       | `/paymentmethods/`             | Manage saved payment accounts             |

## Tech Stack

- Django / Django REST Framework
- PostgreSQL
- Django Channels (WebSocket)
- Redis (channel layer)
- django-background-tasks (scheduled winner selection)
- SimpleJWT (authentication)
- django-guardian (object-level permissions)
- AWS S3 (media storage)

### Docker

```bash
cd Equb
docker-compose up --build
```

This starts:

- Django API server (port 8000)
- PostgreSQL database
- Redis (channel layer backing the WebSocket consumers)
- Background task processor

### Seeding test data

Fills the database with 8 users and 6 equbs covering every lifecycle state
(pending, active, final round, payment stage, completed) plus friendships and
pending requests. Sign in as `alice`; every user's password is `equbtest123`.

```bash
python Equb/manage.py seed_dev          # reset, then rebuild
python Equb/manage.py seed_dev --reset  # wipe seed data
python Equb/manage.py seed_dev --list   # describe the cast, change nothing
```

Re-run any time to get back to a clean state; it only deletes what it created.
Outside Docker, set `POSTGRES_HOST` and `REDIS_URL` (Redis is required — creating
an equb publishes a live update through the channel layer).

## Related

- **Frontend:** [equb_frontend](https://github.com/biruk-chafamo/Equb-Frontend)
