# Changelog

Changes are recorded here for tagged releases. There is no published release yet.

## Unreleased — MVP development

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
