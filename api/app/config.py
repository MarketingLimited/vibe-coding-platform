from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    api_host: str = Field("0.0.0.0")
    api_port: int = Field(9000)
    api_key: str = Field("")
    master_api_key: Optional[str] = Field(None)

    domain: str = Field("localhost")

    # Data stores
    db_type: str = Field("sqlite")
    db_path: Path = Field(Path("/data/projects.db"))
    db_password: Optional[str] = Field(None)

    # Secret storage
    github_secrets_path: Path = Field(Path("/data/github-secrets.bin"))
    github_secrets_key: Optional[str] = Field(None)

    redis_host: str = Field("redis")
    redis_port: int = Field(6379)
    redis_db: int = Field(0)

    # Limits and quotas
    max_projects_per_user: int = Field(10)
    project_cpu_limit: float = Field(2.0)
    project_memory_limit: str = Field("4G")
    project_storage_limit: str = Field("10G")

    exec_timeout: int = Field(300)
    max_output_size: int = Field(10 * 1024 * 1024)

    enable_rate_limit: bool = Field(True)
    rate_limit_per_minute: int = Field(100)
    rate_limit_window_seconds: int = Field(60)
    exec_rate_limit_per_minute: int = Field(60)
    project_create_rate_limit: int = Field(5)
    project_info_rate_limit: int = Field(30)
    password_rotate_rate_limit: int = Field(4)
    project_delete_rate_limit: int = Field(4)

    projects_dir: Path = Field(Path("/projects"))
    logs_dir: Path = Field(Path("/logs"))

    # Internal service endpoints
    project_manager_host: str = Field("project-manager")
    project_manager_port: int = Field(9400)
    project_manager_scheme: str = Field("http")

    cleanup_interval: int = Field(86400)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @property
    def project_manager_base_url(self) -> str:
        return f"{self.project_manager_scheme}://{self.project_manager_host}:{self.project_manager_port}"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""

    settings = Settings()

    if not settings.master_api_key:
        # Fallback to API key when a dedicated master key isn't provided
        settings.master_api_key = settings.api_key

    return settings
