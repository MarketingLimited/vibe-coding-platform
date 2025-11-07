#!/usr/bin/env bash
# =============================================================================
# Vibe Coding Platform - DevBox Entrypoint
# =============================================================================
# Advanced service orchestration with health checks and graceful shutdown
# =============================================================================

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

: "${WORKSPACE:=/workspace}"
: "${PASSWORD:=change_me}"
: "${SSH_PASSWORD:=change_me_ssh}"
: "${SUDO_PASSWORD:=${PASSWORD}}"
: "${CODE_SERVER_PORT:=8443}"
: "${API_PORT:=8000}"
: "${SSH_PORT:=22}"

# Logging
LOG_DIR="${WORKSPACE}/.logs"
mkdir -p "${LOG_DIR}"

CODE_LOG="${LOG_DIR}/code-server.log"
API_LOG="${LOG_DIR}/api.log"
SSH_LOG="${LOG_DIR}/ssh.log"
SYSTEM_LOG="${LOG_DIR}/system.log"

# PID tracking
PIDS=()

# ============================================================================
# Logging Functions
# ============================================================================

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$SYSTEM_LOG"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

# ============================================================================
# Cleanup Function
# ============================================================================

cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    
    # Kill all tracked processes
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping process $pid"
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
    
    # Wait for processes to terminate
    for pid in "${PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
    
    # Stop SSH
    sudo service ssh stop 2>/dev/null || true
    
    log_success "Cleanup completed"
    exit 0
}

# Trap signals
trap cleanup SIGTERM SIGINT SIGQUIT

# ============================================================================
# Health Check Functions
# ============================================================================

wait_for_service() {
    local name="$1"
    local check_cmd="$2"
    local max_attempts=30
    local attempt=0
    
    log_info "Waiting for $name to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if eval "$check_cmd" >/dev/null 2>&1; then
            log_success "$name is ready"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 1
    done
    
    log_error "$name failed to start after ${max_attempts}s"
    return 1
}

# ============================================================================
# SSH Setup
# ============================================================================

setup_ssh() {
    log_info "Setting up SSH server..."
    
    # Configure SSH
    sudo tee /etc/ssh/sshd_config.d/vibe-coding.conf > /dev/null <<EOF
# Vibe Coding Platform SSH Configuration
Port ${SSH_PORT}
PermitRootLogin no
PasswordAuthentication yes
PubkeyAuthentication yes
AllowUsers dev
X11Forwarding no
PrintMotd no
AcceptEnv LANG LC_*
Subsystem sftp /usr/lib/openssh/sftp-server
EOF

    # Set user password
    echo "dev:${SSH_PASSWORD}" | sudo chpasswd
    
    # Generate host keys if they don't exist
    if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
        sudo ssh-keygen -A
    fi
    
    # Start SSH service
    sudo service ssh start
    
    if wait_for_service "SSH" "nc -z localhost ${SSH_PORT}"; then
        log_success "SSH server started on port ${SSH_PORT}"
    else
        log_error "SSH server failed to start"
        return 1
    fi
}

# ============================================================================
# Code Server Setup
# ============================================================================

setup_code_server() {
    log_info "Setting up code-server..."
    
    # Create config directory
    mkdir -p ~/.config/code-server
    
    # Generate configuration
    cat > ~/.config/code-server/config.yaml <<EOF
bind-addr: 0.0.0.0:${CODE_SERVER_PORT}
auth: password
password: ${PASSWORD}
cert: false
disable-telemetry: true
disable-update-check: true
user-data-dir: /home/dev/.local/share/code-server
EOF

    # Install essential extensions
    local extensions=(
        "ms-python.python"
        "dbaeumer.vscode-eslint"
        "esbenp.prettier-vscode"
        "eamodio.gitlens"
        "GitHub.copilot"
        "ms-azuretools.vscode-docker"
    )
    
    log_info "Installing VS Code extensions..."
    for ext in "${extensions[@]}"; do
        code-server --install-extension "$ext" --force 2>&1 | tee -a "$CODE_LOG" || true
    done
    
    # Start code-server in background
    nohup code-server \
        --log info \
        --disable-telemetry \
        --bind-addr "0.0.0.0:${CODE_SERVER_PORT}" \
        >"${CODE_LOG}" 2>&1 &
    
    local code_pid=$!
    PIDS+=("$code_pid")
    
    if wait_for_service "code-server" "curl -sf http://localhost:${CODE_SERVER_PORT}/healthz"; then
        log_success "code-server started (PID: $code_pid)"
    else
        log_error "code-server failed to start"
        return 1
    fi
}

# ============================================================================
# API Server Setup
# ============================================================================

setup_api() {
    log_info "Setting up Exec API..."
    
    cd /opt/runner
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Start API server
    nohup uvicorn app:app \
        --host 0.0.0.0 \
        --port "${API_PORT}" \
        --log-level info \
        --access-log \
        --no-server-header \
        >"${API_LOG}" 2>&1 &
    
    local api_pid=$!
    PIDS+=("$api_pid")
    
    if wait_for_service "API" "curl -sf http://localhost:${API_PORT}/health"; then
        log_success "Exec API started (PID: $api_pid)"
    else
        log_error "Exec API failed to start"
        return 1
    fi
}

# ============================================================================
# Environment Setup
# ============================================================================

setup_environment() {
    log_info "Setting up development environment..."
    
    # Create workspace structure
    mkdir -p "${WORKSPACE}"/{src,tests,docs,scripts,.cache,.logs}
    
    # Setup Git config if not exists
    if [ ! -f ~/.gitconfig ]; then
        cat > ~/.gitconfig <<EOF
[user]
    name = Vibe Coding Dev
    email = dev@kazaaz.com
[core]
    editor = vim
    autocrlf = input
[init]
    defaultBranch = main
[pull]
    rebase = false
EOF
    fi
    
    # Create helpful aliases
    cat > ~/.bash_aliases <<'EOF'
# Vibe Coding Aliases
alias ll='ls -lah'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'
alias grep='grep --color=auto'
alias ports='netstat -tuln'
alias meminfo='free -h'
alias cpuinfo='lscpu'
alias psg='ps aux | grep -v grep | grep -i -e VSZ -e'

# Docker aliases
alias d='docker'
alias dc='docker compose'
alias dps='docker ps'
alias dls='docker ps -a'
alias dim='docker images'

# Python aliases
alias py='python3'
alias pip='python3 -m pip'
alias venv='python3 -m venv'

# Git aliases
alias gs='git status'
alias ga='git add'
alias gc='git commit'
alias gp='git push'
alias gl='git log --oneline -10'

# Project shortcuts
alias workspace='cd /workspace'
alias cache-update='python3 /opt/tools/knowledge_cache.py'
EOF

    # Source aliases in bashrc if not already
    if ! grep -q ".bash_aliases" ~/.bashrc; then
        echo "[ -f ~/.bash_aliases ] && . ~/.bash_aliases" >> ~/.bashrc
    fi
    
    log_success "Environment setup completed"
}

# ============================================================================
# Knowledge Cache Initialization
# ============================================================================

initialize_knowledge_cache() {
    log_info "Initializing knowledge cache..."
    
    # Run knowledge cache if workspace has content
    if [ "$(ls -A ${WORKSPACE} 2>/dev/null)" ]; then
        python3 /opt/tools/knowledge_cache.py 2>&1 | tee -a "$SYSTEM_LOG" || {
            log_warn "Knowledge cache initialization failed (non-fatal)"
        }
    else
        log_info "Workspace is empty, skipping knowledge cache"
    fi
}

# ============================================================================
# System Information
# ============================================================================

display_system_info() {
    cat <<EOF

╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ██╗   ██╗██╗██████╗ ███████╗                           ║
║     ██║   ██║██║██╔══██╗██╔════╝                           ║
║     ██║   ██║██║██████╔╝█████╗                             ║
║     ╚██╗ ██╔╝██║██╔══██╗██╔══╝                             ║
║      ╚████╔╝ ██║██████╔╝███████╗                           ║
║       ╚═══╝  ╚═╝╚═════╝ ╚══════╝                           ║
║                                                              ║
║          Vibe Coding Platform - DevBox                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

🚀 System Information:
   - Hostname: $(hostname)
   - Workspace: ${WORKSPACE}
   - User: $(whoami)
   - Python: $(python3 --version)
   - Node: $(node --version)
   - PHP: $(php --version | head -n1)

📡 Services:
   - SSH Server: localhost:${SSH_PORT}
   - Code Server: http://localhost:${CODE_SERVER_PORT}
   - Exec API: http://localhost:${API_PORT}

📝 Logs:
   - System: ${SYSTEM_LOG}
   - API: ${API_LOG}
   - Code Server: ${CODE_LOG}
   - SSH: ${SSH_LOG}

✨ Ready for development!

EOF
}

# ============================================================================
# Health Monitor (Background)
# ============================================================================

start_health_monitor() {
    (
        while true; do
            sleep 60
            
            # Check API health
            if ! curl -sf http://localhost:${API_PORT}/health >/dev/null 2>&1; then
                log_error "API health check failed"
            fi
            
            # Check code-server health
            if ! curl -sf http://localhost:${CODE_SERVER_PORT}/healthz >/dev/null 2>&1; then
                log_error "code-server health check failed"
            fi
            
            # Check SSH
            if ! nc -z localhost ${SSH_PORT} >/dev/null 2>&1; then
                log_error "SSH health check failed"
            fi
            
            # Log resource usage
            log_info "Memory: $(free -h | awk 'NR==2{print $3 "/" $2}')"
        done
    ) &
    
    PIDS+=($!)
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log_info "Starting Vibe Coding Platform DevBox..."
    
    # Run setup functions
    setup_environment
    setup_ssh || exit 1
    setup_code_server || exit 1
    setup_api || exit 1
    
    # Initialize knowledge cache in background
    initialize_knowledge_cache &
    
    # Start health monitor
    start_health_monitor
    
    # Display system information
    display_system_info
    
    log_success "All services started successfully"
    log_info "DevBox is ready. Press Ctrl+C to stop."
    
    # Wait for all background processes
    wait
}

# Run main function
main
