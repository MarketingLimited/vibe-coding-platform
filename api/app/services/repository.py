"""Persistence helpers for project metadata stored in SQLite."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional


class ProjectRepository:
    """Simple thread-safe SQLite repository for project metadata."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._lock = RLock()
        self._initialise()

    # ---------------------------------------------------------------------
    # internal helpers
    # ---------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialise(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS projects (
                        project_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        project_name TEXT NOT NULL,
                        project_type TEXT NOT NULL,
                        database_engine TEXT,
                        redis_enabled INTEGER NOT NULL DEFAULT 0,
                        password_hash TEXT NOT NULL,
                        container_id TEXT,
                        preview_url TEXT,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                try:
                    conn.execute("ALTER TABLE projects ADD COLUMN preview_url TEXT")
                except sqlite3.OperationalError as exc:  # pragma: no cover - legacy upgrade path
                    message = str(exc).lower()
                    if "duplicate column" not in message:
                        raise
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_projects_username ON projects(username)"
                )

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------
    def upsert(self, payload: Dict[str, str]) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO projects (
                        project_id, username, project_name, project_type,
                        database_engine, redis_enabled, password_hash,
                        container_id, preview_url, status, created_at, updated_at
                    ) VALUES (
                        :project_id, :username, :project_name, :project_type,
                        :database, :redis_enabled, :password_hash,
                        :container_id, :preview_url, :status, :created_at, :updated_at
                    )
                    ON CONFLICT(project_id) DO UPDATE SET
                        username=excluded.username,
                        project_name=excluded.project_name,
                        project_type=excluded.project_type,
                        database_engine=excluded.database_engine,
                        redis_enabled=excluded.redis_enabled,
                        password_hash=excluded.password_hash,
                        container_id=excluded.container_id,
                        preview_url=excluded.preview_url,
                        status=excluded.status,
                        updated_at=excluded.updated_at
                    """,
                    payload,
                )

    def get(self, project_id: str) -> Optional[Dict[str, str]]:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM projects WHERE project_id = ?", (project_id,)
                ).fetchone()
        if not row:
            return None
        return dict(row)

    def list_by_user(self, username: str) -> List[Dict[str, str]]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM projects WHERE username = ? ORDER BY created_at", (username,)
                ).fetchall()
        return [dict(row) for row in rows]

    def delete(self, project_id: str) -> Optional[Dict[str, str]]:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM projects WHERE project_id = ?", (project_id,)
                ).fetchone()
                if row:
                    conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
        if not row:
            return None
        return dict(row)

    def update_status(
        self,
        project_id: str,
        status: str,
        container_id: Optional[str],
        preview_url: Optional[str] = None,
    ) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE projects
                    SET status = ?,
                        container_id = ?,
                        preview_url = COALESCE(?, preview_url),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE project_id = ?
                    """,
                    (status, container_id, preview_url, project_id),
                )

    def update_password(self, project_id: str, password_hash: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE projects
                    SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE project_id = ?
                    """,
                    (password_hash, project_id),
                )

    def count_for_user(self, username: str) -> int:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) AS total FROM projects WHERE username = ?", (username,)
                ).fetchone()
        return int(row["total"]) if row else 0

    def ping(self) -> bool:
        """Validate database connectivity."""

        with self._lock:
            with self._connect() as conn:
                conn.execute("SELECT 1")
        return True
