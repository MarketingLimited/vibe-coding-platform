from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    projects_dir: Path = Field(Path("/projects"))
    logs_dir: Path = Field(Path("/logs"))
    templates_dir: Path = Field(Path("/templates"))
    backups_dir: Path = Field(Path("/backups"))

    docker_host: Optional[str] = Field(None)
    network_name: str = Field("vibe-network")
    proxy_network_name: Optional[str] = Field("vibe-proxy")
    image_prefix: str = Field("vibe-project")

    preview_domain: Optional[str] = Field("kazaaz.com")
    preview_scheme: str = Field("https")
    preview_internal_port: int = Field(4173)
    preview_entrypoints: str = Field("websecure")
    preview_service_scheme: str = Field("http")

    default_cpu_limit: float = Field(2.0)
    default_memory_limit: str = Field("4G")
    default_storage_limit: str = Field("10G")

    auto_cleanup_days: int = Field(30)
    cleanup_inactive_projects: bool = Field(True)

    redis_host: str = Field("redis")
    redis_port: int = Field(6379)
    redis_db: int = Field(0)

    health_poll_interval: int = Field(60)
    gh_config_dir: Path = Field(Path("/root/.config/gh"))

    domain_events_webhook: Optional[str] = Field(None)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }
