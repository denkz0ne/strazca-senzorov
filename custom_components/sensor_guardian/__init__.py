"""Sensor Guardian integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.event import async_call_later

from .availability.collector import async_subscribe_reports
from .availability.profile import learn_report_profile
from .const import DOMAIN
from .storage import GuardianStorage


def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when its options change."""
    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration from YAML (not supported)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load the entry's validated, versioned domain data."""
    storage = GuardianStorage(hass, entry.entry_id)
    data = await storage.async_load()
    runtime = {
        "storage": storage,
        "data": data,
    }
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    def record_report(
        device_id: str, entity_id: str, timestamp: datetime, state: State | None
    ) -> None:
        """Keep a bounded in-memory report history and debounce durable writes."""
        stamp = timestamp.isoformat()
        device = next(
            (item for item in data["devices"] if item["device_id"] == device_id),
            None,
        )
        if device is None:
            return
        device["last_reported_at"] = stamp
        refs = device.get("entity_refs", {})
        if (
            isinstance(refs, dict)
            and refs.get("native_availability") == entity_id
            and state is not None
        ):
            device["native_availability_state"] = state.state
            device["native_available"] = (
                True
                if state.state == "on"
                else False
                if state.state in {"off", "unavailable"}
                else None
            )
        profile = next(
            (
                item
                for item in data["availability_profiles"]
                if item["device_id"] == device_id
            ),
            None,
        )
        if profile is None:
            profile = {
                "profile_id": f"availability_{device_id}",
                "device_id": device_id,
                "report_timestamps": [],
            }
            data["availability_profiles"].append(profile)
        timestamps = profile.setdefault("report_timestamps", [])
        if not timestamps or timestamps[-1] != stamp:
            timestamps.append(stamp)
            del timestamps[:-512]
        profile.update(
            learn_report_profile(
                timestamps,
                explicit_availability=(
                    isinstance(refs, dict)
                    and refs.get("native_availability") is not None
                ),
            )
        )
        previous_cancel = runtime.get("cancel_flush")
        if previous_cancel:
            previous_cancel()

        def flush(_now) -> None:
            runtime.pop("cancel_flush", None)
            hass.async_create_task(storage.async_save(data))

        runtime["cancel_flush"] = async_call_later(hass, 10, flush)

    _entity_ids, unsubscribers = async_subscribe_reports(
        hass, data["devices"], record_report
    )
    for unsubscribe in unsubscribers:
        entry.async_on_unload(unsubscribe)
    entry.async_on_unload(
        lambda: runtime.get("cancel_flush") and runtime["cancel_flush"]()
    )
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the entry and release integration-owned data."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)
    return True
