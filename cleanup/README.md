# Cleanup Service

Automated background service for maintaining platform health by removing inactive projects, truncating logs, and cleaning up orphaned resources.

## Overview

- **Technology**: Python 3.11 + asyncio
- **Port**: None (background service)
- **Execution**: Runs every `CLEANUP_INTERVAL` seconds (default: 24 hours)

## Key Features

- 🗑️ **Inactive Project Removal**: Delete projects inactive for > `MAX_PROJECT_AGE_DAYS`
- 📝 **Log Truncation**: Reduce large log files (> `MAX_LOG_SIZE_MB`)
- 🔧 **Permission Management**: Fix workspace directory permissions
- 🐳 **Orphaned Container Cleanup**: Remove containers without metadata
- 📁 **Orphaned Workspace Cleanup**: Remove directories without Redis entries
- 📨 **Webhook Notifications**: Send cleanup reports

## Quick Start

### Development Mode

```bash
cd cleanup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export REDIS_HOST=localhost
export CLEANUP_INTERVAL=60          # Run every 60 seconds for testing
export MAX_PROJECT_AGE_DAYS=1       # Test with 1 day threshold
export DRY_RUN=true                 # Test mode - no actual deletion

python -m app.main
```

### Production Mode (Docker)

```bash
docker build -t vibe-coding/cleanup:latest ./cleanup
docker run -d \
  --name vibe-cleanup \
  --network vibe-network \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /srv/vibe/projects:/projects \
  -v /srv/vibe/logs:/logs \
  -e REDIS_HOST=redis \
  -e CLEANUP_INTERVAL=86400 \
  -e MAX_PROJECT_AGE_DAYS=30 \
  vibe-coding/cleanup:latest
```

## Cleanup Operations

### 1. Inactive Project Removal
Removes projects that haven't been accessed in `MAX_PROJECT_AGE_DAYS`:
- Deletes Docker container
- Removes workspace directory
- Cleans up Redis keys

### 2. Log Truncation
For logs > `MAX_LOG_SIZE_MB`:
- Keeps last 1000 lines
- Appends truncation notice

### 3. Permission Fixing
Ensures workspace directories have correct permissions (755)

### 4. Orphaned Container Cleanup
Removes containers with `com.vibe.project-id` label but no Redis metadata

### 5. Orphaned Workspace Cleanup
Removes workspace directories without corresponding Redis entries

## Configuration

Key environment variables:

- `CLEANUP_INTERVAL` - Seconds between cleanup cycles (default: 86400 = 24h)
- `MAX_PROJECT_AGE_DAYS` - Inactive threshold (default: 30)
- `MAX_LOG_SIZE_MB` - Log truncation threshold (default: 100)
- `DRY_RUN` - If true, log actions without executing (default: false)
- `domain_events_webhook` - URL for cleanup reports (optional)

## Manual Cleanup Trigger

```bash
# Run cleanup immediately
docker exec vibe-cleanup python -c "
from app.service import CleanupService
import asyncio

async def run():
    service = CleanupService()
    result = await service.run_cleanup_cycle()
    print(f'Cleanup result: {result}')

asyncio.run(run())
"
```

## Testing with DRY_RUN

Enable `DRY_RUN=true` to see what would be deleted without actually deleting:

```bash
export DRY_RUN=true
python -m app.main
tail -f /logs/cleanup.log
```

## Architecture

```
Cleanup Service
    ├─→ Redis (TCP:6379) - Read project metadata
    ├─→ Docker Engine (/var/run/docker.sock) - Container cleanup
    ├─→ File System (/projects, /logs) - Workspace and log cleanup
    └─→ Webhook URL (optional) - Cleanup reports
```

## Key Files

- `app/main.py` - Event loop entry point
- `app/service.py` - CleanupService class
- `app/config.py` - Configuration settings

## Safety Notes

⚠️ **Important Warnings**:
- With `DRY_RUN=true`: Nothing is actually deleted (testing mode)
- Workspace deletion is **permanent** - files cannot be recovered
- Docker socket access is required (mount `/var/run/docker.sock`)
- All timestamps use UTC timezone

## Documentation

For detailed information, see [agents.md](./agents.md)
