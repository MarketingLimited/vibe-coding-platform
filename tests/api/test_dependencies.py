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

import api.app.dependencies as dependencies
from api.app.config import Settings
from api.app.services.secrets import SecretStorage


@pytest.fixture(autouse=True)
def reset_secret_storage():
    dependencies._secret_storage = None  # type: ignore[attr-defined]
    yield
    dependencies._secret_storage = None  # type: ignore[attr-defined]


def test_get_secret_storage_initialises_encrypted_store(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "projects.db",
        github_secrets_path=tmp_path / "github-secrets.bin",
        github_secrets_key="unit-test-github-key",
    )

    storage = dependencies.get_secret_storage(settings)
    assert isinstance(storage, SecretStorage)
    assert settings.github_secrets_path.exists()

    again = dependencies.get_secret_storage(settings)
    assert again is storage


def test_get_secret_storage_requires_encryption_key(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "projects.db",
        github_secrets_path=tmp_path / "github-secrets.bin",
        github_secrets_key=None,
    )

    with pytest.raises(RuntimeError):
        dependencies.get_secret_storage(settings)
