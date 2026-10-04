# One-time Battery Notes migration

Battery Notes is a bootstrap source only. Strážca must operate independently after the import. The intended end state is removal of Battery Notes after the user verifies the imported data and Strážca is deployed.

## Import scope

1. **Bundled model library:** convert the selected Battery Notes snapshot to Strážca's own versioned schema. Preserve source attribution, upstream license and the snapshot/version used. No runtime downloads or ongoing synchronization.
2. **Per-device settings:** import model/battery type, quantity, last replacement and last-reported fields when available; map source device identifiers carefully and show unresolved matches for review.
3. **Battery history:** inspect available Recorder states and long-term statistics for Battery Notes battery entities and replacement fields. Reconstruct possible cycles only when evidence supports it.

## Provenance and uncertainty

Every imported field/cycle retains provenance: `battery_notes_explicit`, `recorder_exact` or `statistics_inferred`. User-confirmed replacements outrank inferred dates. Long-term statistics are aggregates and may not recover exact report timing or replacement events; never present inferred cycles as confirmed history.

## User workflow

1. Detect Battery Notes and offer a one-time import preview.
2. Show counts for matched devices, unmatched devices, imported catalogue rows, recoverable settings, reconstructed cycles and uncertain items.
3. Allow review/correction before applying, with export/backup of the pre-import Strážca data.
4. Apply idempotently; repeating the import must not duplicate cycles or catalogue rows.
5. Verify a post-import summary and retain an import receipt/source version.
6. Only after the user confirms the resulting setup, they can remove Battery Notes. Strážca must not uninstall another integration itself.

## Compatibility and implementation checks

At implementation time, inspect the installed Battery Notes version and actual storage format rather than assuming a schema. Recorder APIs, retained history and statistics availability depend on HA configuration and time. If a source cannot be read, import what is available and explain the gap. Keep migration code isolated and removable from the normal runtime path after migration support is stable.

The upstream project identified in the conversation is [andrew-codechimp/HA-Battery-Notes](https://github.com/andrew-codechimp/HA-Battery-Notes). Its repository currently declares MIT; check the exact snapshot/license when importing and retain the required notice and attribution in the distributed catalogue. See [third-party data notes](../THIRD_PARTY_DATA.md).
