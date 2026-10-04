from datetime import UTC, datetime, timedelta

from custom_components.sensor_guardian.availability.profile import learn_report_profile


def stamps(intervals):
    current = datetime(2025, 1, 1, tzinfo=UTC)
    result = [current]
    for seconds in intervals:
        current += timedelta(seconds=seconds)
        result.append(current)
    return result


def test_stable_intervals_learn_expected_windows():
    profile = learn_report_profile(stamps([300] * 12))
    assert profile["pattern"] == "periodic"
    assert profile["median_interval_seconds"] == 300
    assert profile["p95_interval_seconds"] == 300
    assert profile["pattern_confidence"] == 1


def test_jittery_and_irregular_reports_have_lower_confidence():
    stable = learn_report_profile(stamps([300] * 12))
    jittery = learn_report_profile(stamps([60, 600] * 6))
    assert jittery["pattern"] == "irregular"
    assert jittery["pattern_confidence"] < stable["pattern_confidence"]


def test_few_events_do_not_create_a_periodic_timeout():
    profile = learn_report_profile(stamps([3600]))
    assert profile["pattern"] == "learning"
    assert profile["pattern_confidence"] == 0
    event_only = learn_report_profile([])
    assert event_only["pattern"] == "event_only"
