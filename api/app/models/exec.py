from typing import Optional

from pydantic import BaseModel, Field


class ExecRequest(BaseModel):
    project_id: str
    password: str
    cmd: str = Field(..., min_length=1, max_length=10000)
    cwd: Optional[str] = Field("/workspace", max_length=500)
    timeout: Optional[int] = None


class ExecResponse(BaseModel):
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
