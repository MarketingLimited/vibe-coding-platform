# البنية التقنية - Vibe Coding Platform

## نظرة عامة

منصة Vibe Coding مبنية على معمارية Microservices مع عزل كامل بين المكونات.

## المكونات الرئيسية

### 1. Traefik (Reverse Proxy)
```
Internet → Port 443 → Traefik
                       ↓
          ┌────────────┴────────────┐
          ↓                         ↓
    /code/{project}           /api/{project}
          ↓                         ↓
    Code Server (8443)        FastAPI (8000)
```

**المميزات:**
- TLS تلقائي عبر Let's Encrypt
- توجيه ديناميكي بناءً على المسارات
- Rate limiting مدمج
- Middleware للأمان

**التكوين:**
```yaml
# infra/traefik/docker-compose.yml
- Ports: 80, 443
- Network: edge
- Volumes: letsencrypt, config, logs
```

### 2. DevBox Container

```
DevBox (Ubuntu 22.04)
├── Services
│   ├── SSH Server (Port 22)
│   ├── Code-Server (Port 8443)
│   └── Exec API (Port 8000)
├── Languages
│   ├── Python 3.11
│   ├── Node.js 20
│   ├── PHP 8.3
│   ├── Go 1.22
│   └── Rust (stable)
├── Databases
│   ├── PostgreSQL Client
│   ├── MySQL Client
│   └── SQLite3
└── Tools
    ├── Git, Docker CLI
    ├── ripgrep, fd, jq
    └── tree, make, curl
```

**الأمان:**
- User: dev (non-root, UID 1000)
- Read-only filesystem
- Dropped capabilities
- Resource limits (CPU/Memory)
- Network isolation

### 3. Socket Proxy

```
DevBox → Socket Proxy → Docker Host
   ↓         ↓              ↓
  docker  2375/tcp    /var/run/docker.sock
```

**القيود:**
- CONTAINERS=1 (list, inspect)
- IMAGES=1 (list)
- NETWORKS=1 (list)
- VOLUMES=1 (list)
- INFO=1 (system info)
- BUILD=0 (no build)
- EXEC=0 (no exec)

### 4. Exec API (FastAPI)

```python
POST /exec
├── Validation
│   ├── API Key check
│   ├── Rate limiting
│   ├── Allowlist check
│   └── Path validation
├── Execution
│   ├── Spawn subprocess
│   ├── Monitor timeout
│   └── Capture output
└── Response
    ├── stdout/stderr
    ├── returncode
    └── elapsed_seconds
```

**الحدود:**
- Timeout: 90s (configurable)
- Max output: 5MB
- Rate limit: 100 req/min
- Workspace only: /workspace

### 5. قواعد البيانات (اختيارية)

```
PostgreSQL 16
├── Port: 5432
├── Volume: postgres_data
├── Network: project_net
└── Health check: pg_isready

MySQL 8.0
├── Port: 3306
├── Volume: mysql_data
├── Network: project_net
└── Health check: mysqladmin ping

Redis 7
├── Port: 6379
├── Volume: redis_data
├── Network: project_net
└── Health check: redis-cli ping
```

## تدفق البيانات

### تنفيذ أمر عبر GPT

```
1. ChatGPT
   ↓ (HTTPS + API Key)
2. Traefik
   ↓ (StripPrefix + Security headers)
3. DevBox → Exec API
   ↓ (Validation)
4. Exec API
   ↓ (bash -lc "command")
5. Subprocess
   ↓ (stdout/stderr)
6. Exec API
   ↓ (JSON response)
7. Traefik
   ↓ (HTTPS)
8. ChatGPT
```

### الوصول لـ VS Code

```
1. Browser
   ↓ (HTTPS)
2. Traefik
   ↓ (Route: /code/{project})
3. DevBox → Code-Server
   ↓ (Password auth)
4. Code-Server
   ↓ (WebSocket)
5. Browser
```

### Docker-in-Docker

```
1. DevBox
   ↓ (docker command)
2. Docker CLI
   ↓ (DOCKER_HOST=tcp://socket-proxy:2375)
3. Socket Proxy
   ↓ (Filtered operations)
4. Docker Host
```

## الشبكات

### Edge Network
```
edge (external)
└── Traefik
    └── All DevBox containers
```

**الاستخدام**: توجيه الطلبات الخارجية

### Project Networks
```
{project}_net (internal)
├── DevBox
├── Socket Proxy
├── PostgreSQL (optional)
├── MySQL (optional)
└── Redis (optional)
```

**الاستخدام**: عزل المشاريع عن بعضها

## التخزين

### Volumes لكل مشروع

```
{project}_workspace
├── Type: bind mount
├── Source: ./workspace
└── Target: /workspace

{project}_home
├── Type: volume
└── Target: /home/dev

{project}_postgres_data (optional)
{project}_mysql_data (optional)
{project}_redis_data (optional)
```

### Tmpfs
```
/tmp        → 512MB
/var/tmp    → 256MB
/run        → 64MB
```

**السبب**: سرعة + أمان (يُمسح عند إعادة التشغيل)

## الأمان

### Layers

```
Layer 1: Network
├── Firewall (ufw)
├── SSL/TLS (Let's Encrypt)
└── Private networks

Layer 2: Traefik
├── Rate limiting
├── Security headers
└── IP filtering (optional)

Layer 3: API
├── API Key auth
├── Request validation
└── Allowlist

Layer 4: Container
├── Non-root user
├── Read-only filesystem
├── Dropped capabilities
└── Resource limits

Layer 5: System
├── SELinux/AppArmor
├── Seccomp profiles
└── Audit logging
```

### Best Practices المطبقة

✅ Defense in depth  
✅ Principle of least privilege  
✅ Fail secure defaults  
✅ Complete mediation  
✅ Separation of duties  
✅ Audit logging  

## الأداء

### Resource Allocation

```
Per Project (default):
├── CPU: 0.5-2.0 cores
├── Memory: 512MB-4GB
├── Disk: 2-10GB
└── PIDs: 100

Traefik:
├── CPU: 0.5 cores
├── Memory: 512MB
└── Connections: 10k

Monitoring:
├── CPU: 1.0 cores
├── Memory: 2GB
└── Retention: 30 days
```

### Optimizations

```
Docker:
├── Multi-stage builds
├── Layer caching
└── BuildKit enabled

Network:
├── HTTP/2
├── Gzip compression
└── Connection pooling

Storage:
├── Overlay2 driver
├── Volume mounts
└── Tmpfs for temp files
```

## المراقبة

### Metrics (Prometheus)

```
System:
├── CPU usage
├── Memory usage
├── Disk I/O
└── Network I/O

Container:
├── Container count
├── Restart count
├── Health status
└── Resource usage

Application:
├── Request count
├── Error rate
├── Response time
└── Active connections
```

### Logs

```
/logs/
├── traefik/
│   ├── traefik.log
│   └── access.log
├── projects/
│   └── {project}/
│       ├── api.log
│       ├── code-server.log
│       ├── ssh.log
│       └── system.log
└── system/
    └── setup.log
```

### Alerts (Grafana)

```
Critical:
├── Container down
├── Disk > 90%
└── Memory > 95%

Warning:
├── High CPU usage
├── Many errors
└── Slow response
```

## Scalability

### Horizontal Scaling

```
Current: Single-host
Future:
├── Docker Swarm
├── Kubernetes
└── Cloud-native
```

### Vertical Scaling

```
Easy: Add resources
├── More CPU cores
├── More RAM
└── Faster disks
```

## Backup Strategy

### What to backup

```
Critical:
├── projects/*/workspace/
├── projects/*/.env
├── infra/traefik/letsencrypt/
└── infra/monitoring/

Nice to have:
├── Docker volumes
└── Logs (recent)
```

### Frequency

```
Daily:   Workspace data
Weekly:  Full backup
Monthly: Archive backup
```

## الترقية

### Minor updates (patch)
```bash
docker compose pull
docker compose up -d
```

### Major updates (version)
```bash
# Test in staging first
./upgrade.sh --version 2.1
```

---

**تم التوثيق**: نوفمبر 2025  
**النسخة**: 2.0  
**المعماري**: AlMoelef
