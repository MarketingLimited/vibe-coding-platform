from __future__ import annotations

import io
import sys
import tarfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from project_manager.app.models import ProjectSecrets
from project_manager.app.services.secret_sync import SecretSyncService


class DummyContainer:
    def __init__(self) -> None:
        self.exec_commands: list[list[str]] = []
        self.archives: dict[str, bytes] = {}

    def exec_run(self, cmd):
        self.exec_commands.append(cmd)

        class Result:
            exit_code = 0

        return Result()

    def put_archive(self, path: str, data: bytes) -> bool:
        self.archives[path] = data
        return True


def test_secret_sync_creates_hosts_yaml(tmp_path: Path) -> None:
    container = DummyContainer()
    service = SecretSyncService(tmp_path / ".config" / "gh")
    secrets = ProjectSecrets(
        username="demo",
        github_api_key="ghp_secret_token_1234567890123",
        additional_secrets={
            "github_host": "github.example.com",
            "git_protocol": "ssh",
            "custom": "value",
        },
    )

    result = service.sync("proj-123", container, secrets)
    assert "hosts.yml" in result["path"]

    assert container.exec_commands[0] == ["mkdir", "-p", str(tmp_path / ".config" / "gh")]
    archive = container.archives[str(tmp_path / ".config" / "gh")]

    extracted = _extract_tar_member(archive, "hosts.yml")
    content = yaml.safe_load(extracted.decode("utf-8"))
    assert "github.example.com" in content
    entry = content["github.example.com"]
    assert entry["oauth_token"] == "ghp_secret_token_1234567890123"
    assert entry["git_protocol"] == "ssh"
    assert entry["custom"] == "value"


def _extract_tar_member(archive: bytes, member: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        extracted = tar.extractfile(member)
        assert extracted is not None
        return extracted.read()
