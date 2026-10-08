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

Estimator features are internal: current cycle age, previous cycle durations, robust median pairwise decline rate, drain acceleration, sample count/quality, estimated remaining range and confidence. An ETA is withheld until at least four good observations span seven days, unless the same physical device has completed replacement cycles for a deliberately low-confidence historical estimate. Historical cycles from the same physical device are strongest; same-model local cohort may be a secondary prior. Capacity tables are optional contextual data, not the primary lifetime predictor. These initial gates are implementation defaults and remain tunable after real-world evaluation.

## Availability profile and incident

Availability profile: selected sentinels, bounded rolling report timestamps, median/p90/p95 inter-report intervals, jitter/dispersion, explicit availability capability, learned pattern confidence and last update. Event-driven devices may have no reliable periodic pattern; silence alone cannot mark them offline when pattern confidence is low. Device records retain last report time and the latest explicit native availability state when selected.

Incident: `incident_id`, affected device IDs, opened/updated/closed timestamps, health state, cause, confidence, severity, evidence list, shared parent/dependency, acknowledgement/snooze and notification state. Evidence records include feature, observed value, direction/weight, time and provider. Later evidence may revise the cause, retaining the audit trail.

## Shared dependencies and settings

Dependencies map device → source integration/config entry → known coordinator/gateway/AP when available. Settings cover default timing and score thresholds, notification policy, startup grace, sampling, discovery and provider options. Defaults must be conservative and overridable.

## Versioned persisted payload

The first persisted payload uses Home Assistant Store envelope version `1`, minor version `1`. The root JSON object contains `models`, `devices`, `samples`, `cycles`, `availability_profiles`, `dependencies`, `incidents` and `settings`. Each collection stores normalized records with a stable required ID (`model_id`, `device_id`, `sample_id`, `cycle_id`, `profile_id`, `dependency_id`, or `incident_id`).

`GuardianStorage` uses a private, atomically written Store per config entry. Recorder is not used for ongoing persistence. Known older minor payloads are migrated with defaults; malformed payloads fail validation without an automatic save. Unknown root extension fields are retained. Home Assistant rejects a future major Store version before Strážca writes anything, and Strážca rejects a future minor schema rather than interpreting it as current.

The versioned `async_export()` envelope contains `version`, `minor_version` and validated `data`, without Home Assistant's internal storage key.

Runtime repair 0.1.1 adds optional device fields source_binding_version (2), source_status, report_profile_entity_id and availability_sentinels. The last field identifies authoritative primary availability sources independently from cached auxiliary telemetry. Existing schema 1.1 containers stay compatible; battery samples/cycles and unknown extension fields survive repair. user_overrides protects explicit source/mode/power choices. A separate pre_source_repair Store captures the first legacy payload before changing bindings.

## Implemented schema 1.2 (0.2.0)

This version supersedes the initial 1.1 envelope described above. Root collections add `signal_samples` (sample_id), `health_history` (transition_id) and `battery_stock` (stock_id). Unknown extension fields and existing device/sample/cycle identities survive migration. Old exports are normalized to 1.2; future minor envelopes are rejected.

- Signal observation: device_id, kind, timestamp, value, provenance; daily aggregates also contain min/max/count/resolution. RSSI and LQI remain separate chart series.
- Health transition: device_id, timestamp, state, reason and cause. Same-state checks do not create fake transitions.
- Battery stock: type, manually entered on_hand and minimum. Installation counts derive from tracked assignments; 90-day usage derives only from confirmed replaceable-battery cycles.
- Device additions: rules, paused_mode, battery_replaced_at, history_source/status, native notification pending flag. Pausing preserves history; replacement prevents using previous-cycle values as current.
- Incident additions: kind=availability/battery, acknowledged, snoozed_until, event_sent, last_notified_at and persisted delivery state. Confirmed cause survives inferred revisions. Battery warnings are independent of availability incidents.
- Settings: validated global rules, retention_days (30–730), quiet hours and notification policy; internal tracking_receipts record pending/completed operation phase plus explicitly consented native signal IDs. Public inherited rules are allow-listed, not a dump of internal receipts.

Retention defaults to 365 days. Signal data older than 14 days is reduced to weighted daily summaries. Battery data is capped at 4096 observations independently per device and retained within the configured age; one dated last-known observation is preserved when all data is older. The fleet-wide 10,000 cap is removed. Replacement cycle records are preserved. A battery fact older than seven days is explicitly marked stale; following replacement, the UI awaits a new observation.
