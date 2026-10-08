"""Versioned persistent storage for Sensor Guardian."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .migrations import CURRENT_MAJOR_VERSION, CURRENT_MINOR_VERSION, migrate_payload
from .models import (
    GuardianData,
    StorageDataError,
    empty_store_data,
    validate_store_data,
)


class StorageExport(TypedDict):
    """Versioned portable export payload."""

    version: int
    minor_version: int
    data: GuardianData


class GuardianStorage(Store[dict[str, Any]]):
    """Home Assistant Store wrapper with validated JSON domain records."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Create a private, atomically written store for one config entry."""
        self.entry_id = entry_id
        self.guardian_hass = hass
        super().__init__(
            hass,
            CURRENT_MAJOR_VERSION,
            f"{DOMAIN}.{entry_id}",
            private=True,
            atomic_writes=True,
            max_readable_version=CURRENT_MAJOR_VERSION,
            minor_version=CURRENT_MINOR_VERSION,
            serialize_in_event_loop=True,
        )

    async def async_load(self) -> GuardianData:
        """Load and validate the payload, returning defaults for a new install."""
        data = await super().async_load()
        if data is None:
            return empty_store_data()
        return validate_store_data(data)

    async def async_save(self, data: dict[str, Any]) -> None:
        """Validate and atomically persist a JSON-compatible payload."""
        await super().async_save(validate_store_data(data))

    async def async_export(self) -> StorageExport:
        """Return current schema and payload without internal HA storage metadata."""
        return {
            "version": CURRENT_MAJOR_VERSION,
            "minor_version": CURRENT_MINOR_VERSION,
            "data": await self.async_load(),
        }

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: object
    ) -> GuardianData:
        """Migrate an older stored schema; Store persists it after validation."""
        try:
            if old_major_version == 1 and old_minor_version < 2:
                backup = Store(
                    self.guardian_hass,
                    1,
                    f"{DOMAIN}.pre_schema_1_2.{self.entry_id}",
                    private=True,
                    atomic_writes=True,
                )
                if await backup.async_load() is None:
                    await backup.async_save(
                        {
                            "version": old_major_version,
                            "minor_version": old_minor_version,
                            "data": deepcopy(old_data),
                        }
                    )
            return migrate_payload(old_major_version, old_minor_version, old_data)
        except StorageDataError as err:
            raise StorageDataError(
                f"Cannot migrate Sensor Guardian storage: {err}"
            ) from err
