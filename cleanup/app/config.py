from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    projects_dir: Path = Field(Path("/projects"), env="PROJECTS_DIR")
    logs_dir: Path = Field(Path("/logs"), env="LOGS_DIR")
    cleanup_interval: int = Field(86400, env="CLEANUP_INTERVAL")
    max_project_age_days: int = Field(30, env="MAX_PROJECT_AGE_DAYS")
    max_log_size_mb: int = Field(100, env="MAX_LOG_SIZE_MB")

    redis_host: str = Field("redis", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_db: int = Field(0, env="REDIS_DB")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
