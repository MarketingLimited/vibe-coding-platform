from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from api.app.services.repository import ProjectRepository


def _sample_record(project_id: str) -> dict:
    now = datetime.now(UTC).isoformat()
    return {
        "project_id": project_id,
        "username": "demo",
        "project_name": "Demo",
        "project_type": "python",
        "database": "postgres",
        "redis_enabled": 1,
        "password_hash": "hash",
        "container_id": "abc123",
        "preview_url": "https://demo.example",
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }


def test_repository_persists_and_lists(tmp_path: Path):
    repo = ProjectRepository(tmp_path / "projects.db")
    repo.upsert(_sample_record("demo-1"))
    repo.upsert(_sample_record("demo-2"))

    projects = repo.list_by_user("demo")
    assert len(projects) == 2
    assert {p["project_id"] for p in projects} == {"demo-1", "demo-2"}


def test_repository_delete_returns_last_state(tmp_path: Path):
    repo = ProjectRepository(tmp_path / "projects.db")
    repo.upsert(_sample_record("demo-1"))

    deleted = repo.delete("demo-1")
    assert deleted is not None
    assert deleted["project_id"] == "demo-1"
    assert repo.get("demo-1") is None
