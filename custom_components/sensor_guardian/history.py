"""Bounded real observations; HA state writes never imply physical packets."""

from __future__ import annotations

import hashlib
import logging
import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Any

_LOGGER = logging.getLogger(__name__)


def parse_time(value: Any) -> datetime | None:
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, UTC)
        date = (
            value
            if isinstance(value, datetime)
            else datetime.fromisoformat(value.replace("Z", "+00:00"))
        )
        return date.replace(tzinfo=UTC) if date.tzinfo is None else date.astimezone(UTC)
    except ValueError, TypeError, AttributeError, OverflowError:
        return None


def number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except TypeError, ValueError:
        return None


def stable_id(*values: Any) -> str:
    return hashlib.sha256("|".join(map(str, values)).encode()).hexdigest()[:24]


def record_health(data: dict, device: dict, *, now: datetime) -> bool:
    rows = data.setdefault("health_history", [])
    last = next(
        (row for row in reversed(rows) if row["device_id"] == device["device_id"]), None
    )
    state = device.get("health_state", "unknown")
    if last is not None and last["state"] == state:
        return False
    rows.append(
        {
            "transition_id": stable_id(device["device_id"], state, now.isoformat()),
            "device_id": device["device_id"],
            "timestamp": now.isoformat(),
            "state": state,
            "reason": device.get("health_reason"),
            "provenance": "guardian_evaluation",
        }
    )
    return True


def record_signal(
    data: dict, device_id: str, kind: str, value: Any, *, now: datetime
) -> bool:
    numeric = number(value)
    if numeric is None:
        return False
    rows = data.setdefault("signal_samples", [])
    last = next(
        (
            row
            for row in reversed(rows)
            if row["device_id"] == device_id and row["kind"] == kind
        ),
        None,
    )
    if last is not None:
        timestamp = parse_time(last["timestamp"])
        if (
            timestamp is not None
            and now - timestamp < timedelta(hours=1)
            and abs(numeric - last["value"]) < (5 if kind == "rssi" else 15)
        ):
            return False
    rows.append(
        {
            "sample_id": stable_id(device_id, kind, now.isoformat(), numeric),
            "device_id": device_id,
            "timestamp": now.isoformat(),
            "kind": kind,
            "value": numeric,
            "provenance": "ha_source_observation",
            "resolution": "observation",
        }
    )
    return True


def prune_battery_history(data: dict, *, now: datetime) -> bool:
    """Bound each device independently; preserve one explicitly dated old fact."""
    cutoff = now - timedelta(
        days=min(730, max(30, int(data.get("settings", {}).get("retention_days", 365))))
    )
    groups = defaultdict(list)
    for row in data.get("samples", []):
        if parse_time(row.get("timestamp")):
            groups[row["device_id"]].append(row)
    kept = []
    for rows in groups.values():
        rows.sort(key=lambda row: row["timestamp"])
        recent = [row for row in rows if parse_time(row["timestamp"]) >= cutoff]
        kept.extend((recent or rows[-1:])[-4096:])
    kept.sort(key=lambda row: row["timestamp"])
    changed = kept != data.get("samples", [])
    data["samples"][:] = kept
    return changed


def prune_history(data: dict, *, now: datetime) -> bool:
    """Compact old signal observations into weighted daily summaries."""
    before = (
        [
            (row["sample_id"], row.get("count", 1))
            for row in data.get("signal_samples", [])
        ],
        [row["transition_id"] for row in data.get("health_history", [])],
    )
    cutoff = now - timedelta(
        days=min(730, max(30, int(data.get("settings", {}).get("retention_days", 365))))
    )
    raw_cutoff = now - timedelta(days=14)
    recent, buckets = [], defaultdict(list)
    for row in data.get("signal_samples", []):
        stamp = parse_time(row.get("timestamp"))
        if stamp is None or stamp < cutoff:
            continue
        if stamp >= raw_cutoff and row.get("resolution") != "day":
            recent.append(row)
        else:
            buckets[(row["device_id"], row["kind"], stamp.date().isoformat())].append(
                row
            )
    compacted = []
    for (device_id, kind, day), rows in buckets.items():
        weight = sum(int(row.get("count", 1)) for row in rows)
        compacted.append(
            {
                "sample_id": stable_id(device_id, kind, day),
                "device_id": device_id,
                "kind": kind,
                "timestamp": f"{day}T00:00:00+00:00",
                "value": sum(row["value"] * int(row.get("count", 1)) for row in rows)
                / weight,
                "min": min(row.get("min", row["value"]) for row in rows),
                "max": max(row.get("max", row["value"]) for row in rows),
                "count": weight,
                "resolution": "day",
                "provenance": "aggregated_ha_observations",
            }
        )
    data["signal_samples"][:] = sorted(
        recent + compacted, key=lambda row: row["timestamp"]
    )
    data["health_history"][:] = [
        row
        for row in data.get("health_history", [])
        if (stamp := parse_time(row.get("timestamp"))) and stamp >= cutoff
    ]
    battery_changed = prune_battery_history(data, now=now)
    return battery_changed or before != (
        [(row["sample_id"], row.get("count", 1)) for row in data["signal_samples"]],
        [row["transition_id"] for row in data["health_history"]],
    )


async def async_fill_native_battery_history(hass, runtime: dict) -> bool:
    """Optional one-time Recorder backfill for selected native percentages."""
    from homeassistant.helpers import entity_registry
    from homeassistant.helpers.recorder import get_instance

    if runtime.get("stopping"):
        return False
    try:
        recorder = get_instance(hass)
    except KeyError:
        return False
    from homeassistant.components.recorder import history

    data, registry = runtime["data"], entity_registry.async_get(hass)
    wanted = {}
    for device in data["devices"]:
        source = device.get("entity_refs", {}).get("battery_level")
        row = registry.async_get(source) if source else None
        if (
            row
            and row.platform not in {"battery_notes", "sensor_guardian"}
            and row.device_id == device["device_id"]
            and not row.disabled_by
            and device.get("history_source") != source
            and device.get("tracking_mode") != "ignored"
        ):
            wanted[source] = device
    if not wanted:
        return False
    end = datetime.now(UTC)
    start = end - timedelta(days=90)
    existing = {
        (row["device_id"], row["timestamp"], row.get("level_percent"))
        for row in data["samples"]
    }
    for begin in range(0, len(wanted), 20):
        sources = list(wanted)[begin : begin + 20]
        try:
            rows = await recorder.async_add_executor_job(
                partial(
                    history.get_significant_states,
                    hass,
                    start,
                    end,
                    sources,
                    None,
                    False,
                    True,
                    False,
                    True,
                    False,
                )
            )
        except Exception as error:
            _LOGGER.warning(
                "Native battery history unavailable (%s)", type(error).__name__
            )
            for source in sources:
                wanted[source]["history_status"] = "unavailable"
            continue
        if runtime.get("stopping"):
            return False
        for source in sources:
            device = wanted[source]
            states = rows.get(source, [])
            for state in states[-600:]:
                value = number(
                    state.get("state") if isinstance(state, dict) else state.state
                )
                timestamp = parse_time(
                    state.get("last_updated", state.get("last_changed"))
                    if isinstance(state, dict)
                    else state.last_updated
                )
                if value is None or not 0 <= value <= 100 or timestamp is None:
                    continue
                key = device["device_id"], timestamp.isoformat(), value
                if key in existing:
                    continue
                data["samples"].append(
                    {
                        "sample_id": stable_id("native_history", *key),
                        "device_id": key[0],
                        "timestamp": key[1],
                        "level_percent": value,
                        "quality_flags": [],
                        "source_entity_ids": [source],
                        "provenance": "native_recorder_exact",
                    }
                )
                existing.add(key)
            device["history_source"] = source
            device["history_status"] = (
                "partial" if len(states) > 600 else "loaded" if states else "empty"
            )
    data["samples"].sort(key=lambda row: row["timestamp"])
    runtime["schedule_save"]()
    runtime["refresh_battery_subscriptions"]()
    return True


def async_subscribe_signals(hass, runtime: dict):
    """Observe selected signal entities only and seed the current HA snapshot."""
    from homeassistant.core import callback
    from homeassistant.helpers.event import (
        async_track_state_change_event,
        async_track_state_report_event,
    )

    from .runtime import schedule_device_processing

    mapping = defaultdict(list)
    for device in runtime["data"]["devices"]:
        if device.get("tracking_mode") == "ignored":
            continue
        for signal in device.get("signal", []):
            if isinstance(signal, dict) and isinstance(signal.get("entity_id"), str):
                mapping[signal["entity_id"]].append(
                    (device["device_id"], signal.get("kind", "signal"))
                )

    @callback
    def observe(entity_id):
        state = hass.states.get(entity_id)
        if state is None or state.state in {"unavailable", "unknown"}:
            return
        changed = False
        for device_id, kind in mapping.get(entity_id, []):
            changed |= record_signal(
                runtime["data"], device_id, kind, state.state, now=datetime.now(UTC)
            )
        if changed:
            runtime["schedule_save"]()
            schedule_device_processing(hass, runtime)

    @callback
    def received(event):
        observe(event.data.get("entity_id"))

    ids = sorted(mapping)
    unsubscribers = (
        []
        if not ids
        else [
            async_track_state_change_event(hass, ids, received),
            async_track_state_report_event(hass, ids, received),
        ]
    )
    for entity_id in ids:
        observe(entity_id)
    return unsubscribers
