"""Traefik integration helpers for project preview routing."""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

from ..config import Settings
from ..loggers.domain_events import DomainEventsLogger

logger = logging.getLogger(__name__)


class RouterRegistry:
    """Manage Traefik labels and network attachments for project containers."""

    _slug_regex = re.compile(r"[^a-z0-9-]")

    def __init__(self, settings: Settings, docker_client, docker_errors) -> None:
        self.settings = settings
        self.docker_client = docker_client
        self.docker_errors = docker_errors
        self.domain_events = DomainEventsLogger(settings)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _enabled(self) -> bool:
        return bool(self.settings.preview_domain and self.settings.proxy_network_name)

    def _slugify(self, project_id: str) -> str:
        slug = project_id.lower().replace("_", "-")
        slug = self._slug_regex.sub("-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")
        return slug or "project"

    def _router_name(self, project_id: str) -> str:
        return f"{self._slugify(project_id)}-router"

    def _service_name(self, project_id: str) -> str:
        return f"{self._slugify(project_id)}-service"

    def project_hostname(self, project_id: str) -> Optional[str]:
        if not self._enabled():
            return None
        return f"{self._slugify(project_id)}.{self.settings.preview_domain}"

    def project_url(self, project_id: str) -> Optional[str]:
        host = self.project_hostname(project_id)
        if not host:
            return None
        scheme = self.settings.preview_scheme or "https"
        return f"{scheme}://{host}"

    def ensure_network(self) -> None:
        if not self._enabled():
            return
        try:
            self.docker_client.networks.get(self.settings.proxy_network_name)
        except self.docker_errors.NotFound:  # type: ignore[attr-defined]
            logger.info("Creating proxy network %s", self.settings.proxy_network_name)
            self.docker_client.networks.create(self.settings.proxy_network_name, driver="bridge")

    # ------------------------------------------------------------------
    # label management
    # ------------------------------------------------------------------
    def labels_for(self, project_id: str) -> Dict[str, str]:
        if not self._enabled():
            return {}

        router = self._router_name(project_id)
        service = self._service_name(project_id)
        hostname = self.project_hostname(project_id)
        if not hostname:
            return {}

        labels = {
            "traefik.enable": "true",
            "traefik.docker.network": self.settings.proxy_network_name or "",
            f"traefik.http.routers.{router}.rule": f"Host(`{hostname}`)",
            f"traefik.http.routers.{router}.entrypoints": self.settings.preview_entrypoints,
            f"traefik.http.routers.{router}.tls": "true",
            f"traefik.http.routers.{router}.service": service,
            f"traefik.http.services.{service}.loadbalancer.server.port": str(self.settings.preview_internal_port),
            f"traefik.http.services.{service}.loadbalancer.server.scheme": self.settings.preview_service_scheme,
        }

        return {key: value for key, value in labels.items() if value}

    # ------------------------------------------------------------------
    # network registration
    # ------------------------------------------------------------------
    def attach(self, container, project_id: str) -> None:
        if not self._enabled():
            return
        try:
            network = self.docker_client.networks.get(self.settings.proxy_network_name)
        except self.docker_errors.NotFound:  # type: ignore[attr-defined]
            logger.warning("Proxy network %s missing; recreating", self.settings.proxy_network_name)
            network = self.docker_client.networks.create(self.settings.proxy_network_name, driver="bridge")

        aliases = [self._slugify(project_id)]
        hostname = self.project_hostname(project_id)
        if hostname:
            aliases.append(hostname.split(".")[0])

        try:
            network.connect(container, aliases=list(dict.fromkeys(aliases)))
            self.domain_events.record_success(project_id, hostname, getattr(network, "name", None))
        except self.docker_errors.APIError as exc:  # type: ignore[attr-defined]
            if "already exists" in str(exc).lower():
                logger.debug("Container already attached to proxy network", extra={"project_id": project_id})
                self.domain_events.record_success(project_id, hostname, getattr(network, "name", None))
                return
            error_message = str(exc)
            logger.warning(
                "Failed to attach container to proxy network",
                extra={"project_id": project_id, "error": error_message},
            )
            self.domain_events.record_failure(project_id, hostname, error_message)

    def detach(self, container) -> None:
        if not self._enabled():
            return
        try:
            network = self.docker_client.networks.get(self.settings.proxy_network_name)
        except self.docker_errors.NotFound:  # type: ignore[attr-defined]
            return
        try:
            network.disconnect(container)
        except self.docker_errors.APIError:  # type: ignore[attr-defined]
            logger.debug("Container already detached from proxy network", extra={"container_id": getattr(container, "id", "?")})
