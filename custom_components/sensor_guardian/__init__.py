"""Sensor Guardian integration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .availability.collector import async_subscribe_reports
from .availability.profile import learn_report_profile
from .const import DOMAIN
from .storage import GuardianStorage


def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when its options change."""
    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register integration actions independently of config entry lifecycle."""
    from .panel import async_register_panel
    from .services import async_register_services
    from .websocket_api import async_register_commands

    async_register_services(hass)
    async_register_commands(hass)
    await async_register_panel(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load the entry's validated, versioned domain data."""
    storage = GuardianStorage(hass, entry.entry_id)
    data = await storage.async_load()
    from .websocket_api import load_bundled_models, merge_bundled_models

    if merge_bundled_models(data, load_bundled_models()):
        await storage.async_save(data)
    runtime = {
        "storage": storage,
        "data": data,
        "startup_at": datetime.now(UTC),
        "entities": {},
        "add_entities": {},
    }
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    from .battery.collector import async_subscribe_battery
    from .runtime import async_process_devices

    def schedule_save() -> None:
        previous_cancel = runtime.get("cancel_flush")
        if previous_cancel:
            previous_cancel()

        def flush(_now) -> None:
            runtime.pop("cancel_flush", None)
            hass.async_create_task(storage.async_save(data))

        runtime["cancel_flush"] = async_call_later(hass, 10, flush)

    runtime["schedule_save"] = schedule_save

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
        schedule_save()
        hass.async_create_task(async_process_devices(hass, runtime))

    def refresh_report_subscriptions() -> None:
        for unsubscribe in runtime.pop("report_unsubscribers", []):
            unsubscribe()
        _ids, runtime["report_unsubscribers"] = async_subscribe_reports(
            hass, data["devices"], record_report
        )

    def refresh_battery_subscriptions() -> None:
        for unsubscribe in runtime.pop("battery_unsubscribers", []):
            unsubscribe()
        _ids, runtime["battery_unsubscribers"] = async_subscribe_battery(hass, runtime)

    def unsubscribe_device_listeners() -> None:
        for key in ("report_unsubscribers", "battery_unsubscribers"):
            for unsubscribe in runtime.pop(key, []):
                unsubscribe()

    runtime["refresh_report_subscriptions"] = refresh_report_subscriptions
    runtime["refresh_battery_subscriptions"] = refresh_battery_subscriptions
    refresh_report_subscriptions()
    refresh_battery_subscriptions()
    entry.async_on_unload(unsubscribe_device_listeners)
    entry.async_on_unload(
        lambda: runtime.get("cancel_flush") and runtime["cancel_flush"]()
    )

    def periodic_check(_now) -> None:
        hass.async_create_task(async_process_devices(hass, runtime))

    entry.async_on_unload(
        async_track_time_interval(hass, periodic_check, timedelta(minutes=1))
    )
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await hass.config_entries.async_forward_entry_setups(
        entry, ["binary_sensor", "sensor"]
    )
    await async_process_devices(hass, runtime)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the entry and release integration-owned data."""
    if not await hass.config_entries.async_unload_platforms(
        entry, ["binary_sensor", "sensor"]
    ):
        return False
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)
    return True
