# Project Manager Service - دليل الـAgent

## Purpose

الـ**Project Manager Service** هي الخدمة المسؤولة عن **Container Orchestration**. تُدير:
- **Container Lifecycle**: إنشاء، بدء، إيقاف، حذف Docker containers
- **Workspace Management**: تحضير workspaces و نسخ templates
- **Command Execution**: تنفيذ أوامر shell داخل project containers
- **Git Operations**: commit، log، reset داخل project containers
- **State Synchronization**: مزامنة حالة containers إلى Redis
- **Secret Sync**: نسخ GitHub credentials إلى containers
- **Router Registry**: تسجيل containers مع Traefik للـdynamic routing

**Technology**: Python 3.11 + FastAPI + Docker SDK 7.0.0

**الـPort**: 9400 (internal only - لا يُعرض للخارج)

**الشبكة**: vibe-network (internal Docker network)

---

## Owned Scope

هذه الخدمة تملك:

### Core Services
- `/project-manager/app/services/__init__.py` - ProjectManager class (Container operations)
- `/project-manager/app/services/secret_sync.py` - SecretSyncService (GitHub CLI sync)
- `/project-manager/app/services/router_registry.py` - RouterRegistry (Traefik integration)

### API Layer
- `/project-manager/app/main.py` - FastAPI application + internal endpoints
- `/project-manager/app/models.py` - Request/Response models (ProjectRequest, ProjectStatus, etc.)

### Configuration
- `/project-manager/app/config.py` - Pydantic Settings

### Templates & Images
- `/project-manager/templates/images/python/` - Python project Dockerfile
- `/project-manager/templates/images/nodejs/` - Node.js project Dockerfile
- `/project-manager/templates/images/php/` - PHP project Dockerfile
- `/project-manager/templates/images/full/` - Full-stack project Dockerfile

### Event Logging
- `/project-manager/app/loggers/domain_events.py` - Domain event logging للـwebhook notifications

### Infrastructure
- `/project-manager/Dockerfile` - Service container image
- `/project-manager/requirements.txt` - Python dependencies

---

## Key Files & Entry Points

### Main Entry Point

```python
# /project-manager/app/main.py
from fastapi import FastAPI
from app.services import ProjectManager
from app.config import settings

app = FastAPI(title="Vibe Project Manager")

# Startup: Initialize ProjectManager
@app.on_event("startup")
async def startup():
    global project_manager
    project_manager = ProjectManager()

    # Start background monitoring loop
    asyncio.create_task(project_manager.monitor_containers())

# Internal endpoints
@app.post("/internal/projects")
async def create_project(request: ProjectRequest):
    result = await project_manager.create_project(request)
    return result

@app.post("/internal/projects/{project_id}/exec")
async def exec_in_project(project_id: str, command: ExecCommand):
    result = await project_manager.exec_in_project(project_id, command)
    return result
```

**Command**: `uvicorn app.main:app --host 0.0.0.0 --port 9400`

### Configuration

```python
# /project-manager/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Service Settings
    PROJECT_MANAGER_PORT: int = 9400

    # Docker Settings
    DOCKER_NETWORK: str = "vibe-network"
    PROJECT_IMAGE_PREFIX: str = "vibe-project-"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Paths
    PROJECTS_DIR: str = "/projects"
    TEMPLATES_DIR: str = "/templates/default"

    # Resource Limits
    PROJECT_CPU_LIMIT: float = 2.0         # CPU cores
    PROJECT_MEMORY_LIMIT: str = "4G"       # Memory limit
    PROJECT_STORAGE_LIMIT: str = "10G"     # Disk quota

    # Monitoring
    HEALTH_POLL_INTERVAL: int = 30         # Container state sync (seconds)

    # Timeouts
    CREATE_TIMEOUT: int = 120              # Container creation timeout
    EXEC_TIMEOUT: int = 300                # Command execution timeout
    MAX_OUTPUT_SIZE: int = 10485760        # 10MB

    # Webhooks
    domain_events_webhook: Optional[str] = None  # Event notification URL
```

### Internal API Endpoints

| Method | Path | Description | Called By |
|--------|------|-------------|-----------|
| POST | `/internal/projects` | إنشاء project container | Central API |
| GET | `/internal/projects/{project_id}` | الحصول على حالة المشروع | Central API |
| DELETE | `/internal/projects/{project_id}` | حذف project container | Central API |
| POST | `/internal/projects/{id}/exec` | تنفيذ أمر داخل container | Central API |
| POST | `/internal/projects/{id}/git/commit` | Git commit | Central API |
| POST | `/internal/projects/{id}/git/log` | Git log | Central API |
| POST | `/internal/projects/{id}/git/reset` | Git reset | Central API |
| GET | `/health` | Health check | Central API |

---

## Dependencies & Interfaces

### External Dependencies

```
Project Manager
    │
    ├─→ Docker Engine (/var/run/docker.sock)
    │   └─ Container CRUD operations
    │   └─ Image management
    │   └─ Network creation
    │
    ├─→ Redis (TCP:6379)
    │   └─ State synchronization (project:{id})
    │   └─ Update last_seen timestamps
    │
    ├─→ File System
    │   ├─ /projects/ - Project workspaces (host mount)
    │   ├─ /templates/ - Template files
    │   └─ /logs/ - Service logs
    │
    └─→ (Optional) Traefik
        └─ Dynamic routing via Docker labels
```

### Docker SDK Usage

```python
import docker

# /project-manager/app/services/__init__.py
class ProjectManager:
    def __init__(self):
        # Connect to Docker socket
        self.docker_client = docker.from_env()

        # Ensure network exists
        self._ensure_network_exists()
```

### Python Package Dependencies

```
# Core Framework
fastapi==0.110.0
uvicorn[standard]==0.29.0
pydantic>=2.6.4,<3
pydantic-settings==2.2.1

# Docker Integration
docker==7.0.0
requests-unixsocket==0.3.0  # For Docker socket

# Data & Caching
redis==5.0.1
httpx==0.27.0

# Configuration
PyYAML==6.0.1
python-dotenv==1.0.1
```

File: `/project-manager/requirements.txt`

---

## Local Rules / Patterns

### 1. Container Creation Flow

```python
async def create_project(self, request: ProjectRequest) -> dict:
    """
    Full project creation workflow:
    1. Prepare workspace directory
    2. Copy template files
    3. Create Docker container
    4. Start container
    5. Sync secrets (GitHub CLI)
    6. Update Redis state
    7. Register with router (if enabled)
    """

    # 1. Prepare workspace
    workspace_path = self._prepare_workspace(request.project_id)

    # 2. Copy template
    self._copy_template(workspace_path)

    # 3. Create container
    container = self.docker_client.containers.create(
        image=f"{settings.PROJECT_IMAGE_PREFIX}{request.project_type}:latest",
        name=f"vibe-{request.project_id}",
        detach=True,
        network=settings.DOCKER_NETWORK,
        volumes={
            workspace_path: {'bind': '/workspace', 'mode': 'rw'}
        },
        environment={
            'PROJECT_ID': request.project_id,
            'POSTGRES_ENABLED': str(request.database == 'postgres'),
            'REDIS_ENABLED': str(request.redis),
        },
        labels={
            'com.vibe.project-id': request.project_id,
            'com.vibe.username': request.username,
        },
        cpu_quota=int(settings.PROJECT_CPU_LIMIT * 100000),
        mem_limit=settings.PROJECT_MEMORY_LIMIT,
    )

    # 4. Start
    container.start()

    # 5. Sync secrets
    await self.secret_sync.sync_to_container(container.id, request.secrets)

    # 6. Update Redis
    await self._update_state(request.project_id, container.id, 'running')

    # 7. Register router (if Traefik enabled)
    if settings.ENABLE_TRAEFIK:
        self.router_registry.attach(container, request.project_id)

    return {
        'project_id': request.project_id,
        'container_id': container.id,
        'status': 'running',
        'workspace': workspace_path,
        'preview_url': f"https://{request.project_id}.{settings.DOMAIN}"
    }
```

**File**: `/project-manager/app/services/__init__.py:create_project()`

### 2. Command Execution Pattern

```python
async def exec_in_project(self, project_id: str, command: ExecCommand) -> dict:
    """
    Execute shell command in project container
    """
    # Find container
    container = self._find_container(project_id)

    # Ensure running
    if container.status != 'running':
        container.start()
        time.sleep(2)  # Wait for startup

    # Execute command
    exec_result = container.exec_run(
        cmd=['bash', '-lc', command.cmd],
        workdir=command.cwd or '/workspace',
        demux=True,  # Separate stdout/stderr
        timeout=command.timeout or settings.EXEC_TIMEOUT
    )

    # Extract output
    exit_code = exec_result.exit_code
    stdout = exec_result.output[0].decode() if exec_result.output[0] else ""
    stderr = exec_result.output[1].decode() if exec_result.output[1] else ""

    # Truncate if too large
    if len(stdout) > settings.MAX_OUTPUT_SIZE:
        stdout = stdout[:settings.MAX_OUTPUT_SIZE] + "\n[OUTPUT TRUNCATED]"

    # Update last_seen in Redis
    await self._update_last_seen(project_id)

    return {
        'returncode': exit_code,
        'stdout': stdout,
        'stderr': stderr
    }
```

**File**: `/project-manager/app/services/__init__.py:exec_in_project()`

### 3. Container Monitoring Loop

```python
async def monitor_containers(self):
    """
    Background task: Sync container states to Redis every HEALTH_POLL_INTERVAL
    """
    while True:
        try:
            # Get all vibe containers
            containers = self.docker_client.containers.list(
                all=True,
                filters={'label': 'com.vibe.project-id'}
            )

            for container in containers:
                project_id = container.labels.get('com.vibe.project-id')

                # Reload to get current status
                container.reload()

                # Update Redis
                await self.redis.hset(
                    f"project:{project_id}",
                    mapping={
                        'status': container.status,
                        'container_id': container.id,
                        'last_seen': datetime.utcnow().isoformat()
                    }
                )

        except Exception as e:
            logging.error(f"Monitor loop error: {e}")

        # Wait for next poll
        await asyncio.sleep(settings.HEALTH_POLL_INTERVAL)
```

**File**: `/project-manager/app/services/__init__.py:monitor_containers()`

### 4. Workspace Preparation

```python
def _prepare_workspace(self, project_id: str) -> str:
    """
    Create project workspace directory and set permissions
    """
    workspace_path = os.path.join(settings.PROJECTS_DIR, project_id)

    # Create directory
    os.makedirs(workspace_path, exist_ok=True)

    # Set permissions (readable/writable by container user)
    os.chmod(workspace_path, 0o755)

    return workspace_path

def _copy_template(self, workspace_path: str):
    """
    Copy default template files to workspace
    """
    template_dir = settings.TEMPLATES_DIR

    if os.path.exists(template_dir):
        # Copy all files from template
        shutil.copytree(
            template_dir,
            workspace_path,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('*.pyc', '__pycache__')
        )
```

**File**: `/project-manager/app/services/__init__.py`

### 5. Secret Synchronization

```python
# /project-manager/app/services/secret_sync.py
class SecretSyncService:
    async def sync_to_container(self, container_id: str, secrets: dict):
        """
        Copy GitHub CLI configuration into container
        """
        container = self.docker_client.containers.get(container_id)

        # Create GitHub config directory
        container.exec_run(['mkdir', '-p', '/home/coder/.config/gh'])

        # Write config file
        gh_config = {
            'git_protocol': 'https',
            'hosts': {
                'github.com': {
                    'oauth_token': secrets.get('github_api_key'),
                    'user': secrets.get('github_username', 'user')
                }
            }
        }

        config_yaml = yaml.dump(gh_config)

        # Copy config into container
        container.exec_run([
            'bash', '-c',
            f'echo \'{config_yaml}\' > /home/coder/.config/gh/config.yml'
        ])

        # Set permissions
        container.exec_run(['chmod', '600', '/home/coder/.config/gh/config.yml'])
```

### 6. Git Operations Proxy

```python
async def git_commit(self, project_id: str, data: dict) -> dict:
    """
    Create git commit in project container
    """
    # Prepare git commands
    commands = []

    if data.get('add_all', True):
        commands.append('git add -A')

    commit_cmd = f'git commit -m "{data["message"]}"'
    if data.get('amend', False):
        commit_cmd += ' --amend'

    commands.append(commit_cmd)

    # Execute all commands
    full_cmd = ' && '.join(commands)

    result = await self.exec_in_project(project_id, ExecCommand(
        cmd=full_cmd,
        cwd='/workspace'
    ))

    # Create workspace backup if modify operation
    if result['returncode'] == 0:
        backup_path = self._create_backup(project_id)
        result['backup_path'] = backup_path

    return result
```

**File**: `/project-manager/app/services/__init__.py`

---

## How to Run / Test

### Development Mode

```bash
# Navigate to project-manager directory
cd /home/user/vibe-coding-platform/project-manager

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PROJECT_MANAGER_PORT=9400
export REDIS_HOST=localhost
export PROJECTS_DIR=/tmp/test-projects
export TEMPLATES_DIR=/home/user/vibe-coding-platform/projects/templates/default

# IMPORTANT: Ensure Docker socket access
# User must be in 'docker' group or run with sudo

# Run with auto-reload
uvicorn app.main:app --reload --port 9400
```

### Production Mode (Docker)

```bash
# Build image
docker build -t vibe-coding/project-manager:latest \
  /home/user/vibe-coding-platform/project-manager

# Run container
docker run -d \
  --name vibe-project-manager \
  --network vibe-network \
  -p 9400:9400 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /srv/vibe/projects:/projects \
  -v /srv/vibe/logs:/logs \
  -e REDIS_HOST=redis \
  -e PROJECT_MANAGER_PORT=9400 \
  vibe-coding/project-manager:latest
```

### Testing Internal Endpoints

```bash
# Health check
curl http://localhost:9400/health

# Create project (internal endpoint)
curl -X POST http://localhost:9400/internal/projects \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "alice-test",
    "username": "alice",
    "project_type": "python",
    "database": "none",
    "redis": false,
    "secrets": {
      "github_api_key": "ghp_test123"
    }
  }' | jq

# Get project status
curl http://localhost:9400/internal/projects/alice-test | jq

# Execute command
curl -X POST http://localhost:9400/internal/projects/alice-test/exec \
  -H "Content-Type: application/json" \
  -d '{
    "cmd": "ls -la /workspace",
    "cwd": "/workspace",
    "timeout": 30
  }' | jq

# Delete project
curl -X DELETE http://localhost:9400/internal/projects/alice-test
```

### Building Project Images

```bash
# Build all project type images
cd /home/user/vibe-coding-platform
bash tools/build-project-images.sh

# Build specific image
cd /home/user/vibe-coding-platform/project-manager/templates/images/python
docker build -t vibe-project-python:latest .

# Verify images
docker images | grep vibe-project
```

---

## Common Tasks for Agents

### مهمة: إضافة project type جديد

**Example**: إضافة دعم لـRust projects

1. **Create Dockerfile** في `/project-manager/templates/images/rust/`:
```dockerfile
FROM rust:1.75-slim

# Install development tools
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create workspace
RUN mkdir -p /workspace
WORKDIR /workspace

# Install cargo tools
RUN cargo install cargo-watch

# Create non-root user
RUN useradd -m -u 1000 coder
RUN chown -R coder:coder /workspace

USER coder

CMD ["/bin/bash"]
```

2. **Build image**:
```bash
cd /project-manager/templates/images/rust
docker build -t vibe-project-rust:latest .
```

3. **Update validation** في Central API `/api/app/models/projects.py`:
```python
class ProjectCreate(BaseModel):
    project_type: Literal["python", "nodejs", "php", "full", "rust"]
```

4. **Test**:
```bash
curl -X POST http://localhost:9000/projects/create \
  -H "X-API-Key: key" \
  -d '{"project_type": "rust", ...}'
```

### مهمة: تعديل resource limits

**File**: `/project-manager/app/config.py`

```python
# Before
PROJECT_CPU_LIMIT: float = 2.0        # 2 cores
PROJECT_MEMORY_LIMIT: str = "4G"      # 4GB RAM

# After (للprojects أكبر)
PROJECT_CPU_LIMIT: float = 4.0        # 4 cores
PROJECT_MEMORY_LIMIT: str = "8G"      # 8GB RAM
```

**Or** تطبيق limits مخصصة per project type:
```python
def _get_resource_limits(self, project_type: str) -> dict:
    limits = {
        'python': {'cpu': 2.0, 'memory': '4G'},
        'nodejs': {'cpu': 2.0, 'memory': '4G'},
        'full': {'cpu': 4.0, 'memory': '8G'},  # Full-stack needs more
    }
    return limits.get(project_type, {'cpu': 2.0, 'memory': '4G'})
```

### مهمة: Debug container creation failures

**Checklist**:

1. **Check Docker socket access**:
```bash
ls -la /var/run/docker.sock
# Should be readable/writable

# Test Docker connection
docker ps
```

2. **Check image availability**:
```bash
docker images | grep vibe-project
# Should show vibe-project-python, nodejs, etc.
```

3. **Check workspace directory**:
```bash
ls -la /projects/
# Should be writable by service

# Check permissions
stat /projects/
```

4. **Check Project Manager logs**:
```bash
docker logs vibe-project-manager --tail 100
# Look for Docker API errors
```

5. **Manual container creation test**:
```bash
docker run -it --rm \
  --name test-container \
  --network vibe-network \
  -v /projects/test:/workspace \
  vibe-project-python:latest \
  /bin/bash

# Inside container
ls -la /workspace
python --version
```

6. **Check Redis connection**:
```bash
docker exec vibe-project-manager redis-cli -h redis ping
# Should return PONG
```

### مهمة: Add pre-creation hook

**File**: `/project-manager/app/services/__init__.py`

```python
async def create_project(self, request: ProjectRequest) -> dict:
    # Add custom pre-creation logic
    await self._validate_project_name(request.project_id)
    await self._check_quota(request.username)

    # Original creation flow...
    workspace_path = self._prepare_workspace(request.project_id)
    # ...

async def _validate_project_name(self, project_id: str):
    """Custom validation"""
    if 'test' in project_id and not settings.ALLOW_TEST_PROJECTS:
        raise ValueError("Test projects not allowed")

async def _check_quota(self, username: str):
    """Check user quota"""
    existing = await self.redis.scard(f"user:{username}:projects")
    if existing >= settings.MAX_PROJECTS_PER_USER:
        raise ValueError("Project quota exceeded")
```

### مهمة: Implement container auto-stop

**File**: `/project-manager/app/services/__init__.py`

```python
async def monitor_containers(self):
    """Extended monitoring with auto-stop for idle containers"""
    while True:
        containers = self.docker_client.containers.list(
            filters={'label': 'com.vibe.project-id'}
        )

        for container in containers:
            project_id = container.labels.get('com.vibe.project-id')

            # Get last_seen from Redis
            last_seen_str = await self.redis.hget(f"project:{project_id}", 'last_seen')
            if last_seen_str:
                last_seen = datetime.fromisoformat(last_seen_str)
                idle_minutes = (datetime.utcnow() - last_seen).total_seconds() / 60

                # Auto-stop after 60 minutes idle
                if idle_minutes > 60 and container.status == 'running':
                    logging.info(f"Auto-stopping idle container: {project_id}")
                    container.stop()
                    await self.redis.hset(f"project:{project_id}", 'status', 'stopped')

        await asyncio.sleep(settings.HEALTH_POLL_INTERVAL)
```

---

## Notes / Gotchas

### ⚠️ Docker Socket Permission

- الـservice يجب أن يكون له **write access** لـ`/var/run/docker.sock`
- في Docker Compose: mount بـ`/var/run/docker.sock:/var/run/docker.sock`
- في bare metal: user يجب أن يكون في `docker` group

### ⚠️ Container Naming Conflicts

- Container names يجب أن تكون unique: `vibe-{project_id}`
- إذا container بنفس الاسم موجود (من failed creation):
```python
try:
    existing = self.docker_client.containers.get(f"vibe-{project_id}")
    existing.remove(force=True)
except docker.errors.NotFound:
    pass
```

### ⚠️ Network Creation Race Condition

- `vibe-network` يجب أن تُنشأ قبل أي container creation
- الحل: `_ensure_network_exists()` في `__init__`

```python
def _ensure_network_exists(self):
    try:
        self.docker_client.networks.get(settings.DOCKER_NETWORK)
    except docker.errors.NotFound:
        self.docker_client.networks.create(
            settings.DOCKER_NETWORK,
            driver='bridge'
        )
```

### ⚠️ Volume Mount Permissions

- Container user (uid=1000) يجب أن يستطيع write في `/workspace`
- الـworkspace على الhost يجب أن يكون `chmod 755` أو `777`

### ⚠️ Container Startup Time

- بعض containers تحتاج وقت للـstartup (databases، services)
- عند `exec_in_project`: add sleep(2) بعد `container.start()`

### ⚠️ Output Truncation

- Command output محدود بـ`MAX_OUTPUT_SIZE` (10MB)
- للـoutput كبير: استخدم file redirection داخل المشروع
```bash
python long_script.py > output.txt 2>&1
```

### ⚠️ Git Operations Backup

- `git reset --hard` يحذف uncommitted changes
- الحل الحالي: create workspace backup قبل destructive operations
- Backup location: `/projects/{project_id}.backup.{timestamp}.tar.gz`

### ⚠️ Secret Sync Timing

- Secrets يجب أن تُنسخ **بعد** container startup
- إذا sync fails: container يبقى running لكن بدون GitHub credentials

### ⚠️ Traefik Router Labels

- Labels يجب أن تُضاف **عند creation** (لا يمكن update بعد ذلك)
- للـupdate: يجب recreate الـcontainer

```python
labels = {
    'com.vibe.project-id': project_id,
    'traefik.enable': 'true',
    'traefik.http.routers.{id}.rule': f'Host(`{project_id}.{domain}`)',
}
```
