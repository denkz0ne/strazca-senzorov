# Architecture

## Boundaries

```text
Home Assistant device/entity registries and source integrations
                 │ observations + registry metadata
                 ▼
       Discovery and provider adapters
                 │ normalized observations
       ┌─────────┴──────────┐
       ▼                    ▼
 Availability/evidence   Battery lifecycle/estimator
       └─────────┬──────────┘
                 ▼
       Incident and notification manager
          ┌──────┴──────────┐
          ▼                 ▼
 Minimal HA entities   Panel/API and internal history
```

### Components

- **Discovery:** scans HA device and entity registries, identifies candidate devices and relevant existing entities, matches models against Strážca's bundled catalogue and produces explainable recommendations.
- **Provider adapters:** normalize generic HA evidence first, then add integration-specific evidence where supported (initial candidates: ZHA, Zigbee2MQTT/MQTT, ESPHome, Bluetooth and Wi-Fi integrations). A missing adapter must not prevent generic tracking.
- **Device registry/tracking:** stores opt-in/ignore state, selected entities, power type, battery configuration and per-device overrides. Links Strážca entities to the existing HA device when HA supports that helper-integration pattern.
- **Observation collector:** subscribes only to relevant entities/devices. Captures meaningful changes and report timestamps without globally processing high-volume events.
- **Availability engine:** estimates healthy/degraded/stale/offline/recovering state from explicit availability and learned/reporting timing.
- **Battery engine:** records useful samples and replacement cycles; estimates remaining life and abnormal drain for an individual device, with confidence and range.
- **Evidence/cause engine:** scores battery, connectivity, gateway/upstream, integration and power/network hypotheses. It can return unknown and can revise an incident when later evidence arrives.
- **Incident manager:** opens, groups, updates and closes incidents; handles acknowledgement, snooze, deduplication and notification policy.
- **Storage:** versioned integration-owned storage for model catalogue overrides, tracking configuration, relevant samples, profiles, battery cycles and incidents.
- **HA interface:** minimal entities plus stable event/action/service contracts for automations.
- **Panel:** detailed overview, battery management, discovery, incident history and settings over a documented WebSocket/API layer.

## Data flow

1. Discovery reads HA registries and candidate source entity metadata.
2. The user accepts, edits or ignores a recommendation. Unknown models get a short form with most fields prefilled and battery type as the main required choice; quantity defaults to one and stays editable.
3. The collector reads source entity state/attributes and relevant `last_reported` evidence. It may recommend enabling selected disabled signal entities if the active provider can use them diagnostically.
4. Normalized observations feed independent health and battery engines.
5. Incident evidence is stored with its source and timestamp. Correlated outages can form a parent incident.
6. HA entities expose only actionable summary state. Events/actions support automation and control; the panel reads detailed history and evidence.

## Persistence and lifecycle

Use Home Assistant's integration storage mechanism (exact API/schema version to be chosen at implementation) with explicit schema versioning and safe migrations. Do not use Recorder as the durable source of Strážca history. Recorder and long-term statistics may be read once during Battery Notes bootstrap, subject to HA API availability and data retention.

Keep the data sets logically separated even if stored in one versioned document/database: model catalogue, tracked-device configuration, battery samples/cycles, learned availability profiles, dependencies, incidents and global settings. Avoid per-minute duplicate samples; persist meaningful changes, daily checkpoints, replacements, incidents and recoveries.

## Failure and privacy behavior

- Missing or stale source entities produce partial/unknown evidence, not fabricated values.
- An unavailable coordinator/source integration is represented as shared evidence for affected devices.
- Diagnostics should omit sensitive entity attributes and expose only the evidence needed to explain a result.
- Storage corruption or migration failure must be reported without discarding the original data; migration should be recoverable and idempotent.
