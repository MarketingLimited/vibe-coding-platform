# Project Manager Service

Container orchestration service responsible for managing the lifecycle of project containers, executing commands, and handling git operations.

## Overview

- **Technology**: Python 3.11 + FastAPI + Docker SDK 7.0.0
- **Port**: 9400 (internal only)
- **Network**: vibe-network (internal Docker network)

## Key Features

- 🐳 **Container Lifecycle**: Create, start, stop, delete Docker containers
- 📁 **Workspace Management**: Prepare workspaces and copy templates
- ⚡ **Command Execution**: Run shell commands inside project containers
- 🔧 **Git Operations**: Commit, log, reset inside containers
- 🔄 **State Synchronization**: Sync container status to Redis
- 🔐 **Secret Sync**: Copy GitHub credentials to containers
- 🌐 **Router Registry**: Register containers with Traefik for dynamic routing

## Quick Start

### Development Mode

```bash
cd project-manager
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export PROJECT_MANAGER_PORT=9400
export REDIS_HOST=localhost
export PROJECTS_DIR=/tmp/test-projects
export TEMPLATES_DIR=../projects/templates/default

uvicorn app.main:app --reload --port 9400
```

### Production Mode (Docker)

```bash
docker build -t vibe-coding/project-manager:latest ./project-manager
docker run -d \
  --name vibe-project-manager \
  --network vibe-network \
  -p 9400:9400 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /srv/vibe/projects:/projects \
  -v /srv/vibe/logs:/logs \
  -e REDIS_HOST=redis \
  vibe-coding/project-manager:latest
```

## Internal API Endpoints

| Method | Path | Description | Called By |
|--------|------|-------------|-----------|
| POST | `/internal/projects` | Create project container | Central API |
| GET | `/internal/projects/{id}` | Get project status | Central API |
| DELETE | `/internal/projects/{id}` | Delete project container | Central API |
| POST | `/internal/projects/{id}/exec` | Execute command | Central API |
| POST | `/internal/projects/{id}/git/commit` | Git commit | Central API |
| POST | `/internal/projects/{id}/git/log` | Git log | Central API |
| POST | `/internal/projects/{id}/git/reset` | Git reset | Central API |
| GET | `/health` | Health check | Central API |

## Supported Project Types

Project images are located in `templates/images/`:

- **Python**: Python 3.11-slim with pip, git, development tools
- **Node.js**: Node.js 20 with npm, git, build tools
- **PHP**: PHP 8.2 with composer, git, web server tools
- **Full**: Full-stack with Python, Node.js, databases

## Container Creation Flow

1. Prepare workspace directory
2. Copy template files from `/projects/templates/default`
3. Create Docker container with project-specific image
4. Start container
5. Sync secrets (GitHub CLI configuration)
6. Update Redis state
7. Register with Traefik router (if enabled)

## Testing Internal Endpoints

```bash
# Health check
curl http://localhost:9400/health

# Create project
curl -X POST http://localhost:9400/internal/projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "alice-test",
    "username": "alice",
    "project_type": "python",
    "database": "none",
    "redis": false,
    "secrets": {"github_api_key": "ghp_test123"}
  }'

# Execute command
curl -X POST http://localhost:9400/internal/projects/alice-test/exec \
  -H "Content-Type: application/json" \
  -d '{"cmd": "ls -la /workspace", "cwd": "/workspace", "timeout": 30}'

# Delete project
curl -X DELETE http://localhost:9400/internal/projects/alice-test
```

## Building Project Images

```bash
# Build all project type images
bash tools/build-project-images.sh

# Build specific image
cd project-manager/templates/images/python
docker build -t vibe-project-python:latest .

# Verify images
docker images | grep vibe-project
```

## Architecture

```
Project Manager
    ├─→ Docker Engine (/var/run/docker.sock) - Container operations
    ├─→ Redis (TCP:6379) - State synchronization
    ├─→ File System (/projects, /templates) - Workspaces and templates
    └─→ Traefik (optional) - Dynamic routing
```

## Configuration

Key environment variables:

- `PROJECT_MANAGER_PORT` - Service port (default: 9400)
- `DOCKER_NETWORK` - Docker network name (default: vibe-network)
- `PROJECTS_DIR` - Workspace root directory
- `TEMPLATES_DIR` - Template files directory
- `PROJECT_CPU_LIMIT` - CPU cores per project (default: 2.0)
- `PROJECT_MEMORY_LIMIT` - RAM per project (default: 4G)
- `EXEC_TIMEOUT` - Command timeout in seconds (default: 300)
- `MAX_OUTPUT_SIZE` - Max command output size (default: 10MB)

## Key Files

- `app/main.py` - FastAPI application entry point
- `app/services/__init__.py` - ProjectManager class
- `app/services/secret_sync.py` - GitHub CLI configuration sync
- `app/services/router_registry.py` - Traefik integration
- `app/models.py` - Request/response models
- `templates/images/` - Project type Dockerfiles

## Container Monitoring

The service runs a background monitoring loop every `HEALTH_POLL_INTERVAL` seconds (default: 30) to:
- Check container status
- Update Redis state
- Sync last_seen timestamps

## Adding a New Project Type

1. Create Dockerfile in `templates/images/{type}/`
2. Build image: `docker build -t vibe-project-{type}:latest .`
3. Update validation in Central API models
4. Test creation via API

## Safety Notes

⚠️ **Important Warnings**:
- Docker socket write access is required
- Container names must be unique (format: `vibe-{project_id}`)
- Volume mount permissions: containers run as uid=1000
- Command output is truncated at `MAX_OUTPUT_SIZE`
- Git reset creates automatic workspace backups

## Documentation

For detailed information, see [agents.md](./agents.md)
