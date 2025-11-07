import hashlib
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from ..config import Settings, get_settings


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_password(length: int = 16) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_project_id(username: str, project_name: str) -> str:
    return f"{username}-{project_name}"


def verify_master_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    master_key = settings.master_api_key
    if not master_key or x_api_key != master_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid master API key",
        )


def verify_project_password(
    provided_password: str,
    stored_hash: str,
) -> bool:
    return hash_password(provided_password) == stored_hash
