"""Reviewed, idempotent device onboarding with native-source revalidation."""

from __future__ import annotations

import asyncio
import json
import secrets
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import voluptuous as vol

from .discovery import async_discover_devices
from .history import stable_id
from .sources import apply_source_candidate


def fingerprint(candidate: dict) -> str:
    return stable_id(
        json.dumps(
            {
                key: candidate.get(key)
                for key in (
                    "entity_refs",
                    "sentinels",
                    "availability_sentinels",
                    "signal_entities",
                    "recommended_signal_entities",
                    "config_entry_id",
                )
            },
            sort_keys=True,
        )
    )


def device_record(candidate: dict, choice: dict, models: list) -> dict:
    mode = choice.get("tracking_mode") or candidate["suggested_mode"]
    power = choice.get("power_type") or candidate.get("power_type", "unknown")
    if power == "mains":
        mode = "availability_only"
    if mode.startswith("battery") and not candidate.get("has_battery_data"):
        raise vol.Invalid("Zariadenie nemá použiteľný batériový zdroj")
    device = {
        key: deepcopy(candidate.get(key))
        for key in (
            "device_id",
            "name",
            "area_id",
            "manufacturer",
            "model",
        )
    }
    device.update(
        tracking_mode=mode,
        power_type=power,
        health_state="initializing",
        cause="unknown",
        cause_confidence="none",
        user_overrides={"tracking_mode": mode, "power_type": power},
    )
    apply_source_candidate(device, candidate)
    model = next(
        (
            row
            for row in models
            if str(row.get("manufacturer") or "").casefold()
            == str(device.get("manufacturer") or "").casefold()
            and str(row.get("model") or "").casefold()
            == str(device.get("model") or "").casefold()
        ),
        None,
    )
    if model and power != "mains":
        device.update(
            model_id=model["model_id"],
            battery_type=model.get("default_battery_type"),
            battery_quantity=model.get("default_battery_quantity") or 1,
        )
    if choice.get("battery_type"):
        device["battery_type"] = choice["battery_type"].strip()
        device["battery_quantity"] = choice.get("battery_quantity", 1)
        device["user_overrides"].update(
            battery_type=device["battery_type"],
            battery_quantity=device["battery_quantity"],
        )
    return device


async def preview_tracking(
    hass, runtime: dict, device_ids: list, choices: list
) -> dict:
    selected = list(dict.fromkeys(device_ids))
    candidates = {row["device_id"]: row for row in await async_discover_devices(hass)}
    tracked = {row["device_id"] for row in runtime["data"]["devices"]}
    ignored = set(runtime["data"]["settings"].get("dismissed_device_ids", []))
    options = {row["device_id"]: row for row in choices}
    if set(options) - set(selected):
        raise vol.Invalid("Voľba nepatrí vybranému zariadeniu")
    items = []
    for device_id in selected:
        candidate = candidates.get(device_id)
        if candidate is None or device_id in tracked or device_id in ignored:
            raise vol.Invalid("Kandidát sa zmenil; obnov zoznam")
        choice = options.get(device_id, {})
        device = device_record(candidate, choice, runtime["data"]["models"])
        items.append(
            {
                "device_id": device_id,
                "name": candidate["name"],
                "tracking_mode": device["tracking_mode"],
                "power_type": device["power_type"],
                "battery_type": device.get("battery_type"),
                "battery_quantity": device.get("battery_quantity"),
                "source_integration": candidate["source_integration"],
                "recommended_signal_entities": candidate["recommended_signal_entities"],
                "source_count": len(
                    [value for value in candidate["entity_refs"].values() if value]
                ),
                "fingerprint": fingerprint(candidate),
                "choice": choice,
                "enable_signals": bool(choice.get("enable_signals")),
            }
        )
    preview_id = secrets.token_hex(16)
    expires = datetime.now(UTC) + timedelta(minutes=15)
    plans = runtime.setdefault("tracking_previews", {})
    for key in list(plans):
        if plans[key]["expires_at"] < datetime.now(UTC):
            del plans[key]
    if len(plans) >= 10:
        del plans[next(iter(plans))]
    plans[preview_id] = {"items": items, "expires_at": expires}
    return {
        "preview_id": preview_id,
        "expires_at": expires.isoformat(),
        "items": [
            {
                key: value
                for key, value in item.items()
                if key not in {"fingerprint", "choice"}
            }
            for item in items
        ],
    }


async def apply_tracking(hass, runtime: dict, preview_id: str) -> dict:
    from .discovery_notifier import async_refresh_discovery_notice
    from .runtime import async_process_devices
    from .websocket_api import _add_device_entities

    async with runtime.setdefault("write_lock", asyncio.Lock()):
        receipts = runtime["data"]["settings"].setdefault("tracking_receipts", {})
        if preview_id in receipts:
            return deepcopy(receipts[preview_id])
        plan = runtime.get("tracking_previews", {}).get(preview_id)
        if plan is None or plan["expires_at"] < datetime.now(UTC):
            raise vol.Invalid("Náhľad vypršal; skontroluj zariadenia znovu")
        if runtime.get("stopping") or not runtime.get("ready"):
            raise vol.Invalid("Sledovanie sa práve inicializuje")
        if not all(
            runtime.get("add_entities", {}).get(key)
            for key in ("sensor", "binary_sensor")
        ):
            raise vol.Invalid("HA entity ešte nie sú pripravené")
        candidates = {
            row["device_id"]: row for row in await async_discover_devices(hass)
        }
        existing = {row["device_id"] for row in runtime["data"]["devices"]}
        problems = {
            item["device_id"]
            for item in plan["items"]
            if item["device_id"] not in existing
            and (
                item["device_id"] not in candidates
                or fingerprint(candidates[item["device_id"]]) != item["fingerprint"]
            )
        }
        if problems:
            return {
                "applied": False,
                "results": [
                    {
                        "device_id": item["device_id"],
                        "name": item["name"],
                        "status": "source_changed"
                        if item["device_id"] in problems
                        else "blocked",
                    }
                    for item in plan["items"]
                ],
            }
        added = []
        for item in plan["items"]:
            if item["device_id"] not in existing:
                added.append(
                    device_record(
                        candidates[item["device_id"]],
                        item["choice"],
                        runtime["data"]["models"],
                    )
                )
        data = runtime["data"]
        data["devices"].extend(added)
        result = {
            "applied": True,
            "operation_id": preview_id,
            "results": [
                {
                    "device_id": item["device_id"],
                    "name": item["name"],
                    "status": "tracked",
                }
                for item in plan["items"]
            ],
        }
        receipts[preview_id] = result
        try:
            await runtime["storage"].async_save(data)
        except Exception:
            ids = {row["device_id"] for row in added}
            data["devices"][:] = [
                row for row in data["devices"] if row["device_id"] not in ids
            ]
            receipts.pop(preview_id, None)
            raise
        for device in added:
            _add_device_entities(hass, runtime, device)
        from homeassistant.helpers import entity_registry

        registry = entity_registry.async_get(hass)
        for item in plan["items"]:
            if not item.get("enable_signals"):
                continue
            for entity_id in candidates[item["device_id"]][
                "recommended_signal_entities"
            ]:
                row = registry.async_get(entity_id)
                if row and row.device_id == item["device_id"] and row.disabled_by:
                    registry.async_update_entity(entity_id, disabled_by=None)
        runtime["refresh_report_subscriptions"]()
        runtime["refresh_battery_subscriptions"]()
        await runtime["reconcile_sources"]()
        await async_process_devices(hass, runtime)
        await async_refresh_discovery_notice(hass)
        result["entities_pending"] = any(
            not entity.entity_id
            for row in added
            for entity in runtime.get("entities", {}).get(row["device_id"], [])
        )
        while len(receipts) > 50:
            del receipts[next(iter(receipts))]
        return deepcopy(result)
