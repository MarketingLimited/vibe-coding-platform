import os
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ExecRequest(BaseModel):
    project_id: str
    password: str
    cmd: str = Field(..., min_length=1, max_length=10000)
    cwd: Optional[str] = Field("/workspace", max_length=500)
    timeout: Optional[int] = None

    @field_validator("cwd")
    @classmethod
    def validate_cwd(cls, value: Optional[str]) -> str:
        """
        Validate working directory to prevent path traversal attacks.

        Args:
            value: Working directory path

        Returns:
            Validated and normalized path

        Raises:
            ValueError: If path contains traversal or is outside /workspace
        """
        if not value:
            return "/workspace"

        # Normalize the path
        normalized = os.path.normpath(value)

        # Check for path traversal attempts
        if ".." in value:
            raise ValueError("Working directory cannot contain path traversal (..)")

        # Ensure path starts with /workspace
        if not normalized.startswith("/workspace"):
            raise ValueError("Working directory must be within /workspace")

        return normalized

    @field_validator("cmd")
    @classmethod
    def validate_cmd(cls, value: str) -> str:
        """
        Validate command to prevent extremely dangerous operations.

        Note: This is not a complete security solution, but provides basic protection.
        """
        # List of extremely dangerous patterns
        dangerous_patterns = [
            r'rm\s+-rf\s+/',  # Recursive delete from root
            r'>\s*/dev/sd[a-z]',  # Direct disk write
            r'dd\s+if=',  # Disk operations
            r'mkfs\.',  # Format filesystem
            r':[(][)]',  # Fork bomb pattern
        ]

        cmd_lower = value.lower()

        # Check for dangerous patterns
        for pattern in dangerous_patterns:
            if re.search(pattern, cmd_lower):
                raise ValueError(f"Command contains forbidden pattern: {pattern}")

        # Check for extremely dangerous commands
        dangerous_commands = ['format', 'mkfs']
        first_word = value.split()[0] if value.split() else ""
        if first_word in dangerous_commands:
            raise ValueError(f"Command contains forbidden operation: {first_word}")

        return value


class ExecResponse(BaseModel):
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
