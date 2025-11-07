from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    projects_dir: Path = Field(Path("/projects"), env="PROJECTS_DIR")
    logs_dir: Path = Field(Path("/logs"), env="LOGS_DIR")
    templates_dir: Path = Field(Path("/templates"), env="TEMPLATES_DIR")

    docker_host: Optional[str] = Field(None, env="DOCKER_HOST")
    network_name: str = Field("vibe-network", env="NETWORK_NAME")
    image_prefix: str = Field("vibe-project", env="IMAGE_PREFIX")

    default_cpu_limit: float = Field(2.0, env="DEFAULT_CPU_LIMIT")
    default_memory_limit: str = Field("4G", env="DEFAULT_MEMORY_LIMIT")
    default_storage_limit: str = Field("10G", env="DEFAULT_STORAGE_LIMIT")

    auto_cleanup_days: int = Field(30, env="AUTO_CLEANUP_DAYS")
    cleanup_inactive_projects: bool = Field(True, env="CLEANUP_INACTIVE_PROJECTS")

    redis_host: str = Field("redis", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_db: int = Field(0, env="REDIS_DB")

    health_poll_interval: int = Field(60, env="HEALTH_POLL_INTERVAL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
