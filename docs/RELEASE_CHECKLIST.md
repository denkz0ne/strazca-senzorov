# First release checklist

This checklist is a gate for a future tagged release. The current `main` branch can be tracked by HACS as a custom repository for owner testing, but it is not a supported stable release and live checks remain outstanding.

## Repository and packaging

- [x] Publish the repository's MIT source-code license. `THIRD_PARTY_DATA.md` separately covers the Battery Notes catalogue notice.
- [ ] Confirm `hacs.json`, the integration manifest, translations, and packaged `www/panel.js` in a clean HACS custom-repository install.
- [ ] Install and update through HACS on a disposable Home Assistant Core instance; confirm the panel JS resource and admin-only panel load without external network access.
- [ ] Validate config flow, first startup, unload/reload, restart, data migration, export and restore on the declared minimum Core and the current target Core.
- [ ] Review HACS validation output and Core logs for deprecations, setup warnings and failed resources.

## Product behavior

- [ ] Verify Battery Notes is not a manifest, Python, panel or runtime dependency. Perform preview, backup, import and restore; only then may the user remove Battery Notes.
- [ ] Confirm import is idempotent and Strážca continues to work after Battery Notes removal/restart.
- [ ] Review generated entity count and device links for battery, rechargeable and mains devices.
- [ ] Verify report subscriptions include only selected entities; no global high-volume `state_reported` listener is present.
- [ ] Exercise low-battery dropout, RF loss, shared gateway/source outage, recovery and conflicting evidence; unsupported diagnosis must remain `unknown`.
- [ ] Check event deduplication, incident grouping, recovery notices and configured cooldown behavior.
- [ ] Inspect panel on desktop and narrow viewport; verify keyboard operation, empty/partial data, signal recommendations, import preview, errors and permissions.

## Release approval

- [ ] All required CI and compatibility runs pass on the release commit.
- [ ] Update changelog, documentation, version and supported Core floor.
- [ ] Confirm the intended installation/deployment path with the repository owner.
- [ ] Create and push a version tag only after the release is explicitly requested and approved.

## Prevention dashboard 0.2.0 owner gate

- [ ] HACS uses `main`, offers the merged 0.2.0 commit, and owner downloads it.
- [ ] After owner restart, Settings identifies backend/frontend 0.2.0, schema 1.2 and recent evaluation; no mismatch banner.
- [ ] Compare a battery and mains device against native entities; verify old history, replacement cycles and areas/names survive.
- [ ] Check 7/30/90-day detail, versioned assets, mobile layout and retained edits on the real browser.
- [ ] Exercise preview/apply/new discovery, declined/consented signal enablement, unavailable Recorder, timed snooze/expiry, repetition and grouped notices.
- [ ] Owner confirms live behavior before stable tag/release. CI/mocked browser checks are recorded separately.
