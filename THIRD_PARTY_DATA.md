# Third-party data and attribution

The project uses the Battery Notes device model library only as a one-time conversion source. The bundled data came from [andrew-codechimp/HA-Battery-Notes](https://github.com/andrew-codechimp/HA-Battery-Notes), commit `df7c277cd43a42801aaf820329cb2ce365c1dbda`, file `library/library.json` (schema version 1). That exact snapshot's `LICENSE` is MIT; the notice is copied to `custom_components/sensor_guardian/data/BATTERY_NOTES_LICENSE.txt`. The resulting catalogue records source attribution and commit in its JSON metadata. Upstream Python integration code is not copied.

Before copying data into a release:

- pin the exact upstream commit/release and library file;
- inspect the license and notices at that pinned revision;
- retain the MIT license notice and appropriate attribution in the distributed data bundle;
- record snapshot provenance in the generated catalogue;
- review whether all bundled rows/data are covered by that license and note exceptions;
- do not fetch the upstream library at runtime.

The bundled JSON is transformed data: semantic duplicate rows are collapsed, source model/hardware variants and match rules are retained, and every record receives a deterministic Strážca ID. A missing upstream quantity is represented as one, matching Battery Notes' effective default. Power classification is conservative; sealed/irreplaceable/manual/solar labels are not interpreted as mains power. Lifetime is not copied or inferred from this catalogue.
