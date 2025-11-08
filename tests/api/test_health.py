from __future__ import annotations

import sys
from pathlib import Path

import asyncio
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.app import dependencies
from api.app.config import Settings
from api.app.routers.health import health


class DummyRequestsUnixSocket:
    def __init__(self) -> None:
        self.called = 0

    def monkeypatch(self) -> None:
        self.called += 1


class DummyDockerClient:
    def __init__(self) -> None:
        self.closed = False
        self.pings = 0

    def ping(self) -> None:
        self.pings += 1

    def close(self) -> None:
        self.closed = True


class DummyRedisClient:
    def __init__(self) -> None:
        self.pings = 0

    def ping(self) -> None:
        self.pings += 1


def test_health_endpoint_initialises_docker_unixsocket(monkeypatch) -> None:
    dummy_requests = DummyRequestsUnixSocket()
    dummy_docker = DummyDockerClient()
    dummy_redis = DummyRedisClient()

    monkeypatch.setattr(dependencies, "requests_unixsocket", dummy_requests, raising=False)
    monkeypatch.setattr(dependencies, "_docker_requests_monkeypatched", False, raising=False)
    monkeypatch.setattr(dependencies.docker, "from_env", lambda: dummy_docker)

    docker_dependency = dependencies.get_docker_client()
    docker_client = next(docker_dependency)

    async def invoke() -> dict[str, object]:
        return await health(Settings(), dummy_redis, docker_client)

    try:
        response = asyncio.run(invoke())
    finally:
        docker_dependency.close()

    assert response["status"] == "healthy"
    assert dummy_requests.called == 1
    assert dummy_docker.closed is True
    assert dummy_docker.pings == 1
    assert dummy_redis.pings == 1
