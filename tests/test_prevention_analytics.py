from datetime import UTC, datetime

from custom_components.sensor_guardian.analytics import (
    dashboard,
    device_detail,
    stock_summary,
)
from custom_components.sensor_guardian.models import empty_store_data

NOW = datetime(2026, 10, 7, 20, tzinfo=UTC)


def test_dashboard_counts_unique_devices_and_separates_unknown_from_healthy():
    data = empty_store_data()
    data["devices"] = [
        {"device_id": "a", "health_state": "offline", "power_type": "mains"},
        {"device_id": "b", "health_state": "offline", "power_type": "mains"},
        {
            "device_id": "c",
            "health_state": "unknown",
            "power_type": "replaceable_battery",
            "tracking_mode": "battery_and_availability",
            "entity_refs": {},
        },
    ]
    data["incidents"] = [
        {
            "incident_id": "parent",
            "device_ids": ["a", "b"],
            "opened_at": NOW.isoformat(),
        },
        {
            "incident_id": "child",
            "device_ids": ["a"],
            "parent_incident_id": "parent",
            "opened_at": NOW.isoformat(),
        },
    ]
    result = dashboard(data, now=NOW)
    assert result["counts"]["offline"] == 2
    assert result["counts"]["coverage"] == 1
    assert len(result["alerts"]) == 1
    assert result["alerts"][0]["device_count"] == 2
    assert result["devices"][2]["battery_level"] is None


def test_detail_exposes_real_points_and_current_cycle_estimate_explanation():
    data = empty_store_data()
    data["devices"] = [
        {
            "device_id": "a",
            "name": "Door",
            "tracking_mode": "battery_only",
            "power_type": "replaceable_battery",
            "battery_estimate": {
                "remaining_days_range": None,
                "reason_codes": ["insufficient_history"],
            },
        }
    ]
    data["samples"] = [
        {
            "sample_id": "s",
            "device_id": "a",
            "timestamp": NOW.isoformat(),
            "level_percent": 45,
        }
    ]
    detail = device_detail(data, "a", days=7, now=NOW)
    assert detail["series"]["battery"][0]["value"] == 45
    assert detail["device"]["sample_count"] == 1
    assert detail["device"]["estimate"]["remaining_days_range"] is None
    assert "insufficient_history" in detail["device"]["estimate"]["reason_codes"]
    assert detail["series"]["signal"] == []


def test_stock_uses_confirmed_replacements_not_catalogue_rows_or_recharging():
    data = empty_store_data()
    data["devices"] = [
        {
            "device_id": "a",
            "power_type": "replaceable_battery",
            "battery_type": "AAA",
            "battery_quantity": 2,
        }
    ]
    data["models"] = [
        {
            "model_id": "m",
            "default_battery_type": "CR2032",
            "default_battery_quantity": 99,
        }
    ]
    data["cycles"] = [
        {
            "cycle_id": "c",
            "device_id": "a",
            "started_at": NOW.isoformat(),
            "battery_type": "AAA",
            "battery_quantity": 2,
            "provenance": "user_confirmed",
        },
    ]
    result = stock_summary(data, days=90, now=NOW)
    assert len(result) == 1
    assert result[0]["battery_type"] == "AAA"
    assert result[0]["installed_quantity"] == 2
    assert result[0]["used_quantity"] == 2


def test_replaced_battery_does_not_display_previous_cycle_as_current():
    data = empty_store_data()
    data["devices"] = [
        {
            "device_id": "a",
            "tracking_mode": "battery_only",
            "power_type": "replaceable_battery",
            "battery_replaced_at": NOW.isoformat(),
        }
    ]
    data["samples"] = [
        {
            "sample_id": "old",
            "device_id": "a",
            "timestamp": "2026-10-06T20:00:00+00:00",
            "level_percent": 5,
        }
    ]
    row = dashboard(data, now=NOW)["devices"][0]
    assert row["battery_level"] is None
    assert "battery_source_missing" in row["quality"]["missing"]


def test_available_source_is_not_complete_cadence_coverage():
    data = empty_store_data()
    data["devices"] = [
        {
            "device_id": "a",
            "tracking_mode": "availability_only",
            "health_state": "healthy",
            "health_reason": "source_available_report_pattern_learning",
        }
    ]
    row = dashboard(data, now=NOW)["devices"][0]
    assert "availability_learning" in row["quality"]["missing"]
