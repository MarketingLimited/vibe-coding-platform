"""Encrypted storage for project scoped GitHub credentials."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from pathlib import Path
from threading import RLock
from typing import Dict, Mapping, Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


class SecretStorageError(RuntimeError):
    """Raised when the secrets storage cannot be accessed."""


class SecretStorage:
    """Persist GitHub credentials encrypted at rest on disk."""

    def __init__(self, storage_path: Path, encryption_key: str) -> None:
        if not encryption_key:
            raise ValueError("encryption_key is required for SecretStorage")

        self._path = storage_path
        self._lock = RLock()
        self._fernet = Fernet(self._normalise_key(encryption_key))

        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write({})

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

        payload = self._read()
        payload[project_id] = {
            "github_api_key": github_api_key,
            "additional_secrets": dict(additional_secrets or {}),
        }
        self._write(payload)

        logger.info("Stored encrypted GitHub credentials", extra={"project_id": project_id})

    def get_project_secrets(self, project_id: str) -> Optional[Dict[str, object]]:
        """Return decrypted secrets for a project, if available."""

        payload = self._read()
        entry = payload.get(project_id)
        if not entry:
            return None

        return {
            "github_api_key": entry.get("github_api_key", ""),
            "additional_secrets": dict(entry.get("additional_secrets", {})),
        }

    def delete_project_secrets(self, project_id: str) -> None:
        """Remove secrets associated with the project."""

        payload = self._read()
        if project_id in payload:
            payload.pop(project_id)
            self._write(payload)
            logger.info("Deleted secrets for project", extra={"project_id": project_id})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
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

    def _read(self) -> Dict[str, Dict[str, object]]:
        with self._lock:
            if not self._path.exists():
                return {}

            data = self._path.read_bytes()
            if not data:
                return {}

            try:
                decrypted = self._fernet.decrypt(data)
            except InvalidToken as exc:
                raise SecretStorageError("Unable to decrypt secrets storage") from exc

            try:
                return json.loads(decrypted.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise SecretStorageError("Secrets storage is corrupted") from exc

    def _write(self, payload: Dict[str, Dict[str, object]]) -> None:
        serialised = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        token = self._fernet.encrypt(serialised)

        with self._lock:
            tmp_path = self._path.with_suffix(".tmp")
            tmp_path.write_bytes(token)
            tmp_path.replace(self._path)
