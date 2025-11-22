#!/bin/bash

# =============================================================================
# Project Run Script
# =============================================================================
# Quick start script for running the project in development mode
# This script detects the project type and runs appropriate commands

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect project type
detect_project_type() {
    if [ -f "package.json" ]; then
        echo "nodejs"
    elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
        echo "python"
    elif [ -f "composer.json" ]; then
        echo "php"
    elif [ -f "Gemfile" ]; then
        echo "ruby"
    elif [ -f "go.mod" ]; then
        echo "go"
    elif [ -f "Cargo.toml" ]; then
        echo "rust"
    else
        echo "unknown"
    fi
}

# Run Python project
run_python() {
    info "Running Python project..."

    # Check if virtual environment exists
    if [ -d ".venv" ]; then
        info "Activating virtual environment..."
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        info "Activating virtual environment..."
        source venv/bin/activate
    else
        warn "No virtual environment found. Consider creating one with: python -m venv .venv"
    fi

    # Detect Python framework
    if [ -f "manage.py" ]; then
        # Django
        info "Detected Django project"
        python manage.py runserver 0.0.0.0:8000
    elif [ -f "app.py" ] && grep -q "Flask" app.py 2>/dev/null; then
        # Flask
        info "Detected Flask project"
        export FLASK_APP=app.py
        export FLASK_ENV=development
        flask run --host=0.0.0.0 --port=5000
    elif [ -f "main.py" ] && grep -q "FastAPI\|fastapi" main.py 2>/dev/null; then
        # FastAPI
        info "Detected FastAPI project"
        uvicorn main:app --reload --host 0.0.0.0 --port 8000
    elif [ -f "app.py" ]; then
        # Generic Python app
        info "Running app.py..."
        python app.py
    elif [ -f "main.py" ]; then
        # Generic Python main
        info "Running main.py..."
        python main.py
    else
        error "No Python entry point found (app.py, main.py, or manage.py)"
        exit 1
    fi
}

# Run Node.js project
run_nodejs() {
    info "Running Node.js project..."

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        info "Installing dependencies..."
        npm install
    fi

    # Check package.json scripts
    if grep -q '"dev"' package.json 2>/dev/null; then
        info "Running npm run dev..."
        npm run dev
    elif grep -q '"start:dev"' package.json 2>/dev/null; then
        info "Running npm run start:dev..."
        npm run start:dev
    elif grep -q '"start"' package.json 2>/dev/null; then
        info "Running npm start..."
        npm start
    else
        # Default to running index.js or server.js
        if [ -f "index.js" ]; then
            info "Running index.js..."
            node index.js
        elif [ -f "server.js" ]; then
            info "Running server.js..."
            node server.js
        else
            error "No start script or entry point found"
            exit 1
        fi
    fi
}

# Run PHP project
run_php() {
    info "Running PHP project..."

    # Install dependencies if needed
    if [ -f "composer.json" ] && [ ! -d "vendor" ]; then
        info "Installing dependencies..."
        composer install
    fi

    # Detect PHP framework
    if [ -f "artisan" ]; then
        # Laravel
        info "Detected Laravel project"
        php artisan serve --host=0.0.0.0 --port=8000
    elif [ -f "index.php" ]; then
        # Generic PHP
        info "Starting PHP built-in server..."
        php -S 0.0.0.0:8000
    else
        error "No PHP entry point found"
        exit 1
    fi
}

# Run Ruby project
run_ruby() {
    info "Running Ruby project..."

    # Install dependencies if needed
    if [ ! -d "vendor/bundle" ]; then
        info "Installing dependencies..."
        bundle install
    fi

    # Detect Ruby framework
    if [ -f "config.ru" ]; then
        # Rack-based (Rails, Sinatra, etc.)
        info "Running with rackup..."
        bundle exec rackup -o 0.0.0.0 -p 3000
    else
        error "No Ruby entry point found"
        exit 1
    fi
}

# Run Go project
run_go() {
    info "Running Go project..."

    if [ -f "main.go" ]; then
        info "Running main.go..."
        go run main.go
    else
        error "No main.go found"
        exit 1
    fi
}

# Run Rust project
run_rust() {
    info "Running Rust project..."

    info "Running with cargo..."
    cargo run
}

# Main execution
main() {
    info "Starting project..."

    # Load environment variables if .env exists
    if [ -f ".env" ]; then
        info "Loading environment variables from .env..."
        set -a
        source .env
        set +a
    else
        warn "No .env file found. Using default configuration."
    fi

    # Detect and run project
    PROJECT_TYPE=$(detect_project_type)

    case $PROJECT_TYPE in
        python)
            run_python
            ;;
        nodejs)
            run_nodejs
            ;;
        php)
            run_php
            ;;
        ruby)
            run_ruby
            ;;
        go)
            run_go
            ;;
        rust)
            run_rust
            ;;
        unknown)
            error "Could not detect project type"
            info "Please create one of: package.json, requirements.txt, composer.json, Gemfile, go.mod, Cargo.toml"
            exit 1
            ;;
    esac

    success "Project started successfully!"
}

# Run main function
main "$@"
