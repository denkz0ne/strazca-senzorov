"""Filtered Home Assistant report subscriptions for selected availability sentinels."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_state_report_event,
)


def selected_sentinels(devices: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Build the explicit per-device entity allow-list for report tracking."""
    result: dict[str, set[str]] = {}
    for device in devices:
        if device.get("tracking_mode") == "ignored":
            continue
        device_id = device.get("device_id")
        if not isinstance(device_id, str):
            continue
        refs = device.get("entity_refs", {})
        raw_sentinels = device.get("sentinels", [])
        selected = (
            {entity_id for entity_id in raw_sentinels if isinstance(entity_id, str)}
            if isinstance(raw_sentinels, (list, tuple, set))
            else set()
        )
        if isinstance(refs, dict) and isinstance(refs.get("native_availability"), str):
            selected.add(refs["native_availability"])
        if selected:
            result[device_id] = selected
    return result


def async_subscribe_reports(
    hass: HomeAssistant,
    devices: list[dict[str, Any]],
    action: Callable[[str, str, datetime, Any], None],
) -> tuple[list[str], list[Callable[[], None]]]:
    """Subscribe to state changes/reports for tracked sentinels only and seed now."""
    device_entities = selected_sentinels(devices)
    entity_devices: dict[str, list[str]] = {}
    for device_id, entity_ids in device_entities.items():
        for entity_id in entity_ids:
            entity_devices.setdefault(entity_id, []).append(device_id)
    if not entity_devices:
        return [], []

    @callback
    def handle(event: Event) -> None:
        entity_id = event.data.get("entity_id")
        device_ids = entity_devices.get(entity_id)
        if not device_ids:
            return
        new_state = event.data.get("new_state") or hass.states.get(entity_id)
        last_reported = event.data.get("last_reported")
        if not isinstance(last_reported, datetime) and new_state is not None:
            last_reported = new_state.last_reported
        if isinstance(last_reported, datetime):
            for device_id in device_ids:
                action(device_id, entity_id, last_reported, new_state)

    entity_ids = sorted(entity_devices)
    unsubscribers = [
        async_track_state_change_event(hass, entity_ids, handle),
        async_track_state_report_event(hass, entity_ids, handle),
    ]
    # Register listeners before reading state so the first observation cannot be missed.
    for entity_id, device_ids in entity_devices.items():
        state = hass.states.get(entity_id)
        if state is not None and isinstance(state.last_reported, datetime):
            for device_id in device_ids:
                action(device_id, entity_id, state.last_reported, state)
    return entity_ids, unsubscribers
