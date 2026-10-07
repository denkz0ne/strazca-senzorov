"""Selected source-entity sampling for tracked battery devices."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_state_report_event,
)

from ..events import BATTERY_ATTENTION_EVENT, event_payload
from ..runtime import schedule_device_processing
from .estimator import estimate_remaining_life
from .samples import normalize_reading, should_store_sample


def battery_entity_map(
    devices: list[dict[str, Any]],
) -> dict[str, list[tuple[str, str]]]:
    """Map explicitly selected battery reading entity IDs to devices/reading kinds."""
    result: dict[str, list[tuple[str, str]]] = {}
    for device in devices:
        if device.get("tracking_mode") not in {
            "battery_and_availability",
            "battery_only",
        }:
            continue
        if device.get("power_type") == "mains":
            continue
        refs = device.get("entity_refs", {})
        if not isinstance(refs, dict):
            continue
        for kind in ("battery_level", "battery_low", "voltage"):
            entity_id = refs.get(kind)
            if isinstance(entity_id, str):
                result.setdefault(entity_id, []).append((device["device_id"], kind))
    return result


def async_subscribe_battery(
    hass: HomeAssistant,
    runtime: dict[str, Any],
) -> tuple[list[str], list[Callable[[], None]]]:
    """Subscribe to selected battery entities and seed their current values."""
    entity_devices = battery_entity_map(runtime["data"]["devices"])
    if not entity_devices:
        return [], []

    @callback
    def handle(event: Event) -> None:
        entity_id = event.data.get("entity_id")
        matches = entity_devices.get(entity_id, [])
        if not matches:
            return
        state = event.data.get("new_state") or hass.states.get(entity_id)
        timestamp = event.data.get("last_reported")
        if not isinstance(timestamp, datetime) and state is not None:
            timestamp = state.last_reported
        if not isinstance(timestamp, datetime):
            timestamp = datetime.now(UTC)
        for device_id, _kind in matches:
            _record_current_device(hass, runtime, device_id, timestamp)

    entity_ids = sorted(entity_devices)
    unsubscribers = [
        async_track_state_change_event(hass, entity_ids, handle),
        async_track_state_report_event(hass, entity_ids, handle),
    ]
    for device_id in sorted(
        {device_id for values in entity_devices.values() for device_id, _ in values}
    ):
        _record_current_device(hass, runtime, device_id, datetime.now(UTC))
    return entity_ids, unsubscribers


@callback
def _record_current_device(
    hass: HomeAssistant, runtime: dict[str, Any], device_id: str, timestamp: datetime
) -> None:
    data = runtime["data"]
    device = next(
        (item for item in data["devices"] if item["device_id"] == device_id), None
    )
    if device is None:
        return
    refs = device.get("entity_refs", {})
    if not isinstance(refs, dict):
        return
    level, voltage, low = None, None, None
    source_ids: list[str] = []
    for kind, key in (
        ("battery_level", "level"),
        ("voltage", "voltage"),
        ("battery_low", "low"),
    ):
        entity_id = refs.get(kind)
        state = hass.states.get(entity_id) if isinstance(entity_id, str) else None
        if state is None or state.state in {"unknown", "unavailable"}:
            continue
        source_ids.append(entity_id)
        if key == "low":
            low = state.state == "on"
        else:
            try:
                value = float(state.state)
            except ValueError:
                continue
            if key == "level":
                level = value
            else:
                voltage = (
                    value / 1000
                    if state.attributes.get("unit_of_measurement") == "mV"
                    else value
                )
    sample = normalize_reading(
        timestamp=timestamp,
        level_percent=level,
        voltage=voltage,
        native_low=low,
        now=datetime.now(UTC),
    )
    if sample is None:
        return
    previous = next(
        (item for item in reversed(data["samples"]) if item["device_id"] == device_id),
        None,
    )
    if should_store_sample(previous, sample):
        identity = json.dumps(
            [
                device_id,
                sample["timestamp"],
                sample.get("level_percent"),
                sample.get("voltage"),
                low,
            ],
            separators=(",", ":"),
        )
        sample.update(
            {
                "sample_id": "sample_"
                + hashlib.sha256(identity.encode()).hexdigest()[:20],
                "device_id": device_id,
                "source_entity_ids": source_ids,
                "provenance": "ha_source_entities",
            }
        )
        if not any(
            item["sample_id"] == sample["sample_id"] for item in data["samples"]
        ):
            data["samples"].append(sample)
            if len(data["samples"]) > 10000:
                del data["samples"][:-10000]
    samples = [item for item in data["samples"] if item["device_id"] == device_id]
    cycles = [item for item in data["cycles"] if item["device_id"] == device_id]
    estimate = estimate_remaining_life(samples, cycles)
    previous_attention = bool(device.get("battery_attention"))
    current_level = sample.get("level_percent")
    current_low = sample.get("native_low") is True
    window = estimate.get("remaining_days_range")
    settings = data.get("settings", {})
    replace_soon = bool(
        window
        and window.get("max", 10_000)
        <= float(settings.get("replacement_warning_days", 14))
    )
    device["battery_estimate"] = estimate
    device["battery_attention"] = (
        current_low
        or bool(
            current_level is not None
            and current_level <= float(settings.get("low_battery_threshold", 20))
        )
        or replace_soon
        or bool(estimate.get("abnormal_drain"))
    )
    if device["battery_attention"] and not previous_attention:
        payload = event_payload(device)
        payload["battery_level"] = current_level
        payload["remaining_days_range"] = estimate.get("remaining_days_range")
        hass.bus.async_fire(BATTERY_ATTENTION_EVENT, payload)
    for entity in runtime.get("entities", {}).get(device_id, []):
        entity.async_write_ha_state()
    runtime.get("schedule_save", lambda: None)()
    schedule_device_processing(hass, runtime)
