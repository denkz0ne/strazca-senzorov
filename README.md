# Strážca senzorov

**Strážca senzorov** is a planned Home Assistant custom integration for monitoring device availability, battery condition and likely outage causes. Its primary record is the HA device; battery management is one capability of that device, not the whole product.

The integration is intended to help answer:

- Which tracked devices are healthy, stale, offline or recovering?
- Is a battery likely to need replacement soon, and how reliable is that estimate?
- Does an outage look like a depleted battery, a local connection problem, a shared gateway/integration failure, or is the cause unknown?
- What should be automated, and what should stay as detail in the integration panel?

## Product decisions captured so far

- Battery Notes is a **one-time migration source** for its device model library and any per-device settings/history that can be recovered. It is not a runtime dependency. Once migration has been checked and Strážca is deployed, Battery Notes is intended to be removed.
- Strážca keeps its own normalized model catalogue. Battery type and quantity are device-specific configuration; predicted lifetime is learned from real replacement cycles and observed reports, not asserted from catalogue capacity.
- Runtime observations come primarily from the devices' existing Home Assistant entities: battery percentage, battery-low flag, voltage, native availability, signal (LQI/RSSI or equivalent) and `last_reported`/last-seen evidence where available.
- Discovery should suggest useful diagnostic signal entities for enabling when disabled. It should not enable every entity indiscriminately.
- Create only a small set of automation-friendly HA entities. Battery chemistry, detailed trends, replacement cycles, evidence scores and statistics belong in the integration's own panel/API.
- Cause classification must be evidence-based. When the evidence is weak or competing, report `unknown` rather than invent certainty.
- Mains-powered devices are monitored for availability and incidents; they do not receive battery estimates.

## Documentation map

- [Architecture](docs/ARCHITECTURE.md) — component boundaries and data flow
- [Data model](docs/DATA_MODEL.md) — device, battery cycle, sample, profile and incident records
- [Battery Notes migration](docs/MIGRATION.md) — one-time import and history reconstruction
- [Availability and evidence engine](docs/AVAILABILITY.md) — health states, causal scoring and clustering
- [Home Assistant interface](docs/HOME_ASSISTANT.md) — entities, events, actions and notifications
- [Panel design](docs/FRONTEND.md) — tabs and workflows
- [Development stages](docs/ROADMAP.md) — phased implementation plan
- [Detailed development plan](docs/superpowers/plans/2026-10-04-sensor-guardian-development.md) — task-by-task acceptance checks and GitHub issue map
- [Progress log](docs/PROGRESS.md) — completed work and verification reports
- [Open questions](docs/OPEN_QUESTIONS.md) — decisions still to make
- [Third-party data and attribution](THIRD_PARTY_DATA.md) — Battery Notes snapshot requirements

## Proposed identity

Working display name: **Strážca senzorov** (English: **Sensor Guardian**).

Integration domain: `sensor_guardian`.

Compatibility target: the connected instance reports Home Assistant Core `2026.9.4`; the initial support floor is Core `2026.9`, pending release compatibility runs.

## Status

Development is underway in stages tracked by [GitHub milestone MVP Development](https://github.com/denkz0ne/strazca-senzorov/milestone/1). See the [detailed plan](docs/superpowers/plans/2026-10-04-sensor-guardian-development.md) and [progress report](docs/PROGRESS.md). Until the scaffold is complete, this repository does not contain an installable integration. Thresholds and unclosed design questions remain proposals.

## Principles

1. Preserve source entities and avoid duplicate measurements.
2. Separate observed facts, inferred states and user-confirmed facts.
3. Keep uncertainty visible, including `unknown` as a valid cause.
4. Keep long-term learning data in Strážca storage; do not depend on Recorder retention.
5. Make discovery and recommendations reviewable by the user.
6. Do not notify repeatedly for one continuing incident; debounce, deduplicate and support snoozing.
