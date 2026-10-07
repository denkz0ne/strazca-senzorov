"""Sensor Guardian integration."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.event import async_call_later, async_track_time_interval

from .availability.collector import async_subscribe_reports
from .availability.profile import learn_report_profile
from .const import DOMAIN
from .storage import GuardianStorage


@callback
def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when its options change."""
    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register integration actions independently of config entry lifecycle."""
    from .discovery_notifier import async_register_discovery_listeners
    from .panel import async_register_panel
    from .services import async_register_services
    from .websocket_api import async_register_commands

    async_register_services(hass)
    async_register_commands(hass)
    async_register_discovery_listeners(hass)
    await async_register_panel(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Load the entry's validated, versioned domain data."""
    storage = GuardianStorage(hass, entry.entry_id)
    data = await storage.async_load()
    from .websocket_api import async_load_bundled_models, merge_bundled_models

    if merge_bundled_models(data, await async_load_bundled_models(hass)):
        await storage.async_save(data)
    from .sources import async_reconcile_sources

    if any(device.get("source_binding_version", 0) < 2 for device in data["devices"]):
        from homeassistant.helpers.storage import Store

        backup = Store(hass, 1, f"{DOMAIN}.pre_source_repair.{entry.entry_id}")
        if await backup.async_load() is None:
            await backup.async_save(deepcopy(data))
    if await async_reconcile_sources(hass, data):
        await storage.async_save(data)
    runtime = {
        "storage": storage,
        "data": data,
        "startup_at": datetime.now(UTC),
        "entities": {},
        "add_entities": {},
        "ready": False,
    }
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    from .battery.collector import async_subscribe_battery
    from .runtime import async_process_devices, schedule_device_processing

    def schedule_save() -> None:
        previous_cancel = runtime.get("cancel_flush")
        if previous_cancel:
            return

        @callback
        def flush(_now) -> None:
            runtime.pop("cancel_flush", None)
            hass.async_create_task(storage.async_save(data))

        runtime["cancel_flush"] = async_call_later(hass, 10, flush)

    runtime["schedule_save"] = schedule_save

    @callback
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
        if state is None or state.state in {"unknown", "unavailable"}:
            schedule_save()
            schedule_device_processing(hass, runtime)
            return
        if stamp > (device.get("last_reported_at") or ""):
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
        # Learn one sentinel per device; concurrent sensor writes are not
        # independent reports and otherwise teach microsecond intervals.
        if entity_id != device.get("report_profile_entity_id", entity_id):
            schedule_save()
            schedule_device_processing(hass, runtime)
            return
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
        schedule_device_processing(hass, runtime)

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
        task = runtime.get("_process_task")
        if task and not task.done():
            task.cancel()

    runtime["refresh_report_subscriptions"] = refresh_report_subscriptions
    runtime["refresh_battery_subscriptions"] = refresh_battery_subscriptions
    refresh_report_subscriptions()
    refresh_battery_subscriptions()

    async def reconcile_and_refresh(_event=None) -> None:
        if runtime.get("stopping") or not runtime["ready"]:
            return
        if await async_reconcile_sources(hass, data) or _event is not None:
            refresh_report_subscriptions()
            refresh_battery_subscriptions()
            schedule_save()
            schedule_device_processing(hass, runtime)

    runtime["reconcile_sources"] = reconcile_and_refresh
    if not hass.is_running:
        entry.async_on_unload(
            hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, reconcile_and_refresh
            )
        )
    entry.async_on_unload(unsubscribe_device_listeners)
    entry.async_on_unload(
        lambda: runtime.get("cancel_flush") and runtime["cancel_flush"]()
    )

    @callback
    def periodic_check(_now) -> None:
        schedule_device_processing(hass, runtime)

    entry.async_on_unload(
        async_track_time_interval(hass, periodic_check, timedelta(minutes=1))
    )
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await hass.config_entries.async_forward_entry_setups(
        entry, ["binary_sensor", "sensor"]
    )
    runtime["ready"] = True
    await async_process_devices(hass, runtime)
    from .discovery_notifier import async_refresh_discovery_notice

    await async_refresh_discovery_notice(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the entry and release integration-owned data."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime:
        runtime["stopping"] = True
        task = runtime.get("_process_task")
        if task and not task.done():
            task.cancel()
    if not await hass.config_entries.async_unload_platforms(
        entry, ["binary_sensor", "sensor"]
    ):
        if runtime:
            runtime["stopping"] = False
        return False
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime:
        await runtime["storage"].async_save(runtime["data"])
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)
    return True
