#!/usr/bin/env bash
# =============================================================================
# Setup Script - Vibe Coding Platform
# =============================================================================
# يقوم بتهيئة البيئة الكاملة للمنصة
# الاستخدام: ./setup.sh [--domain your-domain.com] [--email admin@example.com]
# =============================================================================

set -euo pipefail

# ألوان للمخرجات
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# المتغيرات الافتراضية
DOMAIN="${DOMAIN:-kazaaz.com}"
EMAIL="${EMAIL:-admin@kazaaz.com}"
INSTALL_MONITORING="${INSTALL_MONITORING:-yes}"
INSTALL_REGISTRY="${INSTALL_REGISTRY:-no}"

# =============================================================================
# دوال المساعدة
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "فحص المتطلبات..."
    
    # فحص Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker غير مثبت"
        exit 1
    fi
    
    # فحص Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose v2 غير مثبت"
        exit 1
    fi
    
    # فحص الصلاحيات
    if ! docker ps &> /dev/null; then
        log_error "لا توجد صلاحيات لتشغيل Docker"
        exit 1
    fi
    
    log_success "جميع المتطلبات متوفرة"
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                DOMAIN="$2"
                shift 2
                ;;
            --email)
                EMAIL="$2"
                shift 2
                ;;
            --no-monitoring)
                INSTALL_MONITORING="no"
                shift
                ;;
            --with-registry)
                INSTALL_REGISTRY="yes"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "خيار غير معروف: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
الاستخدام: ./setup.sh [OPTIONS]

الخيارات:
  --domain DOMAIN       الدومين الأساسي (افتراضي: kazaaz.com)
  --email EMAIL         البريد الإلكتروني لـ Let's Encrypt
  --no-monitoring       عدم تثبيت نظام المراقبة
  --with-registry       تثبيت Docker registry محلي
  -h, --help           عرض هذه الرسالة

أمثلة:
  ./setup.sh
  ./setup.sh --domain example.com --email admin@example.com
  ./setup.sh --no-monitoring
EOF
}

# =============================================================================
# إنشاء البنية الأساسية
# =============================================================================

create_directory_structure() {
    log_info "إنشاء البنية الأساسية..."
    
    # الدلائل الرئيسية
    mkdir -p {infra/{traefik,monitoring,registry},projects,tools,docs,backup,logs}
    
    # دلائل Traefik
    mkdir -p infra/traefik/{letsencrypt,config}
    chmod 600 infra/traefik/letsencrypt
    
    # دلائل المراقبة
    if [[ "$INSTALL_MONITORING" == "yes" ]]; then
        mkdir -p infra/monitoring/{prometheus,grafana}/{data,config}
    fi
    
    # دلائل السجلات
    mkdir -p logs/{traefik,projects,system}
    
    log_success "تم إنشاء البنية الأساسية"
}

# =============================================================================
# تكوين Traefik
# =============================================================================

setup_traefik() {
    log_info "تكوين Traefik..."
    
    cat > infra/traefik/docker-compose.yml << 'EOF'
version: "3.9"

services:
  traefik:
    image: traefik:v3.1
    container_name: traefik
    restart: unless-stopped
    
    command:
      # Docker provider
      - --providers.docker=true
      - --providers.docker.exposedbydefault=false
      - --providers.file.directory=/config
      - --providers.file.watch=true
      
      # Entrypoints
      - --entrypoints.web.address=:80
      - --entrypoints.websecure.address=:443
      - --entrypoints.web.http.redirections.entrypoint.to=websecure
      - --entrypoints.web.http.redirections.entrypoint.scheme=https
      
      # Let's Encrypt
      - --certificatesresolvers.le.acme.tlschallenge=true
      - --certificatesresolvers.le.acme.email=${ACME_EMAIL}
      - --certificatesresolvers.le.acme.storage=/letsencrypt/acme.json
      
      # API and Dashboard
      - --api.dashboard=true
      - --api.insecure=false
      
      # Logging
      - --log.level=INFO
      - --log.filepath=/logs/traefik.log
      - --accesslog=true
      - --accesslog.filepath=/logs/access.log
      
      # Metrics
      - --metrics.prometheus=true
      - --metrics.prometheus.addEntryPointsLabels=true
      - --metrics.prometheus.addServicesLabels=true
      
    ports:
      - "80:80"
      - "443:443"
    
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./letsencrypt:/letsencrypt
      - ./config:/config:ro
      - ../../logs/traefik:/logs
    
    networks:
      - edge
    
    environment:
      - ACME_EMAIL=${ACME_EMAIL}
    
    labels:
      - traefik.enable=true
      
      # Dashboard
      - traefik.http.routers.dashboard.rule=Host(`${DOMAIN}`) && PathPrefix(`/dashboard`)
      - traefik.http.routers.dashboard.entrypoints=websecure
      - traefik.http.routers.dashboard.tls.certresolver=le
      - traefik.http.routers.dashboard.service=api@internal
      - traefik.http.routers.dashboard.middlewares=dashboard-auth,dashboard-strip
      
      # Middleware: BasicAuth
      - traefik.http.middlewares.dashboard-auth.basicauth.users=${DASHBOARD_AUTH}
      
      # Middleware: StripPrefix
      - traefik.http.middlewares.dashboard-strip.stripprefix.prefixes=/dashboard
      
      # Middleware: Rate limiting
      - traefik.http.middlewares.ratelimit.ratelimit.average=100
      - traefik.http.middlewares.ratelimit.ratelimit.period=1m
      - traefik.http.middlewares.ratelimit.ratelimit.burst=50
      
      # Middleware: Security headers
      - traefik.http.middlewares.security.headers.sslredirect=true
      - traefik.http.middlewares.security.headers.stsSeconds=31536000
      - traefik.http.middlewares.security.headers.stsIncludeSubdomains=true
      - traefik.http.middlewares.security.headers.stsPreload=true
      - traefik.http.middlewares.security.headers.forceSTSHeader=true
      - traefik.http.middlewares.security.headers.frameDeny=true
      - traefik.http.middlewares.security.headers.contentTypeNosniff=true
      - traefik.http.middlewares.security.headers.browserXssFilter=true
      - traefik.http.middlewares.security.headers.referrerPolicy=strict-origin-when-cross-origin

networks:
  edge:
    external: true
    name: edge
EOF

    # إنشاء ملف البيئة
    cat > infra/traefik/.env << EOF
DOMAIN=${DOMAIN}
ACME_EMAIL=${EMAIL}
DASHBOARD_AUTH=$(docker run --rm httpd:alpine htpasswd -nbB admin "$(openssl rand -base64 32)")
EOF

    # إنشاء شبكة edge
    docker network create edge 2>/dev/null || true
    
    log_success "تم تكوين Traefik"
}

# =============================================================================
# تكوين المراقبة
# =============================================================================

setup_monitoring() {
    if [[ "$INSTALL_MONITORING" != "yes" ]]; then
        log_warning "تخطي تثبيت نظام المراقبة"
        return
    fi
    
    log_info "تكوين نظام المراقبة..."
    
    # Prometheus config
    cat > infra/monitoring/prometheus/config/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'vibe-coding'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'traefik'
    static_configs:
      - targets: ['traefik:8080']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
  
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
EOF

    # Docker Compose للمراقبة
    cat > infra/monitoring/docker-compose.yml << 'EOF'
version: "3.9"

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --storage.tsdb.path=/prometheus
      - --storage.tsdb.retention.time=30d
      - --web.console.libraries=/usr/share/prometheus/console_libraries
      - --web.console.templates=/usr/share/prometheus/consoles
    volumes:
      - ./prometheus/config:/etc/prometheus
      - ./prometheus/data:/prometheus
    networks:
      - edge
      - monitoring
    labels:
      - traefik.enable=true
      - traefik.http.routers.prometheus.rule=Host(`${DOMAIN}`) && PathPrefix(`/prometheus`)
      - traefik.http.routers.prometheus.entrypoints=websecure
      - traefik.http.routers.prometheus.tls.certresolver=le
      - traefik.http.services.prometheus.loadbalancer.server.port=9090

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    restart: unless-stopped
    environment:
      - GF_SERVER_ROOT_URL=https://${DOMAIN}/grafana
      - GF_SERVER_SERVE_FROM_SUB_PATH=true
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - ./grafana/data:/var/lib/grafana
      - ./grafana/config:/etc/grafana
    networks:
      - edge
      - monitoring
    labels:
      - traefik.enable=true
      - traefik.http.routers.grafana.rule=Host(`${DOMAIN}`) && PathPrefix(`/grafana`)
      - traefik.http.routers.grafana.entrypoints=websecure
      - traefik.http.routers.grafana.tls.certresolver=le
      - traefik.http.services.grafana.loadbalancer.server.port=3000

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    restart: unless-stopped
    command:
      - --path.rootfs=/host
    volumes:
      - /:/host:ro,rslave
    networks:
      - monitoring

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: cadvisor
    restart: unless-stopped
    privileged: true
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker:/var/lib/docker:ro
    networks:
      - monitoring

networks:
  edge:
    external: true
    name: edge
  monitoring:
    name: monitoring
EOF

    # ملف البيئة للمراقبة
    cat > infra/monitoring/.env << EOF
DOMAIN=${DOMAIN}
GRAFANA_PASSWORD=$(openssl rand -base64 32)
EOF

    docker network create monitoring 2>/dev/null || true
    
    log_success "تم تكوين نظام المراقبة"
}

# =============================================================================
# إنشاء قالب المشروع
# =============================================================================

create_project_template() {
    log_info "إنشاء قالب المشروع..."
    
    mkdir -p projects/template/{runner,tools,config}
    
    # سيتم إنشاء الملفات في الخطوات التالية
    log_success "تم إنشاء قالب المشروع"
}

# =============================================================================
# إنشاء الأدوات المساعدة
# =============================================================================

create_tools() {
    log_info "إنشاء الأدوات المساعدة..."
    
    # سيتم إنشاء السكريبتات في ملفات منفصلة
    chmod +x tools/*.sh 2>/dev/null || true
    
    log_success "تم إنشاء الأدوات المساعدة"
}

# =============================================================================
# تكوين النظام
# =============================================================================

configure_system() {
    log_info "تكوين النظام..."
    
    # تحسين حدود النظام
    cat >> /etc/sysctl.conf << EOF

# Vibe Coding Platform Optimizations
fs.file-max = 500000
fs.inotify.max_user_watches = 524288
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
EOF

    sysctl -p >/dev/null 2>&1 || log_warning "تعذر تطبيق إعدادات sysctl (قد تحتاج صلاحيات root)"
    
    log_success "تم تكوين النظام"
}

# =============================================================================
# الإطلاق الأول
# =============================================================================

initial_start() {
    log_info "إطلاق الخدمات الأساسية..."
    
    # تشغيل Traefik
    (cd infra/traefik && docker compose up -d)
    
    # تشغيل المراقبة
    if [[ "$INSTALL_MONITORING" == "yes" ]]; then
        (cd infra/monitoring && docker compose up -d)
    fi
    
    log_success "تم إطلاق الخدمات الأساسية"
}

# =============================================================================
# عرض النتائج
# =============================================================================

show_summary() {
    cat << EOF

${GREEN}═══════════════════════════════════════════════════════════════${NC}
${GREEN}   تم تثبيت Vibe Coding Platform بنجاح! 🎉${NC}
${GREEN}═══════════════════════════════════════════════════════════════${NC}

${BLUE}📋 معلومات الوصول:${NC}
   - الدومين: https://${DOMAIN}
   - Traefik Dashboard: https://${DOMAIN}/dashboard
   - البريد الإلكتروني: ${EMAIL}

EOF

    if [[ "$INSTALL_MONITORING" == "yes" ]]; then
        cat << EOF
${BLUE}📊 المراقبة:${NC}
   - Prometheus: https://${DOMAIN}/prometheus
   - Grafana: https://${DOMAIN}/grafana
   $(grep GRAFANA_PASSWORD infra/monitoring/.env)

EOF
    fi

    cat << EOF
${YELLOW}⚡ الخطوات التالية:${NC}
   1. تحقق من عمل Traefik:
      docker compose -f infra/traefik/docker-compose.yml ps
   
   2. أنشئ مشروعك الأول:
      ./tools/new-project.sh myapp 22221
   
   3. اقرأ الوثائق:
      cat docs/getting-started.md

${YELLOW}🔒 ملاحظات أمنية:${NC}
   - احفظ ملفات .env في مكان آمن
   - غيّر كلمات المرور الافتراضية
   - فعّل Firewall على المنافذ المطلوبة فقط
   - راجع السجلات بانتظام

${GREEN}═══════════════════════════════════════════════════════════════${NC}

EOF
}

# =============================================================================
# البرنامج الرئيسي
# =============================================================================

main() {
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
║          Vibe Coding Platform - Setup Wizard                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

EOF

    parse_args "$@"
    check_requirements
    
    log_info "بدء التثبيت..."
    log_info "الدومين: $DOMAIN"
    log_info "البريد: $EMAIL"
    echo
    
    create_directory_structure
    setup_traefik
    setup_monitoring
    create_project_template
    create_tools
    configure_system
    initial_start
    
    show_summary
}

main "$@"
