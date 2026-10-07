"""Redacted runtime evidence for functional support."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Expose evidence coverage without device names, IDs or source entity IDs."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    data = runtime.get("data", {})
    devices = []
    for device in data.get("devices", []):
        refs = device.get("entity_refs", {})
        samples = [
            sample
            for sample in data.get("samples", [])
            if sample["device_id"] == device["device_id"]
        ]
        devices.append(
            {
                "source_integration": device.get("source_integration"),
                "tracking_mode": device.get("tracking_mode"),
                "power_type": device.get("power_type"),
                "health_state": device.get("health_state"),
                "health_reason": device.get("health_reason"),
                "binding_version": device.get("source_binding_version", 0),
                "source_coverage": {kind: bool(value) for kind, value in refs.items()},
                "sample_count": len(samples),
                "latest_level": next(
                    (
                        sample["level_percent"]
                        for sample in reversed(samples)
                        if sample.get("level_percent") is not None
                    ),
                    None,
                ),
                "disabled_signal_count": len(
                    device.get("recommended_signal_entities", [])
                ),
            }
        )
    return {
        "device_count": len(devices),
        "devices": devices,
        "sample_count": len(data.get("samples", [])),
        "cycle_count": len(data.get("cycles", [])),
        "active_incident_count": sum(
            not item.get("closed_at") for item in data.get("incidents", [])
        ),
    }
