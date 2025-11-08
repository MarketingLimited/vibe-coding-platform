import os
import shutil
import subprocess
from pathlib import Path

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
