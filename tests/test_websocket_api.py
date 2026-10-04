import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sensor_guardian.models import empty_store_data
from custom_components.sensor_guardian.storage import GuardianStorage
from custom_components.sensor_guardian.websocket_api import (
    add_local_model,
    apply_battery_assignment,
    get_section_page,
    merge_bundled_models,
)


def test_overview_is_compact_and_preserves_unknown_cause():
    result = get_section_page(
        {
            "devices": [
                {
                    "device_id": "d1",
                    "name": "Door",
                    "health_state": "offline",
                    "cause": "unknown",
                    "battery_level": 31,
                    "signal": [{"entity_id": "sensor.secret_rssi", "value": -90}],
                    "entity_refs": {"battery_level": "sensor.door_battery"},
                }
            ]
        },
        "overview",
    )

    assert result["items"] == [
        {
            "device_id": "d1",
            "name": "Door",
            "health_state": "offline",
            "cause": "unknown",
        }
    ]
    assert result["total"] == 1


def test_pagination_and_search_are_bounded():
    data = {"devices": [{"device_id": f"d{n}", "name": f"Room {n}"} for n in range(8)]}
    page = get_section_page(data, "devices", offset=2, limit=3, query="room")

    assert [item["device_id"] for item in page["items"]] == ["d2", "d3", "d4"]
    assert page["offset"] == 2
    assert page["limit"] == 3
    assert page["total"] == 8
    assert page["has_more"] is True

    with pytest.raises(vol.Invalid):
        get_section_page(data, "devices", offset=0, limit=101)


def test_discovery_filter_choices_cover_records_beyond_current_page():
    page = get_section_page(
        {
            "devices": [],
        },
        "discovery",
        limit=1,
        candidates=[
            {
                "device_id": "d1",
                "source_integration": "zha",
                "area_name": "Kitchen",
                "availability_state": "on",
            },
            {
                "device_id": "d2",
                "source_integration": "esphome",
                "area_name": "Garden",
                "availability_state": "unavailable",
            },
        ],
    )

    assert [item["device_id"] for item in page["items"]] == ["d1"]
    assert page["filters"] == {
        "integrations": ["esphome", "zha"],
        "areas": ["Garden", "Kitchen"],
        "availability": ["on", "unavailable"],
    }


def test_battery_page_keeps_cycles_separate_from_model_catalogue():
    page = get_section_page(
        {
            "models": [
                {"model_id": "m1", "model": "D1", "default_battery_type": "CR2032"}
            ],
            "cycles": [{"cycle_id": "c1", "device_id": "d1"}],
        },
        "batteries",
    )
    assert page["items"][0]["model_id"] == "m1"
    assert page["related"]["cycle_count"] == 1


def test_battery_page_includes_current_level_and_name_identifier_without_inventing_it():
    page = get_section_page(
        {
            "devices": [
                {
                    "device_id": "opaque1",
                    "name": "zbt05-kupelna",
                    "tracking_mode": "battery_only",
                    "battery_type": "CR2450",
                    "battery_quantity": 1,
                    "battery_estimate": {},
                    "last_replaced_at": "2026-09-01",
                    "battery_level": 72,
                },
                {
                    "device_id": "opaque2",
                    "name": "Hall sensor",
                    "tracking_mode": "battery_only",
                    "battery_type": "CR2032",
                    "battery_quantity": 2,
                },
            ],
            "models": [],
            "samples": [],
            "cycles": [],
        },
        "batteries",
    )
    rows = page["related"]["tracked_devices"]
    assert rows[0]["identifier"] == "ZBT05"
    assert rows[0]["battery_level"] == 72
    assert rows[1]["identifier"] == ""
    assert rows[1].get("battery_level") is None


def test_settings_page_does_not_return_internal_runtime_data():
    page = get_section_page(
        {
            "settings": {
                "startup_grace_minutes": 15,
                "api_token": "never-expose",
                "unmatched_import_records": [{"source": "private device info"}],
            }
        },
        "settings",
    )
    assert page["settings"] == {"startup_grace_minutes": 15}
    assert page["migration"]["unmatched_import_count"] == 1


def test_bundled_models_seed_empty_storage_without_overwriting_local_edits():
    data = {"models": [{"model_id": "m1", "model": "User edited", "source": "local"}]}

    inserted = merge_bundled_models(
        data,
        [
            {"model_id": "m1", "model": "Upstream"},
            {"model_id": "m2", "model": "Imported"},
        ],
    )

    assert inserted == 1
    assert data["models"] == [
        {"model_id": "m1", "model": "User edited", "source": "local"},
        {"model_id": "m2", "model": "Imported"},
    ]


def test_bundled_catalogue_is_loaded_from_the_local_converted_snapshot():
    from custom_components.sensor_guardian.websocket_api import load_bundled_models

    models = load_bundled_models()
    assert len(models) == 2330
    assert all(model.get("source") == "imported" for model in models)


async def test_bundled_catalogue_is_read_in_the_executor(hass, monkeypatch):
    import threading

    from custom_components.sensor_guardian import websocket_api

    loop_thread = threading.get_ident()
    read_threads = []

    def read_catalogue():
        read_threads.append(threading.get_ident())
        return []

    monkeypatch.setattr(websocket_api, "load_bundled_models", read_catalogue)

    assert await websocket_api.async_load_bundled_models(hass) == []
    assert read_threads
    assert read_threads[0] != loop_thread


def test_local_model_addition_is_unique_and_keeps_user_battery_choice():
    data = {"models": []}
    model = add_local_model(
        data,
        manufacturer="Example",
        model="New sensor",
        battery_type="CR2450",
        battery_quantity=2,
        power_type="replaceable_battery",
    )
    assert model["source"] == "local"
    assert model["default_battery_type"] == "CR2450"
    assert model["default_battery_quantity"] == 2
    with pytest.raises(vol.Invalid):
        add_local_model(
            data,
            manufacturer="Example",
            model="New sensor",
            battery_type="CR2450",
            battery_quantity=2,
            power_type="replaceable_battery",
        )


def test_battery_assignment_changes_only_the_selected_device():
    device = {
        "device_id": "d1",
        "tracking_mode": "battery_and_availability",
        "power_type": "unknown",
    }
    apply_battery_assignment(
        device,
        battery_type="CR2032",
        battery_quantity=1,
        power_type="replaceable_battery",
    )
    assert device["battery_type"] == "CR2032"
    assert device["battery_quantity"] == 1
    assert device["power_type"] == "replaceable_battery"


async def test_authenticated_websocket_returns_only_curated_overview(
    hass, hass_storage, hass_ws_client
):
    data = empty_store_data()
    data["devices"].append(
        {
            "device_id": "d1",
            "name": "Entry sensor",
            "tracking_mode": "availability_only",
            "power_type": "mains",
            "health_state": "offline",
            "cause": "unknown",
            "signal": [{"entity_id": "sensor.private_rssi", "value": -91}],
            "entity_refs": {"native_availability": "binary_sensor.entry_online"},
        }
    )
    entry = MockConfigEntry(domain="sensor_guardian", data={}, unique_id="global")
    entry.add_to_hass(hass)
    storage = GuardianStorage(hass, entry.entry_id)
    hass_storage[storage.key] = {"version": 1, "minor_version": 1, "data": data}
    assert await hass.config_entries.async_setup(entry.entry_id)

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": "sensor_guardian/get_data", "section": "overview"}
    )
    response = await client.receive_json()
    assert response["success"] is True
    item = response["result"]["items"][0]
    assert item["cause"] == "unknown"
    assert "signal" not in item
    assert "entity_refs" not in item
    await client.close()
    await hass.config_entries.async_unload(entry.entry_id)


async def test_panel_can_track_a_candidate_and_attach_runtime_entities(
    hass, hass_storage, hass_ws_client
):
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    from custom_components.sensor_guardian.events import BATTERY_ATTENTION_EVENT

    source_entry = MockConfigEntry(domain="sensor_source", data={})
    source_entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=source_entry.entry_id,
        identifiers={("sensor_source", "device-1")},
        manufacturer="Example",
        name="Door sensor",
        model="D1",
    )
    source = er.async_get(hass).async_get_or_create(
        "sensor",
        "sensor_source",
        "battery-level",
        config_entry=source_entry,
        device_id=device.id,
        original_name="Battery level",
        unit_of_measurement="%",
    )
    hass.states.async_set(source.entity_id, "31", {"unit_of_measurement": "%"})
    entry = MockConfigEntry(domain="sensor_guardian", data={}, unique_id="global")
    entry.add_to_hass(hass)
    storage = GuardianStorage(hass, entry.entry_id)
    hass_storage[storage.key] = {
        "version": 1,
        "minor_version": 1,
        "data": empty_store_data(),
    }
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_ws_client()
    events = []
    hass.bus.async_listen(
        BATTERY_ATTENTION_EVENT, lambda event: events.append(event.data)
    )
    await client.send_json_auto_id(
        {
            "type": "sensor_guardian/track_device",
            "device_id": device.id,
            "tracking_mode": "battery_only",
            "power_type": "replaceable_battery",
        }
    )
    response = await client.receive_json()
    assert response["success"] is True
    runtime = hass.data["sensor_guardian"][entry.entry_id]
    assert runtime["data"]["devices"][0]["device_id"] == device.id
    # Platform callbacks enqueue entity registration on the HA loop after the
    # WebSocket command returns; wait for the registry, not just the command.
    import asyncio

    for _ in range(50):
        await hass.async_block_till_done()
        guardian_entities = er.async_entries_for_config_entry(
            er.async_get(hass), entry.entry_id
        )
        if len(guardian_entities) == 3:
            break
        await asyncio.sleep(0.02)
    assert len(guardian_entities) == 3

    hass.states.async_set(source.entity_id, "10", {"unit_of_measurement": "%"})
    await hass.async_block_till_done()
    assert runtime["data"]["devices"][0]["battery_attention"] is True
    assert len(events) == 1
    await client.close()
    await hass.config_entries.async_unload(entry.entry_id)
