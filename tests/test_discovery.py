from types import SimpleNamespace

from custom_components.sensor_guardian.discovery import rank_device_entities


def entity(
    entity_id,
    domain="sensor",
    *,
    name=None,
    unit=None,
    device_class=None,
    disabled_by=None,
):
    return SimpleNamespace(
        entity_id=entity_id,
        domain=domain,
        original_name=name,
        unique_id=entity_id,
        unit_of_measurement=unit,
        device_class=device_class,
        disabled_by=disabled_by,
    )


def test_ranks_battery_and_availability_with_disabled_signal_recommendation():
    candidate = rank_device_entities(
        "d1",
        [
            entity("sensor.door_battery", unit="%"),
            entity(
                "binary_sensor.door_connectivity",
                "binary_sensor",
                device_class="connectivity",
            ),
            entity("sensor.door_linkquality", disabled_by="integration"),
        ],
    )
    assert candidate is not None
    assert candidate.suggested_mode == "battery_and_availability"
    assert candidate.recommended_signal_entities == ("sensor.door_linkquality",)
    assert candidate.entity_refs["battery_level"] == "sensor.door_battery"


def test_event_only_candidate_with_unknown_type_is_not_forced():
    assert rank_device_entities("d2", [entity("sensor.door_temperature")]) is None


def test_battery_only_candidate_and_manual_dismissal_data_shape():
    candidate = rank_device_entities("d3", [entity("sensor.sensor_battery", unit="%")])
    assert candidate is not None
    assert candidate.suggested_mode == "battery_only"
    assert candidate.confidence == "medium"
