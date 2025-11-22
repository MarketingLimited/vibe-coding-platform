# Setup Tools

Installation and configuration scripts for the VIBE Coding Platform.

## Overview

This directory contains tools and scripts for:
- Platform installation and setup
- Environment configuration
- Dependency installation
- Service initialization
- Database setup

## Files

- `install.sh` - Main installation script
- `setup-env.sh` - Environment variable configuration
- `init-database.sh` - Database initialization
- `build-images.sh` - Build Docker images
- `configure-services.sh` - Configure platform services

## Quick Installation

### One-Command Install

```bash
cd tools/setup
./install.sh
```

This will:
1. Check system requirements
2. Install dependencies
3. Configure environment
4. Build Docker images
5. Initialize database
6. Start services

### Custom Installation

Run individual setup steps:

```bash
# 1. Setup environment
./setup-env.sh

# 2. Build images
./build-images.sh

# 3. Initialize database
./init-database.sh

# 4. Configure services
./configure-services.sh
```

## System Requirements

### Required Software

- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **Python**: 3.11 or higher
- **Git**: 2.30 or higher

### Recommended Hardware

- **CPU**: 4+ cores
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB+ available space
- **Network**: Stable internet connection

### Operating System

Supported platforms:
- Ubuntu 20.04+ / Debian 11+
- CentOS 8+ / RHEL 8+
- macOS 11+
- Windows 10+ with WSL2

## Installation Steps

### 1. Check Requirements

```bash
./install.sh --check-only
```

Verifies:
- Docker installed and running
- Docker Compose available
- Python version
- Available disk space
- Network connectivity

### 2. Environment Setup

```bash
./setup-env.sh
```

Creates:
- `/config/.env` - Main configuration file
- API keys and secrets
- Database paths
- Service URLs

### 3. Build Docker Images

```bash
./build-images.sh
```

Builds:
- Central API image
- Project Manager image
- Cleanup Service image
- Project type images (python, nodejs, php, full)

### 4. Initialize Database

```bash
./init-database.sh
```

Creates:
- SQLite database file
- Database schema
- Initial migrations
- Admin user (optional)

### 5. Start Services

```bash
docker-compose up -d
```

Starts:
- Redis
- Central API
- Project Manager
- Cleanup Service
- Traefik (if configured)

## Configuration

### Environment Variables

Edit `/config/.env` to configure:

```bash
# API Settings
API_KEY=your-secure-api-key
API_PORT=9000
DOMAIN=localhost
API_PUBLIC_BASE_URL=http://localhost:9000

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Database
DB_PATH=/data/projects.db

# Project Manager
PROJECT_MANAGER_HOST=project-manager
PROJECT_MANAGER_PORT=9400

# Resource Limits
MAX_PROJECTS_PER_USER=10
PROJECT_CPU_LIMIT=2.0
PROJECT_MEMORY_LIMIT=4G

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
EXEC_RATE_LIMIT_PER_MINUTE=60

# Cleanup
CLEANUP_INTERVAL=86400
MAX_PROJECT_AGE_DAYS=30

# Security
GITHUB_SECRETS_KEY=your-fernet-key
```

### Generating Secrets

```bash
# Generate API key
openssl rand -hex 32

# Generate Fernet key for secrets encryption
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Installation Modes

### Development Mode

```bash
./install.sh --mode=dev
```

Features:
- Hot reload enabled
- Debug logging
- Local Redis
- In-memory database
- No resource limits

### Production Mode

```bash
./install.sh --mode=production
```

Features:
- Optimized builds
- Resource limits enforced
- Log rotation configured
- Persistent storage
- Security hardening

### Testing Mode

```bash
./install.sh --mode=test
```

Features:
- Fake Redis (fakeredis)
- Temporary database
- Mock external services
- No network requirements

## Verification

### Check Installation

```bash
# Check all services running
docker-compose ps

# Check API health
curl http://localhost:9000/health

# Check Project Manager health
curl http://localhost:9400/health

# Check Redis
redis-cli ping
```

### Run Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run test suite
pytest tests/ -v

# Run smoke tests
./tools/setup/smoke-test.sh
```

## Troubleshooting

### Docker Permission Error

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Port Already in Use

```bash
# Change ports in /config/.env
API_PORT=9001
PROJECT_MANAGER_PORT=9401

# Restart services
docker-compose down
docker-compose up -d
```

### Database Initialization Failed

```bash
# Remove existing database
rm /data/projects.db

# Re-initialize
./init-database.sh
```

### Build Errors

```bash
# Clean Docker cache
docker system prune -a

# Rebuild images
./build-images.sh --no-cache
```

### Redis Connection Error

```bash
# Check Redis running
docker ps | grep redis

# Check Redis logs
docker logs vibe-redis

# Restart Redis
docker-compose restart redis
```

## Uninstallation

### Remove Services

```bash
# Stop all services
docker-compose down

# Remove containers and volumes
docker-compose down -v

# Remove images
docker rmi $(docker images 'vibe-*' -q)
```

### Clean Up Data

```bash
# Remove databases
rm -rf /srv/vibe/data

# Remove logs
rm -rf /srv/vibe/logs

# Remove projects
rm -rf /srv/vibe/projects

# Remove configuration
rm /config/.env
```

## Upgrade

### Upgrade to Latest Version

```bash
# Pull latest code
git pull origin main

# Rebuild images
./build-images.sh

# Run migrations
./tools/setup/migrate.sh

# Restart services
docker-compose restart
```

## Advanced Configuration

### Custom Database Path

```bash
export DB_PATH=/custom/path/projects.db
./init-database.sh
```

### Custom Docker Network

```bash
export DOCKER_NETWORK=my-custom-network
docker network create $DOCKER_NETWORK
docker-compose up -d
```

### Enable Traefik Routing

```bash
export ENABLE_TRAEFIK=true
export DOMAIN=example.com
./configure-services.sh
docker-compose -f docker-compose.yml -f docker-compose.traefik.yml up -d
```

## Backup and Restore

### Backup

```bash
./tools/setup/backup.sh
# Creates: /backups/vibe-backup-{timestamp}.tar.gz
```

### Restore

```bash
./tools/setup/restore.sh /backups/vibe-backup-{timestamp}.tar.gz
```

## Documentation

For platform architecture and design, see the main [README](../../README.md)
