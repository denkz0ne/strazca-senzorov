# Integration panel

The side panel is for detailed management and diagnosis; automations use the smaller HA entity/event interface.

## Tabs

1. **Overview** — tracked devices, area, health, source/transport, battery attention, last seen and active incident. Filters for problems, battery devices, offline/stale, protocol and area. Device detail drawer: health timeline, battery graph/cycle, incident history and explanation of current evidence. Do not surface temperature, occupancy or unrelated device measurements as Strážca-owned data.
2. **Batteries** — device battery assignments, battery type catalogue, replacement history, upcoming replacement needs and optional household stock. Adding an unknown model should require minimal input: review prefilled manufacturer/model/source and select battery type; quantity defaults to one and is editable. Applying the choice to all matching models is optional and explicit.
3. **Devices** — discovery recommendations with match evidence and proposed tracking mode; accept, edit, ignore and undo. Distinguish battery-powered, rechargeable and mains-powered devices. Signal entities that could improve diagnosis can be recommended for enabling here.
4. **Incidents** — grouped and individual incident timeline, current/previous cause, confidence/evidence, acknowledgement, confirmation/correction and recovery.
5. **Settings** — notification policy, startup grace, stale/offline thresholds, sampling, model catalogue management, import status, provider support and diagnostics.

The implemented panel has these five tabs. The detail drawer, household battery stock, advanced filters and some diagnostic affordances above remain design goals unless visible in the current implementation. Panel remains useful with generic provider data and must label unsupported diagnostics clearly.

## Observed current limitations

- The **Devices** discovery tab can show internal HA registry IDs as card titles when a readable name is absent from the current API record. Device/entity context should be made more legible before stable release; see [open questions](OPEN_QUESTIONS.md).
- Overview and Incidents are empty until the user explicitly tracks candidates and incidents occur; discovery by itself does not create tracked records.
- The visible panel is a first usable management surface, not the final detailed analytics dashboard. Do not document planned controls as shipped until they appear in code and pass UI review.

## Requested compact lists (not implemented yet)

These requests are tracked for later UI work: [#11 — battery table](https://github.com/denkz0ne/strazca-senzorov/issues/11), [#12 — device identity and diagnostics table](https://github.com/denkz0ne/strazca-senzorov/issues/12), and [#13 — new-device discovery notification and pending queue](https://github.com/denkz0ne/strazca-senzorov/issues/13).

The section tabs and search row should remain sticky while long panel lists scroll, without hiding headings or keyboard focus. This is tracked in [#14](https://github.com/denkz0ne/strazca-senzorov/issues/14) and is not implemented yet.

The **Batteries** table should use one compact row per tracked battery device and show readable device name, the optional `ZB###`/`ZBT###` identifier parsed from the device name, battery type/quantity, current level, last replacement, concise attention state and remaining-life estimate only when supported by enough history. If the name has no recognized identifier, leave that cell blank; do not derive it from the HA registry ID. For example, `zbt05-kupelna` can display `ZBT05`. Sort/search should cover useful columns; detailed cycles and evidence should stay in a secondary detail view.

The **Devices** list should identify entries from the HA display name and assigned area, plus a `ZB###` or `ZBT###` identifier only when it is present in the name. Missing identifiers remain blank. Show the source HA integration separately from power type/transport. Include available battery, voltage/low flag, battery type/count, replacement, estimate, signal/LQI/RSSI, last-report, tracking mode and availability/cause information. Use compact rows with expandable details for less common fields. Add checkboxes for bulk tracking with explicit confirmation and filters by integration, power source, area and tracking/availability. Do not show an opaque registry hash as the primary label, invent missing values, or enable disabled signal entities automatically.

The **Overview** list should also show the original HA integration for every tracked device, not only the Strážca health state. This is part of issue [#12](https://github.com/denkz0ne/strazca-senzorov/issues/12) and is not yet implemented in the current overview serializer.

Discovery should persist a deduplicated pending queue, update a sidebar count when new HA devices are found, and remove tracked/ignored entries from that queue and the candidate list. Detection and resolution state must survive restart. A device is never tracked without the user's explicit choice.

## MVP packaging and API

The MVP panel is a self-hosted, dependency-free JavaScript custom element in
`custom_components/sensor_guardian/www/panel.js`. `panel.py` registers it as a
Home Assistant custom panel and serves the packaged file from the integration;
no external script CDN or separate Node build step is required. HACS installs and
updates the integration directory as one unit.

The panel is administrator-only. It uses authenticated Home Assistant WebSocket
commands and never keeps durable state in the browser. `websocket_api.py`
provides bounded pages for overview, model catalogue/history, discovery,
incidents and settings. API serializers use per-section field allow-lists;
overview omits battery type, entity references and signal details. Settings and
all write commands validate IDs, page sizes and values.

Write operations cover tracking/dismissing discovery candidates, adding a local
battery-model record, assigning battery type/quantity per device, updating the
initial supported settings, and previewing/applying the one-time Battery Notes
import. Import apply stores a separate pre-import backup first. Replacement,
cause confirmation, snooze and resume use the same Home Assistant actions exposed
to automations. Discovery only recommends disabled signal entities; it does not
enable them.

The first UI release is Slovak, uses native keyboard focus order and semantic
tab/button/input labels, and adapts to narrow viewports. Unknown cause remains
visible as “neznáme”; empty catalogues and candidate/incident lists have explicit
messages. Interaction and layout still need a live Home Assistant browser check
during release hardening.

The current `hacs.json` declares the display name. It does not certify that an
install or update has been exercised by HACS; the first-release checklist
requires a clean install/update and a browser check on a disposable HA instance.

## Interaction principles

- Explain recommendations and cause estimates in ordinary language.
- Show approximate ranges and confidence for lifetime estimates; no false precision.
- Keep unknown and insufficient history visible.
- Make model/library edits local and reversible; preserve per-device overrides.
- Confirm destructive resets and provide export/backup for migration and data reset.
