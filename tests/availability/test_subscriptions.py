import pytest

from custom_components.sensor_guardian.availability.collector import (
    async_subscribe_reports,
    selected_sentinels,
)


def test_subscription_allow_list_contains_only_chosen_availability_entities():
    devices = [
        {
            "device_id": "d1",
            "sentinels": ["binary_sensor.motion"],
            "entity_refs": {
                "native_availability": "binary_sensor.online",
                "battery_level": "sensor.battery",
            },
        },
        {"device_id": "d2", "sentinels": []},
    ]
    assert selected_sentinels(devices) == {
        "d1": {"binary_sensor.motion", "binary_sensor.online"}
    }


@pytest.mark.usefixtures("enable_custom_integrations_for_tests")
async def test_state_change_and_report_events_are_filtered_and_unsubscribed(hass):
    hass.states.async_set("binary_sensor.selected", "off")
    hass.states.async_set("sensor.noisy", "1")
    observed = []
    entity_ids, unsubs = async_subscribe_reports(
        hass,
        [{"device_id": "d1", "sentinels": ["binary_sensor.selected"]}],
        lambda device_id, entity_id, stamp, _state: observed.append(
            (device_id, entity_id, stamp)
        ),
    )
    assert entity_ids == ["binary_sensor.selected"]
    assert len(observed) == 1  # current state is seeded after filtered subscriptions
    hass.states.async_set("sensor.noisy", "2")
    hass.states.async_set("binary_sensor.selected", "on")
    await hass.async_block_till_done()
    assert all(item[1] == "binary_sensor.selected" for item in observed)
    count = len(observed)
    for unsubscribe in unsubs:
        unsubscribe()
    hass.states.async_set("binary_sensor.selected", "off")
    await hass.async_block_till_done()
    assert len(observed) == count
