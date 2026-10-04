# Data model (proposal)

The tracked HA device is the aggregate root. Observations belong to the device, while battery configuration and cycles are optional capabilities.

## Device model catalogue

```yaml
model_id: stable internal id
manufacturer: string | null
model: string | null
model_ids: [string]
hardware_versions: [string]
aliases: [string]
match_rules: [{field, value, match_type}]
default_battery_type: string | null
default_battery_quantity: integer | null
power_hint: battery | rechargeable | mains | unknown
replaceable: boolean | null
source: imported | local
source_attribution: string | null
```

Catalogue defaults are suggestions, not facts about an installed unit. Resolution priority: explicit device override → local model entry → imported snapshot match → observed/inferred hint → unknown. The catalogue does not promise battery lifetime.

## Tracked device

```yaml
device_id: HA device registry ID
name: display name snapshot/reference
area_id: string | null
source_integration: domain | null
config_entry_id: string | null
transport: zigbee | bluetooth | wifi | mqtt | other | unknown
tracking_mode: battery_and_availability | availability_only | battery_only | ignored
power_type: replaceable_battery | rechargeable | mains | unknown
entity_refs:
  battery_level: entity_id | null
  battery_low: entity_id | null
voltage: entity_id | null
native_availability: entity_id | provider reference | null
signal: [{entity_id, kind: lqi | rssi | linkquality | other}]
sentinels: [entity_id]
battery_type: string | null
battery_quantity: integer | null
replacement_history: [cycle_id]
availability_profile_id: string | null
active_incident_ids: [incident_id]
user_overrides: object
```

Registry names and areas can change, so IDs are authoritative and display values should be refreshed from HA.

## Battery sample and cycle

Sample: `timestamp`, `level_percent`, `voltage`, `native_low`, source entity IDs, quality flags and collection provenance. Store only useful changes/checkpoints rather than every poll.

Cycle: `cycle_id`, `device_id`, start/end timestamps, battery type and quantity, optional brand/chemistry, initial/final level, lifetime, replacement reason and confidence/provenance. Provenance values include `user_confirmed`, `battery_notes_explicit`, `recorder_exact`, `statistics_inferred` and `automatic_unconfirmed`. A recharge is a charge cycle, never an assumed replacement.

Estimator features are internal: current cycle age, previous cycle durations, robust short/medium/long drain rates, drain acceleration, sample count/quality, estimated remaining range and confidence. Historical cycles from the same physical device are strongest; same-model local cohort may be a secondary prior. Capacity tables are optional contextual data, not the primary lifetime predictor.

## Availability profile and incident

Availability profile: selected sentinels, median/p90/p95 inter-report intervals, jitter/dispersion, explicit availability capability, learned pattern confidence and last update. Event-driven devices may have no reliable periodic pattern; silence alone cannot mark them offline when pattern confidence is low.

Incident: `incident_id`, affected device IDs, opened/updated/closed timestamps, health state, cause, confidence, severity, evidence list, shared parent/dependency, acknowledgement/snooze and notification state. Evidence records include feature, observed value, direction/weight, time and provider. Later evidence may revise the cause, retaining the audit trail.

## Shared dependencies and settings

Dependencies map device → source integration/config entry → known coordinator/gateway/AP when available. Settings cover default timing and score thresholds, notification policy, startup grace, sampling, discovery and provider options. Defaults must be conservative and overridable.
