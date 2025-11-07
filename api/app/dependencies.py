"""Dependency helpers shared across FastAPI routers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import AsyncGenerator, Generator

import docker
import httpx
import redis
from fastapi import Depends

from .config import Settings, get_settings
from .services.project_manager import ProjectManagerClient
from .services.rate_limiter import RateLimiter
from .services.repository import ProjectRepository

logger = logging.getLogger(__name__)

_project_repository: ProjectRepository | None = None


def get_project_repository(settings: Settings = Depends(get_settings)) -> ProjectRepository:
    """Return a singleton SQLite-backed repository for project metadata."""

    global _project_repository
    if _project_repository is None:
        db_path = Path(settings.db_path)
        logger.info("Initialising project repository", extra={"db_path": str(db_path)})
        _project_repository = ProjectRepository(db_path)
    return _project_repository


def get_redis_client(settings: Settings = Depends(get_settings)) -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
    )


def get_docker_client() -> Generator[docker.DockerClient, None, None]:
    client = docker.from_env()
    try:
        yield client
    finally:
        client.close()


async def get_http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient() as client:
        yield client


def get_project_manager_base_url(settings: Settings = Depends(get_settings)) -> str:
    return settings.project_manager_base_url


async def get_project_manager_client(
    base_url: str = Depends(get_project_manager_base_url),
    http_client=Depends(get_http_client),
) -> ProjectManagerClient:
    return ProjectManagerClient(base_url, http_client)


def get_rate_limiter(
    redis_client=Depends(get_redis_client),
    settings: Settings = Depends(get_settings),
) -> RateLimiter:
    return RateLimiter(
        redis_client,
        window_seconds=settings.rate_limit_window_seconds,
        enabled=settings.enable_rate_limit,
    )
