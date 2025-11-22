# Central API Service - دليل الـAgent

## Purpose

الـ**Central API Service** هو نقطة الدخول الرئيسية للمنصة. يُدير:
- **Authentication**: التحقق من API keys و project passwords
- **Rate Limiting**: حماية من abuse عبر Redis-backed throttling
- **Project CRUD**: إنشاء، قراءة، تحديث، حذف المشاريع
- **Command Execution**: proxy للأوامر إلى Project Manager
- **Git Operations**: commit، log، reset عبر Project Manager
- **Health Monitoring**: endpoints للـhealth checks و metrics

**Technology**: Python 3.11 + FastAPI 0.110.0 + Uvicorn

**الـPort**: 9000 (configurable via `API_PORT`)

---

## Owned Scope

هذه الخدمة تملك:

### HTTP Routing Layer
- `/api/app/routers/projects.py` - Projects CRUD endpoints
- `/api/app/routers/exec.py` - Command execution endpoint
- `/api/app/routers/git.py` - Git operations endpoints
- `/api/app/routers/health.py` - Health & metrics endpoints

### Business Logic Layer
- `/api/app/services/projects.py` - ProjectService (CRUD, cache sync)
- `/api/app/services/execution.py` - ExecutionService (command proxy)
- `/api/app/services/git.py` - GitService (git operations proxy)
- `/api/app/services/project_manager.py` - ProjectManagerClient (HTTP client)
- `/api/app/services/repository.py` - ProjectRepository (SQLite operations)
- `/api/app/services/rate_limiter.py` - RateLimiter (Redis-based)
- `/api/app/services/auth.py` - Authentication (API key verification)
- `/api/app/services/security.py` - Security (password hashing/generation)
- `/api/app/services/secrets.py` - SecretStorage (encrypted GitHub tokens)

### Data Models
- `/api/app/models/projects.py` - ProjectCreate, ProjectInfo, ProjectDelete
- `/api/app/models/exec.py` - ExecRequest, ExecResponse
- `/api/app/models/git.py` - GitCommitRequest, GitLogRequest, GitResetRequest

### Configuration & Utilities
- `/api/app/config.py` - Pydantic Settings class
- `/api/app/dependencies.py` - FastAPI dependency injection
- `/api/app/utils/logging.py` - Audit logging و structured logging

### Infrastructure Files
- `/api/Dockerfile` - Python 3.11-slim image
- `/api/requirements.txt` - Python dependencies
- `/api/app/main.py` - FastAPI application + middleware

---

## Key Files & Entry Points

### Main Entry Point

```python
# /api/app/main.py
from fastapi import FastAPI
from app.routers import projects, exec, git, health

app = FastAPI(title="Vibe Coding Platform API")

# Middleware
@app.middleware("http")
async def audit_requests(request, call_next):
    # Audit logging logic
    pass

# Routers
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(exec.router, prefix="", tags=["Execution"])
app.include_router(git.router, prefix="/git", tags=["Git"])
app.include_router(health.router, prefix="/health", tags=["Health"])

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

**Command**: `uvicorn app.main:app --host 0.0.0.0 --port 9000`

### Configuration

```python
# /api/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 9000
    API_KEY: str  # Master API key (required)
    DOMAIN: str = "localhost"
    API_PUBLIC_BASE_URL: str = "http://localhost:9000"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Database
    DB_PATH: str = "/data/projects.db"

    # Project Manager
    PROJECT_MANAGER_HOST: str = "project-manager"
    PROJECT_MANAGER_PORT: int = 9400
    PROJECT_MANAGER_SCHEME: str = "http"

    # Rate Limiting
    ENABLE_RATE_LIMIT: bool = True
    STRICT_RATE_LIMITING: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    EXEC_RATE_LIMIT_PER_MINUTE: int = 60
    PROJECT_CREATE_RATE_LIMIT: int = 5

    # Resource Limits
    MAX_PROJECTS_PER_USER: int = 10
    EXEC_TIMEOUT: int = 300
    MAX_OUTPUT_SIZE: int = 10485760  # 10MB

    # Secrets
    GITHUB_SECRETS_PATH: str = "/data/github-secrets.bin"
    GITHUB_SECRETS_KEY: str  # Fernet encryption key
```

### API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| **Projects** ||||
| POST | `/projects/create` | إنشاء مشروع جديد | X-API-Key |
| GET | `/projects/{username}` | قائمة مشاريع المستخدم | X-API-Key |
| POST | `/projects/info` | معلومات مشروع محدد | Password |
| DELETE | `/projects/delete` | حذف مشروع | Password |
| POST | `/projects/rotate-password` | تدوير كلمة مرور المشروع | Password |
| **Execution** ||||
| POST | `/exec` | تنفيذ أمر shell | Password |
| **Git** ||||
| POST | `/git/commit` | إنشاء commit | Password |
| POST | `/git/log` | عرض git history | Password |
| POST | `/git/reset` | Reset إلى commit محدد | Password |
| **Health** ||||
| GET | `/health` | Basic health check | None |
| GET | `/health/services` | Detailed service status | None |
| GET | `/metrics` | Prometheus metrics | None |

---

## Dependencies & Interfaces

### External Service Dependencies

```
Central API
    │
    ├─→ Project Manager (HTTP:9400) - Container operations
    │   └─ POST /internal/projects
    │   └─ GET  /internal/projects/{id}
    │   └─ POST /internal/projects/{id}/exec
    │   └─ POST /internal/projects/{id}/git/*
    │
    ├─→ Redis (TCP:6379) - Caching & rate limiting
    │   └─ HSET project:{id}
    │   └─ SADD user:{username}:projects
    │   └─ INCR rate:{scope}
    │
    └─→ SQLite (/data/projects.db) - Persistent storage
        └─ projects table
        └─ project_secrets table
```

### Internal Module Dependencies

```
routers/
  ├─ projects.py
  │   └─→ services/projects.py (ProjectService)
  │       ├─→ services/repository.py (ProjectRepository)
  │       ├─→ services/project_manager.py (ProjectManagerClient)
  │       ├─→ services/rate_limiter.py (RateLimiter)
  │       ├─→ services/security.py (password hashing)
  │       └─→ services/secrets.py (SecretStorage)
  │
  ├─ exec.py
  │   └─→ services/execution.py (ExecutionService)
  │       ├─→ services/projects.py (verify_credentials)
  │       ├─→ services/project_manager.py (forward exec)
  │       └─→ services/rate_limiter.py
  │
  ├─ git.py
  │   └─→ services/git.py (GitService)
  │       ├─→ services/projects.py (verify_credentials)
  │       ├─→ services/project_manager.py (forward git ops)
  │       └─→ services/rate_limiter.py
  │
  └─ health.py
      └─→ services/project_manager.py (health check)
      └─→ Redis client (ping)
```

### Python Package Dependencies

```
# Core Framework
fastapi==0.110.0
uvicorn[standard]==0.29.0
pydantic>=2.6.4,<3
pydantic-settings==2.2.1

# Data & Caching
redis==5.0.1
httpx==0.27.0

# Security
bcrypt==4.1.2
cryptography==41.0.7

# Monitoring
prometheus-fastapi-instrumentator==6.1.0

# Utilities
python-dotenv==1.0.1
```

File: `/api/requirements.txt`

---

## Local Rules / Patterns

### 1. Authentication Flow

```python
# Master API Key (for project creation)
from app.services.auth import verify_master_key

async def verify_api_key(x_api_key: str = Header(...)):
    if not verify_master_key(x_api_key):
        raise HTTPException(401, "Invalid API key")
    return True

# Project Password (for project operations)
from app.services.projects import ProjectService

async def verify_project_access(project_id: str, password: str):
    project_service = ProjectService()
    if not await project_service.verify_credentials(project_id, password):
        raise HTTPException(401, "Invalid credentials")
    return True
```

**Files**:
- `/api/app/services/auth.py:verify_master_key()`
- `/api/app/services/projects.py:verify_credentials()`

### 2. Rate Limiting Pattern

```python
from app.services.rate_limiter import RateLimiter

rate_limiter = RateLimiter()

# في router handler
@router.post("/projects/create")
async def create_project(data: ProjectCreate):
    # Check rate limit
    await rate_limiter.check(
        scope=f"projects:create:{data.username}",
        limit=settings.PROJECT_CREATE_RATE_LIMIT,
        window=settings.RATE_LIMIT_WINDOW_SECONDS
    )
    # إذا exceeded → يرمي HTTPException(429)

    # Continue with creation...
```

**File**: `/api/app/services/rate_limiter.py`

**Scopes**:
- `projects:create:{username}` - 5 req/min
- `exec:{project_id}` - 60 req/min
- `git:{project_id}` - 60 req/min
- `project:info:{project_id}` - 30 req/min

### 3. Data Validation Pattern

```python
from pydantic import BaseModel, Field, field_validator
import re

class ProjectCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    project_name: str = Field(..., min_length=3, max_length=50)

    @field_validator('username', 'project_name')
    def validate_name(cls, v):
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError('Only lowercase letters, numbers, _ and - allowed')
        return v
```

**File**: `/api/app/models/projects.py`

### 4. Cache-Aside Pattern

```python
async def get_project_info(project_id: str) -> Optional[ProjectInfo]:
    # Try cache first
    cached = await redis_client.hgetall(f"project:{project_id}")
    if cached:
        return ProjectInfo(**cached)

    # Cache miss - fetch from SQLite
    project = await repository.get_project(project_id)
    if project:
        # Update cache
        await redis_client.hset(f"project:{project_id}", mapping=project.dict())

    return project
```

**File**: `/api/app/services/projects.py:get_project_info()`

### 5. Proxy Pattern (لـProject Manager)

```python
class ProjectManagerClient:
    def __init__(self):
        self.base_url = f"{settings.PROJECT_MANAGER_SCHEME}://{settings.PROJECT_MANAGER_HOST}:{settings.PROJECT_MANAGER_PORT}"
        self.client = httpx.AsyncClient(timeout=120.0)

    async def create_project(self, project_data: dict) -> dict:
        response = await self.client.post(
            f"{self.base_url}/internal/projects",
            json=project_data
        )
        response.raise_for_status()
        return response.json()
```

**File**: `/api/app/services/project_manager.py`

### 6. Error Handling

```python
from fastapi import HTTPException

# Business logic errors
raise HTTPException(status_code=400, detail="Project already exists")
raise HTTPException(status_code=401, detail="Invalid credentials")
raise HTTPException(status_code=404, detail="Project not found")
raise HTTPException(status_code=429, detail="Rate limit exceeded")
raise HTTPException(status_code=500, detail="Internal server error")

# Validation errors: handled automatically by Pydantic (422)
```

### 7. Audit Logging

```python
import logging
import time
from uuid import uuid4

@app.middleware("http")
async def audit_requests(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000

    logging.info(
        f"method={request.method} path={request.url.path} "
        f"status={response.status_code} duration_ms={duration:.2f} "
        f"request_id={request_id}"
    )

    return response
```

**File**: `/api/app/main.py`

**Log Location**: `/logs/audit.log`

---

## How to Run / Test

### Development Mode

```bash
# Navigate to api directory
cd /home/user/vibe-coding-platform/api

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export API_KEY="test-api-key"
export GITHUB_SECRETS_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
export REDIS_HOST="localhost"  # If Redis running locally
export DB_PATH="/tmp/test-projects.db"

# Run with auto-reload
uvicorn app.main:app --reload --port 9000
```

### Production Mode (Docker)

```bash
# Build image
docker build -t vibe-coding/api:latest /home/user/vibe-coding-platform/api

# Run container
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

### Testing Endpoints

```bash
# Health check
curl http://localhost:9000/health

# Detailed health
curl http://localhost:9000/health/services | jq

# Create project
curl -X POST http://localhost:9000/projects/create \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "project_name": "my-app",
    "project_type": "python",
    "github_api_key": "ghp_test123",
    "database": "none",
    "redis": false
  }' | jq

# Execute command
curl -X POST http://localhost:9000/exec \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "alice-my-app",
    "password": "returned-password-from-creation",
    "cmd": "python --version"
  }' | jq

# Git commit
curl -X POST http://localhost:9000/git/commit \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "alice-my-app",
    "password": "password",
    "message": "Initial commit",
    "add_all": true
  }' | jq
```

### Running Unit Tests

```bash
cd /home/user/vibe-coding-platform

# Install dev dependencies
pip install -r requirements-dev.txt

# Run API-related tests
pytest tests/test_repository.py -v
pytest tests/test_rate_limiter.py -v

# Run with coverage
pytest --cov=api/app tests/
```

---

## Common Tasks for Agents

### مهمة: إضافة endpoint جديد

**Example**: إضافة endpoint لـproject statistics

1. **Create model** في `/api/app/models/projects.py`:
```python
class ProjectStats(BaseModel):
    total_executions: int
    total_commits: int
    last_activity: datetime
```

2. **Create router** في `/api/app/routers/projects.py`:
```python
@router.get("/{project_id}/stats", response_model=ProjectStats)
async def get_project_stats(
    project_id: str,
    password: str = Body(...),
    project_service: ProjectService = Depends(get_project_service)
):
    # Verify credentials
    if not await project_service.verify_credentials(project_id, password):
        raise HTTPException(401, "Invalid credentials")

    # Get stats
    stats = await project_service.get_stats(project_id)
    return stats
```

3. **Implement في service** `/api/app/services/projects.py`:
```python
async def get_stats(self, project_id: str) -> ProjectStats:
    # Fetch from Redis or calculate
    stats = await self.redis.hget(f"stats:{project_id}", "executions")
    # ...
    return ProjectStats(...)
```

4. **Test**:
```bash
curl http://localhost:9000/projects/alice-my-app/stats \
  -X GET \
  -d '{"password": "pwd"}'
```

### مهمة: تعديل rate limit لـendpoint محدد

**File**: `/api/app/routers/exec.py`

```python
# قبل:
await rate_limiter.check(
    scope=f"exec:{request.project_id}",
    limit=settings.EXEC_RATE_LIMIT_PER_MINUTE,  # 60
    window=60
)

# بعد: زيادة الحد إلى 120
await rate_limiter.check(
    scope=f"exec:{request.project_id}",
    limit=120,  # Custom limit
    window=60
)
```

**Or** update في `/config/.env`:
```bash
EXEC_RATE_LIMIT_PER_MINUTE=120
```

### مهمة: إضافة validation rule جديد

**File**: `/api/app/models/exec.py`

```python
class ExecRequest(BaseModel):
    cmd: str = Field(..., min_length=1, max_length=10000)

    @field_validator('cmd')
    def validate_cmd(cls, v: str) -> str:
        dangerous_patterns = [
            'rm -rf /',
            '> /dev/sd',
            # إضافة pattern جديد:
            'curl.*|.*bash',  # منع piping curl to bash
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError(f"Dangerous command pattern detected: {pattern}")
        return v
```

### مهمة: Debug authentication issues

1. **Check API key**:
```bash
# In .env
grep API_KEY /home/user/vibe-coding-platform/config/.env

# Test
curl -H "X-API-Key: wrong-key" http://localhost:9000/projects/alice
# Should return 401
```

2. **Check password hashing**:
```python
# In Python shell
from api.app.services.security import verify_password
verify_password("plain-password", "hashed-from-db")
```

3. **Check Redis cache**:
```bash
redis-cli HGETALL project:alice-my-app
# Should show password_hash field
```

4. **Check logs**:
```bash
tail -f /logs/audit.log | grep 401
```

**Files**:
- `/api/app/services/auth.py`
- `/api/app/services/security.py`
- `/api/app/services/projects.py:verify_credentials()`

### مهمة: إضافة custom middleware

**File**: `/api/app/main.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware

class CustomHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Before request
        request.state.custom_data = "value"

        # Process request
        response = await call_next(request)

        # After request
        response.headers["X-Custom-Header"] = "value"

        return response

# Add to app
app.add_middleware(CustomHeaderMiddleware)
```

---

## Notes / Gotchas

### ⚠️ Password Verification Performance

- bcrypt verification يستغرق ~100-300ms per request
- لا تُخزن plain passwords أبداً
- Redis cache يُسرع lookups لكن password verification لا يمكن cache-ها

### ⚠️ SQLite Concurrent Writes

- SQLite قد تُرجع `SQLITE_BUSY` في high concurrency
- الحل الحالي: retry logic في `repository.py`
- للـproduction: migrate إلى PostgreSQL

**File**: `/api/app/services/repository.py`

### ⚠️ Rate Limiter Redis Dependency

- مع `STRICT_RATE_LIMITING=true`: إذا Redis down، **جميع requests تُرفض**
- مع `STRICT_RATE_LIMITING=false`: إذا Redis down، **لا rate limiting**
- Production يُفضل `true`

### ⚠️ Project Manager Timeout

- Create project timeout: 120 seconds (في ProjectManagerClient)
- إذا container creation بطيء، قد يحدث timeout
- Check Project Manager logs: `docker logs vibe-project-manager`

### ⚠️ Secrets Encryption Key

- `GITHUB_SECRETS_KEY` يجب أن يكون Fernet-compatible (32 bytes base64)
- Generate صحيح:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
- **لا تُغير الkey** بعد تخزين secrets (سيُفقد access)

### ⚠️ Max Output Size

- Command output محدود بـ `MAX_OUTPUT_SIZE` (10MB default)
- Truncation يحدث في Project Manager، ليس في API
- للـcommands طويلة الـoutput: استخدم file redirection في المشروع

### ⚠️ CORS Configuration

- CORS غير مُفعل بشكل افتراضي
- لتفعيله:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**File**: `/api/app/main.py`
