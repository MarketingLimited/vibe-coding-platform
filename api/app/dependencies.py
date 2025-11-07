import logging
from typing import AsyncGenerator, Generator

import docker
import httpx
import redis
from fastapi import Depends

from .config import Settings, get_settings

logger = logging.getLogger(__name__)


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
