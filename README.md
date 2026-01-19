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
- Background task processor

## Related

- **Frontend:** [equb_v3_frontend](https://github.com/biruk-chafamo/equb_v3_frontend)
