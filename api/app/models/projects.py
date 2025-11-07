from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, Field, validator


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

    @validator("project_template", pre=True)
    def normalise_template(cls, value: Optional[str]) -> Optional[str]:
        if value in (None, ""):
            return None
        return value

    @validator("github_api_key")
    def validate_github_api_key(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("GitHub API key is required")
        return value.strip()

    @validator("additional_secrets", pre=True)
    def ensure_dict(cls, value):
        if value in (None, ""):
            return {}
        if isinstance(value, dict):
            return value
        raise ValueError("additional_secrets must be a mapping")

    @validator("database", pre=True)
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
    container_id: Optional[str]
    database: str
    redis: bool
    preview_url: Optional[str]


class ProjectDelete(ProjectAuth):
    pass
