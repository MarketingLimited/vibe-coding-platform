# Tools & Scripts - دليل الـAgent

## Purpose

مجلد **tools/** يحتوي على نصوص برمجية مساعدة (helper scripts) للصيانة والتطوير والنشر:
- **Setup Scripts**: تجهيز البيئة التطويرية والإنتاجية
- **Build Scripts**: بناء Docker images للمشاريع
- **Status & Monitoring**: فحص حالة الخدمات
- **Logging**: عرض logs بشكل منظم
- **Backup & Restore**: نسخ احتياطي للبيانات
- **OpenAPI**: توليد مواصفات API

كل هذه النصوص **اختيارية** وتُستخدم للتسهيل الإداري.

---

## Owned Scope

### Setup Tools
- `/tools/setup/activate.sh` - Interactive environment setup wizard
- مساعد تفاعلي لإنشاء `.env` و تجهيز المتغيرات البيئية

### Build Tools
- `/tools/build-project-images.sh` - Build all project type Docker images
- يبني images لـPython, Node.js, PHP, Full-stack

### Status & Monitoring Tools
- `/tools/vibe-status.sh` - Check platform health and service status
- يعرض حالة الخدمات، containers، Redis، وموارد النظام

### Logging Tools
- `/tools/vibe-logs.sh` - Tail logs for specific services
- عرض logs مع filtering و colored output

### Backup & Restore
- `/tools/vibe-backup.sh` - Backup projects and data
- نسخ احتياطي للـprojects، databases، configurations

### OpenAPI Tools
- `/tools/openapi/render-multitenant-spec.sh` - Generate OpenAPI specification
- توليد OpenAPI spec من FastAPI endpoints

### Documentation
- `/tools/README.md` - Tools usage guide

---

## Key Files & Entry Points

### Setup Script

```bash
# /tools/setup/activate.sh
#!/bin/bash

# Interactive setup wizard
# Prompts for:
# - API_KEY
# - DOMAIN
# - GITHUB_SECRETS_KEY
# - Database settings
# - Resource limits
# - Rate limits

# Creates /config/.env with all settings
# Creates required directories (/projects, /data, /logs)
# Sets proper permissions

echo "=== Vibe Coding Platform Setup ==="
echo ""

# 1. Generate API key
read -p "Enter API key (or press Enter to generate): " api_key
if [ -z "$api_key" ]; then
    api_key=$(openssl rand -hex 32)
    echo "Generated API key: $api_key"
fi

# 2. Domain configuration
read -p "Enter your domain (e.g., example.com): " domain

# 3. Generate encryption key
secrets_key=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')

# 4. Write .env file
cat > /config/.env <<EOF
# API Configuration
API_KEY=$api_key
DOMAIN=$domain
API_PUBLIC_BASE_URL=https://api.$domain

# Secrets
GITHUB_SECRETS_KEY=$secrets_key

# Database
DB_PATH=/data/projects.db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# ... (more settings)
EOF

echo "Setup complete! Configuration saved to /config/.env"
```

**Usage**:
```bash
bash tools/setup/activate.sh
```

### Build Project Images

```bash
# /tools/build-project-images.sh
#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGES_DIR="$SCRIPT_DIR/../project-manager/templates/images"

echo "=== Building Vibe Project Images ==="

# Build each project type
for type in python nodejs php full; do
    echo ""
    echo "Building vibe-project-$type..."

    docker build \
        -t vibe-project-$type:latest \
        -f "$IMAGES_DIR/$type/Dockerfile" \
        "$IMAGES_DIR/$type"

    echo "✓ vibe-project-$type built successfully"
done

echo ""
echo "=== All images built successfully ==="
docker images | grep vibe-project
```

**Usage**:
```bash
bash tools/build-project-images.sh
```

### Status Check Script

```bash
# /tools/vibe-status.sh
#!/bin/bash

echo "=== Vibe Coding Platform Status ==="
echo ""

# 1. Docker services
echo "📦 Docker Services:"
docker-compose ps

echo ""

# 2. Vibe containers
echo "🚀 Project Containers:"
docker ps --filter "label=com.vibe.project-id" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""

# 3. Redis status
echo "💾 Redis:"
docker exec vibe-redis redis-cli ping 2>/dev/null && echo "✓ Redis is running" || echo "✗ Redis is down"

# Count projects
project_count=$(docker exec vibe-redis redis-cli KEYS "project:*" | wc -l)
echo "   Active projects: $project_count"

echo ""

# 4. API health
echo "🌐 API Health:"
curl -s http://localhost:9000/health | jq '.' || echo "✗ API is down"

echo ""

# 5. Disk usage
echo "💿 Disk Usage:"
du -sh /srv/vibe/projects 2>/dev/null || echo "N/A"
du -sh /srv/vibe/logs 2>/dev/null || echo "N/A"

echo ""

# 6. System resources
echo "🖥️  System Resources:"
echo "   Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "   CPU Load: $(uptime | awk -F'load average:' '{print $2}')"
```

**Usage**:
```bash
bash tools/vibe-status.sh
```

### Logs Viewer

```bash
# /tools/vibe-logs.sh
#!/bin/bash

SERVICE=${1:-api}
LINES=${2:-50}

case $SERVICE in
    api)
        docker logs vibe-api --tail $LINES -f
        ;;
    project-manager|pm)
        docker logs vibe-project-manager --tail $LINES -f
        ;;
    cleanup)
        docker logs vibe-cleanup --tail $LINES -f
        ;;
    redis)
        docker logs vibe-redis --tail $LINES -f
        ;;
    traefik|edge)
        docker logs vibe-edge-proxy --tail $LINES -f
        ;;
    all)
        docker-compose logs --tail $LINES -f
        ;;
    *)
        echo "Usage: $0 <service> [lines]"
        echo "Services: api, project-manager, cleanup, redis, traefik, all"
        exit 1
        ;;
esac
```

**Usage**:
```bash
bash tools/vibe-logs.sh api           # API logs (last 50 lines)
bash tools/vibe-logs.sh pm 100        # Project Manager logs (last 100 lines)
bash tools/vibe-logs.sh all           # All services
```

### Backup Script

```bash
# /tools/vibe-backup.sh
#!/bin/bash

BACKUP_DIR="/backups/vibe-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "=== Vibe Platform Backup ==="
echo "Backup location: $BACKUP_DIR"
echo ""

# 1. Backup database
echo "📦 Backing up database..."
cp /srv/vibe/data/projects.db "$BACKUP_DIR/projects.db"
cp /srv/vibe/data/github-secrets.bin "$BACKUP_DIR/github-secrets.bin" 2>/dev/null

# 2. Backup configuration
echo "📝 Backing up configuration..."
cp /home/user/vibe-coding-platform/config/.env "$BACKUP_DIR/.env"

# 3. Backup projects (compressed)
echo "💾 Backing up project workspaces..."
tar -czf "$BACKUP_DIR/projects.tar.gz" -C /srv/vibe/projects . 2>/dev/null

# 4. Backup Redis data
echo "🔴 Backing up Redis..."
docker exec vibe-redis redis-cli SAVE
cp /srv/vibe/redis/dump.rdb "$BACKUP_DIR/redis-dump.rdb" 2>/dev/null

# 5. Create manifest
cat > "$BACKUP_DIR/MANIFEST.txt" <<EOF
Vibe Coding Platform Backup
Created: $(date)
Hostname: $(hostname)

Contents:
- projects.db         : SQLite database
- github-secrets.bin  : Encrypted secrets
- .env                : Configuration
- projects.tar.gz     : All project workspaces
- redis-dump.rdb      : Redis snapshot
EOF

echo ""
echo "✓ Backup complete: $BACKUP_DIR"
echo "Size: $(du -sh $BACKUP_DIR | cut -f1)"
```

**Usage**:
```bash
bash tools/vibe-backup.sh
```

### OpenAPI Spec Generator

```bash
# /tools/openapi/render-multitenant-spec.sh
#!/bin/bash

# Generate OpenAPI spec from FastAPI
docker exec vibe-api python -c "
from app.main import app
import json

# Export OpenAPI schema
schema = app.openapi()

# Write to file
with open('/tmp/openapi.json', 'w') as f:
    json.dump(schema, f, indent=2)
" 2>/dev/null

# Copy from container to host
docker cp vibe-api:/tmp/openapi.json ./openapi.json

echo "✓ OpenAPI spec generated: openapi.json"
```

**Usage**:
```bash
bash tools/openapi/render-multitenant-spec.sh
```

---

## Dependencies & Interfaces

### System Dependencies

```
Tools Scripts
    │
    ├─→ bash (shell interpreter)
    ├─→ docker + docker-compose
    ├─→ jq (JSON processing)
    ├─→ curl (HTTP testing)
    ├─→ openssl (key generation)
    ├─→ python3 (for setup script)
    └─→ tar, gzip (for backups)
```

### External Services (for scripts)

```
Scripts → Docker Engine (container management)
Scripts → Docker Compose (orchestration)
Scripts → Redis CLI (data inspection)
Scripts → File System (backups, logs)
```

---

## Local Rules / Patterns

### 1. Script Exit Codes

جميع النصوص تتبع convention:
- **Exit 0**: Success
- **Exit 1**: General error
- **Exit 2**: Invalid arguments

### 2. Colored Output Pattern

```bash
# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Usage
echo -e "${GREEN}✓ Success${NC}"
echo -e "${RED}✗ Error${NC}"
echo -e "${YELLOW}⚠ Warning${NC}"
```

### 3. Error Handling

```bash
set -e          # Exit on error
set -u          # Exit on undefined variable
set -o pipefail # Exit on pipe failure

# Or with trap
trap 'echo "Error on line $LINENO"' ERR
```

### 4. Docker Compose Detection

```bash
# Check if docker-compose v2 or v1
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi
```

---

## How to Run / Test

### Running Setup Script

```bash
cd /home/user/vibe-coding-platform

# Interactive setup
bash tools/setup/activate.sh

# Verify .env created
cat config/.env
```

### Building Project Images

```bash
# Build all images
bash tools/build-project-images.sh

# Verify images
docker images | grep vibe-project

# Test image
docker run -it --rm vibe-project-python:latest python --version
```

### Checking Platform Status

```bash
# Full status
bash tools/vibe-status.sh

# Quick health check
curl http://localhost:9000/health | jq
```

### Viewing Logs

```bash
# API logs
bash tools/vibe-logs.sh api

# Project Manager logs with more lines
bash tools/vibe-logs.sh pm 200

# All services
bash tools/vibe-logs.sh all
```

### Creating Backup

```bash
# Full backup
bash tools/vibe-backup.sh

# List backups
ls -lh /backups/

# Restore from backup
tar -xzf /backups/vibe-20240115-120000/projects.tar.gz -C /srv/vibe/projects/
```

### Generating OpenAPI Spec

```bash
bash tools/openapi/render-multitenant-spec.sh

# View spec
cat openapi.json | jq '.paths'

# Serve with Swagger UI
docker run -p 8080:8080 \
  -e SWAGGER_JSON=/spec/openapi.json \
  -v $(pwd)/openapi.json:/spec/openapi.json \
  swaggerapi/swagger-ui
```

---

## Common Tasks for Agents

### مهمة: إضافة script جديد

**Example**: Add disk usage monitor script

1. **Create script** `/tools/vibe-disk-usage.sh`:
```bash
#!/bin/bash

echo "=== Disk Usage by Project ==="
echo ""

for project_dir in /srv/vibe/projects/*; do
    if [ -d "$project_dir" ]; then
        project_name=$(basename "$project_dir")
        size=$(du -sh "$project_dir" | cut -f1)
        echo "$project_name: $size"
    fi
done | sort -h -k2
```

2. **Make executable**:
```bash
chmod +x tools/vibe-disk-usage.sh
```

3. **Test**:
```bash
bash tools/vibe-disk-usage.sh
```

### مهمة: Update setup script لإضافة إعداد جديد

**File**: `/tools/setup/activate.sh`

```bash
# Add new configuration option
read -p "Enable debug mode? (y/n): " enable_debug

if [ "$enable_debug" = "y" ]; then
    DEBUG_MODE=true
else
    DEBUG_MODE=false
fi

# Add to .env
echo "DEBUG_MODE=$DEBUG_MODE" >> /config/.env
```

### مهمة: Add automated backup cron job

1. **Create cron script** `/tools/cron/daily-backup.sh`:
```bash
#!/bin/bash

# Run backup
/home/user/vibe-coding-platform/tools/vibe-backup.sh

# Delete backups older than 7 days
find /backups -name "vibe-*" -mtime +7 -exec rm -rf {} \;

# Send notification
curl -X POST https://your-webhook.com/backup-complete \
  -d '{"status": "success", "date": "'$(date)'"}'
```

2. **Add to crontab**:
```bash
crontab -e

# Add line:
0 2 * * * /home/user/vibe-coding-platform/tools/cron/daily-backup.sh >> /var/log/vibe-backup.log 2>&1
```

### مهمة: Debug script failures

**Checklist**:

1. **Enable debug mode**:
```bash
bash -x tools/vibe-status.sh
# Shows each command before execution
```

2. **Check permissions**:
```bash
ls -la tools/*.sh
# All should be executable (rwxr-xr-x)
```

3. **Check dependencies**:
```bash
which jq docker docker-compose curl
```

4. **Check Docker access**:
```bash
docker ps
# Should work without sudo
# If not: add user to docker group
sudo usermod -aG docker $USER
```

5. **Check paths**:
```bash
# Scripts assume specific paths
ls /srv/vibe/projects
ls /home/user/vibe-coding-platform/config/.env
```

### مهمة: Add script logging

**Pattern**:
```bash
#!/bin/bash

LOG_FILE="/var/log/vibe-scripts.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Script started"
# ... script logic
log "Script completed"
```

---

## Notes / Gotchas

### ⚠️ Script Permissions

- جميع النصوص يجب أن تكون **executable**: `chmod +x script.sh`
- إذا لم تكن executable: `bash: Permission denied`
- Fix:
  ```bash
  chmod +x tools/*.sh
  ```

### ⚠️ Path Dependencies

- النصوص تفترض تشغيلها من **repository root**:
  ```bash
  cd /home/user/vibe-coding-platform
  bash tools/vibe-status.sh  # ✓ Correct
  ```

- لا تُشغلها من داخل `/tools`:
  ```bash
  cd tools
  bash vibe-status.sh  # ✗ May fail (relative paths broken)
  ```

### ⚠️ Docker Command Availability

- النصوص تستخدم `docker` و `docker-compose`
- Docker Compose v2 uses `docker compose` (space, not hyphen)
- Detection pattern:
  ```bash
  if command -v docker-compose &> /dev/null; then
      COMPOSE="docker-compose"
  else
      COMPOSE="docker compose"
  fi
  ```

### ⚠️ jq Dependency

- `vibe-status.sh` يحتاج `jq` لـJSON parsing
- إذا غير موجود:
  ```bash
  sudo apt-get install jq  # Debian/Ubuntu
  sudo yum install jq      # RHEL/CentOS
  ```

### ⚠️ Backup Size

- Full project backups يمكن أن تكون **كبيرة جداً**
- Use selective backup:
  ```bash
  # Backup only metadata, not workspaces
  tar -czf backup.tar.gz /srv/vibe/data /config/.env
  ```

### ⚠️ Redis SAVE Command

- `redis-cli SAVE` يُوقف Redis مؤقتاً (blocking)
- للproduction: use `BGSAVE` (background save):
  ```bash
  docker exec vibe-redis redis-cli BGSAVE
  ```

### ⚠️ OpenAPI Spec Changes

- OpenAPI spec يتغير مع كل code change
- يجب re-generate بعد API modifications
- Automate في CI/CD:
  ```yaml
  # .github/workflows/openapi.yml
  - name: Generate OpenAPI spec
    run: bash tools/openapi/render-multitenant-spec.sh
  ```

### ⚠️ Script Output Buffering

- Python output قد يكون buffered في scripts
- Fix: use `-u` flag:
  ```bash
  python -u script.py
  ```

### ⚠️ Color Output in Logs

- ANSI color codes تُكتب في log files
- Strip colors في logs:
  ```bash
  script.sh 2>&1 | sed 's/\x1b\[[0-9;]*m//g' > output.log
  ```

### ⚠️ Cron Environment

- Cron jobs لها PATH محدود
- Use absolute paths:
  ```bash
  #!/bin/bash
  PATH=/usr/local/bin:/usr/bin:/bin
  /usr/bin/docker ps
  ```

### ⚠️ Parallel Script Execution

- لا تُشغل `vibe-backup.sh` مرتين بالتزامن
- قد يحدث corruption للـbackups
- Use lock file:
  ```bash
  LOCK_FILE="/tmp/vibe-backup.lock"

  if [ -f "$LOCK_FILE" ]; then
      echo "Backup already running"
      exit 1
  fi

  touch "$LOCK_FILE"
  trap "rm -f $LOCK_FILE" EXIT

  # ... backup logic
  ```
