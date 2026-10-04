from custom_components.sensor_guardian.battery.replacement import (
    confirm_replacement,
    detect_replacement_candidate,
)
from custom_components.sensor_guardian.models import empty_store_data


def test_level_reset_requires_confirmation_and_mains_are_excluded():
    previous, current = {"level_percent": 18}, {"level_percent": 96}
    candidate = detect_replacement_candidate(
        previous, current, power_type="replaceable_battery"
    )
    assert candidate["requires_confirmation"] is True
    assert detect_replacement_candidate(previous, current, power_type="mains") is None


def test_recharge_increase_is_a_charge_not_a_replacement():
    result = detect_replacement_candidate(
        {"level_percent": 22}, {"level_percent": 90}, power_type="rechargeable"
    )
    assert result["kind"] == "charging"
    assert result["requires_confirmation"] is False


def test_confirm_replacement_closes_previous_cycle_and_is_idempotent():
    data = empty_store_data()
    data["cycles"].append(
        {
            "cycle_id": "old",
            "device_id": "d1",
            "started_at": "2024-01-01T00:00:00+00:00",
        }
    )
    first, created = confirm_replacement(
        data,
        device_id="d1",
        replaced_at="2025-01-01T00:00:00+00:00",
        battery_type="CR2450",
        battery_quantity=2,
    )
    repeated, same = confirm_replacement(
        first,
        device_id="d1",
        replaced_at="2025-01-01T00:00:00+00:00",
        battery_type="CR2450",
        battery_quantity=2,
    )
    assert first["cycles"][0]["ended_at"] == created["started_at"]
    assert len(repeated["cycles"]) == 2
    assert same["cycle_id"] == created["cycle_id"]
    assert repeated["devices"][0]["battery_quantity"] == 2


def test_mains_replacement_is_rejected():
    try:
        confirm_replacement(empty_store_data(), device_id="d1", power_type="mains")
    except ValueError as err:
        assert "Mains" in str(err)
    else:
        raise AssertionError("mains device replacement must be rejected")
