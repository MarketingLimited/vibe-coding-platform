"""Custom Prometheus metrics for the public API."""

from __future__ import annotations

from typing import Optional

from prometheus_client import Counter, Histogram

ACTIVATION_ATTEMPTS = Counter(
    "activation_attempts_total",
    "Count of activation attempts segmented by status and reason.",
    labelnames=("status", "reason"),
)

ACTIVATION_SETUP_DURATION = Histogram(
    "activation_setup_duration_seconds",
    "Observed duration of activation setup workflows in seconds.",
    buckets=(1, 2, 5, 10, 30, 60, 120, 300, 600),
)


def _normalise_reason(reason: Optional[str]) -> str:
    value = (reason or "").strip().lower()
    return value or "unspecified"


def record_activation_success(reason: Optional[str] = None) -> None:
    """Record a successful activation attempt."""

    ACTIVATION_ATTEMPTS.labels("success", _normalise_reason(reason)).inc()


def record_activation_failure(reason: Optional[str] = None) -> None:
    """Record a failed activation attempt."""

    ACTIVATION_ATTEMPTS.labels("failure", _normalise_reason(reason)).inc()


def observe_activation_duration(seconds: float) -> None:
    """Track how long activation setup took in seconds."""

    if seconds < 0:
        return
    ACTIVATION_SETUP_DURATION.observe(seconds)
