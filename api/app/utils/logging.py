"""Logging helpers shared across the API service."""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Request

_request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")
_audit_logger: Optional[logging.Logger] = None


class RequestIdFilter(logging.Filter):
    """Attach the current request id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        record.request_id = _request_id_ctx_var.get()
        return True


def configure_logging(log_directory: Optional[Path] = None) -> None:
    """Configure structured logging for console and optional file outputs."""

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    for existing in list(root_logger.handlers):
        root_logger.removeHandler(existing)

    root_logger.addHandler(handler)

    if log_directory:
        log_directory.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_directory / "api.log")
        file_handler.setFormatter(formatter)
        file_handler.addFilter(RequestIdFilter())
        root_logger.addHandler(file_handler)


def configure_audit_logging(log_directory: Path) -> logging.Logger:
    """Initialise and return a dedicated audit logger writing to ``audit.log``."""

    global _audit_logger
    if _audit_logger:
        return _audit_logger

    log_directory.mkdir(parents=True, exist_ok=True)
    audit_logger = logging.getLogger("vibe.audit")
    audit_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(request_id)s | %(message)s"
    )
    handler = logging.FileHandler(log_directory / "audit.log")
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    audit_logger.addHandler(handler)

    _audit_logger = audit_logger
    return audit_logger


async def set_request_id(request: Request, call_next: Any) -> Any:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    token = _request_id_ctx_var.set(request_id)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
    finally:
        _request_id_ctx_var.reset(token)


def get_audit_logger() -> logging.Logger:
    if not _audit_logger:
        raise RuntimeError("Audit logger not configured")
    return _audit_logger


def log_extra(project_id: str | None = None, **kwargs: Dict[str, Any]) -> Dict[str, Any]:
    return {"project_id": project_id, **kwargs}


__all__ = [
    "configure_logging",
    "configure_audit_logging",
    "set_request_id",
    "get_audit_logger",
    "log_extra",
]
