"""Compact automation-facing device status."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

STATUS_OPTIONS = [
    "initializing",
    "healthy",
    "degraded",
    "stale",
    "offline",
    "recovering",
    "paused",
    "unknown",
]


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create one compact status enum for each tracked device."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    runtime.setdefault("add_entities", {})["sensor"] = async_add_entities
    entities: list[GuardianStatus] = []
    runtime_entities = runtime.setdefault("entities", {})
    for device in runtime["data"]["devices"]:
        if device.get("tracking_mode") == "ignored":
            continue
        entities.append(
            GuardianStatus(
                hass, device, runtime_entities.setdefault(device["device_id"], [])
            )
        )
    async_add_entities(entities)


class GuardianStatus(SensorEntity):
    """Display only the short state label and concise incident attributes."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _attr_translation_key = "guardian_status"

    def __init__(self, hass: HomeAssistant, device: dict, group: list) -> None:
        self.device = device
        refs = device.get("entity_refs", {})
        source_entity = (
            next(
                (
                    refs.get(key)
                    for key in ("native_availability", "battery_level", "battery_low")
                    if refs.get(key)
                ),
                next(iter(device.get("sentinels", [])), None),
            )
            if isinstance(refs, dict)
            else None
        )
        self.device_entry = (
            async_entity_id_to_device(hass, source_entity) if source_entity else None
        )
        self._attr_unique_id = f"{DOMAIN}_{device['device_id']}_status"
        group.append(self)

    @property
    def native_value(self) -> str:
        """Return the current compact health state."""
        value = self.device.get("health_state", "unknown")
        return value if value in STATUS_OPTIONS else "unknown"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Expose just the automation-relevant incident summary."""
        return {
            "cause": self.device.get("cause", "unknown"),
            "confidence": self.device.get("cause_confidence", "none"),
            "since": self.device.get("health_since"),
            "parent_incident_id": self.device.get("parent_incident_id"),
        }
