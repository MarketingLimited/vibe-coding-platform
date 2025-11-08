import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from textwrap import dedent

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

def _docker_available() -> bool:
    return shutil.which("docker") is not None


@pytest.mark.skipif(not _docker_available(), reason="Docker غير متوفر في بيئة الاختبار")
@pytest.mark.parametrize(
    "image, command",
    [
        ("rockylinux:9", "bash install.sh --dry-run"),
        ("debian:12", "bash install-plesk.sh --dry-run"),
    ],
)
def test_installers_support_multiple_distributions(image: str, command: str) -> None:
    """تأكد أن سكربتات التثبيت لا تتوقف مبكراً على التوزيعات المدعومة."""
    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{REPO_ROOT}:/workspace",
        "-w",
        "/workspace",
        image,
        "bash",
        "-lc",
        command,
    ]

    result = subprocess.run(docker_cmd, check=False, capture_output=True, text=True)

    if result.returncode != 0:
        pytest.fail(
            "فشل السكربت على صورة %s:\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (image, result.stdout, result.stderr)
        )

    assert "التوزيعة مدعومة" in result.stdout or "المتطلبات الأساسية" in result.stdout

def test_management_scripts_use_install_dir(tmp_path):
    install_dir = tmp_path / "install"
    install_dir.mkdir()
    bin_dir = tmp_path / "bin"
    log_path = tmp_path / "install.log"
    log_path.touch()

    env = {
        **{k: v for k, v in os.environ.items() if k not in {"INSTALL_DIR", "MANAGEMENT_BIN_DIR", "LOG_FILE"}},
        "INSTALL_DIR": str(install_dir),
        "MANAGEMENT_BIN_DIR": str(bin_dir),
        "LOG_FILE": str(log_path),
    }

    script = f"""
set -e
source "{REPO_ROOT / 'install-common.sh'}"
create_management_scripts
"""

    subprocess.run(["bash", "-lc", script], check=True, env=env)

    vibe_status = bin_dir / "vibe-status"
    assert vibe_status.exists(), "vibe-status helper was not generated"

    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()
    stub_path = stub_dir / "docker"
    stub_path.write_text("#!/bin/bash\npwd\n")
    stub_path.chmod(0o755)

    env_for_status = {
        **os.environ,
        "PATH": f"{stub_dir}:{os.environ.get('PATH', '')}"
    }

    result = subprocess.run(
        [str(vibe_status)],
        check=True,
        capture_output=True,
        text=True,
        env=env_for_status,
    )

    assert result.stdout.strip() == str(install_dir)


@pytest.mark.skipif(not _docker_available(), reason="Docker غير متوفر في بيئة الاختبار")
def test_api_host_mode_accessible_from_external_container(tmp_path):
    """التأكد من أن bind=0.0.0.0 يسمح بالوصول من حاوية أخرى."""

    project_name = f"vibeapitest{uuid.uuid4().hex[:8]}"
    port = 19000 + int(uuid.uuid4().int % 1000)

    data_dir = tmp_path / "data"
    (data_dir / "projects").mkdir(parents=True)
    (data_dir / "logs").mkdir(parents=True)

    config_dir = REPO_ROOT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    env_file = config_dir / ".env"

    original_env = env_file.read_text() if env_file.exists() else None

    env_file.write_text(
        dedent(
            f"""
            # Test configuration for API publish smoke test
            API_HOST=0.0.0.0
            API_PORT={port}
            DOMAIN=localhost
            API_PUBLISH_MODE=host
            API_PUBLISH_BIND=0.0.0.0
            API_KEY=test-api-key
            MASTER_API_KEY=test-master-key
            ADMIN_ALERT_EMAIL=alerts@example.com

            DATA_DIR={data_dir}
            PROJECTS_DIR=/projects
            LOGS_DIR=/logs
            INSTALL_DIR={REPO_ROOT}

            DB_TYPE=sqlite
            DB_PATH=/data/projects.db
            DB_PASSWORD=test-db-pass

            GITHUB_SECRETS_PATH=/data/github-secrets.bin
            GITHUB_SECRETS_KEY=test-github-key

            REDIS_HOST=redis
            REDIS_PORT=6379
            REDIS_DB=0

            MAX_PROJECTS_PER_USER=10
            PROJECT_CPU_LIMIT=2.0
            PROJECT_MEMORY_LIMIT=4G
            PROJECT_STORAGE_LIMIT=10G

            EXEC_TIMEOUT=300
            MAX_OUTPUT_SIZE=10485760

            ENABLE_RATE_LIMIT=true
            RATE_LIMIT_PER_MINUTE=100
            RATE_LIMIT_WINDOW_SECONDS=60
            EXEC_RATE_LIMIT_PER_MINUTE=60
            PROJECT_CREATE_RATE_LIMIT=5
            PROJECT_INFO_RATE_LIMIT=30
            PASSWORD_ROTATE_RATE_LIMIT=4
            PROJECT_DELETE_RATE_LIMIT=4

            PROJECT_MANAGER_PORT=9400
            PROJECT_MANAGER_HOST=project-manager
            PROJECT_MANAGER_SCHEME=http
            HEALTH_POLL_INTERVAL=30
            CLEANUP_INTERVAL=86400
            """
        ).strip()
        + "\n"
    )

    compose_env = {
        **os.environ,
        "COMPOSE_PROJECT_NAME": project_name,
        "DATA_DIR": str(data_dir),
        "API_PORT": str(port),
        "API_PUBLISH_MODE": "host",
        "API_PUBLISH_BIND": "0.0.0.0",
    }

    try:
        subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=REPO_ROOT,
            env=compose_env,
            check=False,
            capture_output=True,
        )

        subprocess.run(
            ["docker", "compose", "up", "-d", "api"],
            cwd=REPO_ROOT,
            env=compose_env,
            check=True,
            capture_output=True,
        )

        curl_cmd = [
            "docker",
            "run",
            "--rm",
            "--add-host",
            "host.docker.internal:host-gateway",
            "curlimages/curl:8.10.1",
            "-sS",
            "--fail",
            "--max-time",
            "5",
            f"http://host.docker.internal:{port}/",
        ]

        last_result = None
        for _ in range(10):
            last_result = subprocess.run(
                curl_cmd,
                check=False,
                capture_output=True,
                text=True,
            )
            if last_result.returncode == 0:
                break
            time.sleep(3)
        else:
            logs = subprocess.run(
                ["docker", "compose", "logs", "api"],
                cwd=REPO_ROOT,
                env=compose_env,
                check=False,
                capture_output=True,
                text=True,
            )
            stdout = last_result.stdout if last_result else ""
            stderr = last_result.stderr if last_result else ""
            pytest.fail(
                "تعذر الوصول إلى واجهة الـ API من الحاوية الخارجية.\n"
                f"curl stdout:\n{stdout}\n"
                f"curl stderr:\n{stderr}\n"
                f"api logs:\n{logs.stdout}\n"
            )

        assert last_result is not None and last_result.returncode == 0
        payload = json.loads(last_result.stdout)
        assert payload.get("status") in {"running", "healthy"}

    finally:
        subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=REPO_ROOT,
            env=compose_env,
            check=False,
            capture_output=True,
        )

        if original_env is None:
            env_file.unlink(missing_ok=True)
        else:
            env_file.write_text(original_env)
