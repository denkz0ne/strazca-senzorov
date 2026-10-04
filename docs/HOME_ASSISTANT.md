# Home Assistant interface

The user wants automation-ready summaries with detailed statistics kept in the Strážca panel. Avoid mirroring source battery/signal measurements.

## Proposed minimal entities

Per tracked device, subject to HA entity/device-registry feasibility:

- `binary_sensor.<device>_guardian_problem`: on when actionable health/availability incident exists; useful summary attributes can include `status`, `cause`, `confidence`, `since` and `parent_incident_id`.
- `sensor.<device>_guardian_status`: compact enum (`healthy`, `degraded`, `stale`, `offline`, `recovering`, `paused`, `unknown`). Consider whether this duplicates the binary summary enough to make one entity optional.
- For battery-tracked devices only, `binary_sensor.<device>_battery_attention`: on for replace-soon, critical or abnormal-drain state. Detailed estimate stays internal unless later automation needs justify one additional entity.

Create no default entities for battery type, quantity, signal, LQI/RSSI, cycle age, confidence statistics, outage counts or trend rates. They remain in the panel. Original source entities remain authoritative.

## Events for automations

Proposed event types:

- `sensor_guardian_incident`
- `sensor_guardian_recovered`
- `sensor_guardian_battery_attention`
- `sensor_guardian_battery_replaced`

Payloads should be versioned and compact: device ID/name, status, cause, confidence, severity, incident ID, timestamp; battery events may add current level and estimated remaining range when available. Avoid publishing sensitive unrelated entity attributes.

## Actions/services

Proposed actions using HA device selectors:

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
