"""Domain event logging and webhook notifications for project previews."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from ..config import Settings


@dataclass(slots=True)
class DomainBindingEvent:
    """Structured payload describing a domain binding attempt."""

    project_id: str
    hostname: Optional[str]
    status: str
    message: str
    network: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "project_id": self.project_id,
            "hostname": self.hostname,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.network:
            payload["network"] = self.network
        if self.error:
            payload["error"] = self.error
        return payload


class DomainEventsLogger:
    """Log domain binding outcomes and optionally notify a webhook."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._webhook_url = getattr(settings, "domain_events_webhook", None)
        self._logger = logging.getLogger("project_manager.domain_events")

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def record_success(self, project_id: str, hostname: Optional[str], network: Optional[str]) -> None:
        event = DomainBindingEvent(
            project_id=project_id,
            hostname=hostname,
            status="success",
            message="Domain binding completed",
            network=network,
        )
        self._logger.info("Domain binding success", extra={"domain_event": event.as_dict()})

    def record_failure(self, project_id: str, hostname: Optional[str], error: str) -> None:
        event = DomainBindingEvent(
            project_id=project_id,
            hostname=hostname,
            status="failure",
            message="Domain binding failed",
            error=error,
        )
        payload = event.as_dict()
        self._logger.error("Domain binding failure", extra={"domain_event": payload})
        self._notify_webhook(payload)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _notify_webhook(self, payload: Dict[str, Any]) -> None:
        if not self._webhook_url:
            return
        try:
            response = httpx.post(self._webhook_url, json=payload, timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network side effects
            self._logger.warning(
                "Failed to notify domain binding webhook", extra={"error": str(exc), "payload": json.dumps(payload)}
            )

