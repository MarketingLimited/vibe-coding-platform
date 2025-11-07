from __future__ import annotations

import base64
import sys
import types
from pathlib import Path

import pytest

if "cryptography.fernet" not in sys.modules:  # pragma: no cover - testing stub
    fake_crypto = types.ModuleType("cryptography")
    fake_fernet = types.ModuleType("fernet")

    class _FakeInvalidToken(Exception):
        pass

    class _FakeFernet:
        def __init__(self, key: bytes) -> None:  # noqa: D401, ANN001
            self._key = key

        def encrypt(self, payload: bytes) -> bytes:
            return base64.urlsafe_b64encode(payload[::-1])

        def decrypt(self, token: bytes) -> bytes:
            try:
                return base64.urlsafe_b64decode(token)[::-1]
            except Exception as exc:  # pragma: no cover
                raise _FakeInvalidToken(str(exc)) from exc

    fake_fernet.Fernet = _FakeFernet
    fake_fernet.InvalidToken = _FakeInvalidToken
    fake_crypto.fernet = fake_fernet
    sys.modules["cryptography"] = fake_crypto
    sys.modules["cryptography.fernet"] = fake_fernet

if "fastapi" not in sys.modules:  # pragma: no cover - testing stub
    fastapi_module = types.ModuleType("fastapi")

    class _APIRouter:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
            pass

        def post(self, *args, **kwargs):  # noqa: ANN001
            def decorator(func):
                return func

            return decorator

        def get(self, *args, **kwargs):  # noqa: ANN001
            def decorator(func):
                return func

            return decorator

        def delete(self, *args, **kwargs):  # noqa: ANN001
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

    status_module = types.ModuleType("status")
    status_module.HTTP_400_BAD_REQUEST = 400
    status_module.HTTP_401_UNAUTHORIZED = 401
    status_module.HTTP_404_NOT_FOUND = 404
    status_module.HTTP_502_BAD_GATEWAY = 502

    fastapi_module.APIRouter = _APIRouter
    fastapi_module.Depends = _depends
    fastapi_module.Header = _header
    fastapi_module.HTTPException = _HTTPException
    fastapi_module.status = status_module
    sys.modules["fastapi"] = fastapi_module
    sys.modules["fastapi.status"] = status_module

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.app.config import Settings
from api.app.models.projects import ProjectCreate
from api.app.routers import projects as projects_router
from api.app.services.projects import ProjectService
from api.app.services.repository import ProjectRepository
from api.app.services.secrets import SecretStorage


@pytest.fixture
def anyio_backend():
    return "asyncio"


class DummyRedis:
    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, str]] = {}
        self._sets: dict[str, set[str]] = {}

    def hset(self, key: str, mapping: dict[str, str]) -> None:
        self._hashes.setdefault(key, {}).update(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    def delete(self, key: str) -> None:
        self._hashes.pop(key, None)

    def sadd(self, key: str, value: str) -> None:
        self._sets.setdefault(key, set()).add(value)

    def srem(self, key: str, value: str) -> None:
        self._sets.setdefault(key, set()).discard(value)

    def exists(self, key: str) -> int:
        return 1 if key in self._hashes else 0


class DummyProjectManager:
    def __init__(self) -> None:
        self.secrets_payload: dict[str, object] | None = None

    async def create_project(self, payload):  # noqa: ANN001
        return {
            "project_id": payload["project_id"],
            "container_id": "container-xyz",
            "status": "starting",
            "info": {"preview_url": "https://demo-preview.kazaaz.com"},
        }

    async def sync_project_secrets(self, project_id: str, payload):  # noqa: ANN001
        self.secrets_payload = {"project_id": project_id, **payload}
        return {"status": "ok"}

    async def delete_project(self, project_id: str) -> dict[str, str]:  # noqa: ARG002
        return {"status": "deleted"}


class DummyRateLimiter:
    def check(self, key: str, limit: int) -> None:  # noqa: ARG002
        return None


@pytest.mark.anyio()
async def test_create_project_returns_preview_url(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "projects.db",
        github_secrets_path=tmp_path / "secrets.db",
        github_secrets_key="preview-test-key",
    )

    repository = ProjectRepository(settings.db_path)
    secret_storage = SecretStorage(settings.github_secrets_path, settings.github_secrets_key)
    redis_client = DummyRedis()
    service = ProjectService(redis_client, settings, repository, secret_storage)
    manager = DummyProjectManager()
    limiter = DummyRateLimiter()

    payload = ProjectCreate(
        username="demo",
        project_name="sample",
        project_type="python",
        github_api_key="ghp_previewtoken01234567890123456789",
        additional_secrets={},
    )

    response = await projects_router.create_project(
        payload,
        project_service=service,
        project_manager=manager,
        rate_limiter=limiter,
    )

    assert response["preview_url"] == "https://demo-preview.kazaaz.com"

    project = service.get_project(response["project_id"])
    assert project is not None
    assert project.preview_url == "https://demo-preview.kazaaz.com"
