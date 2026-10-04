"""Battery reading validation and meaningful-sample retention rules."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


def _timestamp(value: datetime | str | None) -> datetime | None:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_reading(
    *,
    timestamp: datetime | str,
    level_percent: Any = None,
    voltage: Any = None,
    native_low: bool | None = None,
    now: datetime | None = None,
    stale_after: timedelta = timedelta(days=7),
) -> dict[str, Any] | None:
    """Normalize reading units and flag unusable/stale observations."""
    if level_percent is None and voltage is None and native_low is None:
        return None
    parsed = _timestamp(timestamp)
    if parsed is None:
        return None
    current = _timestamp(now or datetime.now(UTC))
    flags: list[str] = []
    level: float | None = None
    voltage_value: float | None = None
    try:
        raw_level = float(level_percent)
        if 0 <= raw_level <= 100:
            level = raw_level
        else:
            flags.append("invalid_percent")
    except TypeError, ValueError:
        if level_percent is not None:
            flags.append("invalid_percent")
    try:
        raw_voltage = float(voltage)
        if 0 < raw_voltage <= 100:
            voltage_value = raw_voltage
        else:
            flags.append("invalid_voltage")
    except TypeError, ValueError:
        if voltage is not None:
            flags.append("invalid_voltage")
    if parsed > current + timedelta(minutes=5):
        flags.append("future_timestamp")
    elif current - parsed > stale_after:
        flags.append("stale")
    if level is not None and level <= 20:
        flags.append("below_low_threshold")
    if level is None and voltage_value is None and native_low is None and not flags:
        return None
    return {
        "timestamp": parsed.isoformat(),
        "level_percent": level,
        "voltage": voltage_value,
        "native_low": native_low if isinstance(native_low, bool) else None,
        "quality_flags": flags,
    }


def should_store_sample(
    previous: dict[str, Any] | None,
    sample: dict[str, Any],
    *,
    checkpoint: timedelta = timedelta(days=1),
    percent_delta: float = 2.0,
    voltage_delta: float = 0.05,
) -> bool:
    """Keep state transitions, useful deltas and occasional checkpoint samples."""
    if previous is None:
        return True
    if (
        sample.get("native_low") != previous.get("native_low")
        and sample.get("native_low") is not None
    ):
        return True
    for key, threshold in (
        ("level_percent", percent_delta),
        ("voltage", voltage_delta),
    ):
        before, after = previous.get(key), sample.get(key)
        if (
            before is not None
            and after is not None
            and abs(after - before) >= threshold
        ):
            return True
    previous_time = _timestamp(previous.get("timestamp"))
    current_time = _timestamp(sample.get("timestamp"))
    return bool(
        previous_time and current_time and current_time - previous_time >= checkpoint
    )
