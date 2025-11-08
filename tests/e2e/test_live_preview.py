import sys
import subprocess
import types
from pathlib import Path
from typing import Dict, Optional

import pytest

# ---------------------------------------------------------------------------
# Runtime stubs for optional dependencies (docker, redis, pydantic)
# ---------------------------------------------------------------------------
if "docker" not in sys.modules:  # pragma: no cover - testing utility
    class _DockerErrors:
        class NotFound(Exception):
            pass

        class APIError(Exception):
            pass

    sys.modules["docker"] = types.SimpleNamespace(errors=_DockerErrors, from_env=lambda: None)

if "redis" not in sys.modules:  # pragma: no cover - testing utility
    class _FakeRedisClient:
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ARG002
            pass

        def hset(self, *args, **kwargs):  # noqa: ANN002, ARG002
            pass

        def close(self) -> None:
            pass

    class _RedisErrors(Exception):
        pass

    sys.modules["redis"] = types.SimpleNamespace(Redis=_FakeRedisClient, RedisError=_RedisErrors)

if "yaml" not in sys.modules:  # pragma: no cover - testing utility
    sys.modules["yaml"] = types.SimpleNamespace(safe_load=lambda *args, **kwargs: {})

# ---------------------------------------------------------------------------
# Minimal pydantic stub (tests run without installing the dependency)
# ---------------------------------------------------------------------------
if "pydantic" not in sys.modules:  # pragma: no cover - testing utility
    class _BaseModel:
        def __init__(self, **data):
            for name, value in self.__class__.__dict__.items():
                if name.startswith("_") or callable(value):
                    continue
                setattr(self, name, value)
            for key, value in data.items():
                setattr(self, key, value)

        def dict(self) -> Dict[str, object]:
            return {
                key: value
                for key, value in self.__dict__.items()
                if not key.startswith("_")
            }

    class _BaseSettings(_BaseModel):
        pass

    def _field(default=None, default_factory=None, **kwargs):  # noqa: ANN001
        if default_factory is not None:
            return default_factory()
        return default

    def _validator(*args, **kwargs):  # noqa: ANN001, ANN002
        def decorator(func):
            return func

        return decorator

    sys.modules["pydantic"] = types.SimpleNamespace(
        BaseModel=_BaseModel,
        BaseSettings=_BaseSettings,
        Field=_field,
        validator=_validator,
    )

from project_manager.app.models import GitCommitCommand, GitLogCommand, GitResetCommand
from project_manager.app.services import ProjectManager


class FakeSettings:
    def __init__(self, base_path: Path) -> None:
        self.projects_dir = base_path / "projects"
        self.logs_dir = base_path / "logs"
        self.templates_dir = base_path / "templates"
        self.backups_dir = base_path / "backups"
        self.gh_config_dir = base_path / ".config" / "gh"
        self.docker_host = None
        self.network_name = "vibe-network"
        self.proxy_network_name = "vibe-proxy"
        self.image_prefix = "vibe-project"
        self.preview_domain = "kazaaz.com"
        self.preview_scheme = "https"
        self.preview_internal_port = 4173
        self.preview_entrypoints = "websecure"
        self.preview_service_scheme = "http"
        self.redis_host = "redis"
        self.redis_port = 6379
        self.redis_db = 0
        self.default_cpu_limit = 2.0
        self.default_memory_limit = "4G"
        self.default_storage_limit = "10G"
        self.auto_cleanup_days = 30
        self.cleanup_inactive_projects = True


class FakeLimits:
    def __init__(self, cpu: float = 2.0, memory: str = "4G", storage: str = "10G") -> None:
        self.cpu = cpu
        self.memory = memory
        self.storage = storage


class FakeRequest:
    def __init__(
        self,
        project_id: str,
        project_type: str,
        username: str,
        database: Optional[str] = None,
        redis_enabled: bool = False,
        limits: Optional[FakeLimits] = None,
    ) -> None:
        self.project_id = project_id
        self.project_type = project_type
        self.username = username
        self.database = database
        self.redis = redis_enabled
        self.limits = limits or FakeLimits()


class FakeRedis:
    def __init__(self) -> None:
        self.store: Dict[str, Dict[str, str]] = {}

    def hset(self, key: str, mapping: Dict[str, str]) -> None:
        self.store[key] = mapping

    def close(self) -> None:  # pragma: no cover - compatibility hook
        pass


class FakeNetwork:
    def __init__(self, name: str, errors: types.SimpleNamespace) -> None:
        self.name = name
        self.errors = errors
        self.connections: list[Dict[str, object]] = []

    def connect(self, container, aliases=None) -> None:
        for connection in self.connections:
            if connection["container"] is container:
                raise self.errors.APIError("container already exists on network")
        container.connected_networks.add(self.name)
        self.connections.append({"container": container, "aliases": aliases or []})

    def disconnect(self, container) -> None:
        remaining = []
        for connection in self.connections:
            if connection["container"] is container:
                continue
            remaining.append(connection)
        self.connections = remaining
        container.connected_networks.discard(self.name)


class FakeNetworks:
    def __init__(self, errors: types.SimpleNamespace) -> None:
        self.errors = errors
        self._networks: Dict[str, FakeNetwork] = {}

    def get(self, name: str) -> FakeNetwork:
        if name not in self._networks:
            raise self.errors.NotFound(f"network {name} not found")
        return self._networks[name]

    def create(self, name: str, driver: str = "bridge") -> FakeNetwork:  # noqa: ARG002
        network = self._networks.get(name)
        if network is None:
            network = FakeNetwork(name, self.errors)
            self._networks[name] = network
        return network


class FakeContainer:
    def __init__(self, manager: "FakeContainers", name: str, image: str, labels: Dict[str, str]) -> None:
        self._manager = manager
        self.name = name
        self.id = f"{name}-id"
        self.image = types.SimpleNamespace(tags=[image])
        self.labels = labels
        self.status = "created"
        self.connected_networks: set[str] = set()

    def start(self) -> None:
        self.status = "running"

    def reload(self) -> None:  # pragma: no cover - no dynamic state
        pass

    def stop(self, timeout: int = 0) -> None:  # noqa: ARG002
        self.status = "exited"

    def remove(self) -> None:
        self._manager.remove_container(self.name)


class FakeContainers:
    def __init__(self, client: "FakeDockerClient", errors: types.SimpleNamespace) -> None:
        self._client = client
        self._errors = errors
        self._containers: Dict[str, FakeContainer] = {}

    def create(self, *, image: str, name: str, labels: Dict[str, str], network: str, **kwargs):  # noqa: ANN003, ARG002
        container = FakeContainer(self, name, image, labels)
        self._containers[name] = container
        try:
            target_network = self._client.networks.get(network)
        except self._errors.NotFound:
            target_network = self._client.networks.create(network)
        target_network.connect(container)
        return container

    def get(self, name: str) -> FakeContainer:
        try:
            return self._containers[name]
        except KeyError as exc:
            raise self._errors.NotFound(f"container {name} not found") from exc

    def list(self, all: bool = True, filters: Optional[Dict[str, str]] = None):  # noqa: ARG002
        containers = list(self._containers.values())
        if not filters:
            return containers
        label_filter = filters.get("label") if filters else None
        if not label_filter:
            return containers
        if isinstance(label_filter, str) and "=" in label_filter:
            key, value = label_filter.split("=", 1)
            return [c for c in containers if c.labels.get(key) == value]
        if isinstance(label_filter, str):
            return [c for c in containers if label_filter in c.labels]
        return containers

    def remove_container(self, name: str) -> None:
        self._containers.pop(name, None)


class FakeDockerClient:
    def __init__(self, errors: types.SimpleNamespace) -> None:
        self.errors = errors
        self.networks = FakeNetworks(errors)
        self.containers = FakeContainers(self, errors)

    def close(self) -> None:  # pragma: no cover - compatibility hook
        pass


class FakeDockerModule:
    def __init__(self) -> None:
        errors = types.SimpleNamespace(NotFound=type("NotFound", (Exception,), {}), APIError=type("APIError", (Exception,), {}))
        self.errors = errors
        self.client = FakeDockerClient(errors)

    def from_env(self) -> FakeDockerClient:
        return self.client


@pytest.fixture()
def fake_environment(monkeypatch, tmp_path: Path):
    import project_manager.app.services as services

    fake_docker = FakeDockerModule()
    fake_redis = FakeRedis()

    monkeypatch.setattr(services, "docker", fake_docker)
    monkeypatch.setattr(services.redis, "Redis", lambda **kwargs: fake_redis)

    settings = FakeSettings(tmp_path)
    settings.projects_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    (settings.templates_dir / "default").mkdir(parents=True, exist_ok=True)
    settings.backups_dir.mkdir(parents=True, exist_ok=True)

    manager = ProjectManager(settings)
    return manager, fake_docker, fake_redis


def test_live_preview_registration(fake_environment):
    manager, fake_docker, fake_redis = fake_environment

    request = FakeRequest(
        project_id="Proj-123",
        project_type="python",
        username="demo",
    )

    status = manager.create_project(request)

    assert status.info["preview_url"] == "https://proj-123.kazaaz.com"

    container = fake_docker.client.containers.get(manager._container_name(request.project_id))
    assert container.labels["traefik.enable"] == "true"
    assert container.labels["traefik.docker.network"] == "vibe-proxy"
    assert container.labels["traefik.http.routers.proj-123-router.rule"] == "Host(`proj-123.kazaaz.com`)"

    proxy_network = fake_docker.client.networks.get("vibe-proxy")
    assert proxy_network.connections[0]["container"] is container
    assert "vibe-proxy" in container.connected_networks

    redis_payload = fake_redis.store[f"project:{request.project_id}"]
    assert redis_payload["preview_url"] == "https://proj-123.kazaaz.com"

    manager.delete_project(request.project_id)
    assert proxy_network.connections == []


def test_git_operations_backup_and_reset(fake_environment, tmp_path: Path):
    manager, _fake_docker, _fake_redis = fake_environment

    project_id = "Proj-git"
    request = FakeRequest(
        project_id=project_id,
        project_type="python",
        username="demo",
    )
    manager.create_project(request)

    workspace = manager._workspace_path(project_id)
    subprocess.run(["git", "init"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=workspace, check=True)

    readme = workspace / "README.md"
    readme.write_text("initial\n")
    subprocess.run(["git", "add", "README.md"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=workspace, check=True)
    initial_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=workspace).decode().strip()

    readme.write_text("updated\n")

    commit_result = manager.git_commit(
        project_id,
        GitCommitCommand(message="update readme", cwd=str(workspace)),
    )
    backup_path = Path(commit_result["backup_path"])
    assert backup_path.exists()
    assert "update readme" in manager.git_log(
        project_id,
        GitLogCommand(limit=5, cwd=str(workspace)),
    )["stdout"]

    readme.write_text("broken change\n")
    reset_result = manager.git_reset(
        project_id,
        GitResetCommand(commit=initial_commit, cwd=str(workspace)),
    )
    reset_backup_path = Path(reset_result["backup_path"])
    assert reset_backup_path.exists()
    assert reset_backup_path != backup_path
    assert manager._last_backups[project_id] == reset_backup_path
    assert readme.read_text() == "initial\n"
