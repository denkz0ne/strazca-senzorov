"""Admin-only prevention UI contracts and durable operator commands."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.persistent_notification import async_dismiss
from homeassistant.helpers import area_registry, device_registry

from . import analytics
from .const import DOMAIN, VERSION
from .discovery import async_discover_devices, display_identifier
from .history import number, stable_id
from .onboarding import apply_tracking, preview_tracking

DEFAULTS = {
    "low_battery_threshold": 20,
    "startup_grace_minutes": 5,
    "recovery_stability_minutes": 2,
    "replacement_warning_days": 14,
    "prevention_horizon_days": 14,
    "retention_days": 365,
    "notifications_enabled": True,
    "quiet_start": "",
    "quiet_end": "",
    "notification_repeat_minutes": 0,
}
MODE = vol.In({"battery_and_availability", "battery_only", "availability_only"})
POWER = vol.In({"replaceable_battery", "rechargeable", "mains", "unknown"})
TIME = vol.Any("", vol.Match(r"^(?:[01]\d|2[0-3]):[0-5]\d$"))
RULES = {
    vol.Optional("low_battery_threshold"): vol.All(
        vol.Coerce(float), vol.Range(min=1, max=100)
    ),
    vol.Optional("startup_grace_minutes"): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=1440)
    ),
    vol.Optional("recovery_stability_minutes"): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=60)
    ),
    vol.Optional("replacement_warning_days"): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=90)
    ),
    vol.Optional("prevention_horizon_days"): vol.All(
        vol.Coerce(int), vol.Range(min=1, max=180)
    ),
    vol.Optional("retention_days"): vol.All(
        vol.Coerce(int), vol.Range(min=30, max=730)
    ),
    vol.Optional("notifications_enabled"): bool,
    vol.Optional("quiet_start"): TIME,
    vol.Optional("quiet_end"): TIME,
    vol.Optional("notification_repeat_minutes"): vol.All(
        vol.Coerce(int), vol.Range(min=0, max=10080)
    ),
}
DEVICE_RULES = {
    key: value
    for key, value in RULES.items()
    if str(key) not in {"retention_days", "quiet_start", "quiet_end"}
}
DEVICE_RULES[vol.Optional("criticality")] = vol.In({"normal", "critical"})


def meta(hass, runtime):
    return {
        "backend_version": VERSION,
        "schema_version": "1.2",
        "started_at": runtime["startup_at"].isoformat(),
        "evaluated_at": runtime.get("last_evaluated_at"),
        "collection_state": "running" if runtime.get("ready") else "starting",
        "time_zone": hass.config.time_zone,
    }


def context(hass, runtime):
    """Enrich native metadata/current values without exporting HA attributes."""
    data = {**runtime["data"], "devices": []}
    devices, areas = device_registry.async_get(hass), area_registry.async_get(hass)
    live = {}
    for original in runtime["data"]["devices"]:
        device = {**original}
        registered = devices.async_get(device["device_id"])
        if registered:
            device.update(
                name=registered.name_by_user or registered.name or device.get("name"),
                area_id=registered.area_id,
            )
        area = (
            areas.async_get_area(device.get("area_id"))
            if device.get("area_id")
            else None
        )
        device["area_name"] = area.name if area else None
        device["identifier"] = display_identifier(device.get("name"))
        data["devices"].append(device)
        readings = live[device["device_id"]] = {}
        for kind, entity_id in device.get("entity_refs", {}).items():
            state = hass.states.get(entity_id) if entity_id else None
            if state is None or state.state in {"unknown", "unavailable"}:
                continue
            if kind in {"battery_level", "voltage"}:
                value = number(state.state)
                if value is not None:
                    readings[kind] = (
                        value / 1000
                        if kind == "voltage"
                        and state.attributes.get("unit_of_measurement") == "mV"
                        else value
                    )
            elif kind == "battery_low" and state.state in {"on", "off"}:
                readings[kind] = state.state == "on"
        readings["signal_values"] = []
        for signal in device.get("signal", []):
            state = hass.states.get(signal["entity_id"])
            value = number(state.state) if state else None
            if value is not None:
                readings["signal_values"].append(
                    {"kind": signal.get("kind"), "value": value}
                )
    return data, live


def page(rows, msg):
    offset, limit = msg.get("offset", 0), msg.get("limit", 50)
    return {
        "items": rows[offset : offset + limit],
        "total": len(rows),
        "has_more": offset + limit < len(rows),
        "offset": offset,
    }


def register_prevention_commands(hass):
    from .websocket_api import _add_device_entities, _get_runtime, _require_admin

    def command(name, fields):
        return websocket_api.websocket_command(
            {vol.Required("type"): f"{DOMAIN}/{name}", **fields}
        )

    paging = {
        vol.Optional("offset", default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=1000000)
        ),
        vol.Optional("limit", default=50): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=100)
        ),
        vol.Optional("query", default=""): vol.All(str, vol.Length(max=200)),
    }

    @command("get_dashboard", {})
    @websocket_api.async_response
    async def get_dashboard(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        data, live = context(hass, runtime)
        result = analytics.dashboard(data, live=live)
        result.pop("devices", None)
        ignored = set(data["settings"].get("dismissed_device_ids", []))
        candidates = await async_discover_devices(
            hass,
            tracked_device_ids={row["device_id"] for row in data["devices"]},
            dismissed_device_ids=ignored,
        )
        result.update(meta=meta(hass, runtime), pending_count=len(candidates))
        connection.send_result(msg["id"], result)

    @command(
        "get_devices",
        {
            **paging,
            vol.Optional("filter", default="all"): vol.In(
                {
                    "all",
                    "offline",
                    "attention",
                    "prevention",
                    "coverage",
                    "battery",
                    "paused",
                }
            ),
            vol.Optional("area", default=""): str,
            vol.Optional("integration", default=""): str,
            vol.Optional("power", default=""): str,
            vol.Optional("sort", default="risk"): vol.In({"risk", "name", "battery"}),
        },
    )
    @websocket_api.async_response
    async def get_devices(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        data, live = context(hass, runtime)
        now, index = datetime.now(UTC), analytics.evidence_index(data)
        rows = [
            analytics.device_snapshot(
                data, device, now=now, index=index, live=live.get(device["device_id"])
            )
            for device in data["devices"]
        ]
        facets = {
            "areas": sorted({row["area_name"] or "Bez oblasti" for row in rows}),
            "integrations": sorted(
                {row["source_integration"] or "unknown" for row in rows}
            ),
        }
        filtered = []
        for row in rows:
            text = " ".join(
                str(row.get(key) or "")
                for key in (
                    "name",
                    "area_name",
                    "source_integration",
                    "battery_type",
                    "identifier",
                )
            )
            selected = msg["filter"]
            allowed = (
                selected == "all"
                or (selected == "offline" and row["health_state"] == "offline")
                or (selected == "attention" and row["risk"]["priority"] <= 1)
                or (selected == "prevention" and row["risk"]["level"] == "watch")
                or (selected == "coverage" and row["quality"]["state"] != "complete")
                or (
                    selected == "battery"
                    and row["power_type"] != "mains"
                    and row["tracking_mode"] != "ignored"
                )
                or (selected == "paused" and row["tracking_mode"] == "ignored")
            )
            if (
                allowed
                and msg["query"].casefold() in text.casefold()
                and (
                    not msg["area"]
                    or (row["area_name"] or "Bez oblasti") == msg["area"]
                )
                and (
                    not msg["integration"]
                    or row["source_integration"] == msg["integration"]
                )
                and (not msg["power"] or row["power_type"] == msg["power"])
            ):
                row["identifier"] = display_identifier(row["name"])
                filtered.append(row)
        filtered.sort(
            key=lambda row: (
                row["risk"]["priority"]
                if msg["sort"] == "risk"
                else row["battery_level"] is None
                if msg["sort"] == "battery"
                else 0,
                row["battery_level"] or 0
                if msg["sort"] == "battery"
                else (row["name"] or "").casefold(),
            )
        )
        connection.send_result(
            msg["id"],
            {**page(filtered, msg), "filters": facets, "meta": meta(hass, runtime)},
        )

    @command(
        "get_device_detail",
        {
            vol.Required("device_id"): str,
            vol.Optional("days", default=30): vol.In({7, 30, 90}),
        },
    )
    @websocket_api.async_response
    async def get_detail(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        data, live = context(hass, runtime)
        try:
            result = analytics.device_detail(
                data,
                msg["device_id"],
                days=msg["days"],
                live=live.get(msg["device_id"]),
            )
        except ValueError as error:
            raise vol.Invalid(str(error)) from error
        result.update(
            meta=meta(hass, runtime),
            inherited_rules=deepcopy(DEFAULTS | data["settings"]),
        )
        # Only native sources on this original device may be selected as overrides.
        from homeassistant.helpers import entity_registry

        result["source_choices"] = [
            {
                "entity_id": row.entity_id,
                "name": row.name or row.original_name or row.entity_id,
                "domain": row.domain,
                "disabled": bool(row.disabled_by),
            }
            for row in entity_registry.async_get(hass).entities.values()
            if row.device_id == msg["device_id"]
            and row.platform not in {"battery_notes", DOMAIN}
            and row.domain
            in {"sensor", "binary_sensor", "switch", "light", "climate", "fan", "cover"}
        ]
        connection.send_result(msg["id"], result)

    @command("get_alerts", {**paging, vol.Optional("closed", default=False): bool})
    @websocket_api.async_response
    async def get_alerts(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        data, _live = context(hass, runtime)
        rows = [
            row
            for row in analytics.alert_rows(data, include_closed=msg["closed"])
            if msg["query"].casefold() in " ".join(row["names"]).casefold()
        ]
        connection.send_result(
            msg["id"], {**page(rows, msg), "meta": meta(hass, runtime)}
        )

    @command("get_candidates", paging)
    @websocket_api.async_response
    async def get_candidates(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        data = runtime["data"]
        rows = await async_discover_devices(
            hass,
            tracked_device_ids={row["device_id"] for row in data["devices"]},
            dismissed_device_ids=set(data["settings"].get("dismissed_device_ids", [])),
        )
        rows = [
            row
            for row in rows
            if msg["query"].casefold()
            in " ".join(
                str(row.get(key) or "")
                for key in ("name", "area_name", "source_integration")
            ).casefold()
        ]
        connection.send_result(
            msg["id"], {**page(rows, msg), "meta": meta(hass, runtime)}
        )

    choice_schema = {
        vol.Optional("enable_signals", default=False): bool,
        vol.Required("device_id"): str,
        vol.Optional("tracking_mode"): MODE,
        vol.Optional("power_type"): POWER,
        vol.Optional("battery_type"): vol.All(str, vol.Length(max=60)),
        vol.Optional("battery_quantity"): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=20)
        ),
    }

    @command(
        "preview_tracking",
        {
            vol.Required("device_ids"): vol.All([str], vol.Length(min=1, max=100)),
            vol.Optional("choices", default=[]): [choice_schema],
        },
    )
    @websocket_api.async_response
    async def preview(hass, connection, msg):
        _require_admin(connection)
        connection.send_result(
            msg["id"],
            await preview_tracking(
                hass, _get_runtime(hass), msg["device_ids"], msg["choices"]
            ),
        )

    @command("apply_tracking", {vol.Required("preview_id"): str})
    @websocket_api.async_response
    async def apply(hass, connection, msg):
        _require_admin(connection)
        connection.send_result(
            msg["id"], await apply_tracking(hass, _get_runtime(hass), msg["preview_id"])
        )

    @command("get_settings", {})
    @websocket_api.async_response
    async def get_settings(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        keys = {str(key) for key in RULES}
        connection.send_result(
            msg["id"],
            {
                "settings": {
                    **DEFAULTS,
                    **{
                        key: value
                        for key, value in runtime["data"]["settings"].items()
                        if key in keys
                    },
                },
                "meta": meta(hass, runtime),
                "migration_count": len(
                    runtime["data"]["settings"].get("migration_receipts", {})
                ),
            },
        )

    @command("save_settings", {vol.Required("values"): RULES})
    @websocket_api.async_response
    async def save_settings(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        proposed = {**runtime["data"]["settings"], **msg["values"]}
        if bool(proposed.get("quiet_start")) != bool(proposed.get("quiet_end")):
            raise vol.Invalid("Vyplň začiatok aj koniec tichých hodín")
        runtime["data"]["settings"].update(msg["values"])
        runtime["refresh_battery_subscriptions"]()
        await runtime["storage"].async_save(runtime["data"])
        connection.send_result(msg["id"], {"saved": True})

    @command(
        "update_device_rules",
        {vol.Required("device_id"): str, vol.Required("values"): DEVICE_RULES},
    )
    @websocket_api.async_response
    async def update_rules(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        device = next(
            (
                row
                for row in runtime["data"]["devices"]
                if row["device_id"] == msg["device_id"]
            ),
            None,
        )
        if not device:
            raise vol.Invalid("Zariadenie sa nesleduje")
        device["rules"] = msg["values"]
        runtime["refresh_battery_subscriptions"]()
        await runtime["storage"].async_save(runtime["data"])
        connection.send_result(msg["id"], {"saved": True})

    @command(
        "set_tracking_active",
        {vol.Required("device_id"): str, vol.Required("active"): bool},
    )
    @websocket_api.async_response
    async def set_active(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        device = next(
            (
                row
                for row in runtime["data"]["devices"]
                if row["device_id"] == msg["device_id"]
            ),
            None,
        )
        if not device:
            raise vol.Invalid("Zariadenie sa nesleduje")
        if not msg["active"]:
            device["paused_mode"] = device.get("tracking_mode", "availability_only")
            device["tracking_mode"] = "ignored"
            device["battery_attention"] = False
            async_dismiss(hass, f"{DOMAIN}_battery_{device['device_id']}")
        else:
            device["tracking_mode"] = device.pop("paused_mode", "availability_only")
            _add_device_entities(hass, runtime, device)
        runtime["refresh_report_subscriptions"]()
        runtime["refresh_battery_subscriptions"]()
        from .runtime import async_process_devices

        await async_process_devices(hass, runtime)
        await runtime["storage"].async_save(runtime["data"])
        connection.send_result(msg["id"], {"saved": True})

    @command(
        "acknowledge_alert",
        {
            vol.Required("incident_id"): str,
            vol.Optional("minutes", default=0): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=10080)
            ),
        },
    )
    @websocket_api.async_response
    async def acknowledge(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        target = next(
            (
                row
                for row in runtime["data"]["incidents"]
                if row["incident_id"] == msg["incident_id"]
            ),
            None,
        )
        if not target:
            raise vol.Invalid("Upozornenie neexistuje")
        ids = set(target["device_ids"])
        until = (
            (datetime.now(UTC) + timedelta(minutes=msg["minutes"])).isoformat()
            if msg["minutes"]
            else None
        )
        for incident in runtime["data"]["incidents"]:
            if (
                incident["incident_id"] == target["incident_id"]
                or incident.get("parent_incident_id") == target["incident_id"]
            ):
                incident["acknowledged"] = True
                if until:
                    incident["snoozed_until"] = until
                async_dismiss(hass, f"{DOMAIN}_incident_{incident['incident_id']}")
        if until:
            for device in runtime["data"]["devices"]:
                if device["device_id"] in ids:
                    device["snoozed_until"] = until
        await runtime["storage"].async_save(runtime["data"])
        connection.send_result(msg["id"], {"saved": True})

    @command("get_stock", {})
    @websocket_api.async_response
    async def get_stock(hass, connection, msg):
        _require_admin(connection)
        connection.send_result(
            msg["id"], {"items": analytics.stock_summary(_get_runtime(hass)["data"])}
        )

    @command(
        "save_stock",
        {
            vol.Required("battery_type"): vol.All(str, vol.Length(min=1, max=60)),
            vol.Required("on_hand"): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100000)
            ),
            vol.Required("minimum"): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100000)
            ),
        },
    )
    @websocket_api.async_response
    async def save_stock(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        kind = msg["battery_type"].strip().upper()
        if not kind:
            raise vol.Invalid("Vyplň typ batérie")
        rows = runtime["data"]["battery_stock"]
        row = next((row for row in rows if row["battery_type"] == kind), None)
        if row is None:
            row = {"stock_id": stable_id(kind), "battery_type": kind}
            rows.append(row)
        row.update(on_hand=msg["on_hand"], minimum=msg["minimum"])
        await runtime["storage"].async_save(runtime["data"])
        connection.send_result(msg["id"], {"saved": True})

    @command("load_native_history", {})
    @websocket_api.async_response
    async def load_history(hass, connection, msg):
        _require_admin(connection)
        runtime = _get_runtime(hass)
        task = runtime.get("history_task")
        if task and not task.done():
            connection.send_result(msg["id"], {"status": "running"})
            return
        runtime["history_task"] = hass.async_create_task(runtime["load_history"]())
        connection.send_result(msg["id"], {"status": "running"})

    @command("get_diagnostics", {})
    @websocket_api.async_response
    async def diagnostics(hass, connection, msg):
        _require_admin(connection)
        from .diagnostics import async_get_config_entry_diagnostics

        entry = hass.config_entries.async_entries(DOMAIN)[0]
        connection.send_result(
            msg["id"], await async_get_config_entry_diagnostics(hass, entry)
        )

    for handler in (
        get_dashboard,
        get_devices,
        get_detail,
        get_alerts,
        get_candidates,
        preview,
        apply,
        get_settings,
        save_settings,
        update_rules,
        set_active,
        acknowledge,
        get_stock,
        save_stock,
        load_history,
        diagnostics,
    ):
        websocket_api.async_register_command(hass, handler)
