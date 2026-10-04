import json
import threading
from pathlib import Path

import pytest

from custom_components.sensor_guardian.migration.battery_notes import (
    apply_import_preview,
    async_read_bundled_catalogue,
    build_import_preview,
    convert_battery_notes_library,
    restore_backup,
)
from custom_components.sensor_guardian.models import StorageDataError, empty_store_data

DATA = Path(__file__).parents[2] / "custom_components" / "sensor_guardian" / "data"


async def test_bundled_catalogue_read_uses_executor(hass, tmp_path, monkeypatch):
    path = tmp_path / "catalogue.json"
    path.write_text('{"models": []}', encoding="utf-8")
    loop_thread = threading.get_ident()
    read_threads = []
    original_read_text = Path.read_text

    def read_text(self, *args, **kwargs):
        read_threads.append(threading.get_ident())
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)

    assert await async_read_bundled_catalogue(hass, path) == {"models": []}
    assert read_threads
    assert read_threads[0] != loop_thread


def test_converts_snapshot_with_stable_ids_and_hints():
    source = {
        "version": 1,
        "devices": [
            {"manufacturer": "A", "model": "M", "battery_type": "CR2032"},
            {"manufacturer": "A", "model": "M", "battery_type": "CR2032"},
            {
                "manufacturer": "A",
                "model": "Watch",
                "battery_type": "Rechargeable",
                "model_match_method": "startswith",
            },
            {"manufacturer": "B", "model": "X", "battery_type": "Irreplaceable"},
        ],
    }
    first = convert_battery_notes_library(source, "abc")
    assert first == convert_battery_notes_library(source, "abc")
    assert len(first["models"]) == 3
    assert (
        next(row for row in first["models"] if row["model"] == "Watch")["power_hint"]
        == "rechargeable"
    )
    assert (
        next(row for row in first["models"] if row["model"] == "X")["power_hint"]
        == "unknown"
    )
    assert (
        next(row for row in first["models"] if row["model"] == "X")["power_hint"]
        != "mains"
    )


def test_pinned_bundle_has_provenance_and_upstream_model_variants():
    bundle = json.loads((DATA / "battery_models.json").read_text(encoding="utf-8"))
    assert bundle["source"]["commit"] == "df7c277cd43a42801aaf820329cb2ce365c1dbda"
    assert len(bundle["models"]) > 2000
    assert (DATA / "BATTERY_NOTES_LICENSE.txt").exists()
    assert len({row["model_id"] for row in bundle["models"]}) == len(bundle["models"])


def test_preview_partial_repeat_backup_and_override_safety():
    preview = build_import_preview(
        source_store={
            "devices": [
                {
                    "device_id": "dev-1",
                    "battery_last_replaced": "2025-01-01T00:00:00+00:00",
                    "battery_last_reported": "2025-01-02T00:00:00+00:00",
                    "battery_last_reported_level": 75,
                }
            ],
            "entities": [
                {
                    "entity_id": "sensor.stale",
                    "battery_last_replaced": "2024-01-01T00:00:00+00:00",
                }
            ],
        },
        source_entries=[
            {
                "data": {
                    "device_id": "dev-1",
                    "battery_type": "CR2032",
                    "battery_quantity": 1,
                }
            }
        ],
        device_ids={"dev-1"},
        entity_to_device={},
        existing_data={
            **empty_store_data(),
            "devices": [
                {
                    "device_id": "dev-1",
                    "battery_type": "CR2450",
                    "user_overrides": {"battery_type": "CR2450"},
                }
            ],
        },
        catalogue_count=3,
    )
    assert preview["matched_device_count"] == 1
    assert preview["unmatched_count"] == 1
    assert preview["cycles"][0]["provenance"] == "battery_notes_explicit"
    applied, backup = apply_import_preview(empty_store_data(), preview)
    repeated, _ = apply_import_preview(applied, preview)
    assert len(repeated["cycles"]) == 1
    assert len(repeated["samples"]) == 1
    assert len(repeated["settings"]["unmatched_import_records"]) == 1
    assert restore_backup(backup) == empty_store_data()


def test_malformed_source_or_backup_is_rejected():
    with pytest.raises(StorageDataError):
        build_import_preview(
            source_store={"devices": "bad"},
            source_entries=[],
            device_ids=set(),
            entity_to_device={},
            existing_data=empty_store_data(),
            catalogue_count=0,
        )
    with pytest.raises(StorageDataError):
        restore_backup({"version": 9, "data": {}})


def test_recorder_and_aggregated_history_keep_distinct_provenance():
    preview = build_import_preview(
        source_store=None,
        source_entries=[],
        device_ids={"dev"},
        entity_to_device={"sensor.battery_plus": "dev"},
        existing_data=empty_store_data(),
        catalogue_count=0,
        recorder_history={
            "sensor.battery_plus": [
                {"state": "80", "last_updated": "2025-01-01T00:00:00+00:00"}
            ]
        },
        recorder_statistics={
            "sensor.battery_plus": [
                {"mean": 79.0, "start": "2025-01-01T00:00:00+00:00"}
            ]
        },
    )
    assert {sample["provenance"] for sample in preview["samples"]} == {
        "recorder_exact",
        "statistics_inferred",
    }
