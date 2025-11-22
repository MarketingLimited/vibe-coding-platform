# Infrastructure - دليل الـAgent

## Purpose

مجلد **infra/** يحتوي على البنية التحتية الاختيارية للمنصة:
- **Edge Proxy (Traefik)**: TLS termination، HTTP→HTTPS redirect، dynamic routing
- **Monitoring Stack (Prometheus + Grafana)**: Metrics collection، dashboards، alerting
- **Certificates Management**: SSL/TLS certificate storage

هذه المكونات **اختيارية** ويمكن تشغيلها حسب احتياجات الإنتاج.

---

## Owned Scope

### Edge Proxy (Traefik)
- `/infra/edge/traefik.yml` - Static configuration
- `/infra/edge/dynamic/` - Dynamic routing rules (file provider)
- `/infra/edge/credentials/` - Basic auth credentials (htpasswd)
- Ports: 80 (HTTP), 443 (HTTPS), 8080 (Dashboard)

### Monitoring Stack
- `/infra/monitoring/prometheus.yml` - Prometheus scrape configuration
- `/infra/monitoring/grafana/provisioning/` - Grafana dashboards و datasources
- `/infra/monitoring/docker-compose.monitoring.yml` - Monitoring services
- Ports: 9090 (Prometheus), 3000 (Grafana)

### Documentation
- `/infra/README.md` - Infrastructure setup guide

---

## Key Files & Entry Points

### Traefik Configuration

```yaml
# /infra/edge/traefik.yml
api:
  dashboard: true           # Enable web UI
  insecure: false          # Require auth for dashboard

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure    # Redirect HTTP → HTTPS
          scheme: https

  websecure:
    address: ":443"
    http:
      tls:
        certResolver: letsencrypt

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@yourdomain.com
      storage: /certs/acme.json
      httpChallenge:
        entryPoint: web

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false     # Only expose containers with traefik.enable=true
    network: vibe-proxy

  file:
    directory: "/dynamic"
    watch: true                # Auto-reload on file changes

log:
  level: INFO
  filePath: /logs/traefik.log

accessLog:
  filePath: /logs/access.log
```

### Prometheus Configuration

```yaml
# /infra/monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'vibe-coding-platform'

scrape_configs:
  # Central API metrics
  - job_name: 'vibe-api'
    static_configs:
      - targets: ['api:9000']
    metrics_path: '/metrics'

  # Project Manager metrics (if exposed)
  - job_name: 'vibe-project-manager'
    static_configs:
      - targets: ['project-manager:9400']
    metrics_path: '/health'

  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Redis exporter (if available)
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Docker Compose for Monitoring

```yaml
# /infra/monitoring/docker-compose.monitoring.yml
version: '3.9'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: vibe-prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    networks:
      - vibe-network

  grafana:
    image: grafana/grafana:latest
    container_name: vibe-grafana
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    networks:
      - vibe-network
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:

networks:
  vibe-network:
    external: true
```

---

## Dependencies & Interfaces

### Traefik Dependencies

```
Traefik Edge Proxy
    │
    ├─→ Docker Socket (/var/run/docker.sock)
    │   └─ Discover services with labels
    │   └─ Dynamic routing configuration
    │
    ├─→ Let's Encrypt ACME
    │   └─ Automatic SSL certificate generation
    │   └─ Certificate renewal
    │
    ├─→ File System
    │   ├─ /certs/acme.json - Certificate storage
    │   ├─ /dynamic/ - Dynamic routing rules
    │   └─ /logs/ - Access & error logs
    │
    └─→ vibe-proxy network
        └─ Separate network for edge routing
```

### Monitoring Dependencies

```
Prometheus
    │
    ├─→ Central API:9000/metrics
    ├─→ Project Manager:9400/health (optional)
    └─→ Redis Exporter:9121 (optional)

Grafana
    │
    └─→ Prometheus:9090 (datasource)
```

---

## Local Rules / Patterns

### 1. Container Label-Based Routing (Traefik)

للتعريض الأوتوماتيكي لproject containers عبر Traefik، يجب إضافة labels:

```python
# In ProjectManager.create_project()
labels = {
    # Enable Traefik
    'traefik.enable': 'true',

    # Router configuration
    f'traefik.http.routers.{project_id}.rule': f'Host(`{project_id}.{domain}`)',
    f'traefik.http.routers.{project_id}.entrypoints': 'websecure',
    f'traefik.http.routers.{project_id}.tls': 'true',
    f'traefik.http.routers.{project_id}.tls.certresolver': 'letsencrypt',

    # Service configuration
    f'traefik.http.services.{project_id}.loadbalancer.server.port': '8000',

    # Network
    'traefik.docker.network': 'vibe-proxy',
}
```

**File**: `/project-manager/app/services/router_registry.py`

### 2. Dynamic Routing Rules (File Provider)

للـstatic routes (لا تعتمد على containers):

```yaml
# /infra/edge/dynamic/api.yml
http:
  routers:
    api-router:
      rule: "Host(`api.yourdomain.com`)"
      service: api-service
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt

  services:
    api-service:
      loadBalancer:
        servers:
          - url: "http://api:9000"
```

### 3. Prometheus Metrics Exposition

في Central API:

```python
# /api/app/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Expose metrics at /metrics
Instrumentator().instrument(app).expose(app)
```

**Metrics Available**:
- `http_requests_total` - Total requests
- `http_request_duration_seconds` - Request latency
- `http_requests_in_progress` - Concurrent requests

### 4. Grafana Dashboard Provisioning

```yaml
# /infra/monitoring/grafana/provisioning/datasources/prometheus.yml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

```yaml
# /infra/monitoring/grafana/provisioning/dashboards/default.yml
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

---

## How to Run / Test

### Starting Traefik Edge Proxy

```bash
# Using docker-compose.yml (with Traefik service)
cd /home/user/vibe-coding-platform

# Ensure vibe-proxy network exists
docker network create vibe-proxy

# Start Traefik
docker-compose up -d edge-proxy

# Check logs
docker logs vibe-edge-proxy --tail 50

# Access dashboard
# http://localhost:8080/dashboard/ (requires auth)
```

### Configuring Let's Encrypt

1. **Update email** في `/infra/edge/traefik.yml`:
```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      email: your-email@yourdomain.com  # ← Update this
```

2. **Ensure port 80 accessible** (للـHTTP challenge):
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

3. **Restart Traefik**:
```bash
docker-compose restart edge-proxy
```

4. **Verify certificate**:
```bash
# Check acme.json
docker exec vibe-edge-proxy cat /certs/acme.json | jq

# Test HTTPS
curl -I https://yourdomain.com
```

### Starting Monitoring Stack

```bash
cd /home/user/vibe-coding-platform/infra/monitoring

# Start Prometheus + Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Check Prometheus
curl http://localhost:9090/api/v1/targets

# Check Grafana
# http://localhost:3000
# Username: admin
# Password: admin (change on first login)
```

### Adding Custom Prometheus Metrics

```python
# /api/app/main.py
from prometheus_client import Counter, Histogram

# Define custom metrics
project_creations = Counter(
    'vibe_project_creations_total',
    'Total number of projects created',
    ['project_type']
)

exec_duration = Histogram(
    'vibe_exec_duration_seconds',
    'Command execution duration',
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0]
)

# Use in code
@router.post("/projects/create")
async def create_project(data: ProjectCreate):
    project_creations.labels(project_type=data.project_type).inc()
    # ...

@router.post("/exec")
async def execute(request: ExecRequest):
    start_time = time.time()
    # ... execute command
    exec_duration.observe(time.time() - start_time)
```

---

## Common Tasks for Agents

### مهمة: إضافة domain جديد للـTraefik

**File**: `/infra/edge/dynamic/custom-domain.yml`

```yaml
http:
  routers:
    my-custom-service:
      rule: "Host(`custom.yourdomain.com`)"
      service: custom-service
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt

  services:
    custom-service:
      loadBalancer:
        servers:
          - url: "http://my-backend:8080"
```

**Test**:
```bash
curl https://custom.yourdomain.com
```

### مهمة: Enable basic auth للـTraefik dashboard

1. **Generate password hash**:
```bash
# Install htpasswd
sudo apt-get install apache2-utils

# Create credentials file
htpasswd -c /infra/edge/credentials/users admin
# Enter password when prompted
```

2. **Update Traefik config** `/infra/edge/traefik.yml`:
```yaml
api:
  dashboard: true

http:
  middlewares:
    dashboard-auth:
      basicAuth:
        usersFile: "/credentials/users"

  routers:
    dashboard:
      rule: "Host(`traefik.yourdomain.com`)"
      service: api@internal
      middlewares:
        - dashboard-auth
```

3. **Mount credentials** في `docker-compose.yml`:
```yaml
edge-proxy:
  volumes:
    - ./infra/edge/credentials:/credentials:ro
```

### مهمة: Add Grafana dashboard

1. **Create dashboard JSON** في `/infra/monitoring/grafana/provisioning/dashboards/vibe.json`:

```json
{
  "dashboard": {
    "title": "Vibe Coding Platform",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Active Projects",
        "targets": [
          {
            "expr": "count(container_running{name=~\"vibe-.*\"})"
          }
        ]
      }
    ]
  }
}
```

2. **Restart Grafana**:
```bash
docker-compose -f infra/monitoring/docker-compose.monitoring.yml restart grafana
```

### مهمة: Configure alert rules (Prometheus)

**File**: `/infra/monitoring/alert-rules.yml`

```yaml
groups:
  - name: vibe-alerts
    interval: 30s
    rules:
      # Alert if API is down
      - alert: APIDown
        expr: up{job="vibe-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Vibe API is down"
          description: "API service has been down for more than 1 minute"

      # Alert if high error rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} req/s"

      # Alert if too many projects
      - alert: TooManyProjects
        expr: count(container_running{name=~"vibe-.*"}) > 100
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "High number of active projects"
```

**Update Prometheus config**:
```yaml
# /infra/monitoring/prometheus.yml
rule_files:
  - /etc/prometheus/alert-rules.yml

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### مهمة: Debug TLS certificate issues

**Checklist**:

1. **Check Traefik logs**:
```bash
docker logs vibe-edge-proxy | grep -i acme
docker logs vibe-edge-proxy | grep -i certificate
```

2. **Verify DNS pointing**:
```bash
nslookup yourdomain.com
# Should point to your server IP
```

3. **Check acme.json permissions**:
```bash
docker exec vibe-edge-proxy ls -la /certs/acme.json
# Should be -rw------- (600)
```

4. **Verify port 80 accessible** (للـACME challenge):
```bash
curl -I http://yourdomain.com/.well-known/acme-challenge/test
# Should not be blocked by firewall
```

5. **Force certificate renewal**:
```bash
# Remove acme.json
rm /srv/vibe/certs/acme.json

# Restart Traefik
docker-compose restart edge-proxy

# Check logs
docker logs -f vibe-edge-proxy
```

6. **Use Let's Encrypt staging** (للـtesting):
```yaml
# /infra/edge/traefik.yml
certificatesResolvers:
  letsencrypt:
    acme:
      caServer: https://acme-staging-v02.api.letsencrypt.org/directory  # ← Staging
```

---

## Notes / Gotchas

### ⚠️ Traefik Network Requirements

- Traefik يجب أن يكون على **نفس الشبكة** مع containers التي يُعرضها
- Use `vibe-proxy` network منفصلة عن `vibe-network`
- Containers تحتاج attachment لـ**كلا الشبكتين**:
  ```yaml
  networks:
    - vibe-network    # Internal communication
    - vibe-proxy      # Traefik routing
  ```

### ⚠️ Let's Encrypt Rate Limits

- **50 certificates** per registered domain per week
- **5 duplicate certificates** per week
- Use **staging environment** للtesting
- Production: use carefully planned certificate requests

### ⚠️ acme.json File Permissions

- **Must be 600** (read/write owner only)
- If permissions wrong: Traefik refuses to start
- Fix:
  ```bash
  chmod 600 /srv/vibe/certs/acme.json
  ```

### ⚠️ Wildcard Certificates

- Traefik supports wildcard (`*.yourdomain.com`)
- Requires **DNS challenge** (not HTTP challenge)
- Needs API credentials for DNS provider

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      dnsChallenge:
        provider: cloudflare
        resolvers:
          - "1.1.1.1:53"
```

### ⚠️ Prometheus Data Retention

- Default retention: **15 days**
- للتعديل:
  ```yaml
  # docker-compose.monitoring.yml
  prometheus:
    command:
      - '--storage.tsdb.retention.time=30d'  # 30 days
      - '--storage.tsdb.retention.size=50GB'  # or size limit
  ```

### ⚠️ Grafana Anonymous Access

- Default: requires login
- للpublic dashboards:
  ```yaml
  # docker-compose.monitoring.yml
  grafana:
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
  ```

### ⚠️ Container Label Updates

- Traefik labels يجب أن تُضاف **عند container creation**
- لا يمكن update labels لـrunning container
- للتعديل: يجب **recreate container**

### ⚠️ Metrics Endpoint Security

- `/metrics` endpoint مُعرض بدون authentication (default)
- للproduction: add authentication middleware
- أو: expose فقط على internal network

```python
# Restrict /metrics to internal IPs
from fastapi import Request, HTTPException

@app.middleware("http")
async def restrict_metrics(request: Request, call_next):
    if request.url.path == "/metrics":
        client_ip = request.client.host
        if not client_ip.startswith("10.") and not client_ip.startswith("192.168."):
            raise HTTPException(403, "Forbidden")
    return await call_next(request)
```

### ⚠️ Grafana Dashboard Persistence

- Dashboards created في UI تُحفظ في database (volume)
- للpersistence: use provisioning files (JSON)
- أو: export dashboards و save في `/infra/monitoring/grafana/provisioning/dashboards/`
