from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProjectLimits(BaseModel):
    cpu: float = Field(2.0, ge=0.1)
    memory: str = Field("4G")
    storage: str = Field("10G")


class ProjectRequest(BaseModel):
    project_id: str
    project_type: str = Field(..., regex=r"^(python|nodejs|php|full)$")
    database: Optional[str]
    redis: bool = False
    username: str
    limits: ProjectLimits = Field(default_factory=ProjectLimits)


class ExecCommand(BaseModel):
    command: str
    cwd: str = "/workspace"
    timeout: Optional[int]
    max_output_size: int = 10 * 1024 * 1024


class ProjectStatus(BaseModel):
    project_id: str
    status: str
    container_id: Optional[str]
    info: Dict[str, str] = Field(default_factory=dict)
