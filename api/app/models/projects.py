from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9_-]+$")
    project_name: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9_-]+$")
    project_type: str = Field(..., pattern=r"^(python|nodejs|php|full)$")
    project_template: Optional[str] = Field(
        None, min_length=1, max_length=100, description="اختيار قالب جاهز"
    )
    github_api_key: str = Field(..., min_length=20, max_length=120)
    additional_secrets: Dict[str, str] = Field(default_factory=dict)
    database: Optional[str] = Field(None, pattern=r"^(postgres|mysql|sqlite|none)?$")
    redis: bool = False

    @field_validator("project_template", mode="before")
    def normalise_template(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        return value

    @field_validator("github_api_key")
    def validate_github_api_key(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("GitHub API key is required")
        return value.strip()

    @field_validator("additional_secrets", mode="before")
    def ensure_dict(cls, value):
        if value in (None, ""):
            return {}
        if isinstance(value, dict):
            return value
        raise ValueError("additional_secrets must be a mapping")

    @field_validator("database", mode="before")
    def normalise_database(cls, value: Optional[str]) -> Optional[str]:
        if value in ("", None, "none"):
            return None
        return value


class ProjectAuth(BaseModel):
    project_id: str
    password: str


class ProjectInfo(BaseModel):
    project_id: str
    username: str
    project_name: str
    project_type: str
    created_at: datetime
    status: str
    container_id: Optional[str] = None
    database: str
    redis: bool
    preview_url: Optional[str] = None


class ProjectDelete(ProjectAuth):
    pass
