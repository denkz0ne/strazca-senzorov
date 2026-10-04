"""Tests for versioned Sensor Guardian storage."""

from __future__ import annotations

import json
from functools import partial
from pathlib import Path

import pytest
from homeassistant.helpers.storage import UnsupportedStorageVersionError

from custom_components.sensor_guardian.models import (
    StorageDataError,
    empty_store_data,
)
from custom_components.sensor_guardian.storage import GuardianStorage


async def _write_file(hass, path: str | Path, content: str) -> None:
    """Write fixture data without blocking Home Assistant's event loop."""
    path = Path(path)
    await hass.async_add_executor_job(
        partial(path.parent.mkdir, parents=True, exist_ok=True)
    )
    await hass.async_add_executor_job(path.write_text, content, "utf-8")


async def _read_bytes(hass, path: str | Path) -> bytes:
    """Read fixture bytes without blocking Home Assistant's event loop."""
    return await hass.async_add_executor_job(Path(path).read_bytes)


async def test_empty_storage_loads_defaults_without_writing(hass):
    """A fresh setup returns an empty schema and waits until there is data to save."""
    storage = GuardianStorage(hass, "entry-1")

    assert await storage.async_load() == empty_store_data()
    assert not Path(storage.path).exists()


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

    assert await GuardianStorage(hass, "entry-2").async_load() == data


async def test_malformed_payload_is_preserved_without_overwrite(hass):
    """Invalid application data raises and leaves the original store untouched."""
    storage = GuardianStorage(hass, "entry-3")
    raw_payload = {"devices": "not-a-list"}
    await _write_file(
        hass,
        storage.path,
        json.dumps(
            {
                "version": 1,
                "minor_version": 1,
                "key": storage.key,
                "data": raw_payload,
            }
        ),
    )
    original_bytes = await _read_bytes(hass, storage.path)

    with pytest.raises(StorageDataError):
        await storage.async_load()

    assert await _read_bytes(hass, storage.path) == original_bytes


async def test_minor_migration_is_idempotent_and_persisted(hass):
    """A prior minor schema upgrades once, adding missing root collections."""
    storage = GuardianStorage(hass, "entry-4")
    old_data = {"devices": []}
    await _write_file(
        hass,
        storage.path,
        json.dumps(
            {
                "version": 1,
                "minor_version": 0,
                "key": storage.key,
                "data": old_data,
            }
        ),
    )

    loaded = await storage.async_load()

    assert loaded == empty_store_data()
    assert await storage.async_load() == loaded
    raw_file = await hass.async_add_executor_job(Path(storage.path).read_text, "utf-8")
    saved = json.loads(raw_file)
    assert saved["minor_version"] == 1


async def test_future_schema_is_rejected_without_changing_file(hass):
    """A newer major version is not rewritten by this older implementation."""
    storage = GuardianStorage(hass, "entry-5")
    future_file = json.dumps(
        {
            "version": 2,
            "minor_version": 0,
            "key": storage.key,
            "data": {"new_field": "preserve me"},
        }
    )
    await _write_file(hass, storage.path, future_file)

    with pytest.raises(UnsupportedStorageVersionError):
        await storage.async_load()

    contents = await hass.async_add_executor_job(Path(storage.path).read_text, "utf-8")
    assert contents == future_file


async def test_export_includes_versions_and_payload(hass):
    """Export is portable and includes an explicit schema version."""
    storage = GuardianStorage(hass, "entry-6")
    data = empty_store_data()
    await storage.async_save(data)

    assert await storage.async_export() == {
        "version": 1,
        "minor_version": 1,
        "data": data,
    }


