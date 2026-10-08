from datetime import UTC, datetime

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sensor_guardian.models import empty_store_data
from custom_components.sensor_guardian.storage import GuardianStorage


async def test_cause_confirmation_and_snooze_resume_actions(hass, hass_storage):
    data = empty_store_data()
    data["devices"].append(
        {"device_id": "d1", "tracking_mode": "availability_only", "power_type": "mains"}
    )
    data["incidents"].append(
        {
            "incident_id": "i1",
            "device_ids": ["d1"],
            "opened_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
            "cause": "unknown",
            "evidence": [],
        }
    )
    entry = MockConfigEntry(domain="sensor_guardian", data={}, unique_id="global")
    entry.add_to_hass(hass)
    storage = GuardianStorage(hass, entry.entry_id)
    hass_storage[storage.key] = {"version": 1, "minor_version": 1, "data": data}
    assert await hass.config_entries.async_setup(entry.entry_id)

    await hass.services.async_call(
        "sensor_guardian",
        "confirm_incident_cause",
        {"incident_id": "i1", "cause": "connectivity"},
        blocking=True,
    )
    await hass.services.async_call(
        "sensor_guardian",
        "snooze_device",
        {"device_id": "d1", "snooze_minutes": 30},
        blocking=True,
    )
    runtime = hass.data["sensor_guardian"][entry.entry_id]
    incident = runtime["data"]["incidents"][0]
    assert incident["confirmed_cause"] == "connectivity"
    assert datetime.fromisoformat(incident["snoozed_until"]) > datetime.now(UTC)
    assert not incident.get("acknowledged")
    assert incident["notification_state"] == "snoozed"

    await hass.services.async_call(
        "sensor_guardian", "resume_device", {"device_id": "d1"}, blocking=True
    )
    assert runtime["data"]["devices"][0]["snoozed_until"] is None
    assert runtime["data"]["incidents"][0]["snoozed_until"] is None
    await hass.config_entries.async_unload(entry.entry_id)
