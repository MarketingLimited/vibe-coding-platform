import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ProjectManagerClient:
    """HTTP client wrapper for the project-manager service."""

    # Default timeout for most operations (30 seconds)
    DEFAULT_TIMEOUT = 30.0
    # Longer timeout for container creation (2 minutes)
    CREATE_TIMEOUT = 120.0

    def __init__(self, base_url: str, http_client: httpx.AsyncClient):
        self._base_url = base_url.rstrip("/")
        self._client = http_client

    async def create_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project container."""
        response = await self._client.post(
            f"{self._base_url}/internal/projects",
            json=payload,
            timeout=self.CREATE_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Project-manager created container", extra={"project_id": payload.get("project_id")})
        return data

    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a project container."""
        response = await self._client.delete(
            f"{self._base_url}/internal/projects/{project_id}",
            timeout=self.DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    async def health(self) -> Dict[str, Any]:
        response = await self._client.get(f"{self._base_url}/health", timeout=5)
        response.raise_for_status()
        return response.json()

    async def get_project_status(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a project."""
        response = await self._client.get(
            f"{self._base_url}/internal/projects/{project_id}",
            timeout=self.DEFAULT_TIMEOUT
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    async def exec_in_project(self, project_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command in a project container."""
        # Use command timeout if provided, otherwise use default + buffer
        cmd_timeout = command.get("timeout")
        request_timeout = (cmd_timeout + 30.0) if cmd_timeout else self.DEFAULT_TIMEOUT

        response = await self._client.post(
            f"{self._base_url}/internal/projects/{project_id}/exec",
            json=command,
            timeout=request_timeout,
        )
        response.raise_for_status()
        return response.json()

    async def git_commit(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a git commit in the project."""
        timeout = payload.get("timeout", self.DEFAULT_TIMEOUT)
        response = await self._client.post(
            f"{self._base_url}/internal/projects/{project_id}/git/commit",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    async def git_log(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Get git log from the project."""
        timeout = payload.get("timeout", self.DEFAULT_TIMEOUT)
        response = await self._client.post(
            f"{self._base_url}/internal/projects/{project_id}/git/log",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    async def git_reset(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Reset git history in the project."""
        timeout = payload.get("timeout", self.DEFAULT_TIMEOUT)
        response = await self._client.post(
            f"{self._base_url}/internal/projects/{project_id}/git/reset",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    async def sync_project_secrets(self, project_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Propagate GitHub credentials to the project-manager service."""
        response = await self._client.post(
            f"{self._base_url}/internal/projects/{project_id}/secrets",
            json=payload,
            timeout=self.DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Project-manager synced secrets", extra={"project_id": project_id})
        return data
