"""Pure schema migration helpers for Sensor Guardian data."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from .models import (
    GuardianData,
    StorageDataError,
    empty_store_data,
    validate_store_data,
)

CURRENT_MAJOR_VERSION = 1
CURRENT_MINOR_VERSION = 2


def migrate_payload(major: int, minor: int, old_data: object) -> GuardianData:
    """Upgrade known old payloads to the current normalized root schema."""
    if major != CURRENT_MAJOR_VERSION or minor > CURRENT_MINOR_VERSION:
        raise StorageDataError(
            f"Unsupported Sensor Guardian schema version {major}.{minor}"
        )
    if not isinstance(old_data, Mapping):
        raise StorageDataError("The previous storage payload must be an object")

    migrated = empty_store_data()
    migrated.update(deepcopy(dict(old_data)))
    for field, empty_value in empty_store_data().items():
        migrated.setdefault(field, empty_value)
    return validate_store_data(migrated)
