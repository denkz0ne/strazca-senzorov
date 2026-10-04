"""Conservative per-device battery lifetime estimates."""

from __future__ import annotations

from datetime import UTC, datetime
from statistics import median
from typing import Any

MIN_SAMPLES = 4
MIN_SPAN_DAYS = 7.0
LOW_BATTERY_PERCENT = 20.0


def _date(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _trend(samples: list[dict[str, Any]]) -> tuple[float | None, float]:
    points: list[tuple[float, float]] = []
    for sample in samples:
        stamp = _date(sample.get("timestamp"))
        level = sample.get("level_percent")
        flags = set(sample.get("quality_flags", []))
        if (
            stamp
            and isinstance(level, (int, float))
            and 0 <= level <= 100
            and not flags.intersection(
                {"stale", "invalid_percent", "aggregated_statistics"}
            )
        ):
            points.append((stamp.timestamp(), float(level)))
    points.sort()
    span = (points[-1][0] - points[0][0]) / 86400 if len(points) > 1 else 0
    rates = [
        (left[1] - right[1]) / ((right[0] - left[0]) / 86400)
        for index, left in enumerate(points)
        for right in points[index + 1 :]
        if right[0] > left[0] and left[1] - right[1] >= 0.2
    ]
    return (median(rates) if rates else None), span


def estimate_remaining_life(
    samples: list[dict[str, Any]],
    cycles: list[dict[str, Any]],
    *,
    now: datetime | None = None,
    low_threshold: float = LOW_BATTERY_PERCENT,
) -> dict[str, Any]:
    """Return a range only when current samples or device history justify one."""
    current = now or datetime.now(UTC)
    valid = [
        sample
        for sample in samples
        if _date(sample.get("timestamp"))
        and isinstance(sample.get("level_percent"), (int, float))
    ]
    valid.sort(key=lambda sample: _date(sample["timestamp"]) or current)
    if not valid:
        return _unknown("no_valid_samples")
    last_level = float(valid[-1]["level_percent"])
    rate, span = _trend(valid)
    days = [
        (_date(cycle.get("ended_at")) - _date(cycle.get("started_at"))).total_seconds()
        / 86400
        for cycle in cycles
        if _date(cycle.get("ended_at"))
        and _date(cycle.get("started_at"))
        and _date(cycle.get("ended_at")) > _date(cycle.get("started_at"))
    ]
    history_days = median(days) if days else None
    current_cycle = next(
        (cycle for cycle in reversed(cycles) if not cycle.get("ended_at")), None
    )
    age = None
    if current_cycle and _date(current_cycle.get("started_at")):
        age = max(
            0.0, (current - _date(current_cycle["started_at"])).total_seconds() / 86400
        )
    reason_codes: list[str] = []
    levels = [float(sample["level_percent"]) for sample in valid]
    coarse_steps = (
        len(set(levels)) >= 3
        and len(set(levels)) <= 8
        and all(level % 10 == 0 for level in levels)
    )
    if (
        rate is not None
        and span >= MIN_SPAN_DAYS
        and len(valid) >= MIN_SAMPLES
        and rate > 0
    ):
        days_left = max(0.0, (last_level - low_threshold) / rate)
        uncertainty = max(0.25, min(0.6, 1.0 - min(span, 30) / 60))
        low = max(0, int(days_left * (1 - uncertainty)))
        high = max(low, int(days_left * (1 + uncertainty) + 0.999))
        confidence = (
            "medium" if len(valid) >= 8 and span >= 21 and not coarse_steps else "low"
        )
        reason_codes.extend(
            ("current_cycle_drain_trend", "robust_median_pairwise_rate")
        )
        if coarse_steps:
            reason_codes.append("coarse_battery_steps")
    elif history_days is not None and age is not None:
        days_left = max(0.0, history_days - age)
        low = max(0, int(days_left * 0.65))
        high = max(low, int(days_left * 1.35 + 0.999))
        confidence = "low"
        reason_codes.append("same_device_cycle_history")
    else:
        result = _unknown("insufficient_history")
        result["sample_count"] = len(valid)
        result["span_days"] = round(span, 1)
        return result
    abnormal = False
    previous_rates = [
        (float(cycle["initial_level"]) - float(cycle["final_level"])) / duration
        for cycle in cycles
        if cycle.get("ended_at")
        and isinstance(cycle.get("initial_level"), (int, float))
        and isinstance(cycle.get("final_level"), (int, float))
        and (
            duration := (
                (_date(cycle["ended_at"]) - _date(cycle["started_at"])).total_seconds()
                / 86400
                if _date(cycle.get("ended_at")) and _date(cycle.get("started_at"))
                else 0
            )
        )
        > 1
    ]
    if rate and previous_rates and rate >= max(1.0, median(previous_rates) * 2.5):
        abnormal = True
        reason_codes.append("abnormal_drain_vs_prior_cycles")
    if last_level <= low_threshold:
        reason_codes.append("at_or_below_low_threshold")
    return {
        "remaining_days_range": {"min": low, "max": high},
        "replacement_window": {"from_days": low, "to_days": high},
        "confidence": confidence,
        "reason_codes": reason_codes,
        "sample_count": len(valid),
        "span_days": round(span, 1),
        "drain_percent_per_day": round(rate, 3) if rate is not None else None,
        "abnormal_drain": abnormal,
    }


def _unknown(reason: str) -> dict[str, Any]:
    return {
        "remaining_days_range": None,
        "replacement_window": None,
        "confidence": "none",
        "reason_codes": [reason],
        "sample_count": 0,
        "span_days": 0.0,
        "drain_percent_per_day": None,
        "abnormal_drain": False,
    }
