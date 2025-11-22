# Vibe Coding Platform - دليل الـ Agents الشامل

## Purpose

**vibe-coding-platform** هي منصة **multi-tenant development environment** توفر بيئات برمجة معزولة للمستخدمين عبر **Docker containers**. تتيح المنصة:
- إنشاء مشاريع معزولة (Python, Node.js, PHP, Full-stack)
- تنفيذ أوامر shell بشكل آمن داخل containers
- إدارة Git operations (commit, log, reset)
- Rate limiting و authentication متقدم
- Monitoring و audit logging

**النمط المعماري**: Microservices مُدارة عبر Docker Compose

---

## Owned Scope

هذا المستودع يحتوي على:
- **4 خدمات رئيسية**: Central API, Project Manager, Cleanup Service, Redis cache
- **Infrastructure**: Traefik edge proxy, Prometheus/Grafana monitoring
- **Project templates**: قوالب جاهزة للمشاريع الجديدة
- **Helper tools**: نصوص برمجية للـsetup و deployment و backup
- **Tests**: اختبارات integration و unit
- **Documentation**: أدلة التثبيت والتشغيل

**التقنيات**:
- Python 3.11, FastAPI 0.110.0, Uvicorn
- Docker SDK 7.0.0, Redis 5.0.1
- SQLite 3 (metadata), Fernet encryption
- bcrypt (password hashing)

---

## Key Files & Entry Points

### نقاط الدخول الرئيسية

| الخدمة | Entry Point | الـPort | الوصف |
|--------|-------------|---------|-------|
| Central API | `/api/app/main.py` | 9000 | Public HTTP API |
| Project Manager | `/project-manager/app/main.py` | 9400 | Internal container orchestration |
| Cleanup Service | `/cleanup/app/main.py` | - | Background maintenance loop |
| Redis | Docker image | 6379 | Cache & rate limiting |

### ملفات التكوين الحرجة

```
/docker-compose.yml              # تعريف جميع الخدمات
/config/.env.example             # قالب المتغيرات البيئية
/config/.env                     # التكوين الفعلي (generated)

/api/app/config.py               # إعدادات Central API
/project-manager/app/config.py  # إعدادات Project Manager
/cleanup/app/config.py           # إعدادات Cleanup Service

/infra/edge/traefik.yml          # TLS termination
/infra/monitoring/prometheus.yml # Metrics collection
```

### Databases & Storage

```
/data/projects.db                # SQLite: projects + secrets metadata
/projects/                       # Project workspaces (runtime)
/projects/templates/default/     # Default template (copied to new projects)
/logs/audit.log                  # Request audit trail
/data/github-secrets.bin         # Encrypted secrets storage
```

---

## Dependencies & Interfaces

### Inter-Service Communication

```
┌──────────────────┐
│   Central API    │ ← HTTP:9000 (Public)
│   Port: 9000     │
└────────┬─────────┘
         │ HTTP
         ├─→ Project Manager:9400 (Internal)
         ├─→ Redis:6379 (TCP)
         └─→ SQLite /data/projects.db (File)

┌──────────────────┐
│ Project Manager  │ ← HTTP:9400 (Internal only)
│   Port: 9400     │
└────────┬─────────┘
         │
         ├─→ Docker Socket /var/run/docker.sock
         ├─→ Redis:6379 (State sync)
         └─→ File System /projects/ (Workspaces)

┌──────────────────┐
│ Cleanup Service  │ ← No ports
└────────┬─────────┘
         │
         ├─→ Redis:6379 (Project state)
         ├─→ Docker Socket (Container deletion)
         └─→ File System (Log truncation)
```

### External Dependencies

- **Docker Engine**: مطلوب على الـhost
- **Docker Compose**: v3.9+
- **Python**: 3.11+
- **Redis**: 7-alpine
- **(Optional)** Traefik: v2.11 للـTLS
- **(Optional)** Prometheus/Grafana: للـmonitoring

---

## Local Rules / Patterns

### 1. Service Isolation

- كل خدمة لها **Dockerfile** و **requirements.txt** منفصل
- Inter-service communication عبر **HTTP** أو **Redis**
- لا shared code بين الخدمات (إلا Pydantic models مُكررة)

### 2. Configuration Management

- جميع الإعدادات عبر **Environment Variables**
- Pydantic Settings classes في كل خدمة (`config.py`)
- Secrets لا تُخزن في plaintext (Fernet encryption)

### 3. Security Patterns

```python
# Authentication
- Master API Key: constant-time comparison (secrets.compare_digest)
- Project Passwords: bcrypt hashing
- GitHub Tokens: Fernet encryption at rest

# Rate Limiting
- Redis-based fixed-window counters
- Fail-closed mode (strict_rate_limiting=true)
- Per-scope limits (create, exec, git, etc.)

# Command Validation
- Dangerous pattern detection (rm -rf /, fork bomb, etc.)
- Path traversal prevention (no .. in cwd)
- Working directory confined to /workspace
```

### 4. Data Flow Patterns

```
Write Path:
  Client → API → Service Layer → Repository → SQLite
                              → Redis Cache (async)

Read Path:
  Client → API → Cache (Redis) → [miss] → SQLite → Update Cache
```

### 5. Error Handling

- FastAPI automatic validation errors (422)
- Custom HTTPException للـbusiness logic errors
- Structured logging مع request_id tracking

### 6. Docker Container Naming

```
Pattern: vibe-{project_id}
Example: vibe-alice-my-app

Labels:
  - com.vibe.project-id={project_id}
  - com.vibe.username={username}
  - traefik.http.routers.{id}.rule=Host(`{id}.{domain}`)
```

---

## How to Run / Test

### التشغيل السريع (Quick Start)

```bash
# 1. Clone repository
git clone <repo-url>
cd vibe-coding-platform

# 2. Setup environment (interactive)
bash tools/setup/activate.sh

# 3. Build project images
bash tools/build-project-images.sh

# 4. Start all services
docker-compose up -d

# 5. Check status
bash tools/vibe-status.sh

# 6. View logs
bash tools/vibe-logs.sh api          # Central API logs
bash tools/vibe-logs.sh project-manager
bash tools/vibe-logs.sh cleanup
```

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run specific service locally (for debugging)
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 9000
```

### Testing Individual Services

```bash
# Test Central API health
curl http://localhost:9000/health

# Test metrics endpoint
curl http://localhost:9000/metrics

# Create a test project (requires API key)
curl -X POST http://localhost:9000/projects/create \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "project_name": "test-project",
    "project_type": "python",
    "github_api_key": "ghp_...",
    "database": "none",
    "redis": false
  }'

# Execute command in project
curl -X POST http://localhost:9000/exec \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "testuser-test-project",
    "password": "returned-password",
    "cmd": "ls -la /workspace"
  }'
```

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_rate_limiter.py -v

# With coverage
pytest --cov=api/app --cov=project-manager/app tests/
```

---

## Common Tasks for Agents

### مهمة: إضافة endpoint جديد للـAPI

1. **إنشاء نموذج Pydantic** في `/api/app/models/`
2. **إضافة route handler** في `/api/app/routers/`
3. **كتابة business logic** في `/api/app/services/`
4. **تحديث dependencies** في `/api/app/dependencies.py` إذا لزم
5. **إضافة tests** في `/tests/`
6. **تحديث OpenAPI spec**: `bash tools/openapi/render-multitenant-spec.sh`

**ملفات ذات صلة**:
- `/api/app/routers/projects.py` (مثال)
- `/api/app/services/projects.py` (مثال)
- `/api/app/models/projects.py` (مثال)

### مهمة: إضافة project type جديد

1. **إنشاء Dockerfile** في `/project-manager/templates/images/{type}/`
2. **Build image**: `docker build -t vibe-project-{type}:latest .`
3. **تحديث validation** في `/api/app/models/projects.py:project_type`
4. **اختبار creation flow** عبر API

**ملفات ذات صلة**:
- `/project-manager/templates/images/python/Dockerfile` (مثال)
- `/api/app/models/projects.py:ProjectCreate`

### مهمة: تعديل rate limits

1. **تحديث env vars** في `/config/.env`:
   ```
   PROJECT_CREATE_RATE_LIMIT=10  # من 5 إلى 10
   EXEC_RATE_LIMIT_PER_MINUTE=120  # من 60 إلى 120
   ```
2. **Restart services**: `docker-compose restart api`
3. **Verify** عبر `/health/services` endpoint

**ملفات ذات صلة**:
- `/api/app/config.py:Settings`
- `/api/app/services/rate_limiter.py`

### مهمة: إضافة cleanup rule جديد

1. **Edit** `/cleanup/app/service.py:CleanupService`
2. **Add method** للـcleanup logic
3. **Call من** `_cleanup_cycle()` method
4. **Test** عبر manual trigger أو wait للـinterval

**ملفات ذات صلة**:
- `/cleanup/app/service.py`
- `/cleanup/app/config.py` (للـintervals)

### مهمة: Debug container creation issues

1. **Check logs**: `bash tools/vibe-logs.sh project-manager`
2. **Inspect workspace**: `ls -la /projects/{project_id}`
3. **Check Docker**: `docker ps -a | grep vibe-`
4. **Check Redis state**: `redis-cli HGETALL project:{project_id}`
5. **Manual creation test**:
   ```bash
   docker run -it --rm \
     --name test-container \
     -v /projects/test:/workspace \
     vibe-project-python:latest \
     /bin/bash
   ```

**ملفات ذات صلة**:
- `/project-manager/app/services/__init__.py:create_project()`
- `/project-manager/templates/images/`

### مهمة: إضافة monitoring metric جديد

1. **Import** Prometheus client في `/api/app/main.py`
2. **Define metric**:
   ```python
   from prometheus_client import Counter
   custom_metric = Counter('custom_operations_total', 'Description')
   ```
3. **Increment** في الكود المناسب: `custom_metric.inc()`
4. **Verify** في `GET /metrics` endpoint
5. **Add to Grafana dashboard** في `/infra/monitoring/grafana/`

**ملفات ذات صلة**:
- `/api/app/main.py` (Prometheus setup)
- `/infra/monitoring/prometheus.yml`

---

## Notes / Gotchas

### ⚠️ Docker Socket Permission

- الـProject Manager يحتاج write access لـ`/var/run/docker.sock`
- إذا كان الـcontainer لا يستطيع create containers، check:
  ```bash
  ls -la /var/run/docker.sock
  # يجب أن يكون readable/writable للـcontainer user
  ```

### ⚠️ Redis Connection

- إذا فشل Redis connection:
  - Check `REDIS_HOST` في `.env` (يجب أن يكون `redis` في Docker network)
  - Verify network: `docker network inspect vibe-network`
  - Test connection: `docker exec -it vibe-api redis-cli -h redis ping`

### ⚠️ Rate Limiting Behavior

- مع `STRICT_RATE_LIMITING=true`: إذا Redis down، **جميع الطلبات تُرفض**
- مع `STRICT_RATE_LIMITING=false`: إذا Redis down، **جميع الطلبات تُقبل**
- Production: يُفضل `true` للأمان

### ⚠️ SQLite Locking

- SQLite في concurrent writes قد يحدث `SQLITE_BUSY` errors
- الحل الحالي: Retry logic في `repository.py`
- للـhigh-load production: migrate إلى PostgreSQL

### ⚠️ Container Cleanup

- Cleanup service يعمل كل 24 ساعة (default)
- للـimmediate cleanup:
  ```bash
  docker exec vibe-cleanup python -c "from app.service import CleanupService; import asyncio; asyncio.run(CleanupService().run_once())"
  ```

### ⚠️ Preview URLs

- يحتاج wildcard DNS: `*.yourdomain.com → server-ip`
- Traefik يُنشئ routes تلقائيًا بناءً على container labels
- إذا preview URL لا يعمل:
  1. Check Traefik logs: `docker logs vibe-edge-proxy`
  2. Verify DNS: `nslookup project-id.yourdomain.com`
  3. Check container labels: `docker inspect vibe-{project-id}`

### ⚠️ Secrets Encryption

- `GITHUB_SECRETS_KEY` يجب أن يكون **32 bytes** (Fernet requirement)
- Generate صحيح:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- إذا تغير الـkey، **جميع الsecrets القديمة لن تُفك تشفيرها**

### ⚠️ Project ID Conflicts

- Project IDs: `{username}-{project_name}`
- لا يمكن لنفس username إنشاء نفس project_name مرتين
- الحذف يُحرر الـID للاستخدام المستقبلي

---

## Agent Map (خريطة الـAgents)

هذا المستودع مُنظم في وحدات مستقلة، كل منها له `agents.md` خاص:

| الوحدة | الملف | الوصف |
|--------|------|-------|
| **Central API** | [`/api/agents.md`](./api/agents.md) | HTTP API service، auth، routing، caching |
| **Project Manager** | [`/project-manager/agents.md`](./project-manager/agents.md) | Container lifecycle، Docker operations |
| **Cleanup Service** | [`/cleanup/agents.md`](./cleanup/agents.md) | Background maintenance، log truncation |
| **Infrastructure** | [`/infra/agents.md`](./infra/agents.md) | Traefik proxy، Prometheus، Grafana |
| **Tools** | [`/tools/agents.md`](./tools/agents.md) | Helper scripts، setup، backup |
| **Templates** | [`/projects/templates/agents.md`](./projects/templates/agents.md) | Project templates، workspace initialization |

**نصيحة للـagents**: ابدأ من الـagent المناسب حسب المهمة:
- لـAPI changes → `/api/agents.md`
- لـcontainer issues → `/project-manager/agents.md`
- لـinfra setup → `/infra/agents.md`
- لـscripts/tools → `/tools/agents.md`
