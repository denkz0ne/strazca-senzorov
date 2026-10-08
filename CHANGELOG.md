# Changelog

Changes are recorded here for tagged releases. There is no published release yet.

## Unreleased — MVP development

### 0.2.0 � prevention dashboard and persistent evidence

- Replace the original tabs with intervention/prevention/coverage dashboard, tracked devices, shared detail, alerts, guided onboarding and settings. Battery stock/catalogue are secondary utilities.
- Add real 7/30/90-day charts, replacement boundaries/history, prediction confidence/reasons, source editing, per-device inherited rules and stale-value dates. Preserve drafts, selection, focus and mobile layouts.
- Persist signal checkpoints/daily aggregates and health transitions in schema 1.2 with a pre-upgrade backup; optionally fill selected native battery Recorder history. Bound battery history per device, preserving last-known provenance.
- Add durable revalidated onboarding receipts, explicit signal consent, independent battery alerts, timed snooze/quiet hours/repetition and clean grouped notices. Keep minimal HA entities/actions/events compatible.
- Version root element/module assets and display active backend/frontend version. Add admin DTO/API, migration compatibility and Chromium regressions; update architecture, data model, guides and owner update checklist.
- No automatic owner HAOS install/restart and no stable tag/release. Live verification remains issue #10.

### 0.1.1 — native runtime data repair

- Correct numeric/localized battery classification and exclude Battery Notes/Guardian helpers from runtime sources.
- Repair old bindings with a separate pre-repair backup; retain battery assignments, cycles and explicit user choices.
- Use native source availability without confusing switch off with offline; expose intentional battery-only availability as not monitored.
- Correct mains-voltage classification and bulk per-device recommendations.
- Add tracked mode/power editing, explicit signal enabling, redacted diagnostics, sample/report counts, live panel refresh and local dates.
- Coalesce report evaluation/registry updates, learn from one cadence source, bound trend work and flush storage under continuous reports.
- Deliver deduplicated native incident/battery notifications with recovery/replacement dismissal and a notification setting.
- Warn on rapid recent drain before enough history exists for an ETA; separate current-cycle trend from previous battery cycles.
- Add Chromium interaction checks and runtime/API regression coverage. Owner HAOS update and live checks remain required.

### 0.1.0 — MVP baseline

- Refresh project status, HAOS/HACS update instructions and the log hotfix report after PR #15 merged to `main`.
- Add a complete Slovak user guide, developer guide and documentation/versioning policy.
- Add a pull request checklist to keep documentation, changelog, manifest version and hotfix evidence in step with code.
- Document first-run discovery behavior and the current opaque discovery-card ID limitation.
- Add compact battery, overview and discovery tables with friendly HA identity, ZB/ZBT labels, area, filters and confirmed bulk tracking.
- Add a deduplicated persistent discovery notice, sticky panel navigation/search and narrow-screen table scrolling.
- Run bundled catalogue reads in Home Assistant's executor and mark timer callbacks event-loop safe; add regression coverage for HA 2026.9 thread checks.
- Add device availability and battery lifecycle monitoring.
- Add evidence-based outage diagnosis and incident grouping.
- Add minimal automation entities, actions and transition events.
- Add an administrator-only Slovak management panel and one-time Battery Notes importer.
- Add a self-hosted model catalogue converted from Battery Notes data; no runtime dependency or network fetch.
- Complete live Home Assistant and HACS installation checks before the first release.
