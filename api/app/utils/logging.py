import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any, Dict

from fastapi import Request

_request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Attach the current request id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id_ctx_var.get()
        return True


def configure_logging() -> None:
    """Configure structured logging for the service."""

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(request_id)s | %(name)s | %(message)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove default handlers installed by uvicorn
    for existing in list(root_logger.handlers):
        root_logger.removeHandler(existing)

    root_logger.addHandler(handler)


async def set_request_id(request: Request, call_next: Any) -> Any:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    token = _request_id_ctx_var.set(request_id)
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
    finally:
        _request_id_ctx_var.reset(token)


def log_extra(project_id: str | None = None, **kwargs: Dict[str, Any]) -> Dict[str, Any]:
    extra = {"project_id": project_id, **kwargs}
    return extra
