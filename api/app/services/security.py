"""Security helper functions shared across services."""

from __future__ import annotations

import re
import secrets

import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with a salt.

    Args:
        password: Plain text password to hash

    Returns:
        Base64-encoded bcrypt hash

    Note:
        Uses 12 rounds for security while maintaining reasonable performance.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against a bcrypt hash using constant-time comparison.

    Args:
        password: Plain text password to verify
        hashed: Stored bcrypt hash

    Returns:
        True if password matches, False otherwise

    Note:
        Uses constant-time comparison to prevent timing attacks.
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except (ValueError, AttributeError):
        # Invalid hash format
        return False


def generate_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_project_id(username: str, project_name: str) -> str:
    """
    Generate a project ID from username and project name with validation.

    Args:
        username: User's username
        project_name: Name of the project

    Returns:
        Validated project ID

    Raises:
        ValueError: If username or project_name contain invalid characters
    """
    # Ensure inputs match expected pattern (lowercase alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-z0-9_-]+$', username):
        raise ValueError("Invalid username format. Must contain only lowercase letters, numbers, hyphens, and underscores.")
    if not re.match(r'^[a-z0-9_-]+$', project_name):
        raise ValueError("Invalid project_name format. Must contain only lowercase letters, numbers, hyphens, and underscores.")

    project_id = f"{username}-{project_name}"

    # Additional length check
    if len(project_id) > 100:
        raise ValueError("Project ID too long (max 100 characters)")

    return project_id


def verify_project_password(provided_password: str, stored_hash: str) -> bool:
    """
    Verify a project password against stored hash.

    Deprecated: Use verify_password() instead for consistent naming.
    """
    return verify_password(provided_password, stored_hash)
