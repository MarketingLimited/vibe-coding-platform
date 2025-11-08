from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class ProjectLimits(BaseModel):
    cpu: float = Field(2.0, ge=0.1)
    memory: str = Field("4G")
    storage: str = Field("10G")


class ProjectRequest(BaseModel):
    project_id: str
    project_type: str = Field(..., pattern=r"^(python|nodejs|php|full)$")
    database: Optional[str] = None
    redis: bool = False
    username: str
    limits: ProjectLimits = Field(default_factory=ProjectLimits)


class ProjectSecrets(BaseModel):
    username: str
    github_api_key: str = Field(..., min_length=20)
    additional_secrets: Dict[str, str] = Field(default_factory=dict)

    @field_validator("github_api_key")
    def _trim_token(cls, value: str) -> str:
        token = value.strip()
        if not token:
            raise ValueError("github_api_key cannot be empty")
        return token


class ExecCommand(BaseModel):
    command: str
    cwd: str = "/workspace"
    timeout: Optional[int] = None
    max_output_size: int = 10 * 1024 * 1024


class GitCommandBase(BaseModel):
    cwd: str = "/workspace"
    timeout: Optional[int] = None
    max_output_size: int = Field(10 * 1024 * 1024, ge=1024)


class GitCommitCommand(GitCommandBase):
    message: str = Field(..., min_length=1)
    add_all: bool = True
    amend: bool = False


class GitLogCommand(GitCommandBase):
    limit: int = Field(10, ge=1, le=100)
    format: Optional[str] = None


class GitResetCommand(GitCommandBase):
    commit: str = Field(..., min_length=4)
    hard: bool = True


class ProjectStatus(BaseModel):
    project_id: str
    status: str
    container_id: Optional[str] = None
    info: Dict[str, str] = Field(default_factory=dict)
