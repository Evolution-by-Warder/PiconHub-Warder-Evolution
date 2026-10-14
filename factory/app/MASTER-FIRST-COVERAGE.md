# MASTER-FIRST coverage and approval migration

The Factory reads the Warder Master as the source of truth. It does not treat a
PNG, a service reference, a filename match, or pixel equality as proof of
approval. With no explicit local evidence, Master services are reported as
`KNOWN_UNAPPROVED`; no artwork task is suppressed by this coverage gate.

## Local evidence file

The optional file is kept only in the user's workspace:

`D:\WARDER-PICON-FACTORY\03-REGISTRY\master-approval-evidence.json`

It is never generated from the Master index, checked into this repository,
uploaded to GitHub, or written by the engine. The engine reads it without
modification and binds every entry to the exact current Master commit and
variant SHA-256 values.

Minimal schema:

```json
{
  "schema": 1,
  "master_commit": "<full exact Master snapshot commit>",
  "services": {
    "<exact service reference>": {
      "identity_verified": true,
      "artwork_approved": true,
      "approval_ref": "<existing human approval record ID>",
      "evidence_sha256": "<SHA-256 of that immutable approval record>",
      "variants": {
        "transparent": "<current Master PNG SHA-256>",
        "black": "<current Master PNG SHA-256>",
        "white": "<current Master PNG SHA-256>"
      }
    }
  }
}
```

Only put variants in `variants` for which the approval record proves approval
and the recorded hash matches the current Master. The full three-style set is
required for `APPROVED_COMPLETE`; a smaller proven set is `APPROVED_INCOMPLETE`.
The app does not infer missing approval. A changed commit, changed hash,
conflicted Master style, missing approval reference, or invalid hash fails
closed and keeps affected source candidates in review. A manifest populated
with guesses is not a safe migration.

## Filtering and audit

Only pending `ARTWORK_REVIEW` tasks for an exact `APPROVED_COMPLETE` service can
move to `COVERED_BY_APPROVED_MASTER`. The original review ID, source
observations, candidate hashes, Master evidence hash, and a coverage evidence
hash remain in that run's review queue audit and anonymized review-evidence
export. Identity-review work is not removed by artwork coverage. Existing
decisions are left intact. New services and different service references are
never merged because of common operator, name, or logo.
