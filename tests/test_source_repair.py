"""Coverage for automatic native-source repair without history loss."""

from copy import deepcopy

from custom_components.sensor_guardian.sources import apply_source_candidate


def candidate():
    return {
        "entity_refs": {
            "battery_level": "sensor.bateria",
            "battery_low": None,
            "voltage": None,
            "native_availability": None,
        },
        "sentinels": ["sensor.bateria"],
        "signal_entities": [],
        "recommended_signal_entities": ["sensor.lqi"],
        "source_integration": "zha",
        "config_entry_id": "zha-entry",
        "power_type": "replaceable_battery",
    }


def test_old_numeric_low_binding_is_repaired_idempotently_without_losing_user_data():
    device = {
        "device_id": "d",
        "entity_refs": {"battery_low": "sensor.bateria"},
        "tracking_mode": "battery_only",
        "battery_type": "AAA",
        "battery_quantity": 2,
        "replacement_history": ["cycle-1"],
    }
    assert apply_source_candidate(device, candidate())
    assert device["tracking_mode"] == "battery_and_availability"
    assert device["replacement_history"] == ["cycle-1"]
    assert device["battery_type"] == "AAA"
    assert not apply_source_candidate(device, candidate())


def test_explicit_user_modes_and_source_overrides_are_preserved():
    device = {
        "device_id": "d",
        "entity_refs": {"battery_low": "sensor.bateria"},
        "tracking_mode": "battery_only",
        "power_type": "rechargeable",
        "user_overrides": {
            "tracking_mode": "battery_only",
            "power_type": "rechargeable",
            "entity_refs": True,
        },
    }
    original = deepcopy(device)
    apply_source_candidate(device, candidate())
    for key in ("entity_refs", "tracking_mode", "power_type", "user_overrides"):
        assert device[key] == original[key]
