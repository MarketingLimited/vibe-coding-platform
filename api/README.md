# Central API Service

The Central API Service is the main entry point for the VIBE Coding Platform. It provides HTTP endpoints for project management, command execution, and git operations.

## Overview

- **Technology**: Python 3.11 + FastAPI 0.110.0 + Uvicorn
- **Port**: 9000 (configurable via `API_PORT`)
- **Purpose**: Authentication, rate limiting, project CRUD, command proxy

## Key Features

- 🔐 **Authentication**: API key verification and project password validation
- 🚦 **Rate Limiting**: Redis-backed request throttling
- 📦 **Project Management**: Create, read, update, delete projects
- ⚡ **Command Execution**: Proxy commands to Project Manager
- 🔧 **Git Operations**: Commit, log, reset via Project Manager
- 📊 **Health Monitoring**: Health checks and Prometheus metrics

## Quick Start

### Development Mode

```bash
cd api
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export API_KEY="test-api-key"
export GITHUB_SECRETS_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
export REDIS_HOST="localhost"
export DB_PATH="/tmp/test-projects.db"

uvicorn app.main:app --reload --port 9000
```

### Production Mode (Docker)

```bash
docker build -t vibe-coding/api:latest ./api
docker run -d \
  --name vibe-api \
  --network vibe-network \
  -p 9000:9000 \
  -v /srv/vibe/data:/data \
  -v /srv/vibe/logs:/logs \
  -e API_KEY="your-secure-key" \
  -e GITHUB_SECRETS_KEY="your-fernet-key" \
  vibe-coding/api:latest
```

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/projects/create` | Create new project | X-API-Key |
| GET | `/projects/{username}` | List user projects | X-API-Key |
| POST | `/projects/info` | Get project info | Password |
| DELETE | `/projects/delete` | Delete project | Password |
| POST | `/exec` | Execute shell command | Password |
| POST | `/git/commit` | Create git commit | Password |
| GET | `/health` | Basic health check | None |
| GET | `/metrics` | Prometheus metrics | None |

## Architecture

```
Central API
    ├─→ Project Manager (HTTP:9400) - Container operations
    ├─→ Redis (TCP:6379) - Caching & rate limiting
    └─→ SQLite (/data/projects.db) - Persistent storage
```

## Key Files

- `app/main.py` - FastAPI application entry point
- `app/routers/` - HTTP route handlers
- `app/services/` - Business logic layer
- `app/models/` - Request/response models
- `app/config.py` - Configuration settings

## Testing

```bash
# Health check
curl http://localhost:9000/health

# Create project
curl -X POST http://localhost:9000/projects/create \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "project_name": "my-app", "project_type": "python"}'

# Execute command
curl -X POST http://localhost:9000/exec \
  -H "Content-Type: application/json" \
  -d '{"project_id": "alice-my-app", "password": "pwd", "cmd": "python --version"}'
```

## Configuration

Key environment variables:

- `API_KEY` - Master API key (required)
- `GITHUB_SECRETS_KEY` - Fernet encryption key (required)
- `REDIS_HOST` - Redis server hostname
- `PROJECT_MANAGER_HOST` - Project Manager service hostname
- `RATE_LIMIT_PER_MINUTE` - General rate limit (default: 100)
- `MAX_PROJECTS_PER_USER` - Project quota (default: 10)

## Documentation

For detailed information, see [agents.md](./agents.md)
