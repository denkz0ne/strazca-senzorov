# Third-party data and attribution

The project intends to use the Battery Notes device model library only as a one-time conversion/import source. The upstream repository identified is [andrew-codechimp/HA-Battery-Notes](https://github.com/andrew-codechimp/HA-Battery-Notes), whose repository currently declares the MIT license.

Before copying data into a release:

- pin the exact upstream commit/release and library file;
- inspect the license and notices at that pinned revision;
- retain the MIT license notice and appropriate attribution in the distributed data bundle;
- record snapshot provenance in the generated catalogue;
- review whether all bundled rows/data are covered by that license and note exceptions;
- do not fetch the upstream library at runtime.

This file records the intended process, not a completed import. No upstream database is included yet.
