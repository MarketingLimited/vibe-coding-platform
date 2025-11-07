"""Synchronise project secrets into running containers."""

from __future__ import annotations

import io
import logging
import tarfile
import time
from pathlib import Path
from typing import Dict

import yaml

from ..models import ProjectSecrets

logger = logging.getLogger(__name__)


class SecretSyncError(RuntimeError):
    """Raised when secrets cannot be propagated into the container."""


class SecretSyncService:
    """Render GitHub CLI configuration and copy it into the container."""

    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def sync(self, project_id: str, container, secrets: ProjectSecrets) -> Dict[str, str]:
        """Create the GitHub hosts file for the supplied container."""

        hosts_path = self._config_dir / "hosts.yml"
        content = self._render_hosts_yaml(secrets)

        self._prepare_directory(container, hosts_path.parent)
        self._copy_file(container, hosts_path, content.encode("utf-8"))

        logger.info(
            "Injected GitHub credentials", extra={"project_id": project_id, "path": str(hosts_path)}
        )
        return {"path": str(hosts_path)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prepare_directory(self, container, path: Path) -> None:
        result = container.exec_run(["mkdir", "-p", str(path)])
        exit_code = getattr(result, "exit_code", 1)
        if exit_code not in (0, None):
            raise SecretSyncError(f"Failed to create directory {path}: exit code {exit_code}")

    def _copy_file(self, container, destination: Path, content: bytes) -> None:
        data_stream = io.BytesIO()
        with tarfile.open(fileobj=data_stream, mode="w") as tar:
            info = tarfile.TarInfo(name=destination.name)
            info.size = len(content)
            info.mtime = int(time.time())
            info.mode = 0o600
            tar.addfile(info, io.BytesIO(content))
        data_stream.seek(0)

        success = container.put_archive(str(destination.parent), data_stream.getvalue())
        if not success:
            raise SecretSyncError(f"Failed to copy secrets file to {destination}")

    def _render_hosts_yaml(self, secrets: ProjectSecrets) -> str:
        host = secrets.additional_secrets.get("github_host", "github.com")
        entry = {
            "user": secrets.additional_secrets.get("github_user", secrets.username),
            "oauth_token": secrets.github_api_key,
            "git_protocol": secrets.additional_secrets.get("git_protocol", "https"),
            "hostname": secrets.additional_secrets.get("hostname", host),
        }
        extras = {
            key: value
            for key, value in secrets.additional_secrets.items()
            if key not in {"github_host", "github_user", "git_protocol", "hostname"}
        }
        entry.update(extras)
        document = {host: entry}
        return yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
