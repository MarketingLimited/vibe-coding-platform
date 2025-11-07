from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from ..config import Settings, get_settings
from .security import generate_project_id, generate_password, hash_password, verify_project_password


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
