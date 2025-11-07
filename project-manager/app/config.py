from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    projects_dir: Path = Field(Path("/projects"), env="PROJECTS_DIR")
    logs_dir: Path = Field(Path("/logs"), env="LOGS_DIR")
    templates_dir: Path = Field(Path("/templates"), env="TEMPLATES_DIR")

    docker_host: Optional[str] = Field(None, env="DOCKER_HOST")
    network_name: str = Field("vibe-network", env="NETWORK_NAME")
    proxy_network_name: Optional[str] = Field("vibe-proxy", env="PROXY_NETWORK_NAME")
    image_prefix: str = Field("vibe-project", env="IMAGE_PREFIX")

    preview_domain: Optional[str] = Field("kazaaz.com", env="PREVIEW_DOMAIN")
    preview_scheme: str = Field("https", env="PREVIEW_SCHEME")
    preview_internal_port: int = Field(4173, env="PREVIEW_INTERNAL_PORT")
    preview_entrypoints: str = Field("websecure", env="PREVIEW_ENTRYPOINTS")
    preview_service_scheme: str = Field("http", env="PREVIEW_SERVICE_SCHEME")

    default_cpu_limit: float = Field(2.0, env="DEFAULT_CPU_LIMIT")
    default_memory_limit: str = Field("4G", env="DEFAULT_MEMORY_LIMIT")
    default_storage_limit: str = Field("10G", env="DEFAULT_STORAGE_LIMIT")

    auto_cleanup_days: int = Field(30, env="AUTO_CLEANUP_DAYS")
    cleanup_inactive_projects: bool = Field(True, env="CLEANUP_INACTIVE_PROJECTS")

    redis_host: str = Field("redis", env="REDIS_HOST")
    redis_port: int = Field(6379, env="REDIS_PORT")
    redis_db: int = Field(0, env="REDIS_DB")

    health_poll_interval: int = Field(60, env="HEALTH_POLL_INTERVAL")
    gh_config_dir: Path = Field(Path("/root/.config/gh"), env="GH_CONFIG_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
