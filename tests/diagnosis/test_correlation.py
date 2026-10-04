from custom_components.sensor_guardian.diagnosis.dependencies import (
    build_dependencies,
    correlated_clusters,
)


def test_shared_gateway_outages_cluster_but_individual_outage_does_not():
    devices = [
        {
            "device_id": f"d{i}",
            "provider_ref": "coordinator-1",
            "source_integration": "zha",
        }
        for i in range(4)
    ] + [
        {
            "device_id": "solo",
            "provider_ref": "coordinator-2",
            "source_integration": "zha",
        }
    ]
    dependencies = build_dependencies(devices)
    outages = [
        {"device_id": f"d{i}", "opened_at": f"2025-01-01T00:0{i}:00+00:00"}
        for i in range(4)
    ] + [{"device_id": "solo", "opened_at": "2025-01-01T00:01:00+00:00"}]
    clusters = correlated_clusters(outages, dependencies)
    assert len(clusters) == 1
    assert clusters[0]["device_ids"] == ["d0", "d1", "d2", "d3"]


def test_separate_or_nonoverlapping_dependencies_are_not_grouped():
    devices = [
        {"device_id": "a", "provider_ref": "gateway-a"},
        {"device_id": "b", "provider_ref": "gateway-a"},
        {"device_id": "c", "provider_ref": "gateway-b"},
        {"device_id": "d", "provider_ref": "gateway-b"},
    ]
    outages = [
        {"device_id": "a", "opened_at": "2025-01-01T00:00:00+00:00"},
        {"device_id": "b", "opened_at": "2025-01-01T00:30:00+00:00"},
        {"device_id": "c", "opened_at": "2025-01-01T00:01:00+00:00"},
        {"device_id": "d", "opened_at": "2025-01-01T00:02:00+00:00"},
    ]
    assert correlated_clusters(outages, build_dependencies(devices)) == []
