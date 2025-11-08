from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

fastapi_module = types.ModuleType("fastapi")


class _APIRouter:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass

    def post(self, *args, **kwargs):  # noqa: ANN001, ANN003
        def decorator(func):
            return func

        return decorator

    def get(self, *args, **kwargs):  # noqa: ANN001, ANN003
        def decorator(func):
            return func

        return decorator

    def delete(self, *args, **kwargs):  # noqa: ANN001, ANN003
        def decorator(func):
            return func

        return decorator


def _depends(dependency=None):  # noqa: ANN001
    return dependency


def _header(default=None, alias=None):  # noqa: ANN001
    return default


class _HTTPException(Exception):
    def __init__(self, status_code: int, detail: str) -> None:  # noqa: D401
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


fastapi_module.APIRouter = _APIRouter
fastapi_module.Depends = _depends
fastapi_module.Header = _header
fastapi_module.HTTPException = _HTTPException
sys.modules["fastapi"] = fastapi_module

from api.app.config import Settings
from api.app.models.git import (
    GitCommandResponse,
    GitCommitRequest,
    GitLogRequest,
    GitResetRequest,
)
from api.app.routers.git import git_commit, git_log, git_reset


class DummyProjectService:
    def __init__(self, valid: bool = True) -> None:
        self.valid = valid
        self.settings = Settings()
        self.checked: list[tuple[str, str]] = []

    def verify_credentials(self, project_id: str, password: str) -> bool:
        self.checked.append((project_id, password))
        return self.valid


class DummyLimiter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def check(self, key: str, limit: int) -> None:
        self.calls.append((key, limit))


class DummyGitService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    async def commit(self, request: GitCommitRequest) -> GitCommandResponse:
        self.calls.append(("commit", request))
        return GitCommandResponse(returncode=0, stdout="done", stderr="", backup_path="/tmp/backup")

    async def log(self, request: GitLogRequest) -> GitCommandResponse:
        self.calls.append(("log", request))
        return GitCommandResponse(returncode=0, stdout="log", stderr="")

    async def reset(self, request: GitResetRequest) -> GitCommandResponse:
        self.calls.append(("reset", request))
        return GitCommandResponse(returncode=0, stdout="reset", stderr="", backup_path="/tmp/reset")


def test_git_commit_validates_and_forwards() -> None:
    project_service = DummyProjectService(valid=True)
    limiter = DummyLimiter()
    git_service = DummyGitService()

    request = GitCommitRequest(project_id="demo", password="secret", message="msg")
    response = asyncio.run(git_commit(request, project_service, git_service, limiter))

    assert response.backup_path == "/tmp/backup"
    assert project_service.checked == [("demo", "secret")]
    assert limiter.calls[0][0] == "git:demo"
    assert git_service.calls[0][0] == "commit"


def test_git_routes_require_valid_credentials() -> None:
    project_service = DummyProjectService(valid=False)
    limiter = DummyLimiter()
    git_service = DummyGitService()

    request = GitLogRequest(project_id="demo", password="bad")
    with pytest.raises(Exception) as exc:
        asyncio.run(git_log(request, project_service, git_service, limiter))
    assert getattr(exc.value, "status_code", None) == 401
    assert not limiter.calls


def test_git_reset_forwards_payload() -> None:
    project_service = DummyProjectService(valid=True)
    limiter = DummyLimiter()
    git_service = DummyGitService()

    request = GitResetRequest(project_id="demo", password="secret", commit="abcd1234")
    result = asyncio.run(git_reset(request, project_service, git_service, limiter))

    assert result.backup_path == "/tmp/reset"
    assert git_service.calls[-1][0] == "reset"
