#!/usr/bin/env bash
# =============================================================================
# New Project Creator - Vibe Coding Platform
# =============================================================================
# Creates a new isolated development environment
# Usage: ./new-project.sh <name> <ssh-port> [--with-postgres] [--with-mysql] [--with-redis]
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# =============================================================================
# Parse Arguments
# =============================================================================

show_help() {
    cat << EOF
Usage: ./new-project.sh <name> <ssh-port> [OPTIONS]

Arguments:
  name          Project name (alphanumeric, dash, underscore)
  ssh-port      SSH port number (> 1024, unique)

Options:
  --with-postgres    Add PostgreSQL database
  --with-mysql       Add MySQL database
  --with-redis       Add Redis cache
  --domain DOMAIN    Custom domain (default: kazaaz.com)
  --subnet OCTET     Custom subnet octet (default: auto)
  -h, --help         Show this help

Examples:
  ./new-project.sh myapp 22221
  ./new-project.sh shop 22230 --with-postgres --with-redis
  ./new-project.sh blog 22240 --with-mysql --domain example.com
EOF
}

if [[ $# -lt 2 ]]; then
    log_error "Missing required arguments"
    show_help
    exit 1
fi

PROJECT_NAME="$1"
SSH_PORT="$2"
shift 2

# Defaults
DOMAIN="${DOMAIN:-kazaaz.com}"
WITH_POSTGRES=false
WITH_MYSQL=false
WITH_REDIS=false
SUBNET_OCTET=""

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-postgres) WITH_POSTGRES=true; shift ;;
        --with-mysql) WITH_MYSQL=true; shift ;;
        --with-redis) WITH_REDIS=true; shift ;;
        --domain) DOMAIN="$2"; shift 2 ;;
        --subnet) SUBNET_OCTET="$2"; shift 2 ;;
        -h|--help) show_help; exit 0 ;;
        *) log_error "Unknown option: $1"; show_help; exit 1 ;;
    esac
done

# =============================================================================
# Validation
# =============================================================================

# Validate project name
if ! [[ "$PROJECT_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    log_error "Invalid project name. Use only alphanumeric, dash, and underscore."
    exit 1
fi

# Validate SSH port
if ! [[ "$SSH_PORT" =~ ^[0-9]+$ ]] || [ "$SSH_PORT" -lt 1024 ] || [ "$SSH_PORT" -gt 65535 ]; then
    log_error "Invalid SSH port. Must be between 1024 and 65535."
    exit 1
fi

# Check if project exists
if [ -d "projects/$PROJECT_NAME" ]; then
    log_error "Project '$PROJECT_NAME' already exists"
    exit 1
fi

# Check if SSH port is in use
if ss -tln | grep -q ":$SSH_PORT "; then
    log_error "Port $SSH_PORT is already in use"
    exit 1
fi

# Auto-assign subnet if not provided
if [ -z "$SUBNET_OCTET" ]; then
    # Find free subnet (check 20.x to 254.x)
    for i in {20..254}; do
        if ! docker network ls --format '{{.Name}}' | grep -q "${PROJECT_NAME}_net"; then
            if ! docker network inspect "172.$i.0.0/24" &>/dev/null; then
                SUBNET_OCTET=$i
                break
            fi
        fi
    done
    
    if [ -z "$SUBNET_OCTET" ]; then
        log_error "Could not find free subnet"
        exit 1
    fi
fi

log_info "Creating project: $PROJECT_NAME"
log_info "SSH Port: $SSH_PORT"
log_info "Domain: $DOMAIN"
log_info "Subnet: 172.$SUBNET_OCTET.0.0/24"

# =============================================================================
# Copy Template
# =============================================================================

log_info "Copying project template..."
cp -r projects/template "projects/$PROJECT_NAME"
cd "projects/$PROJECT_NAME"

# =============================================================================
# Generate Secrets
# =============================================================================

log_info "Generating secrets..."

generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

API_KEY=$(generate_password)
CODE_SERVER_PASSWORD=$(generate_password)
SSH_PASSWORD=$(generate_password)
POSTGRES_PASSWORD=$(generate_password)
MYSQL_PASSWORD=$(generate_password)
MYSQL_ROOT_PASSWORD=$(generate_password)
REDIS_PASSWORD=$(generate_password)

# =============================================================================
# Create .env File
# =============================================================================

log_info "Creating environment configuration..."

cat > .env << EOF
# =============================================================================
# Vibe Coding Platform - Project: $PROJECT_NAME
# Generated: $(date)
# =============================================================================

# Project Configuration
PROJECT_NAME=$PROJECT_NAME
DOMAIN=$DOMAIN
SUBNET_OCTET=$SUBNET_OCTET
SSH_PORT=$SSH_PORT

# Security
API_KEY=$API_KEY
CODE_SERVER_PASSWORD=$CODE_SERVER_PASSWORD
SSH_PASSWORD=$SSH_PASSWORD

# Database Configuration
POSTGRES_ENABLED=$WITH_POSTGRES
POSTGRES_USER=${PROJECT_NAME}_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=${PROJECT_NAME}_db

MYSQL_ENABLED=$WITH_MYSQL
MYSQL_USER=${PROJECT_NAME}_user
MYSQL_PASSWORD=$MYSQL_PASSWORD
MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD
MYSQL_DB=${PROJECT_NAME}_db

REDIS_ENABLED=$WITH_REDIS
REDIS_PASSWORD=$REDIS_PASSWORD
EOF

# Secure the .env file
chmod 600 .env

# =============================================================================
# Create Docker Compose Profiles
# =============================================================================

# Add profiles to compose command based on options
COMPOSE_PROFILES=""
[ "$WITH_POSTGRES" = true ] && COMPOSE_PROFILES="$COMPOSE_PROFILES --profile with-postgres"
[ "$WITH_MYSQL" = true ] && COMPOSE_PROFILES="$COMPOSE_PROFILES --profile with-mysql"
[ "$WITH_REDIS" = true ] && COMPOSE_PROFILES="$COMPOSE_PROFILES --profile with-redis"

# =============================================================================
# Create Directories
# =============================================================================

log_info "Creating project directories..."
mkdir -p workspace/{src,tests,docs,scripts,.cache,.logs}
mkdir -p .cache/{pip,npm,composer}
mkdir -p init-scripts/{postgres,mysql}

# Create .gitignore
cat > workspace/.gitignore << 'EOF'
# Vibe Coding Platform
.cache/
.logs/
.knowledge_cache/
*.log

# Environment
.env
.env.*
!.env.example

# Dependencies
node_modules/
vendor/
.venv/
__pycache__/

# IDE
.vscode/
.idea/
*.swp
*.swo
EOF

# =============================================================================
# Build and Start
# =============================================================================

log_info "Building Docker images..."
docker compose build --no-cache

log_info "Creating network..."
docker network create ${PROJECT_NAME}_net 2>/dev/null || true

log_info "Starting services..."
docker compose $COMPOSE_PROFILES up -d

# Wait for services to be healthy
log_info "Waiting for services to start..."
sleep 10

# Check if devbox is healthy
if docker compose ps | grep -q "$PROJECT_NAME.*healthy"; then
    log_success "Project created successfully!"
else
    log_warn "Services started but health check pending"
fi

# =============================================================================
# Display Information
# =============================================================================

cat << EOF

${GREEN}═══════════════════════════════════════════════════════════════${NC}
${GREEN}   Project Created: $PROJECT_NAME 🎉${NC}
${GREEN}═══════════════════════════════════════════════════════════════${NC}

${BLUE}📋 Access Information:${NC}
   - Code Server:  https://${DOMAIN}/code/${PROJECT_NAME}
   - Exec API:     https://${DOMAIN}/api/${PROJECT_NAME}/exec
   - SSH:          ssh dev@your-server -p ${SSH_PORT}
   
${BLUE}🔑 Credentials:${NC}
   - API Key:      $API_KEY
   - Code Server:  $CODE_SERVER_PASSWORD
   - SSH:          $SSH_PASSWORD

EOF

if [ "$WITH_POSTGRES" = true ]; then
    cat << EOF
${BLUE}🐘 PostgreSQL:${NC}
   - Host:     postgres
   - Database: ${PROJECT_NAME}_db
   - User:     ${PROJECT_NAME}_user
   - Password: $POSTGRES_PASSWORD

EOF
fi

if [ "$WITH_MYSQL" = true ]; then
    cat << EOF
${BLUE}🐬 MySQL:${NC}
   - Host:     mysql
   - Database: ${PROJECT_NAME}_db
   - User:     ${PROJECT_NAME}_user
   - Password: $MYSQL_PASSWORD
   - Root:     $MYSQL_ROOT_PASSWORD

EOF
fi

if [ "$WITH_REDIS" = true ]; then
    cat << EOF
${BLUE}🔴 Redis:${NC}
   - Host:     redis
   - Password: $REDIS_PASSWORD

EOF
fi

cat << EOF
${YELLOW}⚠️  Important:${NC}
   - Save credentials from: projects/$PROJECT_NAME/.env
   - Check logs: docker compose -f projects/$PROJECT_NAME/docker-compose.yml logs -f
   - Access workspace: projects/$PROJECT_NAME/workspace/

${YELLOW}📚 Next Steps:${NC}
   1. Connect via SSH or Code Server
   2. Start developing your project
   3. Use API for automated tasks
   4. Generate knowledge cache: 
      curl -X POST https://${DOMAIN}/api/${PROJECT_NAME}/exec \\
        -H "X-API-Key: $API_KEY" \\
        -d '{"cmd":"python3 /opt/tools/knowledge_cache.py"}'

${GREEN}═══════════════════════════════════════════════════════════════${NC}

EOF

# Save credentials to secure file
cat > .credentials << EOF
Project: $PROJECT_NAME
Created: $(date)

API_KEY=$API_KEY
CODE_SERVER_PASSWORD=$CODE_SERVER_PASSWORD
SSH_PASSWORD=$SSH_PASSWORD
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
MYSQL_PASSWORD=$MYSQL_PASSWORD
MYSQL_ROOT_PASSWORD=$MYSQL_ROOT_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
EOF

chmod 600 .credentials

log_success "Setup complete! Credentials saved to: projects/$PROJECT_NAME/.credentials"
