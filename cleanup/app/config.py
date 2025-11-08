from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    projects_dir: Path = Field(Path("/projects"))
    logs_dir: Path = Field(Path("/logs"))
    db_path: Path = Field(Path("/data/projects.db"))
    cleanup_interval: int = Field(86400)
    max_project_age_days: int = Field(30)
    max_log_size_mb: int = Field(100)

    redis_host: str = Field("redis")
    redis_port: int = Field(6379)
    redis_db: int = Field(0)

    notification_webhook: Optional[str] = Field(None)
    max_storage_usage_gb: int = Field(200)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
