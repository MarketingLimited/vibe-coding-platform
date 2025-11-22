# Cleanup Service - دليل الـAgent

## Purpose

الـ**Cleanup Service** هي خدمة صيانة background تعمل بشكل دوري للحفاظ على صحة المنصة. تُدير:
- **Inactive Project Removal**: حذف المشاريع الغير نشطة (تجاوزت `MAX_PROJECT_AGE_DAYS`)
- **Log Truncation**: تقليص حجم ملفات الـlogs الكبيرة
- **Permission Management**: إصلاح permissions للـworkspaces
- **Orphaned Container Cleanup**: حذف containers بدون metadata
- **Webhook Notifications**: إرسال تقارير عن عمليات الصيانة

**Technology**: Python 3.11 + asyncio

**Port**: لا توجد (background service بدون HTTP API)

**Execution**: Async loop كل `CLEANUP_INTERVAL` ثانية (default: 86400 = 24 ساعة)

---

## Owned Scope

هذه الخدمة تملك:

### Core Service
- `/cleanup/app/service.py` - CleanupService class (main cleanup logic)

### Entry Point
- `/cleanup/app/main.py` - Async event loop + startup

### Configuration
- `/cleanup/app/config.py` - Pydantic Settings

### Infrastructure
- `/cleanup/Dockerfile` - Python 3.11-slim image
- `/cleanup/requirements.txt` - Minimal dependencies

---

## Key Files & Entry Points

### Main Entry Point

```python
# /cleanup/app/main.py
import asyncio
from app.service import CleanupService
from app.config import settings

async def main():
    """Main event loop"""
    cleanup_service = CleanupService()

    logging.info("Cleanup service started")
    logging.info(f"Running cleanup every {settings.CLEANUP_INTERVAL} seconds")

    while True:
        try:
            # Run cleanup cycle
            await cleanup_service.run_cleanup_cycle()

            # Send webhook notification if configured
            if settings.domain_events_webhook:
                await cleanup_service.send_cleanup_report()

        except Exception as e:
            logging.error(f"Cleanup cycle failed: {e}")

        # Wait for next cycle
        await asyncio.sleep(settings.CLEANUP_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
```

**Command**: `python -m app.main`

### Configuration

```python
# /cleanup/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Cleanup Settings
    CLEANUP_INTERVAL: int = 86400          # Run every 24 hours
    MAX_PROJECT_AGE_DAYS: int = 30         # Remove projects inactive for 30 days
    MAX_LOG_SIZE_MB: int = 100             # Truncate logs larger than 100MB

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Docker
    DOCKER_SOCKET: str = "/var/run/docker.sock"

    # Paths
    PROJECTS_DIR: str = "/projects"
    LOGS_DIR: str = "/logs"

    # Webhooks
    domain_events_webhook: Optional[str] = None  # Cleanup report URL

    # Options
    DRY_RUN: bool = False                  # If True, log actions without executing
```

### Cleanup Service Class

```python
# /cleanup/app/service.py
class CleanupService:
    def __init__(self):
        self.redis = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        self.docker_client = docker.from_env()

    async def run_cleanup_cycle(self):
        """Full cleanup cycle"""
        logging.info("=== Starting cleanup cycle ===")

        # 1. Remove inactive projects
        removed_projects = await self._cleanup_inactive_projects()

        # 2. Truncate large logs
        truncated_logs = await self._truncate_large_logs()

        # 3. Fix workspace permissions
        await self._fix_workspace_permissions()

        # 4. Clean orphaned containers
        orphaned = await self._cleanup_orphaned_containers()

        # 5. Clean orphaned workspaces
        orphaned_dirs = await self._cleanup_orphaned_workspaces()

        logging.info(f"Cleanup complete: {len(removed_projects)} projects, "
                    f"{len(truncated_logs)} logs, {len(orphaned)} containers, "
                    f"{len(orphaned_dirs)} workspaces")

        return {
            'removed_projects': removed_projects,
            'truncated_logs': truncated_logs,
            'orphaned_containers': orphaned,
            'orphaned_workspaces': orphaned_dirs
        }
```

---

## Dependencies & Interfaces

### External Dependencies

```
Cleanup Service
    │
    ├─→ Redis (TCP:6379)
    │   └─ Read project metadata (last_seen timestamps)
    │   └─ Delete project keys
    │
    ├─→ Docker Engine (/var/run/docker.sock)
    │   └─ List containers (with vibe labels)
    │   └─ Remove orphaned containers
    │
    ├─→ File System
    │   ├─ /projects/ - Project workspaces (delete inactive)
    │   └─ /logs/ - Service logs (truncate large files)
    │
    └─→ (Optional) Webhook URL
        └─ Send cleanup reports via HTTP POST
```

### Python Package Dependencies

```
# Minimal dependencies
redis==5.0.1
pydantic>=2.6.4,<3
pydantic-settings==2.2.1
httpx==0.27.0            # For webhook notifications
docker==7.0.0            # For container cleanup (optional)
```

File: `/cleanup/requirements.txt`

---

## Local Rules / Patterns

### 1. Inactive Project Detection

```python
async def _cleanup_inactive_projects(self) -> list:
    """
    Remove projects that haven't been accessed in MAX_PROJECT_AGE_DAYS
    """
    removed = []
    cutoff_date = datetime.utcnow() - timedelta(days=settings.MAX_PROJECT_AGE_DAYS)

    # Get all project keys from Redis
    project_keys = self.redis.keys("project:*")

    for key in project_keys:
        # Get last_seen timestamp
        last_seen_str = self.redis.hget(key, 'last_seen')

        if last_seen_str:
            last_seen = datetime.fromisoformat(last_seen_str)

            # Check if inactive
            if last_seen < cutoff_date:
                project_id = key.replace('project:', '')

                if not settings.DRY_RUN:
                    # Delete container
                    await self._delete_project_container(project_id)

                    # Delete workspace
                    await self._delete_workspace(project_id)

                    # Delete Redis keys
                    self.redis.delete(key)
                    username = self.redis.hget(key, 'username')
                    if username:
                        self.redis.srem(f"user:{username}:projects", project_id)

                logging.info(f"Removed inactive project: {project_id}")
                removed.append(project_id)

    return removed
```

**File**: `/cleanup/app/service.py:_cleanup_inactive_projects()`

### 2. Log Truncation

```python
async def _truncate_large_logs(self) -> list:
    """
    Truncate log files larger than MAX_LOG_SIZE_MB
    Keep last 1000 lines
    """
    truncated = []
    max_size_bytes = settings.MAX_LOG_SIZE_MB * 1024 * 1024

    log_files = glob.glob(os.path.join(settings.LOGS_DIR, "*.log"))

    for log_path in log_files:
        file_size = os.path.getsize(log_path)

        if file_size > max_size_bytes:
            if not settings.DRY_RUN:
                # Read last 1000 lines
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    last_lines = lines[-1000:]

                # Overwrite with truncated content
                with open(log_path, 'w') as f:
                    f.writelines(last_lines)
                    f.write(f"\n[LOG TRUNCATED - Original size: {file_size} bytes]\n")

            logging.info(f"Truncated log: {log_path} ({file_size} bytes)")
            truncated.append(log_path)

    return truncated
```

**File**: `/cleanup/app/service.py:_truncate_large_logs()`

### 3. Permission Fixing

```python
async def _fix_workspace_permissions(self):
    """
    Ensure workspace directories are readable/writable
    Fix common permission issues
    """
    workspaces = glob.glob(os.path.join(settings.PROJECTS_DIR, "*"))

    for workspace in workspaces:
        if os.path.isdir(workspace):
            try:
                # Ensure 755 permissions
                current_mode = os.stat(workspace).st_mode & 0o777

                if current_mode != 0o755:
                    if not settings.DRY_RUN:
                        os.chmod(workspace, 0o755)
                    logging.info(f"Fixed permissions for {workspace}")

            except Exception as e:
                logging.error(f"Failed to fix permissions for {workspace}: {e}")
```

**File**: `/cleanup/app/service.py:_fix_workspace_permissions()`

### 4. Orphaned Container Cleanup

```python
async def _cleanup_orphaned_containers(self) -> list:
    """
    Remove Docker containers with vibe labels but no Redis metadata
    """
    orphaned = []

    # Get all vibe containers
    containers = self.docker_client.containers.list(
        all=True,
        filters={'label': 'com.vibe.project-id'}
    )

    for container in containers:
        project_id = container.labels.get('com.vibe.project-id')

        # Check if project exists in Redis
        exists = self.redis.exists(f"project:{project_id}")

        if not exists:
            # Orphaned container
            if not settings.DRY_RUN:
                container.remove(force=True)

            logging.info(f"Removed orphaned container: {container.name}")
            orphaned.append(container.name)

    return orphaned
```

**File**: `/cleanup/app/service.py:_cleanup_orphaned_containers()`

### 5. Orphaned Workspace Cleanup

```python
async def _cleanup_orphaned_workspaces(self) -> list:
    """
    Remove workspace directories with no corresponding Redis entry
    """
    orphaned = []

    workspaces = glob.glob(os.path.join(settings.PROJECTS_DIR, "*"))

    for workspace_path in workspaces:
        project_id = os.path.basename(workspace_path)

        # Skip templates directory
        if project_id == 'templates':
            continue

        # Check if project exists in Redis
        exists = self.redis.exists(f"project:{project_id}")

        if not exists:
            if not settings.DRY_RUN:
                shutil.rmtree(workspace_path)

            logging.info(f"Removed orphaned workspace: {workspace_path}")
            orphaned.append(workspace_path)

    return orphaned
```

**File**: `/cleanup/app/service.py:_cleanup_orphaned_workspaces()`

### 6. Webhook Notification

```python
async def send_cleanup_report(self):
    """
    Send cleanup report to configured webhook URL
    """
    if not settings.domain_events_webhook:
        return

    report = {
        'event': 'cleanup_completed',
        'timestamp': datetime.utcnow().isoformat(),
        'summary': self.last_cleanup_result,
        'server': os.environ.get('HOSTNAME', 'unknown')
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.domain_events_webhook,
                json=report,
                timeout=10.0
            )
            response.raise_for_status()
            logging.info(f"Cleanup report sent to webhook")

    except Exception as e:
        logging.error(f"Failed to send cleanup report: {e}")
```

**File**: `/cleanup/app/service.py:send_cleanup_report()`

---

## How to Run / Test

### Development Mode

```bash
# Navigate to cleanup directory
cd /home/user/vibe-coding-platform/cleanup

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export REDIS_HOST=localhost
export CLEANUP_INTERVAL=60           # Run every 60 seconds for testing
export MAX_PROJECT_AGE_DAYS=1        # Test with 1 day threshold
export DRY_RUN=true                  # Test mode - no actual deletion

# Run service
python -m app.main
```

### Production Mode (Docker)

```bash
# Build image
docker build -t vibe-coding/cleanup:latest \
  /home/user/vibe-coding-platform/cleanup

# Run container
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

### Manual Cleanup Trigger

```bash
# Run cleanup immediately (without waiting for interval)
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

### Testing with DRY_RUN

```bash
# Enable dry-run mode
export DRY_RUN=true

# Run cleanup
python -m app.main

# Check logs - should show what WOULD be deleted without actually deleting
tail -f /logs/cleanup.log
```

### Unit Testing

```bash
cd /home/user/vibe-coding-platform

# Install dev dependencies
pip install -r requirements-dev.txt

# Run cleanup service tests
pytest tests/test_cleanup_service.py -v
```

---

## Common Tasks for Agents

### مهمة: تعديل inactive project threshold

**File**: `/config/.env`

```bash
# Before (30 days)
MAX_PROJECT_AGE_DAYS=30

# After (60 days)
MAX_PROJECT_AGE_DAYS=60
```

**Restart**:
```bash
docker-compose restart cleanup
```

### مهمة: تغيير cleanup interval

**File**: `/config/.env`

```bash
# Before (24 hours)
CLEANUP_INTERVAL=86400

# After (12 hours)
CLEANUP_INTERVAL=43200

# For hourly cleanup
CLEANUP_INTERVAL=3600
```

### مهمة: إضافة cleanup rule جديد

**File**: `/cleanup/app/service.py`

**Example**: Cleanup expired backups

```python
async def run_cleanup_cycle(self):
    # Existing cleanup operations...
    removed_projects = await self._cleanup_inactive_projects()
    truncated_logs = await self._truncate_large_logs()

    # Add new cleanup rule
    expired_backups = await self._cleanup_expired_backups()

    return {
        # ...
        'expired_backups': expired_backups
    }

async def _cleanup_expired_backups(self) -> list:
    """Remove backup files older than 7 days"""
    removed = []
    cutoff = datetime.utcnow() - timedelta(days=7)

    backup_pattern = os.path.join(settings.PROJECTS_DIR, "*.backup.*.tar.gz")
    backups = glob.glob(backup_pattern)

    for backup_path in backups:
        # Get file modification time
        mtime = datetime.fromtimestamp(os.path.getmtime(backup_path))

        if mtime < cutoff:
            if not settings.DRY_RUN:
                os.remove(backup_path)

            logging.info(f"Removed expired backup: {backup_path}")
            removed.append(backup_path)

    return removed
```

### مهمة: Debug لماذا المشاريع لا تُحذف

**Checklist**:

1. **Check cleanup service logs**:
```bash
docker logs vibe-cleanup --tail 100
# Look for cleanup cycle runs
```

2. **Check Redis last_seen timestamps**:
```bash
redis-cli HGET project:alice-my-app last_seen
# Compare with current date
```

3. **Verify DRY_RUN is disabled**:
```bash
docker exec vibe-cleanup env | grep DRY_RUN
# Should be empty or "false"
```

4. **Check MAX_PROJECT_AGE_DAYS**:
```bash
docker exec vibe-cleanup env | grep MAX_PROJECT_AGE_DAYS
```

5. **Manual test**:
```python
from datetime import datetime, timedelta
import redis

r = redis.Redis(host='redis', decode_responses=True)

# Get project
project_id = "alice-old-project"
last_seen_str = r.hget(f"project:{project_id}", 'last_seen')

if last_seen_str:
    last_seen = datetime.fromisoformat(last_seen_str)
    age_days = (datetime.utcnow() - last_seen).days
    print(f"Project age: {age_days} days")
```

### مهمة: Add cleanup metrics

**File**: `/cleanup/app/service.py`

```python
class CleanupService:
    def __init__(self):
        # ...
        self.metrics = {
            'total_cleanups': 0,
            'total_projects_removed': 0,
            'total_logs_truncated': 0,
        }

    async def run_cleanup_cycle(self):
        result = {
            # ... cleanup operations
        }

        # Update metrics
        self.metrics['total_cleanups'] += 1
        self.metrics['total_projects_removed'] += len(result['removed_projects'])
        self.metrics['total_logs_truncated'] += len(result['truncated_logs'])

        # Log metrics
        logging.info(f"Cleanup metrics: {self.metrics}")

        return result
```

### مهمة: Configure webhook notifications

**File**: `/config/.env`

```bash
# Add webhook URL
domain_events_webhook=https://your-monitoring-service.com/webhooks/cleanup
```

**Test webhook**:
```bash
# Manual trigger with webhook
docker exec vibe-cleanup python -c "
from app.service import CleanupService
import asyncio

async def test():
    service = CleanupService()
    await service.run_cleanup_cycle()
    await service.send_cleanup_report()

asyncio.run(test())
"

# Check webhook endpoint received the POST request
```

---

## Notes / Gotchas

### ⚠️ Docker Socket Permission

- الـservice يحتاج read access لـDocker socket للـcontainer cleanup
- Mount: `/var/run/docker.sock:/var/run/docker.sock:ro` (read-only كافي)

### ⚠️ DRY_RUN Mode

- مع `DRY_RUN=true`: **لا شيء يُحذف فعلاً**
- يُستخدم للtesting و verification
- Production يجب أن يكون `DRY_RUN=false` أو unset

### ⚠️ Workspace Deletion Risks

- حذف workspace يحذف **جميع ملفات المشروع نهائياً**
- لا يمكن استرجاعها بعد الحذف
- Recommendation: create backups قبل الحذف

```python
async def _delete_workspace(self, project_id: str):
    workspace_path = os.path.join(settings.PROJECTS_DIR, project_id)

    # Create backup before deletion
    backup_path = f"{workspace_path}.backup.{int(time.time())}.tar.gz"
    shutil.make_archive(backup_path.replace('.tar.gz', ''), 'gztar', workspace_path)

    # Now safe to delete
    shutil.rmtree(workspace_path)
```

### ⚠️ Redis Key Consistency

- إذا Redis down أثناء cleanup: قد تُحذف containers لكن Redis keys تبقى
- الحل: orphaned workspace cleanup يتعامل مع هذه الحالة

### ⚠️ Log Truncation Side Effects

- Truncation يحذف البيانات القديمة
- إذا كنت تستخدم log aggregation (ELK، Splunk): تأكد أن الlogs exported قبل truncation
- Recommendation: ship logs قبل truncation

### ⚠️ Cleanup Interval Considerations

- `CLEANUP_INTERVAL` قصير جداً (< 1 hour): overhead على النظام
- `CLEANUP_INTERVAL` طويل جداً (> 1 week): قد تتراكم المشاريع القديمة
- Recommended: 24 hours (86400 seconds)

### ⚠️ Timezone Issues

- جميع timestamps في UTC (`datetime.utcnow()`)
- عند مقارنة مع external systems: تأكد من timezone conversion

### ⚠️ Container Removal Failures

- إذا container running: `force=True` مطلوب للحذف
- إذا container has volumes: قد يحتاج `v=True` (حذف volumes)

```python
container.remove(force=True, v=True)
```

### ⚠️ File System Race Conditions

- إذا cleanup service و project manager يعملون في نفس الوقت:
  - Cleanup قد يحذف workspace أثناء إنشاء مشروع
  - الحل: check Redis قبل الحذف (already implemented)
