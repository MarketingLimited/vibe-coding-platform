# =============================================================================
# Vibe Coding Platform - DevBox Container
# Multi-stage optimized build with all development tools
# =============================================================================

# =============================================================================
# Stage 1: Base System
# =============================================================================
FROM ubuntu:22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Asia/Bahrain \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NODE_VERSION=20 \
    PHP_VERSION=8.3 \
    GO_VERSION=1.22.0 \
    RUST_VERSION=stable

# System packages and core tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core utilities
    sudo ca-certificates curl wget git gnupg lsb-release apt-transport-https \
    software-properties-common build-essential pkg-config \
    # Network and SSH
    openssh-server openssh-client netcat-openbsd telnet iputils-ping \
    # File operations
    unzip zip tar xz-utils bzip2 gzip \
    # Text processing
    jq ripgrep fd-find silversearcher-ag vim nano \
    # Process management
    procps htop tree make \
    # Security
    ca-certificates gnupg2 \
 && ln -s /usr/bin/fdfind /usr/local/bin/fd \
 && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Stage 2: Python Environment
# =============================================================================
FROM base AS python-env

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip python3-dev \
    # Python build dependencies
    libpq-dev libmysqlclient-dev libssl-dev libffi-dev \
    # Data science libs (optional)
    libopenblas-dev liblapack-dev \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install common packages
RUN python3 -m pip install --no-cache-dir --upgrade \
    pip setuptools wheel \
    # Web frameworks
    fastapi uvicorn[standard] gunicorn \
    # Database drivers
    psycopg2-binary mysqlclient sqlalchemy alembic \
    # Development tools
    pytest pytest-cov pytest-asyncio black ruff mypy flake8 \
    # Utilities
    python-dotenv pydantic requests httpx redis celery \
    # Monitoring
    psutil prometheus-client

# =============================================================================
# Stage 3: Node.js Environment
# =============================================================================
FROM python-env AS node-env

# Install Node.js from NodeSource
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
 && apt-get install -y nodejs \
 && rm -rf /var/lib/apt/lists/*

# Install global npm packages
RUN npm install -g \
    npm@latest \
    pnpm@latest \
    yarn@latest \
    typescript@latest \
    ts-node@latest \
    nodemon@latest \
    pm2@latest \
    @vue/cli@latest \
    create-react-app@latest \
    vite@latest \
 && npm cache clean --force

# =============================================================================
# Stage 4: PHP Environment
# =============================================================================
FROM node-env AS php-env

# Add PHP repository
RUN add-apt-repository ppa:ondrej/php -y \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
    php${PHP_VERSION}-cli \
    php${PHP_VERSION}-fpm \
    php${PHP_VERSION}-common \
    php${PHP_VERSION}-mysql \
    php${PHP_VERSION}-pgsql \
    php${PHP_VERSION}-sqlite3 \
    php${PHP_VERSION}-curl \
    php${PHP_VERSION}-gd \
    php${PHP_VERSION}-mbstring \
    php${PHP_VERSION}-xml \
    php${PHP_VERSION}-zip \
    php${PHP_VERSION}-bcmath \
    php${PHP_VERSION}-intl \
    php${PHP_VERSION}-redis \
    php${PHP_VERSION}-imagick \
 && rm -rf /var/lib/apt/lists/*

# Install Composer
RUN curl -sS https://getcomposer.org/installer | php -- \
    --install-dir=/usr/local/bin --filename=composer \
 && composer --version

# =============================================================================
# Stage 5: Database Clients
# =============================================================================
FROM php-env AS db-env

# PostgreSQL client
RUN curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
    gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" | \
    tee /etc/apt/sources.list.d/pgdg.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
    postgresql-client-16 \
    mysql-client \
    sqlite3 \
    redis-tools \
 && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Stage 6: Additional Languages
# =============================================================================
FROM db-env AS lang-env

# Install Go
RUN wget -q https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz \
 && tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz \
 && rm go${GO_VERSION}.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}" \
    GOPATH="/go" \
    GO111MODULE=on

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --default-toolchain ${RUST_VERSION} \
 && /root/.cargo/bin/rustup component add rustfmt clippy

ENV PATH="/root/.cargo/bin:${PATH}"

# Install Java (OpenJDK)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    openjdk-21-jdk-headless \
 && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Stage 7: Development Tools
# =============================================================================
FROM lang-env AS dev-tools

# Install code-server
RUN curl -fsSL https://code-server.dev/install.sh | sh \
 && code-server --version

# Install additional dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Git tools
    git-lfs tig \
    # Docker CLI (will use host socket)
    docker.io docker-compose-v2 \
    # Database tools
    pgcli mycli \
    # Network tools
    nmap tcpdump \
 && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Stage 8: User Setup and Security
# =============================================================================
FROM dev-tools AS final

# Create non-root user
ARG USERNAME=dev
ARG UID=1000
ARG GID=1000

RUN groupadd --gid ${GID} ${USERNAME} \
 && useradd -s /bin/bash --uid ${UID} --gid ${GID} -m ${USERNAME} \
 && echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-${USERNAME} \
 && chmod 0440 /etc/sudoers.d/90-${USERNAME}

# Setup SSH
RUN mkdir -p /var/run/sshd /home/${USERNAME}/.ssh \
 && chmod 700 /home/${USERNAME}/.ssh \
 && chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}

# Configure SSH
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config \
 && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config \
 && sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config \
 && sed -i 's/UsePAM yes/UsePAM no/' /etc/ssh/sshd_config \
 && echo "AllowUsers ${USERNAME}" >> /etc/ssh/sshd_config

# =============================================================================
# Runner API Setup
# =============================================================================

USER ${USERNAME}
WORKDIR /opt/runner

# Copy requirements and install
COPY --chown=${USERNAME}:${USERNAME} runner/requirements.txt ./
RUN python3 -m venv .venv \
 && . .venv/bin/activate \
 && pip install --no-cache-dir -r requirements.txt

# Copy runner application
COPY --chown=${USERNAME}:${USERNAME} runner/app.py ./
COPY --chown=${USERNAME}:${USERNAME} runner/middleware.py ./
COPY --chown=${USERNAME}:${USERNAME} runner/security.py ./

# =============================================================================
# Tools Setup
# =============================================================================

USER root

# Create directories
RUN mkdir -p /opt/tools /workspace /home/${USERNAME}/.config \
 && chown -R ${USERNAME}:${USERNAME} /opt/tools /workspace /home/${USERNAME}/.config

# Copy tools
COPY --chown=${USERNAME}:${USERNAME} tools/knowledge_cache.py /opt/tools/
COPY --chown=${USERNAME}:${USERNAME} tools/project_analyzer.py /opt/tools/
COPY --chown=${USERNAME}:${USERNAME} tools/db_schema_extractor.py /opt/tools/

# Make tools executable
RUN chmod +x /opt/tools/*.py

# =============================================================================
# Entrypoint
# =============================================================================

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER ${USERNAME}
WORKDIR /workspace

# Expose ports
EXPOSE 8000 8443 22

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Labels
LABEL maintainer="AlMoelef <admin@marketing.limited>" \
      version="2.0" \
      description="Vibe Coding Platform - Complete Development Environment" \
      org.opencontainers.image.source="https://github.com/kazaaz/vibe-coding"

CMD ["/bin/bash", "-lc", "/entrypoint.sh"]
