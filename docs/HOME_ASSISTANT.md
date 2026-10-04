# Home Assistant interface

The user wants automation-ready summaries with detailed statistics kept in the Strážca panel. Avoid mirroring source battery/signal measurements.

## Implemented minimal entities

Per tracked device, the initial inventory is three entities at most:

- `binary_sensor.<device>_guardian_problem`: on when availability needs attention, with only status, cause, qualitative confidence, start time and parent incident ID attributes.
- `sensor.<device>_guardian_status`: compact enum (`initializing`, `healthy`, `degraded`, `stale`, `offline`, `recovering`, `paused`, `unknown`). Keep this alongside the problem flag: automations often need both a simple boolean and the current state label.
- For battery-tracked devices only, `binary_sensor.<device>_battery_attention`: on for low/replace-soon/abnormal drain. Detailed estimate remains internal.

Create no default entities for battery type, quantity, signal, LQI/RSSI, cycle age, confidence statistics, outage counts or trend rates. They remain in the panel. Original source entities remain authoritative.

## Implemented events for automations

Version 1 event types (payloads carry `version: 1`; incident/recovery events include compact status, cause, qualitative confidence, severity, incident ID and timestamp; grouped outages may include affected device IDs):

- `sensor_guardian_incident`
- `sensor_guardian_recovered`
- `sensor_guardian_battery_attention`
- `sensor_guardian_battery_replaced`

Payloads use `version: 1` and compact fields: `device_id`, `device_name`, `status`, `cause`, `confidence`, `severity`, `incident_id`, `timestamp`; grouped outage events may include `device_ids`. Battery replacement adds `battery_type`, `battery_quantity` and `cycle_id`. Unrelated HA attributes are excluded.

## Implemented actions/services

The `sensor_guardian` action domain currently exposes:

- `mark_battery_replaced`: required `device_id`; optional `battery_type`, `battery_quantity` (1–20), `brand`, `reason`, `replaced_at` (ISO timestamp).
- `confirm_incident_cause`: required `incident_id` and `cause` (`battery`, `connectivity`, `gateway_upstream`, `integration`, `power_or_network`, `unknown`).
- `snooze_device`: required `device_id`; optional `snooze_minutes` (1–10,080; default 60).
- `resume_device`: required `device_id`.

The panel uses these same backend actions for replacement, cause confirmation and snooze/resume behavior. The separate admin-only panel WebSocket commands are documented in [the developer guide](DEVELOPER_GUIDE.md).

## Linking and discovery

Helper entities attach to the original HA device through the supported helper-integration API. Discovery proposals are actionable and dismissible: battery plus availability, availability only, battery only, ignore/unknown. Necessary disabled LQI/RSSI/link-quality entities may be recommended, but are not enabled automatically.

## Notifications

Emit state/events suitable for user-defined automations. Configurable notifications should have severity, deduplication, cooldown, startup grace, snooze and optional recovery notices. Do not create one bespoke notifier entity per device.
