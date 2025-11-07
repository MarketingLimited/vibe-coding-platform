import logging
import os
import shutil
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import httpx
import redis

from .config import Settings

logger = logging.getLogger(__name__)


class CleanupService:
    def __init__(self, settings: Settings, redis_client: Optional[redis.Redis] = None):
        self.settings = settings
        self.redis = redis_client or redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )
        self._db_path = Path(settings.db_path)

    def _list_projects(self) -> Iterable[Path]:
        if not self.settings.projects_dir.exists():
            return []
        return [p for p in self.settings.projects_dir.iterdir() if p.is_dir()]

    def _project_status_from_db(self, project_id: str) -> Optional[str]:
        if not self._db_path.exists():
            return None
        try:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT status FROM projects WHERE project_id = ?", (project_id,)
                ).fetchone()
        except sqlite3.Error as exc:  # pragma: no cover - defensive logging only
            logger.warning(
                "Failed to read status from database", extra={"project_id": project_id, "error": str(exc)}
            )
            return None
        if not row:
            return None
        status_value = row[0]
        if isinstance(status_value, bytes):
            status_value = status_value.decode("utf-8", errors="ignore")
        return str(status_value)

    def _project_is_active(self, project_id: str) -> bool:
        data = self.redis.hgetall(f"project:{project_id}") or {}
        status = str(data.get("status", "")).lower()
        if status in {"active", "running", "starting"}:
            return True

        db_status = self._project_status_from_db(project_id)
        if db_status and db_status.lower() in {"active", "running", "starting"}:
            return True

        return False

    def cleanup_projects(self) -> List[str]:
        threshold = datetime.now(UTC) - timedelta(days=self.settings.max_project_age_days)
        removed: List[str] = []
        for project_path in self._list_projects():
            project_id = project_path.name
            if self._project_is_active(project_id):
                continue
            mtime = datetime.fromtimestamp(project_path.stat().st_mtime, UTC)
            if mtime > threshold:
                continue
            logger.info("Removing inactive project", extra={"project_id": project_id})
            shutil.rmtree(project_path, ignore_errors=True)
            self.redis.delete(f"project:{project_id}")
            removed.append(project_id)
        return removed

    def cleanup_logs(self) -> List[str]:
        if not self.settings.logs_dir.exists():
            return []
        max_bytes = self.settings.max_log_size_mb * 1024 * 1024
        truncated: List[str] = []
        for log_file in self.settings.logs_dir.rglob("*.log"):
            if log_file.stat().st_size > max_bytes:
                logger.info("Truncating oversized log", extra={"path": str(log_file)})
                with open(log_file, "w", encoding="utf-8") as fh:
                    fh.write("[truncated by cleanup service]\n")
                truncated.append(str(log_file))
        return truncated

    def ensure_permissions(self) -> None:
        for path in [self.settings.projects_dir, self.settings.logs_dir]:
            if path.exists():
                os.chmod(path, 0o750)

    def storage_usage_gb(self) -> float:
        total_bytes = 0
        for base_path in [self.settings.projects_dir, self.settings.logs_dir]:
            if not base_path.exists():
                continue
            for item in base_path.rglob("*"):
                if item.is_file():
                    total_bytes += item.stat().st_size
        return total_bytes / (1024**3)

    async def _send_notification(self, summary: Dict[str, object]) -> None:
        if not self.settings.notification_webhook:
            return
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(self.settings.notification_webhook, json=summary)
        except Exception as exc:  # pragma: no cover - network errors are logged only
            logger.warning("Failed to post cleanup notification", extra={"error": str(exc)})

    async def run_once(self) -> Dict[str, object]:
        logger.info("Running cleanup iteration")
        self.ensure_permissions()
        removed_projects = self.cleanup_projects()
        truncated_logs = self.cleanup_logs()
        usage_gb = round(self.storage_usage_gb(), 2)
        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "removed_projects": removed_projects,
            "truncated_logs": truncated_logs,
            "storage_usage_gb": usage_gb,
        }
        if usage_gb > self.settings.max_storage_usage_gb:
            summary["storage_warning"] = (
                f"Storage usage {usage_gb}GB exceeds configured limit {self.settings.max_storage_usage_gb}GB"
            )
            logger.warning(summary["storage_warning"])
        await self._send_notification(summary)
        return summary
