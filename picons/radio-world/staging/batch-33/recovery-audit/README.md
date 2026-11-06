# Batch 33: read-only recovery audit

This checkpoint uses only the existing authorized GitHub connection and GitHub Actions managed service credentials. Browser sign-in, user tokens, repeated Base64 transfers and production publication are prohibited.

- `expected-payloads.json`: exact SHA256, Git blob SHA1, length and archive/reference/variant membership for 5,400 approved PNG entries (5,220 unique byte sequences). Metadata only; no PNG bytes or substitute artwork.
- `preservation-proof.json`: all 171 existing local country ZIPs were read and matched against the previously saved preflight; ZIP CRC passed. Nothing was rewritten.
- `held-identity-review.json`: exact hold causes for 14 HDF references. Their names/streams/groups match the historical records; the issue is HDF versus country-group assignment, not changed names. These remain held, and all nine approved PNG hashes are retained.
- `audit_remote_inputs.py`: scans current main and Radio branch tips, Radio ZIP objects, all accessible Release listings and available Radio Actions artifacts. Each recovered PNG is SHA256 checked. The report identifies bounded-scan omissions and errors explicitly. It does not claim that unreadable, expired or unscanned historical data are absent.

The workflow has `contents: read` and `actions: read`; it cannot commit country packages or publish Releases. It saves an audit artifact containing a machine-readable missing-input list and any exact recovered PNG bytes. Missing inputs are a valid audit outcome, not successful archive recovery. Full original ZIP reproduction is not claimed until each original archive size and SHA256 matches.

The original source archives and all 171 country ZIPs remain local unless a remote artifact/commit is explicitly verified. The existing import workflow is not triggered: `source-ready.json` is deliberately absent. No stable Radio code, production country index, skin, satellite picons or Vhannibal files change.
