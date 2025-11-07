from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class ProjectCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9_-]+$")
    project_name: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z0-9_-]+$")
    project_type: str = Field("python", pattern=r"^(python|nodejs|php|full)$")
    database: Optional[str] = Field(None, pattern=r"^(postgres|mysql|sqlite|none)?$")
    redis: bool = False

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


class ProjectDelete(ProjectAuth):
    pass
