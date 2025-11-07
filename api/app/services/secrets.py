"""Encrypted storage for project scoped GitHub credentials."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Dict, Mapping, Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class SecretStorageError(RuntimeError):
    """Raised when the secrets storage cannot be accessed."""


class SecretStorage:
    """Persist GitHub credentials encrypted at rest inside SQLite."""

    def __init__(self, storage_path: Path, encryption_key: str) -> None:
        if not encryption_key:
            raise ValueError("encryption_key is required for SecretStorage")

        self._db_path = storage_path
        self._lock = RLock()
        self._fernet = Fernet(self._normalise_key(encryption_key))

        self._initialise()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def store_project_secrets(
        self,
        project_id: str,
        github_api_key: str,
        additional_secrets: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Persist the GitHub token and optional secrets for a project."""

        if not project_id:
            raise ValueError("project_id is required")
        if not github_api_key:
            raise ValueError("github_api_key is required")

        payload = {
            "github_api_key": github_api_key,
            "additional_secrets": dict(additional_secrets or {}),
        }
        encrypted = self._encrypt(payload)
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO project_secrets (project_id, payload, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(project_id) DO UPDATE SET
                        payload = excluded.payload,
                        updated_at = excluded.updated_at
                    """,
                    (project_id, encrypted, timestamp, timestamp),
                )

        logger.info("Stored encrypted GitHub credentials", extra={"project_id": project_id})

    def get_project_secrets(self, project_id: str) -> Optional[Dict[str, object]]:
        """Return decrypted secrets for a project, if available."""

        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT payload FROM project_secrets WHERE project_id = ?",
                    (project_id,),
                ).fetchone()

        if not row:
            return None

        try:
            return self._decrypt(row[0])
        except SecretStorageError:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise SecretStorageError("Failed to load project secrets") from exc

    def delete_project_secrets(self, project_id: str) -> None:
        """Remove secrets associated with the project."""

        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM project_secrets WHERE project_id = ?", (project_id,))

        logger.info("Deleted secrets for project", extra={"project_id": project_id})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        return connection

    def _initialise(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS project_secrets (
                        project_id TEXT PRIMARY KEY,
                        payload BLOB NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )

    def _normalise_key(self, raw_key: str) -> bytes:
        """Return a Fernet compatible base64 key derived from the raw input."""

        key = raw_key.strip()
        if len(key) == 44:
            try:
                base64.urlsafe_b64decode(key.encode("utf-8"))
                return key.encode("utf-8")
            except Exception:  # pragma: no cover - defensive guard
                logger.debug("Provided encryption key is not base64 encoded")

        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest)

    def _encrypt(self, payload: Dict[str, object]) -> bytes:
        serialised = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return self._fernet.encrypt(serialised)

    def _decrypt(self, token: bytes) -> Dict[str, object]:
        try:
            decrypted = self._fernet.decrypt(token)
        except InvalidToken as exc:
            raise SecretStorageError("Unable to decrypt secrets storage") from exc

        try:
            return json.loads(decrypted.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SecretStorageError("Secrets storage is corrupted") from exc
