#!/usr/bin/env bash
# =============================================================================
# Vibe Coding Platform - General Linux Installer
# =============================================================================
# Usage: curl -sSL https://raw.githubusercontent.com/MarketingLimited/vibe-coding-platform/main/install.sh | sudo bash
# =============================================================================

set -euo pipefail

COMMON_URL="https://raw.githubusercontent.com/MarketingLimited/vibe-coding-platform/main/install-common.sh"

load_common_library() {
    local script_dir
    script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

    if [ -f "$script_dir/install-common.sh" ]; then
        # shellcheck disable=SC1091
        . "$script_dir/install-common.sh"
    else
        local tmp_file
        tmp_file=$(mktemp)
        curl -fsSL "$COMMON_URL" -o "$tmp_file"
        # shellcheck disable=SC1090
        . "$tmp_file"
        rm -f "$tmp_file"
    fi
}

load_common_library

DRY_RUN=false
SKIP_FIREWALL=false
SKIP_SYSTEMD=false

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-firewall)
                SKIP_FIREWALL=true
                shift
                ;;
            --skip-systemd)
                SKIP_SYSTEMD=true
                shift
                ;;
            *)
                warn "وسيطة غير معروفة: $1"
                shift
                ;;
        esac
    done
}

banner() {
    if command -v clear >/dev/null 2>&1; then
        clear
    fi
    cat << "EOF_BANNER"
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║      ██╗   ██╗██╗██████╗ ███████╗                            ║
║      ██║   ██║██║██╔══██╗██╔════╝                            ║
║      ██║   ██║██║██████╔╝█████╗                              ║
║      ╚██╗ ██╔╝██║██╔══██╗██╔══╝                              ║
║       ╚████╔╝ ██║██████╔╝███████╗                            ║
║        ╚═══╝  ╚═╝╚═════╝ ╚══════╝                            ║
║                                                              ║
║        Vibe Coding Platform - General Linux Installer        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
EOF_BANNER
    echo
}

main() {
    parse_args "$@"

    banner

    init_installation_context
    init_logging

    log "بدء التثبيت العام لمنصة Vibe Coding..."

    check_root
    detect_distro
    require_supported_family "debian" "rhel"
    ensure_prerequisites

    if [ "$DRY_RUN" = true ]; then
        success "وضع التجربة: التوزيعة مدعومة ومدير الحزم تم التعرف عليه ($PACKAGE_MANAGER)"
        return 0
    fi

    ensure_docker
    check_port
    create_directories
    download_files
    generate_secrets

    if [ "$SKIP_FIREWALL" = false ]; then
        setup_firewall
    else
        warn "تخطي إعداد الجدار الناري بناءً على خيار --skip-firewall"
    fi

    create_docker_network
    build_images
    start_services
    create_management_scripts

    if [ "$SKIP_SYSTEMD" = false ]; then
        setup_systemd
    else
        warn "تخطي إنشاء خدمة systemd بناءً على خيار --skip-systemd"
    fi

    show_summary
    success "التثبيت اكتمل بنجاح!"
}

main "$@"
