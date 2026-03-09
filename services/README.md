
## Architecture
Microservice structure built with FastAPI, Django REST Framework, PostgreSQL, Redis, Celery, and WebSockets — orchestrated with Docker Compose and Nginx.
```
Client
  │
  ▼
Nginx (port 80) ← single entry point, rate limiting, routing
  ├── /api/auth/*          → User Service    (FastAPI  :8001)
  ├── /api/users/*         → User Service    (FastAPI  :8001)
  ├── /api/tasks/*         → Task Service    (Django   :8002)
  ├── /api/categories/*    → Task Service    (Django   :8002)
  ├── /api/notifications/* → Notif Service   (FastAPI  :8003)
  ├── /api/ws              → Notif Service   (WebSocket)
  └── /api/analytics/*     → Analytics Svc  (FastAPI  :8004)
```

## Installation

```sh
# 1. Clone and enter the project
git clone <your-repo> taskforge && cd taskforge

# 2. Set up environment
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET_KEY and POSTGRES_PASSWORD

# 3. Build and start
make build
make up

# 4. Run Django migrations
make migrate

# 5. Check everything is healthy
make health
```

## Services

| Service | Framework | Port | Swagger UI |
|---|---|---|---|
| User Service | FastAPI | :8001 (internal) | `/api/docs` |
| Task Service | Django REST | :8002 (internal) | `/api/tasks/docs/` |
| Notification Service | FastAPI | :8003 (internal) | `/api/docs` |
| Analytics Service | FastAPI | :8004 (internal) | `/api/docs` |
| Frontend Service | Vite + React | :3000 (internal) | `/` |

All services are accessed via Nginx on **port 80** in Docker.

## Docker 
