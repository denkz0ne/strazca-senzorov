"""Tests for versioned Sensor Guardian storage."""

from __future__ import annotations

import pytest
from homeassistant.helpers.storage import UnsupportedStorageVersionError

from custom_components.sensor_guardian.models import (
    StorageDataError,
    empty_store_data,
)
from custom_components.sensor_guardian.storage import GuardianStorage


async def test_empty_storage_loads_defaults_without_writing(hass):
    """A fresh setup returns an empty schema and waits until there is data to save."""
    storage = GuardianStorage(hass, "entry-1")

    assert await storage.async_load() == empty_store_data()


async def test_save_and_reload_preserves_normalized_records(hass):
    """Valid domain records survive an atomic store roundtrip."""
    storage = GuardianStorage(hass, "entry-2")
    data = empty_store_data()
    data["devices"].append(
        {
            "device_id": "device-abc",
            "name": "Hall motion",
            "tracking_mode": "battery_and_availability",
            "power_type": "replaceable_battery",
        }
    )

    await storage.async_save(data)

    assert storage._atomic_writes is True
    assert storage._private is True
    assert await GuardianStorage(hass, "entry-2").async_load() == data


async def test_malformed_payload_is_preserved_without_overwrite(hass_storage, hass):
    """Invalid application data raises and leaves mocked Store data untouched."""
    storage = GuardianStorage(hass, "entry-3")
    fixture = {
        "version": 1,
        "minor_version": 1,
        "data": {"devices": "not-a-list"},
    }
    hass_storage[storage.key] = fixture.copy()

    with pytest.raises(StorageDataError):
        await storage.async_load()

    assert hass_storage[storage.key] == fixture


async def test_minor_migration_is_idempotent_and_persisted(hass_storage, hass):
    """A prior minor schema upgrades once, adding missing root collections."""
    storage = GuardianStorage(hass, "entry-4")
    hass_storage[storage.key] = {"version": 1, "minor_version": 0, "data": {}}

    loaded = await storage.async_load()

    assert loaded == empty_store_data()
    assert await storage.async_load() == loaded
    assert hass_storage[storage.key]["minor_version"] == 2
    assert hass_storage[storage.key]["data"] == loaded


async def test_future_schema_is_rejected_without_changing_file(hass_storage, hass):
    """A newer major version is not rewritten by this older implementation."""
    storage = GuardianStorage(hass, "entry-5")
    fixture = {
        "version": 2,
        "minor_version": 0,
        "data": {"new_field": "preserve me"},
    }
    hass_storage[storage.key] = fixture.copy()

    with pytest.raises(UnsupportedStorageVersionError):
        await storage.async_load()

    assert hass_storage[storage.key] == fixture


async def test_export_includes_versions_and_payload(hass):
    """Export is portable and includes an explicit schema version."""
    storage = GuardianStorage(hass, "entry-6")
    data = empty_store_data()
    await storage.async_save(data)

    assert await storage.async_export() == {
        "version": 1,
        "minor_version": 2,
        "data": data,
    }
