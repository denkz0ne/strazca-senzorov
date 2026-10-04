"""Keep one native Home Assistant notification in sync with discovery."""

from __future__ import annotations

from homeassistant.components.persistent_notification import async_create, async_dismiss
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.device_registry import EVENT_DEVICE_REGISTRY_UPDATED
from homeassistant.helpers.entity_registry import EVENT_ENTITY_REGISTRY_UPDATED

from .const import DOMAIN
from .discovery import async_discover_devices

NOTIFICATION_ID = f"{DOMAIN}_discovery"


async def async_refresh_discovery_notice(hass: HomeAssistant) -> int:
    """Refresh a single actionable notice; registry state is the durable queue."""
    runtimes = hass.data.get(DOMAIN, {})
    runtime = next(
        (
            value
            for value in runtimes.values()
            if isinstance(value, dict) and "data" in value
        ),
        None,
    )
    if runtime is None:
        async_dismiss(hass, NOTIFICATION_ID)
        return 0
    data = runtime["data"]
    tracked = {item["device_id"] for item in data.get("devices", [])}
    dismissed = set(data.get("settings", {}).get("dismissed_device_ids", []))
    candidates = await async_discover_devices(
        hass, tracked_device_ids=tracked, dismissed_device_ids=dismissed
    )
    count = len(candidates)
    runtime["discovery_pending_count"] = count
    if count:
        async_create(
            hass,
            f"Nájdených čakajúcich zariadení: **{count}**. "
            "Otvor [Strážcu senzorov](/sensor_guardian) a rozhodni, "
            "ktoré chceš sledovať.",
            title="Nové zariadenia na kontrolu",
            notification_id=NOTIFICATION_ID,
        )
    else:
        async_dismiss(hass, NOTIFICATION_ID)
    return count


def async_register_discovery_listeners(hass: HomeAssistant) -> None:
    """Recalculate after device pairing updates either HA registry."""

    @callback
    def registry_changed(_event: Event) -> None:
        hass.async_create_task(async_refresh_discovery_notice(hass))

    hass.bus.async_listen(EVENT_DEVICE_REGISTRY_UPDATED, registry_changed)
    hass.bus.async_listen(EVENT_ENTITY_REGISTRY_UPDATED, registry_changed)
