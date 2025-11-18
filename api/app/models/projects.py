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
    @classmethod
    def validate_github_api_key(cls, value: str) -> str:
        """Validate GitHub API key format and length."""
        if not value or not value.strip():
            raise ValueError("GitHub API key is required")

        value = value.strip()

        # GitHub tokens have specific prefixes (not enforced strictly, just logged)
        # Note: Some tokens may not follow this pattern, so we don't fail validation
        valid_prefixes = ["ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_"]
        if not any(value.startswith(prefix) for prefix in valid_prefixes):
            # Just a warning, don't fail validation as format may vary
            pass

        return value

    @field_validator("additional_secrets", mode="before")
    @classmethod
    def ensure_dict(cls, value):
        """Ensure additional_secrets is a valid dictionary."""
        if value in (None, ""):
            return {}
        if isinstance(value, dict):
            return value
        raise ValueError("additional_secrets must be a mapping")

    @field_validator("additional_secrets")
    @classmethod
    def validate_additional_secrets(cls, value: Dict[str, str]) -> Dict[str, str]:
        """
        Validate additional secrets for security and format.

        Args:
            value: Dictionary of additional secrets

        Returns:
            Validated secrets dictionary

        Raises:
            ValueError: If secrets are invalid
        """
        if not isinstance(value, dict):
            raise ValueError("additional_secrets must be a dictionary")

        # Validate secret keys
        import re
        for key in value.keys():
            if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
                raise ValueError(
                    f"Invalid secret key format: {key}. "
                    "Must be uppercase with underscores (e.g., MY_SECRET_KEY)"
                )

            if len(key) > 64:
                raise ValueError(f"Secret key too long: {key} (max 64 characters)")

        # Validate secret values
        for key, val in value.items():
            if not isinstance(val, str):
                raise ValueError(f"Secret value for {key} must be a string")

            if len(val) > 10000:
                raise ValueError(f"Secret value for {key} is too long (max 10000 characters)")

        if len(value) > 50:
            raise ValueError("Too many additional secrets (max 50)")

        return value

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
