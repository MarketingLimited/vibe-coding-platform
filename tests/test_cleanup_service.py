from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys
import types

redis_stub = types.ModuleType("redis")
redis_stub.Redis = type("Redis", (), {})
redis_stub.RedisError = Exception
sys.modules.setdefault("redis", redis_stub)

httpx_stub = types.ModuleType("httpx")


class _AsyncClient:
    async def __aenter__(self):  # pragma: no cover - stubbed behaviour
        return self

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - stubbed behaviour
        return None

    async def post(self, *_args, **_kwargs):  # pragma: no cover - stubbed behaviour
        return None


httpx_stub.AsyncClient = _AsyncClient
sys.modules.setdefault("httpx", httpx_stub)

pydantic_stub = types.ModuleType("pydantic")


class _BaseSettings:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _field(default=None, **_kwargs):
    return default


pydantic_stub.BaseSettings = _BaseSettings
pydantic_stub.Field = _field
sys.modules.setdefault("pydantic", pydantic_stub)

from cleanup.app.service import CleanupService


class FakeRedis:
    def __init__(self, hashes: dict[str, dict[str, str]] | None = None) -> None:
        self._hashes = hashes or {}
        self.deleted_keys: list[str] = []

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    def delete(self, key: str) -> None:
        self.deleted_keys.append(key)
        self._hashes.pop(key, None)


class DummySettings:
    def __init__(
        self,
        projects_dir: Path,
        logs_dir: Path,
        db_path: Path,
        cleanup_interval: int = 60,
        max_project_age_days: int = 30,
        max_log_size_mb: int = 10,
        max_storage_usage_gb: int = 500,
    ) -> None:
        self.projects_dir = projects_dir
        self.logs_dir = logs_dir
        self.db_path = db_path
        self.cleanup_interval = cleanup_interval
        self.max_project_age_days = max_project_age_days
        self.max_log_size_mb = max_log_size_mb
        self.max_storage_usage_gb = max_storage_usage_gb
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_db = 0
        self.notification_webhook = None


def _make_settings(tmp_path: Path) -> DummySettings:
    projects_dir = tmp_path / "projects"
    logs_dir = tmp_path / "logs"
    db_path = tmp_path / "data" / "projects.db"
    projects_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)
    db_path.parent.mkdir(parents=True)
    return DummySettings(projects_dir, logs_dir, db_path)


def _age_path(path: Path, days: int) -> None:
    timestamp = (datetime.now(UTC) - timedelta(days=days)).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_cleanup_skips_active_project_via_redis(tmp_path):
    settings = _make_settings(tmp_path)
    project_dir = settings.projects_dir / "alice-demo"
    project_dir.mkdir()
    _age_path(project_dir, 60)

    redis = FakeRedis({"project:alice-demo": {"status": "active"}})
    service = CleanupService(settings, redis_client=redis)

    removed = service.cleanup_projects()

    assert removed == []
    assert project_dir.exists()


def test_cleanup_skips_active_project_via_database(tmp_path):
    settings = _make_settings(tmp_path)
    project_dir = settings.projects_dir / "bob-app"
    project_dir.mkdir()
    _age_path(project_dir, 90)

    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("CREATE TABLE projects (project_id TEXT PRIMARY KEY, status TEXT)")
        conn.execute("INSERT INTO projects(project_id, status) VALUES (?, ?)", ("bob-app", "running"))

    service = CleanupService(settings, redis_client=FakeRedis())

    removed = service.cleanup_projects()

    assert removed == []
    assert project_dir.exists()


def test_cleanup_removes_inactive_project(tmp_path):
    settings = _make_settings(tmp_path)
    project_dir = settings.projects_dir / "carol-site"
    project_dir.mkdir()
    _age_path(project_dir, 120)

    with sqlite3.connect(settings.db_path) as conn:
        conn.execute("CREATE TABLE projects (project_id TEXT PRIMARY KEY, status TEXT)")
        conn.execute("INSERT INTO projects(project_id, status) VALUES (?, ?)", ("carol-site", "deleted"))

    redis = FakeRedis({})
    service = CleanupService(settings, redis_client=redis)

    removed = service.cleanup_projects()

    assert removed == ["carol-site"]
    assert not project_dir.exists()
    assert redis.deleted_keys == ["project:carol-site"]
