"""Sensor Guardian integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

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
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "storage": storage,
        "data": data,
    }
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the entry and release integration-owned data."""
    hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN):
        hass.data.pop(DOMAIN, None)
    return True
