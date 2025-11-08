"""Primary service layer for the project manager."""

from __future__ import annotations

import logging
import shlex
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import docker
import redis
try:  # pragma: no cover - fallback when dependency not installed in tests
    import requests_unixsocket
except ModuleNotFoundError:  # pragma: no cover - fallback when dependency not installed in tests
    requests_unixsocket = None  # type: ignore[assignment]

from ..config import Settings
from ..models import (
    ExecCommand,
    GitCommitCommand,
    GitLogCommand,
    GitResetCommand,
    ProjectRequest,
    ProjectSecrets,
    ProjectStatus,
)
from .router_registry import RouterRegistry
from .secret_sync import SecretSyncError, SecretSyncService

logger = logging.getLogger(__name__)


_docker_requests_monkeypatched = False


def _ensure_docker_requests_adapter() -> None:
    """Register support for http+docker URLs used by the Docker client."""

    global _docker_requests_monkeypatched
    if _docker_requests_monkeypatched:
        return

    if requests_unixsocket is None:  # pragma: no cover - only reached in partial installs
        logger.debug("requests-unixsocket is not installed; Docker socket support disabled")
        _docker_requests_monkeypatched = True
        return

    requests_unixsocket.monkeypatch()
    _docker_requests_monkeypatched = True


class ProjectManager:
    """Manage per-project Docker containers and metadata synchronisation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        _ensure_docker_requests_adapter()
        self.docker_client = docker.from_env()
        self.redis = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
        self.secret_sync = SecretSyncService(settings.gh_config_dir)
        self.router_registry = RouterRegistry(settings, self.docker_client, docker.errors)
        self._ensure_directories()
        self._ensure_network()
        self.router_registry.ensure_network()
        self._last_backups: Dict[str, Path] = {}

    # ------------------------------------------------------------------
    # environment preparation
    # ------------------------------------------------------------------
    def _ensure_directories(self) -> None:
        self.settings.projects_dir.mkdir(parents=True, exist_ok=True)
        self.settings.logs_dir.mkdir(parents=True, exist_ok=True)
        self.settings.backups_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_network(self) -> None:
        try:
            self.docker_client.networks.get(self.settings.network_name)
        except docker.errors.NotFound:
            logger.info("Creating network %s", self.settings.network_name)
            self.docker_client.networks.create(
                self.settings.network_name,
                driver="bridge",
            )

    def _image_name(self, project_type: str) -> str:
        return f"{self.settings.image_prefix}-{project_type}:latest"

    def _workspace_path(self, project_id: str) -> Path:
        return self.settings.projects_dir / project_id

    def _template_path(self) -> Path:
        return self.settings.templates_dir / "default"

    def _prepare_workspace(self, project_id: str) -> Path:
        workspace = self._workspace_path(project_id)
        if workspace.exists():
            return workspace

        workspace.mkdir(parents=True, exist_ok=True)
        template = self._template_path()
        if template.exists():
            for item in template.iterdir():
                dest = workspace / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
        return workspace

    def _container_name(self, project_id: str) -> str:
        return f"vibe-{project_id}"

    def _find_container(self, project_id: str) -> Optional[docker.models.containers.Container]:
        name = self._container_name(project_id)
        try:
            return self.docker_client.containers.get(name)
        except docker.errors.NotFound:
            return None

    def _backup_root(self, project_id: str) -> Path:
        return self.settings.backups_dir / project_id

    def _create_workspace_backup(self, project_id: str) -> Path:
        workspace = self._workspace_path(project_id)
        if not workspace.exists():
            raise FileNotFoundError(f"Workspace for {project_id} does not exist")

        backup_root = self._backup_root(project_id)
        backup_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup_path = backup_root / f"{timestamp}-{uuid.uuid4().hex[:8]}"
        shutil.copytree(workspace, backup_path)
        self._last_backups[project_id] = backup_path
        return backup_path

    @staticmethod
    def _truncate_output(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[:limit] + "\n...[truncated]"

    def _run_git_command(
        self,
        project_id: str,
        command: str,
        cwd: str,
        timeout: Optional[int],
        max_output_size: int,
        extra_state: Optional[Dict[str, str]] = None,
    ) -> Dict[str, object]:
        container = self._find_container(project_id)
        if not container:
            raise docker.errors.NotFound(f"Container not found for {project_id}")
        if container.status != "running":
            container.start()

        stdout = ""
        stderr = ""
        returncode = 0

        if hasattr(container, "exec_run"):
            result = container.exec_run(
                cmd=["bash", "-lc", command],
                workdir=cwd,
                demux=True,
                timeout=timeout,
            )
            stdout_bytes, stderr_bytes = result.output if isinstance(result.output, tuple) else (result.output, b"")
            stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
            stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")
            returncode = result.exit_code
        else:
            host_cwd = cwd
            if not Path(cwd).exists():
                host_cwd = str(self._workspace_path(project_id))
            try:
                completed = subprocess.run(
                    ["bash", "-lc", command],
                    cwd=host_cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    check=False,
                )
                stdout = completed.stdout
                stderr = completed.stderr
                returncode = completed.returncode
            except subprocess.TimeoutExpired as exc:
                stdout = (exc.stdout or "")
                stderr = (exc.stderr or "") + "\nCommand timed out"
                returncode = 124

        stdout = self._truncate_output(stdout, max_output_size)
        stderr = self._truncate_output(stderr, max_output_size)

        container.reload()
        self._update_state(project_id, container.status, container.id, extra_state)

        return {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    # ------------------------------------------------------------------
    # metadata helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _project_key(project_id: str) -> str:
        return f"project:{project_id}"

    def _update_state(
        self, project_id: str, status: str, container_id: Optional[str], extra: Optional[Dict[str, str]] = None
    ) -> None:
        payload: Dict[str, str] = {
            "status": status,
            "container_id": container_id or "",
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }
        preview_url = extra.get("preview_url") if extra else None
        if not preview_url:
            preview_url = self.router_registry.project_url(project_id)
        if preview_url:
            payload["preview_url"] = preview_url
        if extra:
            payload.update(extra)
        try:
            self.redis.hset(self._project_key(project_id), mapping=payload)
        except redis.RedisError as exc:  # pragma: no cover - log only
            logger.warning(
                "Failed to publish project state", extra={"project_id": project_id, "error": str(exc)}
            )

    def sync_container_states(self) -> Dict[str, str]:
        summary: Dict[str, str] = {}
        containers = self.docker_client.containers.list(all=True, filters={"label": "com.vibe.project-id"})
        for container in containers:
            project_id = container.labels.get("com.vibe.project-id")
            if not project_id:
                continue
            container.reload()
            status = container.status
            summary[project_id] = status
            self._update_state(project_id, status, container.id)
        return summary

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def create_project(self, request: ProjectRequest) -> ProjectStatus:
        workspace = self._prepare_workspace(request.project_id)

        container = self._find_container(request.project_id)
        if container:
            raise docker.errors.APIError(f"Container already exists for {request.project_id}")

        image = self._image_name(request.project_type)

        environment = {
            "PROJECT_ID": request.project_id,
            "WORKSPACE": str(workspace),
            "PROJECT_TYPE": request.project_type,
            "PROJECT_USERNAME": request.username,
        }
        if request.database:
            environment[f"{request.database.upper()}_ENABLED"] = "true"
        if request.redis:
            environment["REDIS_ENABLED"] = "true"

        logger.info("Creating container", extra={"project_id": request.project_id, "image": image})
        labels = {
            "com.vibe.project-id": request.project_id,
            "com.vibe.project-type": request.project_type,
        }
        labels.update(self.router_registry.labels_for(request.project_id))

        container = self.docker_client.containers.create(
            image=image,
            name=self._container_name(request.project_id),
            detach=True,
            environment=environment,
            volumes={str(workspace): {"bind": "/workspace", "mode": "rw"}},
            network=self.settings.network_name,
            labels=labels,
            mem_limit=request.limits.memory,
            cpu_period=100000,
            cpu_quota=int(request.limits.cpu * 100000),
            tty=True,
        )

        container.start()
        container.reload()
        self.router_registry.attach(container, request.project_id)
        preview_url = self.router_registry.project_url(request.project_id)
        logger.info("Container started", extra={"project_id": request.project_id, "container_id": container.id})
        extra = {"workspace": str(workspace)}
        if preview_url:
            extra["preview_url"] = preview_url
        self._update_state(request.project_id, container.status, container.id, extra)

        return ProjectStatus(
            project_id=request.project_id,
            status=container.status,
            container_id=container.id,
            info={key: value for key, value in {"workspace": str(workspace), "preview_url": preview_url}.items() if value},
        )

    def sync_project_secrets(self, project_id: str, secrets: ProjectSecrets) -> Dict[str, str]:
        """Write the GitHub CLI configuration into the project container."""

        container = self._find_container(project_id)
        if not container:
            raise docker.errors.NotFound(f"Container not found for {project_id}")

        if container.status != "running":
            container.start()
            container.reload()

        try:
            result = self.secret_sync.sync(project_id, container, secrets)
        except SecretSyncError as exc:
            logger.error(
                "Secret synchronisation failed", extra={"project_id": project_id, "error": str(exc)}
            )
            raise

        self._update_state(
            project_id,
            container.status,
            container.id,
            {"secrets_synced": datetime.now(timezone.utc).isoformat()},
        )
        return result

    def delete_project(self, project_id: str) -> ProjectStatus:
        container = self._find_container(project_id)
        if container:
            logger.info("Stopping container", extra={"project_id": project_id})
            self.router_registry.detach(container)
            container.stop(timeout=15)
            container.remove()
        workspace = self._workspace_path(project_id)
        if workspace.exists():
            shutil.rmtree(workspace)
        self._update_state(project_id, "deleted", None)
        return ProjectStatus(project_id=project_id, status="deleted", container_id=container.id if container else None)

    def get_status(self, project_id: str) -> Optional[ProjectStatus]:
        container = self._find_container(project_id)
        if not container:
            self._update_state(project_id, "missing", None)
            return None
        container.reload()
        preview_url = self.router_registry.project_url(project_id)
        info: Dict[str, str] = {"image": container.image.tags[0] if container.image.tags else ""}
        if preview_url:
            info["preview_url"] = preview_url

        status = ProjectStatus(
            project_id=project_id,
            status=container.status,
            container_id=container.id,
            info=info,
        )
        self._update_state(project_id, status.status, status.container_id)
        return status

    def exec(self, project_id: str, command: ExecCommand) -> dict:
        container = self._find_container(project_id)
        if not container:
            raise docker.errors.NotFound(f"Container not found for {project_id}")
        if container.status != "running":
            container.start()

        logger.info("Executing command", extra={"project_id": project_id, "cmd": command.command})
        result = container.exec_run(
            cmd=f"bash -lc '{command.command}'",
            workdir=command.cwd,
            demux=True,
        )
        stdout = result.output[0].decode("utf-8", errors="replace") if result.output[0] else ""
        stderr = result.output[1].decode("utf-8", errors="replace") if result.output[1] else ""

        if len(stdout) > command.max_output_size:
            stdout = stdout[: command.max_output_size] + "\n...[truncated]"
        if len(stderr) > command.max_output_size:
            stderr = stderr[: command.max_output_size] + "\n...[truncated]"

        self._update_state(project_id, container.status, container.id)

        return {
            "returncode": result.exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "elapsed_seconds": 0.0,
        }

    def git_commit(self, project_id: str, command: GitCommitCommand) -> Dict[str, object]:
        backup_path = self._create_workspace_backup(project_id)
        git_args = ["git", "commit"]
        if command.add_all:
            self._run_git_command(
                project_id,
                "git add --all",
                command.cwd,
                command.timeout,
                command.max_output_size,
            )
            git_args.append("--all")
        if command.amend:
            git_args.append("--amend")
        git_args.extend(["-m", command.message])
        git_command = " ".join(shlex.quote(part) for part in git_args)
        result = self._run_git_command(
            project_id,
            git_command,
            command.cwd,
            command.timeout,
            command.max_output_size,
            {"last_git_backup": str(backup_path)},
        )
        result["backup_path"] = str(backup_path)
        return result

    def git_log(self, project_id: str, command: GitLogCommand) -> Dict[str, object]:
        git_args = ["git", "log", "-n", str(command.limit)]
        if command.format:
            git_args.append(f"--pretty={command.format}")
        git_command = " ".join(shlex.quote(part) for part in git_args)
        return self._run_git_command(
            project_id,
            git_command,
            command.cwd,
            command.timeout,
            command.max_output_size,
        )

    def git_reset(self, project_id: str, command: GitResetCommand) -> Dict[str, object]:
        backup_path = self._create_workspace_backup(project_id)
        git_args = ["git", "reset"]
        if command.hard:
            git_args.append("--hard")
        git_args.append(command.commit)
        git_command = " ".join(shlex.quote(part) for part in git_args)
        result = self._run_git_command(
            project_id,
            git_command,
            command.cwd,
            command.timeout,
            command.max_output_size,
            {"last_git_backup": str(backup_path)},
        )
        result["backup_path"] = str(backup_path)
        return result

    def close(self) -> None:
        self.docker_client.close()
        try:
            self.redis.close()
        except Exception:  # pragma: no cover - redis client may not expose close
            pass
