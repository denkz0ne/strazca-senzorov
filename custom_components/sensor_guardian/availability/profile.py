"""Robust report cadence profiles; event-only patterns remain non-periodic."""

from __future__ import annotations

from datetime import UTC, datetime
from statistics import median


def _parse(value: str | datetime) -> datetime | None:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _quantile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction + 0.999)))
    return ordered[index]


def learn_report_profile(
    timestamps: list[str | datetime], *, explicit_availability: bool = False
) -> dict[str, float | bool | int | str | None]:
    """Learn interval quantiles and confidence from one device's report times."""
    parsed = sorted(stamp for value in timestamps if (stamp := _parse(value)))
    intervals = [
        (right - left).total_seconds()
        for left, right in zip(parsed, parsed[1:], strict=False)
        if (right - left).total_seconds() > 0
    ]
    typical = median(intervals) if intervals else None
    jitter = (
        median([abs(value - typical) for value in intervals]) / typical
        if typical
        else None
    )
    count = len(intervals)
    if count < 3:
        confidence = 0.0
        pattern = "learning"
    else:
        confidence = min(1.0, count / 12) * max(0.0, 1.0 - min(jitter or 0.0, 1.0))
        pattern = "periodic" if (jitter or 0) <= 0.5 and count >= 4 else "irregular"
    if not intervals:
        pattern = "event_only"
    return {
        "median_interval_seconds": typical,
        "p90_interval_seconds": _quantile(intervals, 0.9),
        "p95_interval_seconds": _quantile(intervals, 0.95),
        "jitter_seconds": median([abs(value - typical) for value in intervals])
        if typical
        else None,
        "pattern_confidence": round(confidence, 3),
        "interval_count": count,
        "pattern": pattern,
        "explicit_availability": explicit_availability,
    }
