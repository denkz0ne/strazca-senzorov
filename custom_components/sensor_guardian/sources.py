"""Reconcile native evidence bindings while preserving user history."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry

from .discovery import async_discover_devices

BINDING_VERSION = 2


def apply_source_candidate(device: dict[str, Any], candidate: dict[str, Any]) -> bool:
    """Repair source selection; never recreate device IDs or battery cycles."""
    before = deepcopy(device)
    refs = candidate["entity_refs"]
    old_refs = device.get("entity_refs", {})
    overrides = device.get("user_overrides", {})
    if not isinstance(overrides, dict):
        overrides = {}
    legacy = device.get("source_binding_version", 0) < BINDING_VERSION
    broken_low = old_refs.get("battery_low") == refs.get("battery_level") and bool(
        refs.get("battery_level")
    )
    derived_source = device.get("source_integration") in {
        "battery_notes",
        "sensor_guardian",
    }
    if not overrides.get("entity_refs"):
        device["entity_refs"] = dict(refs)
        device["sentinels"] = list(candidate["sentinels"])
        device["signal"] = [
            {
                "entity_id": entity_id,
                "kind": "rssi" if "rssi" in entity_id.lower() else "lqi",
            }
            for entity_id in candidate["signal_entities"]
        ]
        device["report_profile_entity_id"] = refs.get("battery_level") or next(
            iter(candidate["sentinels"]), None
        )
    device["recommended_signal_entities"] = candidate["recommended_signal_entities"]
    device["source_integration"] = candidate["source_integration"]
    device["config_entry_id"] = candidate.get("config_entry_id")
    device["transport"] = {
        "zha": "zigbee",
        "mqtt": "mqtt",
        "esphome": "wifi",
        "bluetooth": "bluetooth",
    }.get(candidate["source_integration"], "unknown")
    device["source_status"] = "native"
    if legacy and not overrides.get("tracking_mode"):
        if (broken_low or derived_source) and device.get(
            "tracking_mode"
        ) == "battery_only":
            device["tracking_mode"] = "battery_and_availability"
        elif (
            old_refs.get("voltage")
            and not old_refs.get("battery_level")
            and not old_refs.get("battery_low")
            and candidate["power_type"] == "mains"
        ):
            device["tracking_mode"] = "availability_only"
            if not overrides.get("power_type"):
                device["power_type"] = "mains"
    device["source_binding_version"] = BINDING_VERSION
    return device != before


async def async_reconcile_sources(hass: HomeAssistant, data: dict[str, Any]) -> bool:
    """Repair tracked bindings using one indexed native registry discovery pass."""
    if not data["devices"]:
        return False
    candidates = {
        candidate["device_id"]: candidate
        for candidate in await async_discover_devices(hass)
    }
    changed = False
    for device in data["devices"]:
        candidate = candidates.get(device["device_id"])
        if candidate is None:
            # Preserve configured refs while a provider is temporarily not ready.
            continue
        old_profile_entity = device.get("report_profile_entity_id")
        if apply_source_candidate(device, candidate):
            changed = True
            if old_profile_entity != device.get("report_profile_entity_id"):
                data["availability_profiles"][:] = [
                    profile
                    for profile in data["availability_profiles"]
                    if profile["device_id"] != device["device_id"]
                ]
        registry_device = device_registry.async_get(hass).async_get(device["device_id"])
        if registry_device:
            device["name"] = registry_device.name_by_user or registry_device.name
            device["area_id"] = registry_device.area_id
    return changed
