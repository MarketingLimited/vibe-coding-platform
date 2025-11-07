import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import redis

from ..config import Settings
from ..models.projects import ProjectCreate, ProjectInfo
from .auth import generate_password, generate_project_id, hash_password

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, redis_client: redis.Redis, settings: Settings):
        self.redis = redis_client
        self.settings = settings

    @staticmethod
    def _project_key(project_id: str) -> str:
        return f"project:{project_id}"

    @staticmethod
    def _user_projects_key(username: str) -> str:
        return f"user:{username}:projects"

    def _serialize_project(self, data: Dict[str, str]) -> ProjectInfo:
        return ProjectInfo(
            project_id=data["project_id"],
            username=data["username"],
            project_name=data["project_name"],
            project_type=data["project_type"],
            created_at=datetime.fromisoformat(data["created_at"]),
            status=data.get("status", "unknown"),
            container_id=data.get("container_id"),
            database=data.get("database", "none"),
            redis=data.get("redis", "False").lower() == "true",
        )

    def _store_project(self, project_data: Dict[str, str]) -> None:
        project_id = project_data["project_id"]
        self.redis.hset(self._project_key(project_id), mapping=project_data)
        self.redis.sadd(self._user_projects_key(project_data["username"]), project_id)

    def project_exists(self, project_id: str) -> bool:
        return bool(self.redis.exists(self._project_key(project_id)))

    def get_project(self, project_id: str) -> Optional[ProjectInfo]:
        data = self.redis.hgetall(self._project_key(project_id))
        if not data:
            return None
        return self._serialize_project(data)

    def list_user_projects(self, username: str) -> List[ProjectInfo]:
        project_ids = self.redis.smembers(self._user_projects_key(username))
        return [
            project
            for project_id in project_ids
            if (project := self.get_project(project_id)) is not None
        ]

    def remove_project(self, project_id: str) -> Optional[ProjectInfo]:
        project = self.get_project(project_id)
        if not project:
            return None
        self.redis.delete(self._project_key(project_id))
        self.redis.srem(self._user_projects_key(project.username), project_id)
        return project

    def create_project_record(
        self, payload: ProjectCreate, container_id: str, status: str
    ) -> Dict[str, str]:
        project_id = generate_project_id(payload.username, payload.project_name)
        password = generate_password()
        password_hash = hash_password(password)

        project_data = {
            "project_id": project_id,
            "username": payload.username,
            "project_name": payload.project_name,
            "project_type": payload.project_type,
            "database": (payload.database or "none"),
            "redis": json.dumps(payload.redis),
            "password_hash": password_hash,
            "container_id": container_id,
            "created_at": datetime.utcnow().isoformat(),
            "status": status,
        }

        self._store_project(project_data)
        logger.info("Registered project", extra={"project_id": project_id, "username": payload.username})

        return {"project_id": project_id, "password": password, "container_id": container_id}

    def can_create_project(self, username: str) -> bool:
        project_ids = self.redis.smembers(self._user_projects_key(username))
        return len(project_ids) < self.settings.max_projects_per_user

    def verify_credentials(self, project_id: str, password: str) -> bool:
        data = self.redis.hgetall(self._project_key(project_id))
        if not data:
            return False
        stored_hash = data.get("password_hash")
        if not stored_hash:
            return False
        return hash_password(password) == stored_hash

    def update_container_status(self, project_id: str, status: str, container_id: Optional[str]) -> None:
        key = self._project_key(project_id)
        if not self.redis.exists(key):
            return
        mapping: Dict[str, str] = {"status": status}
        if container_id:
            mapping["container_id"] = container_id
        self.redis.hset(key, mapping=mapping)

    def rotate_password(self, project_id: str) -> Optional[str]:
        key = self._project_key(project_id)
        if not self.redis.exists(key):
            return None
        password = generate_password()
        self.redis.hset(key, mapping={"password_hash": hash_password(password)})
        return password
