"""Security helper functions shared across services."""

from __future__ import annotations

import hashlib
import secrets


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def generate_password(length: int = 16) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_project_id(username: str, project_name: str) -> str:
    return f"{username}-{project_name}"


def verify_project_password(provided_password: str, stored_hash: str) -> bool:
    return hash_password(provided_password) == stored_hash
