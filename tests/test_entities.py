from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sensor_guardian.events import BATTERY_ATTENTION_EVENT
from custom_components.sensor_guardian.models import empty_store_data
from custom_components.sensor_guardian.storage import GuardianStorage


async def test_minimal_entities_link_to_source_device_and_unload(hass, hass_storage):
    source_entry = MockConfigEntry(domain="sensor_source", data={})
    source_entry.add_to_hass(hass)
    source_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=source_entry.entry_id,
        identifiers={("sensor_source", "device-1")},
        manufacturer="Example",
        name="Door sensor",
        model="D1",
    )
    source_entity = er.async_get(hass).async_get_or_create(
        "sensor",
        "sensor_source",
        "battery-1",
        config_entry=source_entry,
        device_id=source_device.id,
        original_name="Battery",
        unit_of_measurement="%",
    )
    hass.states.async_set(source_entity.entity_id, "10", {"unit_of_measurement": "%"})

    data = empty_store_data()
    data["devices"].append(
        {
            "device_id": source_device.id,
            "name": "Door sensor",
            "tracking_mode": "battery_only",
            "power_type": "replaceable_battery",
            "entity_refs": {"battery_level": source_entity.entity_id},
        }
    )
    entry = MockConfigEntry(domain="sensor_guardian", data={}, unique_id="global")
    entry.add_to_hass(hass)
    storage = GuardianStorage(hass, entry.entry_id)
    hass_storage[storage.key] = {"version": 1, "minor_version": 1, "data": data}
    battery_events = []
    hass.bus.async_listen(
        BATTERY_ATTENTION_EVENT, lambda event: battery_events.append(event.data)
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entries = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert len(entries) == 3
    assert {item.domain for item in entries} == {"binary_sensor", "sensor"}
    assert all(item.device_id == source_device.id for item in entries)
    battery_attention = next(
        item for item in entries if item.unique_id.endswith("_battery_attention")
    )
    assert hass.states.get(battery_attention.entity_id).state == "on"
    assert len(battery_events) == 1
    assert battery_events[0]["battery_level"] == 10

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert hass.services.has_service("sensor_guardian", "mark_battery_replaced")
    entries_after_unload = er.async_entries_for_config_entry(
        er.async_get(hass), entry.entry_id
    )
    assert len(entries_after_unload) == 3
    assert all(hass.states.get(item.entity_id) is None for item in entries_after_unload)


async def test_problem_status_and_incident_event_transition_are_deduplicated(
    hass, hass_storage
):
    data = empty_store_data()
    data["devices"].append(
        {
            "device_id": "device-offline",
            "name": "Offline device",
            "tracking_mode": "availability_only",
            "power_type": "mains",
            "native_available": False,
        }
    )
    entry = MockConfigEntry(domain="sensor_guardian", data={}, unique_id="global")
    entry.add_to_hass(hass)
    storage = GuardianStorage(hass, entry.entry_id)
    hass_storage[storage.key] = {"version": 1, "minor_version": 1, "data": data}
    events = []
    hass.bus.async_listen(
        "sensor_guardian_incident", lambda event: events.append(event.data)
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    runtime = hass.data["sensor_guardian"][entry.entry_id]
    assert runtime["data"]["devices"][0]["health_state"] == "offline"
    assert len(events) == 1
    await hass.services.async_call(
        "sensor_guardian",
        "resume_device",
        {"device_id": "device-offline"},
        blocking=True,
    )
    from custom_components.sensor_guardian.runtime import async_process_devices

    await async_process_devices(hass, runtime)
    assert len(events) == 1
    assert events[0]["version"] == 1
    assert events[0]["cause"] == "unknown"
    assert "entity_attributes" not in events[0]

    assert await hass.config_entries.async_unload(entry.entry_id)
