# Home Assistant interface

The user wants automation-ready summaries with detailed statistics kept in the Strážca panel. Avoid mirroring source battery/signal measurements.

## Proposed minimal entities

Per tracked device, the initial inventory is three entities at most:

- `binary_sensor.<device>_guardian_problem`: on when availability needs attention, with only status, cause, qualitative confidence, start time and parent incident ID attributes.
- `sensor.<device>_guardian_status`: compact enum (`initializing`, `healthy`, `degraded`, `stale`, `offline`, `recovering`, `paused`, `unknown`). Keep this alongside the problem flag: automations often need both a simple boolean and the current state label.
- For battery-tracked devices only, `binary_sensor.<device>_battery_attention`: on for low/replace-soon/abnormal drain. Detailed estimate remains internal.

Create no default entities for battery type, quantity, signal, LQI/RSSI, cycle age, confidence statistics, outage counts or trend rates. They remain in the panel. Original source entities remain authoritative.

## Events for automations

Version 1 event types (payloads carry `version: 1`; incident/recovery events include compact status, cause, qualitative confidence, severity, incident ID and timestamp; grouped outages may include affected device IDs):

- `sensor_guardian_incident`
- `sensor_guardian_recovered`
- `sensor_guardian_battery_attention`
- `sensor_guardian_battery_replaced`

Payloads should be versioned and compact: device ID/name, status, cause, confidence, severity, incident ID, timestamp; battery events may add current level and estimated remaining range when available. Avoid publishing sensitive unrelated entity attributes.

## Actions/services

Version 1 actions use HA device selectors where a device is the target:

- `sensor_guardian.mark_battery_replaced` (type/quantity, optional brand/reason/date)
- `sensor_guardian.confirm_incident_cause` (incident/device, selected cause)
- `sensor_guardian.snooze_device`
- `sensor_guardian.resume_device`
- optional import/diagnostic actions if they can be safely exposed through config/panel instead

Panel buttons should call the same backend actions so behavior is consistent. Final naming/schema must follow current HA conventions during implementation.

## Linking and discovery

Prefer attaching helper entities to the original HA device when supported by the supported HA minimum. Discovery proposals should be actionable and dismissible: battery plus availability, availability only, battery only, ignore/unknown. For necessary disabled LQI/RSSI/link-quality entities, explain why they help and offer an explicit enable recommendation; enabling policy must be verified against HA registry APIs and provider behavior.

## Notifications

Emit state/events suitable for user-defined automations. Configurable notifications should have severity, deduplication, cooldown, startup grace, snooze and optional recovery notices. Do not create one bespoke notifier entity per device.
