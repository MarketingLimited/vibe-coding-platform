import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ProjectManagerClient:
    """HTTP client wrapper for the project-manager service."""

    def __init__(self, base_url: str, http_client: httpx.AsyncClient):
        self._base_url = base_url.rstrip("/")
        self._client = http_client

    async def create_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(f"{self._base_url}/internal/projects", json=payload)
        response.raise_for_status()
        data = response.json()
        logger.info("Project-manager created container", extra={"project_id": payload.get("project_id")})
        return data

    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        response = await self._client.delete(f"{self._base_url}/internal/projects/{project_id}")
        response.raise_for_status()
        return response.json()

    async def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        response = await self._client.get(f"{self._base_url}/internal/projects/{project_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def exec_in_project(self, project_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/internal/projects/{project_id}/exec",
            json=command,
            timeout=command.get("timeout", None),
        )
        response.raise_for_status()
        return response.json()
