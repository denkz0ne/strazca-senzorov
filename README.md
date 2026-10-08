# Strážca senzorov

**Strážca senzorov** is a Home Assistant custom integration for monitoring device availability, battery condition and likely outage causes. Its primary record is the HA device; battery management is one capability of that device, not the whole product. The current implementation is merged into `main` and can be tracked through HACS as a custom repository. It has no stable tagged release, and live behavior still needs owner-run validation.

The integration is intended to help answer:

- Which tracked devices are healthy, stale, offline or recovering?
- Is a battery likely to need replacement soon, and how reliable is that estimate?
- Does an outage look like a depleted battery, a local connection problem, a shared gateway/integration failure, or is the cause unknown?
- What should be automated, and what should stay as detail in the integration panel?

## Prevention dashboard 0.2.0

Dashboard for urgent interventions, preventive recommendations and data coverage; compact tracked devices with 7/30/90-day detail charts; actionable battery/availability alerts; reviewed bulk onboarding; global/device settings and secondary battery stock. Explicit uncertainty, dated last-known values and replacement boundaries prevent invented measurements. Native-source observations remain independent of Battery Notes. See [user guide](docs/USER_GUIDE.md) and [approved design](docs/superpowers/specs/2026-10-07-prevention-first-ui-design.md).

Store schema 1.2 preserves older histories with a pre-upgrade backup. Backend/frontend version checks make stale installation visible. CI checks real packaged assets with simulated HA data; the owner still performs HACS download and HA restart.

## Product decisions captured so far

- Battery Notes is a **one-time migration source** for its device model library and any per-device settings/history that can be recovered. It is not a runtime dependency. Once migration has been checked and Strážca is deployed, Battery Notes is intended to be removed.
- Strážca keeps its own normalized model catalogue. Battery type and quantity are device-specific configuration; predicted lifetime is learned from real replacement cycles and observed reports, not asserted from catalogue capacity.
- Runtime observations come primarily from the devices' existing Home Assistant entities: battery percentage, battery-low flag, voltage, native availability, signal (LQI/RSSI or equivalent) and `last_reported`/last-seen evidence where available.
- Discovery should suggest useful diagnostic signal entities for enabling when disabled. It should not enable every entity indiscriminately.
- Create only a small set of automation-friendly HA entities. Battery chemistry, detailed trends, replacement cycles, evidence scores and statistics belong in the integration's own panel/API.
- Cause classification must be evidence-based. When the evidence is weak or competing, report `unknown` rather than invent certainty.
- Mains-powered devices are monitored for availability and incidents; they do not receive battery estimates.

## Documentation map

- [Používateľský návod](docs/USER_GUIDE.md) — first setup, tracking, battery import, automation and troubleshooting
- [Vývojársky návod](docs/DEVELOPER_GUIDE.md) — development checks, module map, storage/API contracts and releases
- [Documentation policy](docs/DOCUMENTATION_POLICY.md) — required docs/changelog updates for features and hotfixes

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
- [First-release checklist](docs/RELEASE_CHECKLIST.md) — required live HA/HACS validation and release gates
- [Changelog](CHANGELOG.md) — release history (no release has been published)

## Proposed identity

Working display name: **Strážca senzorov** (English: **Sensor Guardian**).

Integration domain: `sensor_guardian`.

Compatibility target: the connected instance reports Home Assistant Core `2026.9.4`; the initial support floor is Core `2026.9`, pending release compatibility runs.

## Current behavior and status

Runtime repair version 0.1.1 corrects missing native battery readings, repairs legacy source bindings, distinguishes mains power from batteries and uses primary HA entity availability. It also adds tracked mode editing, explicit signal activation, diagnostic coverage and native alert notices. See the [update guide](docs/USER_GUIDE.md#aktualizácia-opravy-011) and [repair plan](docs/superpowers/plans/2026-10-07-runtime-data-repair.md). Installation/restart and final live validation remain owner-controlled.

Implementation stages are tracked by [GitHub milestone MVP Development](https://github.com/denkz0ne/strazca-senzorov/milestone/1). See the [detailed plan](docs/superpowers/plans/2026-10-04-sensor-guardian-development.md) and [progress report](docs/PROGRESS.md). The changes described here are merged into `main`, but there is no stable tagged release. The repository owner still needs to update the live HA installation and confirm runtime behavior. Some thresholds and design questions remain proposals.

There is no published release yet. For the current HACS custom-repository installation, use HACS to update `denkz0ne/strazca-senzorov` from its default `main` branch, then fully restart Home Assistant and refresh the browser. The log-driven fixes in this update move bundled catalogue reads off the event loop and make scheduled callbacks thread-safe. Review the fresh log before relying on automated diagnosis. On first open, use **Zariadenia** to review candidates in the compact table and explicitly track selected devices; discovery alone never starts tracking. New candidates update one native Home Assistant notification with the pending count. HA does not expose a supported numeric badge for an individual custom panel. Do not remove Battery Notes until its import has been previewed, backed up, applied and verified in Strážca.

## Principles

1. Preserve source entities and avoid duplicate measurements.
2. Separate observed facts, inferred states and user-confirmed facts.
3. Keep uncertainty visible, including `unknown` as a valid cause.
4. Keep long-term learning data in Strážca storage; do not depend on Recorder retention.
5. Make discovery and recommendations reviewable by the user.
6. Do not notify repeatedly for one continuing incident; debounce, deduplicate and support snoozing.

# Development status

The MVP implementation is merged into `main`. It targets Home Assistant Core 2026.9+, uses one global config entry and has no runtime Battery Notes dependency. It is not a tagged release, and live deployment checks are still pending.

## Local development

Use Python 3.14, then install `requirements_test.txt`. Run `ruff check .` and `pytest -q`. The GitHub Actions workflow runs the same checks on Linux, which is required by Home Assistant Core's test runtime.

See [the development plan](docs/superpowers/plans/2026-10-04-sensor-guardian-development.md) and [progress log](docs/PROGRESS.md) for scope and stage status.
