from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.app.config import Settings
from api.app.models.projects import ProjectCreate
from api.app.services.projects import ProjectService
from api.app.services.repository import ProjectRepository
from api.app.services.secrets import SecretStorage


class DummyRedis:
    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, str]] = {}
        self._sets: dict[str, set[str]] = {}

    def hset(self, key: str, mapping: dict[str, str]) -> None:
        self._hashes.setdefault(key, {}).update(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    def delete(self, key: str) -> None:
        self._hashes.pop(key, None)

    def sadd(self, key: str, value: str) -> None:
        self._sets.setdefault(key, set()).add(value)

    def srem(self, key: str, value: str) -> None:
        self._sets.setdefault(key, set()).discard(value)

    def exists(self, key: str) -> int:
        return 1 if key in self._hashes else 0


@pytest.fixture()
def project_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "projects.db",
        github_secrets_path=tmp_path / "secrets.db",
        github_secrets_key="unit-test-key",
    )


def test_secret_storage_encrypts_payload(tmp_path: Path) -> None:
    storage = SecretStorage(tmp_path / "secrets.db", "encryption-key")
    storage.store_project_secrets("demo", "ghp_token_value_1234567890", {"scope": "repo"})

    secrets = storage.get_project_secrets("demo")
    assert secrets == {
        "github_api_key": "ghp_token_value_1234567890",
        "additional_secrets": {"scope": "repo"},
    }

    with sqlite3.connect(tmp_path / "secrets.db") as conn:
        row = conn.execute(
            "SELECT payload FROM project_secrets WHERE project_id = ?",
            ("demo",),
        ).fetchone()
    assert row is not None
    assert isinstance(row[0], (bytes, bytearray))
    assert b"ghp_token_value_1234567890" not in row[0]

    storage.delete_project_secrets("demo")
    with sqlite3.connect(tmp_path / "secrets.db") as conn:
        row = conn.execute(
            "SELECT payload FROM project_secrets WHERE project_id = ?",
            ("demo",),
        ).fetchone()
    assert row is None


def test_project_service_persists_and_rolls_out_secrets(project_settings: Settings) -> None:
    redis_client = DummyRedis()
    repository = ProjectRepository(project_settings.db_path)
    storage = SecretStorage(project_settings.github_secrets_path, project_settings.github_secrets_key)
    service = ProjectService(redis_client, project_settings, repository, storage)

    payload = ProjectCreate(
        username="demo",
        project_name="sample",
        project_type="python",
        github_api_key="ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        additional_secrets={"scope": "repo"},
    )

    record = service.create_project_record(payload, container_id="container-1", status="active")
    stored = storage.get_project_secrets(record["project_id"])
    assert stored is not None
    assert stored["github_api_key"] == "ghp_abcdefghijklmnopqrstuvwxyz0123456789"
    assert stored["additional_secrets"] == {"scope": "repo"}

    service.remove_project(record["project_id"])
    assert storage.get_project_secrets(record["project_id"]) is None
