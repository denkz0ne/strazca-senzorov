"""Health state transitions separate from cause diagnosis."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from .profile import _parse


def evaluate_health(
    *,
    now: datetime,
    startup_at: datetime,
    last_reported: datetime | str | None,
    profile: dict[str, Any],
    native_available: bool | None = None,
    source_available: bool | None = None,
    previous_state: str = "unknown",
    recovery_started_at: datetime | str | None = None,
    startup_grace: timedelta = timedelta(minutes=5),
    recovery_stability: timedelta = timedelta(minutes=2),
) -> dict[str, Any]:
    """Return a conservative state and reason without assigning outage cause."""
    now = _utc(now)
    startup_at = _utc(startup_at)
    if native_available is False:
        return {
            "state": "offline",
            "reason": "native_availability_unavailable",
            "threshold_seconds": 0,
        }
    if native_available is True:
        return _recovery_state(
            now, previous_state, recovery_started_at, recovery_stability
        )
    if source_available is False:
        return {
            "state": "initializing" if now - startup_at < startup_grace else "offline",
            "reason": "startup_grace"
            if now - startup_at < startup_grace
            else "source_entities_unavailable",
            "threshold_seconds": None,
        }
    if now - startup_at < startup_grace and last_reported is None:
        return {
            "state": "initializing",
            "reason": "startup_grace",
            "threshold_seconds": None,
        }
    confidence = float(profile.get("pattern_confidence") or 0)
    p90 = profile.get("p90_interval_seconds")
    p95 = profile.get("p95_interval_seconds")
    if (
        confidence < 0.4
        or not isinstance(p90, (int, float))
        or not isinstance(p95, (int, float))
    ):
        if source_available is True:
            result = _recovery_state(
                now, previous_state, recovery_started_at, recovery_stability
            )
            if result["state"] == "healthy":
                result["reason"] = "source_available_report_pattern_learning"
            return result
        return {
            "state": "unknown",
            "reason": "report_pattern_not_periodic",
            "threshold_seconds": None,
        }
    last = _parse(last_reported) if last_reported is not None else None
    if last is None:
        return {
            "state": "unknown",
            "reason": "no_report_timestamp",
            "threshold_seconds": None,
        }
    elapsed = max(0.0, (now - last).total_seconds())
    degraded_after = max(30.0, float(p90) * 1.25)
    stale_after = max(degraded_after, float(p95) * 1.5)
    offline_after = max(stale_after, float(p95) * 3.0)
    if elapsed >= offline_after:
        state, reason = "offline", "missed_multiple_expected_reports"
    elif elapsed >= stale_after:
        state, reason = "stale", "report_older_than_learned_p95"
    elif elapsed >= degraded_after:
        state, reason = "degraded", "report_interval_exceeded"
    elif previous_state in {"offline", "stale", "degraded", "recovering"}:
        return _recovery_state(
            now, previous_state, recovery_started_at, recovery_stability
        )
    else:
        state, reason = "healthy", "within_learned_report_window"
    return {
        "state": state,
        "reason": reason,
        "threshold_seconds": offline_after,
        "seconds_since_report": elapsed,
    }


def _recovery_state(
    now: datetime,
    previous: str,
    started: datetime | str | None,
    stability: timedelta,
) -> dict[str, Any]:
    if previous in {"offline", "stale", "degraded", "recovering"}:
        recovery_start = _parse(started) if started is not None else now
        if now - recovery_start < stability:
            return {
                "state": "recovering",
                "reason": "connectivity_returned_stability_window",
                "threshold_seconds": stability.total_seconds(),
            }
    return {"state": "healthy", "reason": "available", "threshold_seconds": None}


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
