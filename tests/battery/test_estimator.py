from datetime import UTC, datetime, timedelta

from custom_components.sensor_guardian.battery.estimator import estimate_remaining_life


def samples(levels, *, start="2025-01-01T00:00:00+00:00", step_days=7):
    first = datetime.fromisoformat(start)
    return [
        {
            "timestamp": (first + timedelta(days=i * step_days)).isoformat(),
            "level_percent": level,
        }
        for i, level in enumerate(levels)
    ]


def test_sparse_and_flat_traces_do_not_claim_an_eta():
    assert (
        estimate_remaining_life(samples([90, 85, 80], step_days=1), [])[
            "remaining_days_range"
        ]
        is None
    )
    flat = estimate_remaining_life(samples([80, 80, 80, 80]), [])
    assert flat["remaining_days_range"] is None
    assert flat["reason_codes"] == ["insufficient_history"]


def test_robust_trend_returns_a_range_and_explains_steep_drain():
    result = estimate_remaining_life(
        samples([90, 80, 65, 50, 35]), [], now=datetime(2025, 2, 1, tzinfo=UTC)
    )
    assert result["remaining_days_range"]["min"] < result["remaining_days_range"]["max"]
    assert "robust_median_pairwise_rate" in result["reason_codes"]
    assert result["confidence"] in {"low", "medium"}


def test_same_device_history_supplies_wide_low_confidence_range():
    cycles = [
        {
            "cycle_id": "old",
            "device_id": "d1",
            "started_at": "2024-01-01T00:00:00+00:00",
            "ended_at": "2024-07-01T00:00:00+00:00",
        },
        {
            "cycle_id": "current",
            "device_id": "d1",
            "started_at": "2025-01-01T00:00:00+00:00",
        },
    ]
    result = estimate_remaining_life(
        samples([80]), cycles, now=datetime(2025, 2, 1, tzinfo=UTC)
    )
    assert result["confidence"] == "low"
    assert "same_device_cycle_history" in result["reason_codes"]


def test_abnormal_drain_compares_against_prior_device_cycle():
    cycles = [
        {
            "cycle_id": "old",
            "device_id": "d1",
            "started_at": "2024-01-01T00:00:00+00:00",
            "ended_at": "2024-05-01T00:00:00+00:00",
            "initial_level": 100,
            "final_level": 20,
        }
    ]
    result = estimate_remaining_life(samples([90, 70, 50, 30, 10]), cycles)
    assert result["abnormal_drain"] is True
    assert "abnormal_drain_vs_prior_cycles" in result["reason_codes"]
