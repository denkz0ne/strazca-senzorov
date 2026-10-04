"""Normalize compact evidence records without copying unrelated state data."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

CAUSES = (
    "battery",
    "connectivity",
    "gateway_upstream",
    "integration",
    "power_or_network",
)


def normalize_evidence(
    *,
    feature: str,
    value: Any,
    observed_at: datetime | str,
    provider: str = "generic",
    provenance: str = "observed",
    quality: str = "normal",
) -> dict[str, Any]:
    """Build the allow-listed evidence shape used by cause scoring."""
    if isinstance(observed_at, datetime):
        stamp = (
            observed_at.astimezone(UTC).isoformat()
            if observed_at.tzinfo
            else observed_at.replace(tzinfo=UTC).isoformat()
        )
    elif isinstance(observed_at, str):
        stamp = observed_at
    else:
        raise ValueError("Evidence timestamp must be a datetime or ISO string")
    return {
        "feature": feature,
        "value": value,
        "observed_at": stamp,
        "provider": provider,
        "provenance": provenance,
        "quality": quality,
    }
