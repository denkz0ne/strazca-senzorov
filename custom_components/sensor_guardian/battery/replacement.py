"""Battery replacement candidates and confirmed cycle operations."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from ..models import GuardianData, empty_store_data, validate_store_data


def detect_replacement_candidate(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    *,
    power_type: str,
    jump_threshold: float = 25.0,
    high_level: float = 70.0,
) -> dict[str, Any] | None:
    """Detect reset-like jumps without converting them into automatic replacements."""
    if power_type == "mains":
        return None
    level = current.get("level_percent")
    if not isinstance(level, (int, float)):
        return None
    if power_type == "rechargeable":
        if (
            previous
            and isinstance(previous.get("level_percent"), (int, float))
            and level - previous["level_percent"] >= jump_threshold
        ):
            return {
                "kind": "charging",
                "requires_confirmation": False,
                "reason_code": "recharge_level_increase",
            }
        return None
    before = previous.get("level_percent") if previous else None
    if (
        isinstance(before, (int, float))
        and level >= high_level
        and level - before >= jump_threshold
    ):
        return {
            "kind": "replacement_candidate",
            "requires_confirmation": True,
            "reason_code": "large_battery_level_reset",
        }
    return None


def confirm_replacement(
    data: dict[str, Any] | None,
    *,
    device_id: str,
    replaced_at: str | None = None,
    battery_type: str | None = None,
    battery_quantity: int | None = None,
    brand: str | None = None,
    reason: str = "user_confirmed",
    power_type: str = "replaceable_battery",
) -> tuple[GuardianData, dict[str, Any]]:
    """Close the prior battery cycle and open a user-confirmed replacement cycle."""
    if power_type == "mains":
        raise ValueError("Mains-powered devices cannot have battery replacement cycles")
    if battery_quantity is not None and battery_quantity < 1:
        raise ValueError("Battery quantity must be at least one")
    result = validate_store_data(data if data is not None else empty_store_data())
    timestamp = replaced_at or datetime.now(UTC).isoformat()
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as err:
        raise ValueError("Replacement time must be an ISO timestamp") from err
    timestamp = parsed.isoformat()
    stable = json.dumps(
        [device_id, timestamp, battery_type, battery_quantity], separators=(",", ":")
    )
    cycle_id = "cycle_" + hashlib.sha256(stable.encode()).hexdigest()[:20]
    existing = next(
        (cycle for cycle in result["cycles"] if cycle["cycle_id"] == cycle_id), None
    )
    if existing:
        return result, deepcopy(existing)
    cycles = [cycle for cycle in result["cycles"] if cycle["device_id"] == device_id]
    for cycle in cycles:
        if not cycle.get("ended_at"):
            cycle["ended_at"] = timestamp
            cycle["replacement_reason"] = reason
    cycle = {
        "cycle_id": cycle_id,
        "device_id": device_id,
        "started_at": timestamp,
        "battery_type": battery_type,
        "battery_quantity": battery_quantity or 1,
        "brand": brand,
        "replacement_reason": reason,
        "provenance": "user_confirmed",
    }
    result["cycles"].append(cycle)
    device = next(
        (item for item in result["devices"] if item["device_id"] == device_id), None
    )
    if device is None:
        device = {"device_id": device_id}
        result["devices"].append(device)
    device.setdefault("replacement_history", []).append(cycle_id)
    if battery_type is not None:
        device["battery_type"] = battery_type
        device.setdefault("user_overrides", {})["battery_type"] = battery_type
    if battery_quantity is not None:
        device["battery_quantity"] = battery_quantity
        device.setdefault("user_overrides", {})["battery_quantity"] = battery_quantity
    return result, deepcopy(cycle)
