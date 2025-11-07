import logging
from typing import Dict

from ..config import Settings
from ..models.exec import ExecRequest, ExecResponse
from .project_manager import ProjectManagerClient

logger = logging.getLogger(__name__)


class ExecutionService:
    def __init__(self, settings: Settings, project_manager: ProjectManagerClient):
        self.settings = settings
        self.project_manager = project_manager

    async def execute(self, req: ExecRequest) -> ExecResponse:
        payload: Dict[str, object] = {
            "command": req.cmd,
            "cwd": req.cwd or "/workspace",
            "timeout": min(req.timeout or self.settings.exec_timeout, self.settings.exec_timeout),
            "max_output_size": self.settings.max_output_size,
        }
        logger.info("Forwarding exec request to project-manager", extra={"project_id": req.project_id})
        result = await self.project_manager.exec_in_project(req.project_id, payload)
        return ExecResponse(**result)
