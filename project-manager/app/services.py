import logging
import shutil
from pathlib import Path
from typing import Optional

import docker

from .config import Settings
from .models import ExecCommand, ProjectRequest, ProjectStatus

logger = logging.getLogger(__name__)


class ProjectManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.docker_client = docker.from_env()
        self._ensure_directories()
        self._ensure_network()

    def _ensure_directories(self) -> None:
        self.settings.projects_dir.mkdir(parents=True, exist_ok=True)
        self.settings.logs_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_network(self) -> None:
        try:
            self.docker_client.networks.get(self.settings.network_name)
        except docker.errors.NotFound:
            logger.info("Creating network %s", self.settings.network_name)
            self.docker_client.networks.create(self.settings.network_name, driver="bridge")

    def _image_name(self, project_type: str) -> str:
        return f"{self.settings.image_prefix}-{project_type}:latest"

    def _workspace_path(self, project_id: str) -> Path:
        return self.settings.projects_dir / project_id

    def _template_path(self) -> Path:
        template = self.settings.templates_dir / "default"
        return template

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
        container = self.docker_client.containers.create(
            image=image,
            name=self._container_name(request.project_id),
            detach=True,
            environment=environment,
            volumes={str(workspace): {"bind": "/workspace", "mode": "rw"}},
            network=self.settings.network_name,
            labels={
                "com.vibe.project-id": request.project_id,
                "com.vibe.project-type": request.project_type,
            },
            mem_limit=request.limits.memory,
            cpu_period=100000,
            cpu_quota=int(request.limits.cpu * 100000),
            tty=True,
        )

        container.start()
        container.reload()
        logger.info("Container started", extra={"project_id": request.project_id, "container_id": container.id})

        return ProjectStatus(
            project_id=request.project_id,
            status=container.status,
            container_id=container.id,
            info={"workspace": str(workspace)},
        )

    def delete_project(self, project_id: str) -> ProjectStatus:
        container = self._find_container(project_id)
        if container:
            logger.info("Stopping container", extra={"project_id": project_id})
            container.stop(timeout=15)
            container.remove()
        workspace = self._workspace_path(project_id)
        if workspace.exists():
            shutil.rmtree(workspace)
        return ProjectStatus(project_id=project_id, status="deleted", container_id=container.id if container else None)

    def get_status(self, project_id: str) -> Optional[ProjectStatus]:
        container = self._find_container(project_id)
        if not container:
            return None
        container.reload()
        return ProjectStatus(
            project_id=project_id,
            status=container.status,
            container_id=container.id,
            info={"image": container.image.tags[0] if container.image.tags else ""},
        )

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

        return {
            "returncode": result.exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "elapsed_seconds": 0.0,
        }

    def close(self) -> None:
        self.docker_client.close()
