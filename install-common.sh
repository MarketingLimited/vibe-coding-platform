#!/usr/bin/env bash
# Shared helpers for Vibe Coding Platform installers

# shellcheck shell=bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

init_installation_context() {
    INSTALL_DIR="${INSTALL_DIR:-/opt/vibe-coding}"
    DATA_DIR="${DATA_DIR:-/var/lib/vibe-coding}"
    BUILD_IMAGES_SCRIPT="${BUILD_IMAGES_SCRIPT:-$INSTALL_DIR/tools/build-project-images.sh}"
    LOG_FILE="${LOG_FILE:-/var/log/vibe-coding-install.log}"
    API_PORT="${API_PORT:-${VIBE_API_PORT:-9000}}"
    DOMAIN="${DOMAIN:-${VIBE_DOMAIN:-localhost}}"
}

init_logging() {
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"
    chmod 640 "$LOG_FILE"
}

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✓${NC} $*" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}✗${NC} $*" | tee -a "$LOG_FILE"
    exit 1
}

warn() {
    echo -e "${YELLOW}⚠${NC} $*" | tee -a "$LOG_FILE"
}

check_root() {
    if [ "${EUID}" -ne 0 ]; then
        error "هذا السكربت يحتاج صلاحيات root. استخدم: sudo $0"
    fi
}

# Distribution detection -----------------------------------------------------

detect_distro() {
    if [ ! -f /etc/os-release ]; then
        error "غير قادر على تحديد التوزيعة (ملف /etc/os-release غير موجود)"
    fi

    # shellcheck disable=SC1091
    . /etc/os-release

    DISTRO_ID="${ID:-unknown}"
    DISTRO_NAME="${NAME:-$DISTRO_ID}"
    DISTRO_PRETTY_NAME="${PRETTY_NAME:-$DISTRO_NAME}"
    local id_like="${ID_LIKE:-}"
    local detection_string="$DISTRO_ID $id_like"

    case "$detection_string" in
        *ubuntu*|*debian*|*linuxmint*|*pop*)
            DISTRO_FAMILY="debian"
            PACKAGE_MANAGER="apt"
            PACKAGE_UPDATE_CMD="DEBIAN_FRONTEND=noninteractive apt-get update -y"
            PACKAGE_INSTALL_CMD="DEBIAN_FRONTEND=noninteractive apt-get install -y"
            ;;
        *rocky*|*almalinux*|*centos*|*rhel*|*fedora*)
            DISTRO_FAMILY="rhel"
            if command -v dnf >/dev/null 2>&1; then
                PACKAGE_MANAGER="dnf"
                PACKAGE_UPDATE_CMD="dnf -y makecache"
                PACKAGE_INSTALL_CMD="dnf -y install"
            else
                PACKAGE_MANAGER="yum"
                PACKAGE_UPDATE_CMD="yum -y makecache"
                PACKAGE_INSTALL_CMD="yum -y install"
            fi
            ;;
        *sles*|*opensuse*)
            DISTRO_FAMILY="suse"
            PACKAGE_MANAGER="zypper"
            PACKAGE_UPDATE_CMD="zypper --non-interactive refresh"
            PACKAGE_INSTALL_CMD="zypper --non-interactive install"
            ;;
        *)
            DISTRO_FAMILY="unknown"
            PACKAGE_MANAGER=""
            PACKAGE_UPDATE_CMD=""
            PACKAGE_INSTALL_CMD=""
            ;;
    esac

    log "نظام التشغيل: $DISTRO_PRETTY_NAME (العائلة: $DISTRO_FAMILY)"
}

require_supported_family() {
    local supported=false
    for family in "$@"; do
        if [ "$DISTRO_FAMILY" = "$family" ]; then
            supported=true
            break
        fi
    done

    if [ "$supported" = false ]; then
        error "التوزيعة الحالية ($DISTRO_PRETTY_NAME) غير مدعومة بواسطة هذا السكربت"
    fi
}

ensure_prerequisites() {
    if [ "${DRY_RUN:-false}" = true ]; then
        log "تخطي تثبيت الحزم (وضع التجربة)"
        return 0
    fi

    if [ -z "${PACKAGE_MANAGER:-}" ]; then
        warn "لم يتم التعرف على مدير الحزم. تأكد من تثبيت curl وgit وopenssl يدوياً"
        return 0
    fi

    local packages=(curl git openssl ca-certificates tar)

    log "تحديث فهارس الحزم ($PACKAGE_MANAGER)..."
    if ! bash -lc "$PACKAGE_UPDATE_CMD" >> "$LOG_FILE" 2>&1; then
        warn "فشل تحديث فهارس الحزم. يمكن المتابعة إن كانت الحزم مثبتة مسبقاً"
    fi

    log "تثبيت الحزم المطلوبة: ${packages[*]}"
    if ! bash -lc "$PACKAGE_INSTALL_CMD ${packages[*]}" >> "$LOG_FILE" 2>&1; then
        warn "تعذر تثبيت بعض الحزم. تأكد من توفر curl وgit وopenssl يدوياً"
    else
        success "تم التحقق من المتطلبات الأساسية"
    fi
}

check_plesk() {
    if [ -f /usr/local/psa/version ]; then
        local version
        version=$(cat /usr/local/psa/version)
        log "Plesk مثبت: $version"
        return 0
    fi

    warn "Plesk غير مثبت (الاستمرار بدون تكامل Plesk)"
    return 1
}

ensure_docker() {
    if [ "${DRY_RUN:-false}" = true ]; then
        log "تخطي تثبيت Docker (وضع التجربة)"
        return 0
    fi

    if ! command -v docker >/dev/null 2>&1; then
        log "تثبيت Docker باستخدام سكربت get.docker.com..."
        curl -fsSL https://get.docker.com | sh >> "$LOG_FILE" 2>&1
        systemctl enable docker >> "$LOG_FILE" 2>&1 || true
        systemctl start docker >> "$LOG_FILE" 2>&1 || true
        success "تم تثبيت Docker"
    else
        success "Docker مثبت: $(docker --version)"
    fi

    if ! docker compose version >/dev/null 2>&1; then
        error "Docker Compose v2 غير مثبت. قم بتثبيته أو ترقية Docker"
    fi
}

check_port() {
    if ss -tlnp | grep -q ":$API_PORT " ; then
        error "المنفذ $API_PORT مستخدم. غيّر القيمة عبر: export VIBE_API_PORT=9001"
    fi
    success "المنفذ $API_PORT متاح"
}

create_directories() {
    log "إنشاء المجلدات..."

    mkdir -p "$INSTALL_DIR"/{api,project-manager,cleanup,config,infra,projects,tools}
    mkdir -p "$DATA_DIR"/{projects,databases,logs}

    chmod 750 "$INSTALL_DIR" "$DATA_DIR"

    success "تم إنشاء المجلدات"
}

download_files() {
    log "تنزيل ملفات المنصة..."
    cd "$INSTALL_DIR"
    if [ -d .git ]; then
        git pull origin main >> "$LOG_FILE" 2>&1
    else
        git clone https://github.com/MarketingLimited/vibe-coding-platform.git . >> "$LOG_FILE" 2>&1
    fi
    success "تم جلب آخر إصدار"
}

generate_secrets() {
    log "توليد المفاتيح وملفات البيئة..."

    local api_key db_password github_key github_path project_manager_port
    api_key=$(openssl rand -hex 32)
    db_password=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)
    project_manager_port=9400
    github_key=$(openssl rand -hex 32)
    github_path="/data/github-secrets.bin"

    cat > "$INSTALL_DIR/config/.env" << EOF_ENV
# Vibe Coding Platform Configuration
# Generated: $(date)

# API Settings
API_PORT=$API_PORT
API_KEY=$api_key
API_HOST=0.0.0.0

# Domain
DOMAIN=$DOMAIN

# Database
DB_PATH=/data/projects.db
DB_PASSWORD=$db_password

# GitHub secrets storage
GITHUB_SECRETS_PATH=$github_path
GITHUB_SECRETS_KEY=$github_key

# Paths
INSTALL_DIR=$INSTALL_DIR
DATA_DIR=$DATA_DIR

# Limits
MAX_PROJECTS_PER_USER=10
PROJECT_CPU_LIMIT=2.0
PROJECT_MEMORY_LIMIT=4G
PROJECT_STORAGE_LIMIT=10G

# Timeouts
EXEC_TIMEOUT=300
MAX_OUTPUT_SIZE=10485760

# Security
ENABLE_RATE_LIMIT=true
RATE_LIMIT_PER_MINUTE=100

# Internal services
PROJECT_MANAGER_PORT=$project_manager_port

# Cleanup
CLEANUP_INTERVAL=86400
MAX_PROJECT_AGE_DAYS=30
MAX_LOG_SIZE_MB=100
EOF_ENV

    chmod 600 "$INSTALL_DIR/config/.env"
    cp "$INSTALL_DIR/config/.env" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"

    success "تم تجهيز ملفات التكوين"
}

setup_firewall() {
    log "تكوين الجدار الناري (UFW)..."
    if command -v ufw >/dev/null 2>&1; then
        ufw allow from 127.0.0.1 to any port "$API_PORT" >> "$LOG_FILE" 2>&1 || true
        ufw allow from ::1 to any port "$API_PORT" >> "$LOG_FILE" 2>&1 || true
        ufw deny "$API_PORT" >> "$LOG_FILE" 2>&1 || true
        success "تم تحديث قواعد UFW"
    else
        warn "UFW غير مثبت، تخطي تكوين الجدار الناري"
    fi
}

create_docker_network() {
    log "فحص شبكة Docker..."
    if ! docker network ls | grep -q "vibe-network"; then
        docker network create \
            --driver bridge \
            --subnet 172.30.0.0/16 \
            --opt com.docker.network.bridge.name=vibe0 \
            vibe-network >> "$LOG_FILE" 2>&1
        success "تم إنشاء شبكة vibe-network"
    else
        success "الشبكة موجودة مسبقاً"
    fi
}

build_images() {
    log "بناء صور Docker..."
    cd "$INSTALL_DIR"
    docker compose build --no-cache >> "$LOG_FILE" 2>&1
    if [ -x "$BUILD_IMAGES_SCRIPT" ]; then
        log "بناء صور المشاريع الأساسية..."
        "$BUILD_IMAGES_SCRIPT" >> "$LOG_FILE" 2>&1
    else
        warn "لم يتم العثور على سكربت بناء صور المشاريع ($BUILD_IMAGES_SCRIPT)"
    fi
    success "انتهى بناء الصور"
}

start_services() {
    log "تشغيل الخدمات عبر Docker Compose..."
    cd "$INSTALL_DIR"
    docker compose up -d >> "$LOG_FILE" 2>&1

    log "انتظار جاهزية API على المنفذ $API_PORT..."
    for _ in {1..30}; do
        if curl -sf "http://localhost:$API_PORT/health" >/dev/null 2>&1; then
            success "API جاهز"
            return 0
        fi
        sleep 1
    done
    warn "قد يستغرق API وقتاً أطول ليصبح جاهزاً"
}

create_management_scripts() {
    log "إنشاء سكربتات الإدارة في /usr/local/bin..."

    cat > /usr/local/bin/vibe-status << 'EOS'
#!/bin/bash
cd /opt/vibe-coding && docker compose ps
EOS

    cat > /usr/local/bin/vibe-logs << 'EOS'
#!/bin/bash
cd /opt/vibe-coding && docker compose logs -f "$@"
EOS

    cat > /usr/local/bin/vibe-restart << 'EOS'
#!/bin/bash
cd /opt/vibe-coding && docker compose restart
EOS

    cat > /usr/local/bin/vibe-stop << 'EOS'
#!/bin/bash
cd /opt/vibe-coding && docker compose stop
EOS

    cat > /usr/local/bin/vibe-start << 'EOS'
#!/bin/bash
cd /opt/vibe-coding && docker compose start
EOS

    cat > /usr/local/bin/vibe-update << 'EOS'
#!/bin/bash
cd /opt/vibe-coding
 git pull origin main
 docker compose build
 docker compose up -d
EOS

    chmod +x /usr/local/bin/vibe-*
    success "سكربتات الإدارة جاهزة"
}

setup_systemd() {
    log "إعداد خدمة systemd..."
    cat > /etc/systemd/system/vibe-coding.service << EOF_SERVICE
[Unit]
Description=Vibe Coding Platform
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
ExecReload=/usr/bin/docker compose restart

[Install]
WantedBy=multi-user.target
EOF_SERVICE

    systemctl daemon-reload >> "$LOG_FILE" 2>&1 || true
    systemctl enable vibe-coding.service >> "$LOG_FILE" 2>&1 || true
    success "تم إنشاء خدمة systemd"
}

show_summary() {
    cat << EOF_SUMMARY
${GREEN}═══════════════════════════════════════════════════════════════${NC}
${GREEN}   تم تثبيت Vibe Coding Platform بنجاح! 🎉${NC}
${GREEN}═══════════════════════════════════════════════════════════════${NC}

${BLUE}📋 معلومات الوصول:${NC}
   - API Endpoint:  http://localhost:$API_PORT
   - API Key:       (راجع $INSTALL_DIR/config/.env)
   - GitHub Secrets: /data/github-secrets.bin
   - Health Check:  http://localhost:$API_PORT/health

${YELLOW}⚠️  مهم للأمان:${NC}
   - API يعمل على localhost فقط
   - استخدم Reverse Proxy للوصول الخارجي عند الحاجة

${BLUE}🔧 أوامر الإدارة:${NC}
   vibe-status      # حالة الخدمات
   vibe-logs        # عرض السجلات
   vibe-restart     # إعادة تشغيل
   vibe-stop        # إيقاف
   vibe-start       # تشغيل
   vibe-update      # تحديث

${BLUE}📂 المجلدات:${NC}
   التثبيت:    $INSTALL_DIR
   البيانات:   $DATA_DIR
   السجلات:    $DATA_DIR/logs
   التكوين:    $INSTALL_DIR/config/.env
   صور المشاريع: tools/build-project-images.sh

${GREEN}═══════════════════════════════════════════════════════════════${NC}
EOF_SUMMARY
}
