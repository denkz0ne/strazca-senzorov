from datetime import UTC, datetime

from custom_components.sensor_guardian.events import (
    INCIDENT_EVENT,
    RECOVERED_EVENT,
    event_for_transition,
    event_payload,
)


def test_event_contract_is_versioned_compact_and_transition_only():
    assert event_for_transition("healthy", "offline") == INCIDENT_EVENT
    assert event_for_transition("offline", "stale") is None
    assert event_for_transition("offline", "healthy") == RECOVERED_EVENT
    assert event_for_transition("unknown", "unknown") is None
    payload = event_payload(
        {
            "device_id": "d1",
            "name": "Door",
            "health_state": "offline",
            "cause": "unknown",
            "unrelated": "secret",
        },
        timestamp=datetime(2025, 1, 1, tzinfo=UTC),
    )
    assert payload["version"] == 1
    assert payload["device_name"] == "Door"
    assert "unrelated" not in payload


async def test_battery_replaced_service_fires_one_compact_event(hass, hass_storage):
    from homeassistant.core import Event
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.sensor_guardian.models import empty_store_data
    from custom_components.sensor_guardian.storage import GuardianStorage

    data = empty_store_data()
    data["devices"].append(
        {
            "device_id": "d1",
            "tracking_mode": "battery_only",
            "power_type": "replaceable_battery",
            "battery_type": "CR2032",
        }
    )
    entry = MockConfigEntry(domain="sensor_guardian", data={}, unique_id="global")
    entry.add_to_hass(hass)
    storage = GuardianStorage(hass, entry.entry_id)
    hass_storage[storage.key] = {"version": 1, "minor_version": 1, "data": data}
    seen: list[Event] = []
    hass.bus.async_listen("sensor_guardian_battery_replaced", seen.append)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.services.async_call(
        "sensor_guardian",
        "mark_battery_replaced",
        {
            "device_id": "d1",
            "battery_type": "CR2450",
            "battery_quantity": 2,
            "replaced_at": "2025-01-01T00:00:00+00:00",
        },
        blocking=True,
    )
    assert len(seen) == 1
    assert seen[0].data["version"] == 1
    assert seen[0].data["battery_type"] == "CR2450"
    assert (
        hass.data["sensor_guardian"][entry.entry_id]["data"]["devices"][0][
            "battery_quantity"
        ]
        == 2
    )
    await hass.config_entries.async_unload(entry.entry_id)
