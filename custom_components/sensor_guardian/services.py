"""Validated Home Assistant actions for lifecycle and incident control."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components.persistent_notification import async_dismiss
from homeassistant.core import HomeAssistant, ServiceCall

from .battery.replacement import confirm_replacement
from .const import DOMAIN
from .diagnosis.incidents import revise_cause
from .events import BATTERY_REPLACED_EVENT, event_payload
from .runtime import _merge_data

CAUSES = {
    "battery",
    "connectivity",
    "gateway_upstream",
    "integration",
    "power_or_network",
    "unknown",
}
CAUSE_SCHEMA = vol.In({value: value for value in sorted(CAUSES)})
DEVICE_SCHEMA = vol.Any(str, vol.All([str], vol.Length(min=1, max=1)))


def _device_id(value: Any) -> str:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str):
        return value[0]
    raise vol.Invalid("Select exactly one device")


def _runtime(hass: HomeAssistant) -> dict[str, Any]:
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        raise vol.Invalid("Sensor Guardian is not set up")
    return next(iter(entries.values()))


def async_register_services(hass: HomeAssistant) -> None:
    """Register actions once for the single global config entry."""
    if hass.services.has_service(DOMAIN, "mark_battery_replaced"):
        return

    async def mark_replaced(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        data = runtime["data"]
        device_id = _device_id(call.data["device_id"])
        device = next(
            (item for item in data["devices"] if item["device_id"] == device_id), None
        )
        if device is None:
            raise vol.Invalid("Device is not tracked by Sensor Guardian")
        updated, cycle = confirm_replacement(
            data,
            device_id=device_id,
            replaced_at=call.data.get("replaced_at"),
            battery_type=call.data.get("battery_type"),
            battery_quantity=call.data.get("battery_quantity"),
            brand=call.data.get("brand"),
            reason=call.data.get("reason", "user_confirmed"),
            power_type=device.get("power_type", "unknown"),
        )
        payload = None
        if not any(
            existing["cycle_id"] == cycle["cycle_id"] for existing in data["cycles"]
        ):
            device = next(
                item for item in updated["devices"] if item["device_id"] == device_id
            )
            device["battery_attention"] = False
            payload = event_payload(device)
            payload.update(
                {
                    "battery_type": cycle.get("battery_type"),
                    "battery_quantity": cycle.get("battery_quantity"),
                    "cycle_id": cycle["cycle_id"],
                }
            )
        _merge_data(runtime, updated)
        await runtime["storage"].async_save(runtime["data"])
        if payload is not None:
            hass.bus.async_fire(BATTERY_REPLACED_EVENT, payload)
            async_dismiss(hass, f"{DOMAIN}_battery_{device_id}")
        _write_device_entities(runtime, device_id)

    async def confirm_cause(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        incident = next(
            (
                item
                for item in runtime["data"]["incidents"]
                if item["incident_id"] == call.data["incident_id"]
            ),
            None,
        )
        if incident is None:
            raise vol.Invalid("Unknown incident ID")
        cause = call.data["cause"]
        revised, _changed = revise_cause(
            incident,
            {"cause": cause, "confidence": "high", "reason_code": "user_confirmed"},
            incident.get("evidence", []),
            now=datetime.now(UTC),
            provenance="user_confirmed",
        )
        incident.update(revised)
        for device_id in incident["device_ids"]:
            device = next(
                (
                    item
                    for item in runtime["data"]["devices"]
                    if item["device_id"] == device_id
                ),
                None,
            )
            if device is not None:
                device["cause"] = cause
                device["cause_confidence"] = "high"
                _write_device_entities(runtime, device_id)
        await runtime["storage"].async_save(runtime["data"])

    async def snooze(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        device_id = _device_id(call.data["device_id"])
        device = _tracked_device(runtime, device_id)
        until = (
            datetime.now(UTC) + timedelta(minutes=call.data.get("snooze_minutes", 60))
        ).isoformat()
        device["snoozed_until"] = until
        for incident in runtime["data"]["incidents"]:
            if device_id in incident["device_ids"] and not incident.get("closed_at"):
                incident["snoozed_until"] = until
                incident["acknowledged"] = True
        await runtime["storage"].async_save(runtime["data"])

    async def resume(call: ServiceCall) -> None:
        runtime = _runtime(hass)
        device_id = _device_id(call.data["device_id"])
        device = _tracked_device(runtime, device_id)
        device["snoozed_until"] = None
        for incident in runtime["data"]["incidents"]:
            if device_id in incident["device_ids"] and not incident.get("closed_at"):
                incident["snoozed_until"] = None
        await runtime["storage"].async_save(runtime["data"])

    schemas = {
        "mark_battery_replaced": vol.Schema(
            {
                vol.Required("device_id"): DEVICE_SCHEMA,
                vol.Optional("battery_type"): str,
                vol.Optional("battery_quantity"): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=20)
                ),
                vol.Optional("brand"): str,
                vol.Optional("reason"): str,
                vol.Optional("replaced_at"): str,
            }
        ),
        "confirm_incident_cause": vol.Schema(
            {vol.Required("incident_id"): str, vol.Required("cause"): CAUSE_SCHEMA}
        ),
        "snooze_device": vol.Schema(
            {
                vol.Required("device_id"): DEVICE_SCHEMA,
                vol.Optional("snooze_minutes", default=60): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=10080)
                ),
            }
        ),
        "resume_device": vol.Schema({vol.Required("device_id"): DEVICE_SCHEMA}),
    }
    for name, handler in (
        ("mark_battery_replaced", mark_replaced),
        ("confirm_incident_cause", confirm_cause),
        ("snooze_device", snooze),
        ("resume_device", resume),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=schemas[name])


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove service actions when the global config entry unloads."""
    for name in (
        "mark_battery_replaced",
        "confirm_incident_cause",
        "snooze_device",
        "resume_device",
    ):
        hass.services.async_remove(DOMAIN, name)


def _tracked_device(runtime: dict[str, Any], device_id: str) -> dict[str, Any]:
    device = next(
        (item for item in runtime["data"]["devices"] if item["device_id"] == device_id),
        None,
    )
    if device is None:
        raise vol.Invalid("Device is not tracked by Sensor Guardian")
    return device


def _write_device_entities(runtime: dict[str, Any], device_id: str) -> None:
    for entity in runtime.get("entities", {}).get(device_id, []):
        entity.async_write_ha_state()
