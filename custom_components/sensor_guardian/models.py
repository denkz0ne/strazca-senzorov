"""Typed, JSON-serializable Sensor Guardian records."""

from __future__ import annotations

from copy import deepcopy
from typing import Literal, NotRequired, TypedDict

TrackingMode = Literal[
    "battery_and_availability", "availability_only", "battery_only", "ignored"
]
PowerType = Literal["replaceable_battery", "rechargeable", "mains", "unknown"]
Transport = Literal["zigbee", "bluetooth", "wifi", "mqtt", "other", "unknown"]


class ModelRecord(TypedDict):
    """Local battery/model catalogue record."""

    model_id: str
    manufacturer: NotRequired[str | None]
    model: NotRequired[str | None]
    model_ids: NotRequired[list[str]]
    hardware_versions: NotRequired[list[str]]
    aliases: NotRequired[list[str]]
    match_rules: NotRequired[list[dict[str, str]]]
    default_battery_type: NotRequired[str | None]
    default_battery_quantity: NotRequired[int | None]
    power_hint: NotRequired[PowerType]
    replaceable: NotRequired[bool | None]
    source: NotRequired[Literal["imported", "local"]]
    source_attribution: NotRequired[str | None]


class DeviceRecord(TypedDict):
    """Tracked Home Assistant device and its selected evidence entities."""

    device_id: str
    name: NotRequired[str]
    area_id: NotRequired[str | None]
    source_integration: NotRequired[str | None]
    config_entry_id: NotRequired[str | None]
    last_reported_at: NotRequired[str | None]
    native_available: NotRequired[bool | None]
    native_availability_state: NotRequired[str | None]
    transport: NotRequired[Transport]
    tracking_mode: NotRequired[TrackingMode]
    power_type: NotRequired[PowerType]
    entity_refs: NotRequired[dict[str, str | None]]
    signal: NotRequired[list[dict[str, str]]]
    sentinels: NotRequired[list[str]]
    battery_type: NotRequired[str | None]
    battery_quantity: NotRequired[int | None]
    replacement_history: NotRequired[list[str]]
    availability_profile_id: NotRequired[str | None]
    active_incident_ids: NotRequired[list[str]]
    user_overrides: NotRequired[dict[str, object]]


class BatterySample(TypedDict):
    """Useful sampled battery observation, not a copy of every report."""

    sample_id: str
    device_id: str
    timestamp: str
    level_percent: NotRequired[float | None]
    voltage: NotRequired[float | None]
    native_low: NotRequired[bool | None]
    source_entity_ids: NotRequired[list[str]]
    quality_flags: NotRequired[list[str]]
    provenance: NotRequired[str]


class BatteryCycle(TypedDict):
    """Battery replacement or charge cycle for one physical device."""

    cycle_id: str
    device_id: str
    started_at: str
    ended_at: NotRequired[str | None]
    battery_type: NotRequired[str | None]
    battery_quantity: NotRequired[int | None]
    brand: NotRequired[str | None]
    chemistry: NotRequired[str | None]
    initial_level: NotRequired[float | None]
    final_level: NotRequired[float | None]
    replacement_reason: NotRequired[str | None]
    confidence: NotRequired[float | None]
    provenance: NotRequired[str]


class AvailabilityProfile(TypedDict):
    """Learned report cadence and availability evidence profile."""

    profile_id: str
    device_id: str
    median_interval_seconds: NotRequired[float | None]
    p90_interval_seconds: NotRequired[float | None]
    p95_interval_seconds: NotRequired[float | None]
    jitter_seconds: NotRequired[float | None]
    explicit_availability: NotRequired[bool]
    pattern_confidence: NotRequired[float]
    updated_at: NotRequired[str | None]
    report_timestamps: NotRequired[list[str]]
    interval_count: NotRequired[int]
    pattern: NotRequired[str]


class DependencyRecord(TypedDict):
    """Shared integration, coordinator, gateway or network dependency."""

    dependency_id: str
    device_ids: NotRequired[list[str]]
    source_integration: NotRequired[str | None]
    config_entry_id: NotRequired[str | None]
    transport: NotRequired[Transport]
    provider_ref: NotRequired[str | None]


class IncidentRecord(TypedDict):
    """Availability/battery incident with evidence and notification state."""

    incident_id: str
    device_ids: list[str]
    opened_at: str
    updated_at: str
    health_state: NotRequired[str]
    cause: NotRequired[str]
    confidence: NotRequired[float | None]
    severity: NotRequired[str]
    evidence: NotRequired[list[dict[str, object]]]
    parent_incident_id: NotRequired[str | None]
    dependency_id: NotRequired[str | None]
    acknowledged: NotRequired[bool]
    snoozed_until: NotRequired[str | None]
    notification_state: NotRequired[str]


class GuardianData(TypedDict):
    """Root payload stored under Home Assistant's versioned Store envelope."""

    models: list[ModelRecord]
    devices: list[DeviceRecord]
    samples: list[BatterySample]
    cycles: list[BatteryCycle]
    availability_profiles: list[AvailabilityProfile]
    dependencies: list[DependencyRecord]
    incidents: list[IncidentRecord]
    settings: dict[str, object]


COLLECTION_FIELDS = (
    "models",
    "devices",
    "samples",
    "cycles",
    "availability_profiles",
    "dependencies",
    "incidents",
)


class StorageDataError(ValueError):
    """Raised when persisted Sensor Guardian data is malformed."""


def empty_store_data() -> GuardianData:
    """Return a fresh empty schema payload."""
    return {
        "models": [],
        "devices": [],
        "samples": [],
        "cycles": [],
        "availability_profiles": [],
        "dependencies": [],
        "incidents": [],
        "settings": {},
    }


def validate_store_data(value: object) -> GuardianData:
    """Validate persisted record containers without discarding unknown fields."""
    if not isinstance(value, dict):
        raise StorageDataError("The storage payload must be a JSON object")

    data = deepcopy(value)
    for field in COLLECTION_FIELDS:
        records = data.get(field)
        if not isinstance(records, list) or any(
            not isinstance(record, dict) for record in records
        ):
            raise StorageDataError(f"Storage field '{field}' must be a list of objects")

    if not isinstance(data.get("settings"), dict):
        raise StorageDataError("Storage field 'settings' must be an object")

    required_ids = {
        "models": "model_id",
        "devices": "device_id",
        "samples": "sample_id",
        "cycles": "cycle_id",
        "availability_profiles": "profile_id",
        "dependencies": "dependency_id",
        "incidents": "incident_id",
    }
    for collection, identifier in required_ids.items():
        for index, record in enumerate(data[collection]):
            if not isinstance(record.get(identifier), str) or not record[identifier]:
                raise StorageDataError(
                    f"Storage record {collection}[{index}] requires '{identifier}'"
                )

    return data  # type: ignore[return-value]
