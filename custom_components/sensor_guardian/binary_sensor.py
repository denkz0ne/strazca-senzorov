"""Small automation-facing binary summaries."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device import async_entity_id_to_device
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

PROBLEM_STATES = {"degraded", "stale", "offline"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create two summary flags per tracked device, plus battery attention if used."""
    runtime = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []
    runtime_entities = runtime.setdefault("entities", {})
    for device in runtime["data"]["devices"]:
        if device.get("tracking_mode") == "ignored":
            continue
        group = runtime_entities.setdefault(device["device_id"], [])
        entities.append(GuardianProblem(hass, device, group))
        if (
            device.get("tracking_mode") in {"battery_and_availability", "battery_only"}
            and device.get("power_type") != "mains"
        ):
            entities.append(GuardianBatteryAttention(hass, device, group))
    async_add_entities(entities)


class _GuardianBinarySensor(BinarySensorEntity):
    """Shared device link and compact incident attributes."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, device: dict, group: list) -> None:
        self.device = device
        self.group = group
        self.device_entry = None
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
        if source_entity:
            self.device_entry = async_entity_id_to_device(hass, source_entity)
        group.append(self)

    @property
    def available(self) -> bool:
        return True

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "status": self.device.get("health_state", "unknown"),
            "cause": self.device.get("cause", "unknown"),
            "confidence": self.device.get("cause_confidence", "none"),
            "since": self.device.get("health_since"),
            "parent_incident_id": self.device.get("parent_incident_id"),
        }


class GuardianProblem(_GuardianBinarySensor):
    """True when availability needs attention."""

    _attr_translation_key = "guardian_problem"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, hass: HomeAssistant, device: dict, group: list) -> None:
        super().__init__(hass, device, group)
        self._attr_unique_id = f"{DOMAIN}_{device['device_id']}_problem"

    @property
    def is_on(self) -> bool:
        return self.device.get("health_state") in PROBLEM_STATES


class GuardianBatteryAttention(_GuardianBinarySensor):
    """True when the selected battery needs near-term action."""

    _attr_translation_key = "battery_attention"
    _attr_icon = "mdi:battery-alert-variant-outline"

    def __init__(self, hass: HomeAssistant, device: dict, group: list) -> None:
        super().__init__(hass, device, group)
        self._attr_unique_id = f"{DOMAIN}_{device['device_id']}_battery_attention"

    @property
    def is_on(self) -> bool:
        return bool(self.device.get("battery_attention", False))
