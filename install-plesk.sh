#!/usr/bin/env bash
# =============================================================================
# Vibe Coding Platform - Plesk One-Command Installer
# =============================================================================
# Compatible with: Ubuntu 24.04 + Plesk
# Installation: curl -sSL https://raw.githubusercontent.com/MarketingLimited/vibe-coding-platform/main/install-plesk.sh | sudo bash
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Configuration
INSTALL_DIR="/opt/vibe-coding"
DATA_DIR="/var/lib/vibe-coding"
BUILD_IMAGES_SCRIPT="$INSTALL_DIR/tools/build-project-images.sh"
LOG_FILE="/var/log/vibe-coding-install.log"
API_PORT="${VIBE_API_PORT:-9000}"
DOMAIN="${VIBE_DOMAIN:-localhost}"

# =============================================================================
# Functions
# =============================================================================

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

banner() {
    clear
    cat << "EOF"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ██╗   ██╗██╗██████╗ ███████╗                           ║
║     ██║   ██║██║██╔══██╗██╔════╝                           ║
║     ██║   ██║██║██████╔╝█████╗                             ║
║     ╚██╗ ██╔╝██║██╔══██╗██╔══╝                             ║
║      ╚████╔╝ ██║██████╔╝███████╗                           ║
║       ╚═══╝  ╚═╝╚═════╝ ╚══════╝                           ║
║                                                              ║
║          Vibe Coding Platform - Plesk Edition               ║
║               One-Command Installation                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF
    echo
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "هذا السكريبت يحتاج صلاحيات root. استخدم: sudo $0"
    fi
}

check_ubuntu() {
    if [ ! -f /etc/os-release ]; then
        error "نظام غير مدعوم"
    fi
    
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        error "يعمل فقط على Ubuntu (حالياً: $ID)"
    fi
    
    log "نظام التشغيل: Ubuntu $VERSION"
}

check_plesk() {
    if [ -f /usr/local/psa/version ]; then
        PLESK_VERSION=$(cat /usr/local/psa/version)
        log "Plesk مثبت: $PLESK_VERSION"
        return 0
    else
        warn "Plesk غير مثبت (سيعمل النظام بدونه)"
        return 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log "تثبيت Docker..."
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        success "تم تثبيت Docker"
    else
        success "Docker مثبت: $(docker --version)"
    fi
    
    if ! docker compose version &> /dev/null; then
        error "Docker Compose v2 غير مثبت"
    fi
}

check_port() {
    if ss -tlnp | grep -q ":$API_PORT "; then
        error "المنفذ $API_PORT مستخدم. غيّر المنفذ: export VIBE_API_PORT=9001"
    fi
    success "المنفذ $API_PORT متاح"
}

create_directories() {
    log "إنشاء المجلدات..."

    mkdir -p "$INSTALL_DIR"/{api,project-manager,cleanup,config,infra,projects,tools}
    mkdir -p "$DATA_DIR"/{projects,databases,logs}

    chmod 750 "$INSTALL_DIR"
    chmod 750 "$DATA_DIR"

    success "تم إنشاء المجلدات"
}

download_files() {
    log "تنزيل الملفات..."
    
    cd "$INSTALL_DIR"
    
    if [ -d .git ]; then
        git pull origin main
    else
        git clone https://github.com/MarketingLimited/vibe-coding-platform.git .
    fi
    
    success "تم تنزيل الملفات"
}

generate_secrets() {
    log "توليد المفاتيح الأمنية..."

    API_KEY=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)
    PROJECT_MANAGER_PORT=9400
    GITHUB_SECRETS_KEY=$(openssl rand -hex 32)
    GITHUB_SECRETS_PATH="/data/github-secrets.bin"

    cat > "$INSTALL_DIR/config/.env" << EOF
# Vibe Coding Platform Configuration
# Generated: $(date)

# API Settings
API_PORT=$API_PORT
API_KEY=$API_KEY
API_HOST=0.0.0.0

# Domain
DOMAIN=$DOMAIN

# Database
DB_PATH=/data/projects.db
DB_PASSWORD=$DB_PASSWORD

# GitHub secrets storage
GITHUB_SECRETS_PATH=$GITHUB_SECRETS_PATH
GITHUB_SECRETS_KEY=$GITHUB_SECRETS_KEY

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
PROJECT_MANAGER_PORT=$PROJECT_MANAGER_PORT

# Cleanup
CLEANUP_INTERVAL=86400
MAX_PROJECT_AGE_DAYS=30
MAX_LOG_SIZE_MB=100
EOF

    chmod 600 "$INSTALL_DIR/config/.env"
    cp "$INSTALL_DIR/config/.env" "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
    success "تم توليد المفاتيح"
}

setup_firewall() {
    log "تكوين Firewall..."
    
    if command -v ufw &> /dev/null; then
        # السماح فقط من localhost
        ufw allow from 127.0.0.1 to any port $API_PORT
        ufw allow from ::1 to any port $API_PORT
        
        # منع الوصول الخارجي
        ufw deny $API_PORT
        
        success "تم تكوين Firewall"
    else
        warn "UFW غير مثبت، تخطي تكوين Firewall"
    fi
}

create_docker_network() {
    log "إنشاء شبكة Docker..."
    
    if ! docker network ls | grep -q vibe-network; then
        docker network create \
            --driver bridge \
            --subnet 172.30.0.0/16 \
            --opt com.docker.network.bridge.name=vibe0 \
            vibe-network
        
        success "تم إنشاء شبكة vibe-network"
    else
        success "الشبكة موجودة مسبقاً"
    fi
}

build_images() {
    log "بناء صور Docker (قد يستغرق بضع دقائق)..."

    cd "$INSTALL_DIR"
    docker compose build --no-cache

    if [ -x "$BUILD_IMAGES_SCRIPT" ]; then
        log "بناء صور المشاريع الأساسية..."
        "$BUILD_IMAGES_SCRIPT"
    else
        warn "لم يتم العثور على سكربت بناء صور المشاريع ($BUILD_IMAGES_SCRIPT)"
    fi

    success "تم بناء الصور"
}

start_services() {
    log "تشغيل الخدمات..."
    
    cd "$INSTALL_DIR"
    docker compose up -d
    
    # انتظار جاهزية API
    log "انتظار جاهزية API..."
    for i in {1..30}; do
        if curl -sf http://localhost:$API_PORT/health > /dev/null 2>&1; then
            success "API جاهز"
            return 0
        fi
        sleep 1
    done
    
    warn "API قد يحتاج المزيد من الوقت للبدء"
}

create_management_scripts() {
    log "إنشاء سكريبتات الإدارة..."
    
    # Status script
    cat > /usr/local/bin/vibe-status << 'EOF'
#!/bin/bash
cd /opt/vibe-coding && docker compose ps
EOF
    
    # Logs script
    cat > /usr/local/bin/vibe-logs << 'EOF'
#!/bin/bash
cd /opt/vibe-coding && docker compose logs -f "$@"
EOF
    
    # Restart script
    cat > /usr/local/bin/vibe-restart << 'EOF'
#!/bin/bash
cd /opt/vibe-coding && docker compose restart
EOF
    
    # Stop script
    cat > /usr/local/bin/vibe-stop << 'EOF'
#!/bin/bash
cd /opt/vibe-coding && docker compose stop
EOF
    
    # Start script
    cat > /usr/local/bin/vibe-start << 'EOF'
#!/bin/bash
cd /opt/vibe-coding && docker compose start
EOF
    
    # Update script
    cat > /usr/local/bin/vibe-update << 'EOF'
#!/bin/bash
cd /opt/vibe-coding
git pull origin main
docker compose build
docker compose up -d
EOF
    
    chmod +x /usr/local/bin/vibe-*
    success "تم إنشاء سكريبتات الإدارة"
}

setup_systemd() {
    log "إنشاء خدمة systemd..."
    
    cat > /etc/systemd/system/vibe-coding.service << EOF
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
EOF
    
    systemctl daemon-reload
    systemctl enable vibe-coding.service
    
    success "تم إنشاء خدمة systemd"
}

show_summary() {
    cat << EOF

${GREEN}═══════════════════════════════════════════════════════════════${NC}
${GREEN}   تم تثبيت Vibe Coding Platform بنجاح! 🎉${NC}
${GREEN}═══════════════════════════════════════════════════════════════${NC}

${BLUE}📋 معلومات الوصول:${NC}
   - API Endpoint:  http://localhost:$API_PORT
   - API Key:       $API_KEY
   - GitHub Secrets: /data/github-secrets.bin (المفتاح داخل config/.env)
   - Health Check:  http://localhost:$API_PORT/health

${YELLOW}⚠️  مهم للأمان:${NC}
   - API يعمل على localhost فقط
   - لا يمكن الوصول إليه من الخارج مباشرة
   - استخدم Plesk كـ reverse proxy إن أردت الوصول الخارجي

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

${BLUE}🔌 إعداد GPT Action:${NC}
   1. في ChatGPT GPT Builder → Actions
   2. استيراد: $INSTALL_DIR/openapi-spec.yaml
   3. API Key: $API_KEY
   4. Base URL: http://95.217.62.146:$API_PORT

${YELLOW}📝 الخطوات التالية:${NC}
   1. اختبر API: curl http://localhost:$API_PORT/health
   2. راجع التكوين: cat $INSTALL_DIR/config/.env
   3. اقرأ الوثائق: cat $INSTALL_DIR/README.md
   4. أعد GPT Action حسب التعليمات أعلاه

${PURPLE}💡 نصيحة:${NC}
   احفظ API Key في مكان آمن، ستحتاجه لإعداد GPT

${GREEN}═══════════════════════════════════════════════════════════════${NC}

EOF
}

# =============================================================================
# Main Installation
# =============================================================================

main() {
    banner
    
    log "بدء التثبيت..."
    
    check_root
    check_ubuntu
    check_plesk
    check_docker
    check_port
    create_directories
    download_files
    generate_secrets
    setup_firewall
    create_docker_network
    build_images
    start_services
    create_management_scripts
    setup_systemd
    
    show_summary
    
    success "التثبيت اكتمل بنجاح!"
}

# Run installation
main "$@"
