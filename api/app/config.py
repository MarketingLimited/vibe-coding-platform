from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(9000, env="API_PORT")
    api_key: str = Field("", env="API_KEY")
    master_api_key: Optional[str] = Field(None, env="MASTER_API_KEY")

    domain: str = Field("localhost", env="DOMAIN")

    # Data stores
    db_type: str = Field("sqlite", env="DB_TYPE")
    db_path: Path = Field(Path("/data/projects.db"), env="DB_PATH")
    db_password: Optional[str] = Field(None, env="DB_PASSWORD")

    # Secret storage
    github_secrets_path: Path = Field(Path("/data/github-secrets.bin"), env="GITHUB_SECRETS_PATH")
    github_secrets_key: Optional[str] = Field(None, env="GITHUB_SECRETS_KEY")

    redis_host: str = Field("redis", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_db: int = Field(0, env="REDIS_DB")

    # Limits and quotas
    max_projects_per_user: int = Field(10, env="MAX_PROJECTS_PER_USER")
    project_cpu_limit: float = Field(2.0, env="PROJECT_CPU_LIMIT")
    project_memory_limit: str = Field("4G", env="PROJECT_MEMORY_LIMIT")
    project_storage_limit: str = Field("10G", env="PROJECT_STORAGE_LIMIT")

    exec_timeout: int = Field(300, env="EXEC_TIMEOUT")
    max_output_size: int = Field(10 * 1024 * 1024, env="MAX_OUTPUT_SIZE")

    enable_rate_limit: bool = Field(True, env="ENABLE_RATE_LIMIT")
    rate_limit_per_minute: int = Field(100, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_window_seconds: int = Field(60, env="RATE_LIMIT_WINDOW_SECONDS")
    exec_rate_limit_per_minute: int = Field(60, env="EXEC_RATE_LIMIT_PER_MINUTE")
    project_create_rate_limit: int = Field(5, env="PROJECT_CREATE_RATE_LIMIT")
    project_info_rate_limit: int = Field(30, env="PROJECT_INFO_RATE_LIMIT")
    password_rotate_rate_limit: int = Field(4, env="PASSWORD_ROTATE_RATE_LIMIT")
    project_delete_rate_limit: int = Field(4, env="PROJECT_DELETE_RATE_LIMIT")

    projects_dir: Path = Field(Path("/projects"), env="PROJECTS_DIR")
    logs_dir: Path = Field(Path("/logs"), env="LOGS_DIR")

    # Internal service endpoints
    project_manager_host: str = Field("project-manager", env="PROJECT_MANAGER_HOST")
    project_manager_port: int = Field(9400, env="PROJECT_MANAGER_PORT")
    project_manager_scheme: str = Field("http", env="PROJECT_MANAGER_SCHEME")

    cleanup_interval: int = Field(86400, env="CLEANUP_INTERVAL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

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
