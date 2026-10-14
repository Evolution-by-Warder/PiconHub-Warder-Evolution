# Warder ID permanence and artwork history

## Binding identity rules

**WARDER ID IS PERMANENT. LOGO IS UPDATABLE. HISTORY IS IMMUTABLE.**

- Every approved station identity has one unique Warder ID. Never change,
  recycle, or reassign an existing ID. Retired identities and their IDs remain
  historically addressable.
- Keep the station identity, operator/satellite links, current and historical
  service references, graphic variants, sources, and approval history
  traceable from that canonical ID.
- A station name, operator, or logo may change without changing the Warder ID
  only when evidence establishes continuity of the same station identity.
- A shared logo or shared name is artwork/name evidence, never identity proof.
  Ambiguous service mappings require review.
- An OpenATV/Vhannibal artwork difference alone is not rebrand evidence.
  Existing approved Master artwork cannot be overwritten automatically.

## Current repository boundary

The tracked Factory `master_registry.py` indexes the read-only PiconHub tree by
exact Enigma2 service-reference filename and records position, provider, style,
path, and SHA-256. It does not define, store, allocate, or migrate Warder IDs.
No alternative ID is created here. The runtime emits a read-only
`warder-identity-audit-<run>.json`; until a canonical Warder ID authority is
provided, the correct result is `WARDER_ID_SCHEMA_NOT_PRESENT`, not an empty
successful audit. The audit adapter accepts canonical records but never
generates IDs or writes the Master.

## Confirmed logo update lifecycle

1. Resolve the existing Warder ID from its canonical authority.
2. Record evidence that the station identity continues and that an official
   rebrand occurred. A source feed or changed image is insufficient.
3. Prepare a candidate transparent/black/white triplet and preserve its source
   hashes. Run technical and visual QA.
4. Obtain an explicit human approval for that exact evidence and all approved
   variant hashes.
5. Append an immutable history event containing the same Warder ID, previous
   and new variant SHA-256 values, evidence reference/hash, approval time, and
   QA/approval flags.
6. Only a separate authorized Master update may change current graphics. The
   Factory proposal/history helper does not perform that update.

Unconfirmed artwork changes are recorded as `UNVERIFIED_ARTWORK_CHANGE` for
audit and do not reopen a complete approved service as a mandatory review by
themselves. Explicit evidence can produce `CONFIRMED_REBRAND`, which still
requires QA and approval. Existing workflow categories map to the current
MASTER-FIRST states; no second ID registry is introduced.

## Read-only identity audit

The normalized audit input is an adapter over records from the canonical
authority, not a new storage schema. It checks current-ID uniqueness,
historical reassignment/reuse, link collections, history references, and
retirement. A missing canonical source is reported as unavailable. It never
renumbers or repairs data. Do not feed service-reference-only Master indexes
as if they were Warder ID records.
