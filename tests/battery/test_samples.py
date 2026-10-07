from datetime import UTC, datetime, timedelta

from custom_components.sensor_guardian.battery.samples import (
    normalize_reading,
    should_store_sample,
)


def test_invalid_ranges_and_stale_reports_are_flagged():
    now = datetime(2025, 1, 10, tzinfo=UTC)
    sample = normalize_reading(
        timestamp=(now - timedelta(days=10)).isoformat(),
        level_percent=130,
        voltage=-1,
        now=now,
    )
    assert sample["level_percent"] is None
    assert sample["voltage"] is None
    assert {"invalid_percent", "invalid_voltage", "stale"} == set(
        sample["quality_flags"]
    )


def test_bad_timestamp_and_empty_observation_are_rejected():
    assert normalize_reading(timestamp="not-a-time", level_percent=20) is None
    assert normalize_reading(timestamp="2025-01-01T00:00:00Z") is None


def test_sample_retention_keeps_transitions_deltas_and_daily_checkpoints():
    old = {
        "timestamp": "2025-01-01T00:00:00+00:00",
        "level_percent": 80,
        "native_low": False,
    }
    assert not should_store_sample(
        old, {**old, "timestamp": "2025-01-01T01:00:00+00:00", "level_percent": 79.5}
    )
    assert should_store_sample(old, {**old, "level_percent": 78})
    assert should_store_sample(old, {**old, "native_low": True})
    assert should_store_sample(old, {**old, "timestamp": "2025-01-02T00:00:00+00:00"})


def test_first_numeric_reading_after_binding_repair_is_retained_immediately():
    old = {
        "timestamp": "2025-01-01T00:00:00+00:00",
        "level_percent": None,
        "voltage": None,
        "native_low": False,
    }
    repaired = {
        **old,
        "timestamp": "2025-01-01T01:00:00+00:00",
        "level_percent": 45,
        "native_low": None,
    }
    assert should_store_sample(old, repaired)
