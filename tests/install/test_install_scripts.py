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
