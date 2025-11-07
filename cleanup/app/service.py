import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import redis

from .config import Settings

logger = logging.getLogger(__name__)


class CleanupService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )

    def _list_projects(self) -> Iterable[Path]:
        if not self.settings.projects_dir.exists():
            return []
        return [p for p in self.settings.projects_dir.iterdir() if p.is_dir()]

    def _project_is_active(self, project_id: str) -> bool:
        data = self.redis.hgetall(f"project:{project_id}")
        if not data:
            return False
        return data.get("status", "inactive") == "active"

    def cleanup_projects(self) -> None:
        threshold = datetime.utcnow() - timedelta(days=self.settings.max_project_age_days)
        for project_path in self._list_projects():
            project_id = project_path.name
            if self._project_is_active(project_id):
                continue
            mtime = datetime.utcfromtimestamp(project_path.stat().st_mtime)
            if mtime > threshold:
                continue
            logger.info("Removing inactive project", extra={"project_id": project_id})
            shutil.rmtree(project_path, ignore_errors=True)
            self.redis.delete(f"project:{project_id}")

    def cleanup_logs(self) -> None:
        if not self.settings.logs_dir.exists():
            return
        max_bytes = self.settings.max_log_size_mb * 1024 * 1024
        for log_file in self.settings.logs_dir.rglob("*.log"):
            if log_file.stat().st_size > max_bytes:
                logger.info("Truncating oversized log", extra={"path": str(log_file)})
                with open(log_file, "w", encoding="utf-8") as fh:
                    fh.write("[truncated by cleanup service]\n")

    def ensure_permissions(self) -> None:
        for path in [self.settings.projects_dir, self.settings.logs_dir]:
            if path.exists():
                os.chmod(path, 0o750)

    def run_once(self) -> None:
        logger.info("Running cleanup iteration")
        self.ensure_permissions()
        self.cleanup_projects()
        self.cleanup_logs()
