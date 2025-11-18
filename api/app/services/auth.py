import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from ..config import Settings, get_settings


def verify_master_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    """
    Verify the master API key using constant-time comparison.

    Args:
        x_api_key: API key from X-API-Key header
        settings: Application settings

    Raises:
        HTTPException: If the API key is invalid or missing

    Note:
        Uses secrets.compare_digest to prevent timing attacks.
    """
    master_key = settings.master_api_key
    if not master_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Master API key not configured",
        )

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(x_api_key, master_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid master API key",
        )
