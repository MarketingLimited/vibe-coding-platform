import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import redis

from ..config import Settings
from ..models.projects import ProjectCreate, ProjectInfo
from .security import generate_password, generate_project_id, hash_password
from .repository import ProjectRepository
from .secrets import SecretStorage

logger = logging.getLogger(__name__)


class ProjectService:
    """Coordinate project metadata across Redis cache and SQLite storage."""

    def __init__(
        self,
        redis_client: redis.Redis,
        settings: Settings,
        repository: ProjectRepository,
        secret_storage: Optional[SecretStorage] = None,
    ) -> None:
        self.redis = redis_client
        self.settings = settings
        self.repository = repository
        self.secret_storage = secret_storage

    # ------------------------------------------------------------------
    # Redis helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _project_key(project_id: str) -> str:
        return f"project:{project_id}"

    @staticmethod
    def _user_projects_key(username: str) -> str:
        return f"user:{username}:projects"

    def _cache_mapping(self, data: Dict[str, str]) -> Dict[str, str]:
        mapping = {
            "project_id": data["project_id"],
            "username": data["username"],
            "project_name": data["project_name"],
            "project_type": data["project_type"],
            "database": data.get("database", data.get("database_engine", "none")),
            "redis": json.dumps(bool(int(data.get("redis_enabled", "0"))))
            if "redis_enabled" in data
            else data.get("redis", "false"),
            "password_hash": data["password_hash"],
            "container_id": data.get("container_id", ""),
            "created_at": data["created_at"],
            "status": data.get("status", "unknown"),
        }
        return mapping

    def _rehydrate_cache(self, data: Dict[str, str]) -> None:
        mapping = self._cache_mapping(data)
        project_id = mapping["project_id"]
        username = mapping["username"]
        self.redis.hset(self._project_key(project_id), mapping=mapping)
        self.redis.sadd(self._user_projects_key(username), project_id)

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def _serialise(self, data: Dict[str, str]) -> ProjectInfo:
        database_value = data.get("database") or data.get("database_engine") or "none"
        redis_value = data.get("redis")
        if redis_value is None and "redis_enabled" in data:
            redis_value = bool(int(data["redis_enabled"]))
        elif isinstance(redis_value, str):
            redis_value = redis_value.lower() == "true"
        else:
            redis_value = bool(redis_value)

        created_at_raw = data.get("created_at")
        created_at = (
            datetime.fromisoformat(created_at_raw)
            if created_at_raw
            else datetime.now(timezone.utc)
        )

        return ProjectInfo(
            project_id=data["project_id"],
            username=data["username"],
            project_name=data["project_name"],
            project_type=data.get("project_type", "python"),
            created_at=created_at,
            status=data.get("status", "unknown"),
            container_id=data.get("container_id"),
            database=database_value,
            redis=bool(redis_value),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def project_exists(self, project_id: str) -> bool:
        if self.redis.exists(self._project_key(project_id)):
            return True
        record = self.repository.get(project_id)
        if not record:
            return False
        self._rehydrate_cache(record)
        return True

    def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        data = self.redis.hgetall(self._project_key(project_id))
        if data:
            return self._serialise(data)

        record = self.repository.get(project_id)
        if not record:
            return None
        self._rehydrate_cache(record)
        return self._serialise(record)

    def list_user_projects(self, username: str) -> List[ProjectInfo]:
        records = self.repository.list_by_user(username)
        projects: List[ProjectInfo] = []
        for record in records:
            self._rehydrate_cache(record)
            projects.append(self._serialise(record))
        return projects

    def remove_project(self, project_id: str) -> Optional[ProjectInfo]:
        project = self.get_project(project_id)
        if not project:
            return None

        logger.info("Removing project from metadata store", extra={"project_id": project_id})
        self.repository.delete(project_id)
        self.redis.delete(self._project_key(project_id))
        self.redis.srem(self._user_projects_key(project.username), project_id)
        if self.secret_storage:
            self.secret_storage.delete_project_secrets(project_id)
        return project

    def create_project_record(
        self, payload: ProjectCreate, container_id: str, status: str
    ) -> Dict[str, str]:
        project_id = generate_project_id(payload.username, payload.project_name)
        password = generate_password()
        password_hash = hash_password(password)
        timestamp = datetime.now(timezone.utc).isoformat()

        database_value = (payload.database or "none")

        record = {
            "project_id": project_id,
            "username": payload.username,
            "project_name": payload.project_name,
            "project_type": payload.project_type,
            "database": database_value,
            "database_engine": database_value,
            "redis_enabled": "1" if payload.redis else "0",
            "password_hash": password_hash,
            "container_id": container_id,
            "created_at": timestamp,
            "updated_at": timestamp,
            "status": status,
        }

        logger.info(
            "Registered project",
            extra={"project_id": project_id, "username": payload.username},
        )
        self.repository.upsert(record)
        self._rehydrate_cache(record)

        if self.secret_storage:
            try:
                self.secret_storage.store_project_secrets(
                    project_id,
                    payload.github_api_key,
                    payload.additional_secrets,
                )
            except Exception:
                logger.exception(
                    "Failed to persist GitHub credentials",
                    extra={"project_id": project_id},
                )
                self.repository.delete(project_id)
                self.redis.delete(self._project_key(project_id))
                self.redis.srem(self._user_projects_key(payload.username), project_id)
                raise

        return {
            "project_id": project_id,
            "password": password,
            "container_id": container_id,
        }

    def can_create_project(self, username: str) -> bool:
        count = self.repository.count_for_user(username)
        return count < self.settings.max_projects_per_user

    def verify_credentials(self, project_id: str, password: str) -> bool:
        data = self.redis.hgetall(self._project_key(project_id))
        if not data:
            record = self.repository.get(project_id)
            if not record:
                return False
            self._rehydrate_cache(record)
            data = record

        stored_hash = data.get("password_hash")
        if not stored_hash:
            return False
        return hash_password(password) == stored_hash

    def update_container_status(
        self, project_id: str, status: str, container_id: Optional[str]
    ) -> None:
        logger.info(
            "Updating project status",
            extra={"project_id": project_id, "status": status, "container_id": container_id},
        )
        self.repository.update_status(project_id, status, container_id)
        mapping: Dict[str, str] = {"status": status}
        if container_id:
            mapping["container_id"] = container_id
        self.redis.hset(self._project_key(project_id), mapping=mapping)

    def rotate_password(self, project_id: str) -> Optional[str]:
        if not self.repository.get(project_id):
            return None

        password = generate_password()
        password_hash = hash_password(password)
        self.repository.update_password(project_id, password_hash)
        self.redis.hset(self._project_key(project_id), mapping={"password_hash": password_hash})
        logger.info("Rotated project password", extra={"project_id": project_id})
        return password
