# Runtime data repair

The owner requests functioning availability, battery readings and diagnostics for existing tracked devices. Source reads on HA are authorized; installation/restart remains owner-controlled.

## Evidence

- Live native ZHA readings: ZB65 45 %, ZB79 100 %, both sensor device_class battery. Panel reports battery unknown.
- Discovery classifies sensor device_class battery as battery_low before checking the numeric percentage kind. Localized names also fail text-only matching.
- Discovery includes Battery Notes and Guardian helper entities in source selection. A tracked ZHA device consequently reports battery_notes as its provider.
- Standalone mains voltage is counted as battery evidence. Bulk tracking applies global defaults instead of the recommendations shown in rows.
- Availability uses only connectivity binary sensors or learned periodicity, ignoring explicit unavailable states of the actual source entities.

## Steps

1. Reproduce with percentage/localized/helper/mains tests and persisted broken-binding setup test; run on GitHub Actions.
2. Classify native entities by domain/device class/unit, exclude migration/helper platforms, select real source sentinels and correct discovery defaults.
3. Reconcile existing bindings on startup and registry changes without dropping battery cycles, samples, user configuration or explicit source overrides.
4. Evaluate source HA availability without equating switch off with offline or inventing periodic radio traffic. Keep cause unknown when evidence is insufficient.
5. Let the owner edit tracked mode/power in the panel; expose source/learning gaps and refresh open panels; fix bulk defaults.
6. Verify regression and lifecycle/API cases in GitHub CI, update docs/changelog and PR, prepare owner HACS update. Do not mark migration/restore or live UI checks completed without evidence.
