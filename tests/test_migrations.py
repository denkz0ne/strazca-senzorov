"""Pure schema migration coverage."""

import pytest

from custom_components.sensor_guardian.migrations import migrate_payload
from custom_components.sensor_guardian.models import (
    StorageDataError,
    empty_store_data,
)


def test_minor_migration_is_idempotent():
    """Applying the v1.0 upgrader to its own output preserves the data."""
    first = migrate_payload(1, 0, {"devices": []})

    assert first == empty_store_data()
    assert migrate_payload(1, 0, first) == first


def test_migration_preserves_unknown_extension_fields():
    """Local extension fields survive normalization for forward-safe roundtrips."""
    payload = {"devices": [], "custom_extension": {"kept": True}}

    assert migrate_payload(1, 0, payload)["custom_extension"] == {"kept": True}


def test_migration_rejects_future_minor_schema():
    """A downgrade does not silently discard newer minor-version data."""
    with pytest.raises(StorageDataError, match="Unsupported Sensor Guardian schema"):
        migrate_payload(1, 2, empty_store_data())
