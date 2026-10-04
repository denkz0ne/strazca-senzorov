"""Versioned compact automation events and transition deduplication."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

INCIDENT_EVENT = "sensor_guardian_incident"
RECOVERED_EVENT = "sensor_guardian_recovered"
BATTERY_ATTENTION_EVENT = "sensor_guardian_battery_attention"
BATTERY_REPLACED_EVENT = "sensor_guardian_battery_replaced"
ACTIONABLE_STATES = {"degraded", "stale", "offline"}


def event_for_transition(previous: str, current: str) -> str | None:
    """Choose an event only on actionable/recovered transition edges."""
    if current in ACTIONABLE_STATES and previous not in ACTIONABLE_STATES:
        return INCIDENT_EVENT
    if current == "healthy" and previous in ACTIONABLE_STATES:
        return RECOVERED_EVENT
    return None


def event_payload(
    device: dict[str, Any],
    *,
    incident: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
    device_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build a compact, versioned payload without unrelated HA attributes."""
    current = timestamp or datetime.now(UTC)
    payload = {
        "version": 1,
        "device_id": device["device_id"],
        "device_name": device.get("name", device["device_id"]),
        "status": device.get("health_state", "unknown"),
        "cause": device.get("cause", "unknown"),
        "confidence": device.get("cause_confidence", "none"),
        "severity": incident.get("severity", "warning") if incident else "info",
        "incident_id": incident.get("incident_id") if incident else None,
        "timestamp": current.astimezone(UTC).isoformat(),
    }
    if device_ids:
        payload["device_ids"] = sorted(set(device_ids))
    return payload


def fire_event(
    hass,
    event_type: str,
    device: dict[str, Any],
    *,
    incident: dict[str, Any] | None = None,
    device_ids: list[str] | None = None,
) -> None:
    """Fire a known versioned event with the allow-listed payload."""
    hass.bus.async_fire(
        event_type,
        event_payload(device, incident=incident, device_ids=device_ids),
    )
