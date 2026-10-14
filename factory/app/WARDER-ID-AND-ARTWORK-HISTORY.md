# Warder ID registry and artwork history

## Binding identity rules

**WARDER ID IS PERMANENT. LOGO IS UPDATABLE. HISTORY IS IMMUTABLE.**

> Warder ID identifies the logical station/service identity, not a PNG file and not an Enigma2 service reference.

> A confirmed logo rebrand updates artwork history under the existing Warder ID.

- One logical station/service identity has one unique Warder ID. Transparent,
  black, and white assets share that ID.
- Never change, recycle, or reassign an issued Warder ID. Retired identities
  remain in the registry and retain their ID forever.
- Names, operators, satellites, frequencies, transponders, SIDs, service
  references, source packages, and artwork may change without changing the ID
  only when continuity of the same logical identity is explicitly established.
- A shared logo or name is never identity proof. Ambiguous mappings stay
  ambiguous and do not receive IDs.
- External source adapters are observations only; none is the identity
  authority. The Warder Master remains the artwork authority.
- Approval evidence is a separate evidence document. Its presence, Master PNG
  presence, or a service reference does not alone imply a human approval.

## One canonical Git authority

The sole canonical registry is tracked at
`factory/registry/warder-identity-registry.json` in the Git repository on
`factory-warder-development`. The same file is the only Warder ID namespace.
The Factory fetches a commit-pinned snapshot and may keep a checksum-verified
cache under `11-APP/.factory-data`; that cache is disposable and never an
authority. `master_registry.py` remains a read-only service-reference/artwork
index, not another identity system. `master-approval-evidence.json` remains
separate and is never derived from this registry.

The version 1 registry is JSON with `schema`, `authority`, `id_format`,
`next_sequence`, `issued_ids`, `records`, and append-only `history`. Each
identity record carries its canonical identity key, current and historical
names, provider/operator links, satellite positions, current and historical
service references, current artwork hashes, artwork history, source
provenance, approval-history references, status, creation/first-seen metadata,
and append-only history references.

New IDs use `WARDER-00000001`, `WARDER-00000002`, and so on. Allocation is a
pure operation that requires explicit human identity confirmation plus a
timestamped evidence reference and SHA-256. Sequence numbers only advance;
retired records remain reserved. No ID is generated from a service reference,
station label, provider, satellite, or artwork match.

The migration audit is read-only and classifies exact existing current or
historical service-reference links as `AUTO_MAPPABLE`; multiple links as
`AMBIGUOUS` or `CONFLICT`; and unmatched records as `NEW_ID_REQUIRED`. That
last category is a review requirement, not permission to allocate an ID.
Invalid or unavailable registry state fails closed; offline mode may display
only a checksum-verified cache with its old commit clearly shown. The GUI
identity view is read-only and displays approval status from the Git approval
ledger in the same commit-pinned snapshot.

## Git-native Warder Master store

The complete durable Master is a single Git data set on the development
branch, not a local JSON database:

| Path | Durable contents |
| --- | --- |
| `factory/registry/warder-identity-registry.json` | Warder IDs, identity links, current/historic references, current art hashes and immutable history |
| `factory/registry/master-approval-ledger.json` | Append-only human decisions and exact evidence/artwork hashes |
| `factory/approved-picons/<WARDER-ID>/vNNNN/{transparent,black,white}.png` | Immutable 220×132 RGBA approved artwork versions |
| `factory/registry/*.schema.json` | Machine-readable document schemas |

Each approval event is referenced by the corresponding identity history and
each artwork approval names the exact three asset paths and SHA-256 values.
Rebrands add a new immutable version directory and append previous and new
hashes; no existing PNG is overwritten. A decision that has not reached and
passed readback from Git is `PENDING`, never Master-approved.

`warder_master_store.py` creates one commit containing the registry, approval
ledger, and all new PNG blobs. It requires the expected full development HEAD,
validates the parent-to-child history, checks all PNG bytes and references,
refuses pre-existing asset paths, advances only
`factory-warder-development` without force, and reads the commit back. A
stale HEAD or API failure before ref update leaves the branch unchanged.
`COMMITTED_UNVERIFIED` is not reported as success and must be read back before
retrying; it must not be blindly committed a second time.

The local `master-approval-evidence.json` is only an import aid for historical
evidence. It is no longer used by MASTER-FIRST to mark tasks covered. Coverage
requires identity and artwork approval events from the same verified Git
snapshot and exact artwork hashes. Unknown historical approvals remain
unverified until evidence is migrated.

## Clean-machine recovery and current migration boundary

A clean Git clone contains the registry, approval ledger, schemas, and every
tracked approved asset, so it can reconstruct the durable Warder Master
without a private local database. Windows CI performs a fresh-clone validation
against the cloned files. It does not prove that a particular user's PC or
workspace was restored. The repository audit at the introduction of this
store found no canonical historical Warder ID data or approval ledger in the
development branch; the initial registry and ledger are empty. The existing
service-reference Master index and production artwork have not been copied,
reclassified as approved, or changed by this migration. Those historical
records need a separately verified, reviewable migration from their actual
Git evidence.

Git retains the append-only commits, but an independent backup mirror is an
operational repository-hosting control. This change does not claim to create
an independent backup service; recovery is verified from a clean clone of the
Git repository currently available.

## Append-only changes and confirmed rebrands

Identity changes are represented by evidence-backed events appended to the
registry history. Name, provider, satellite, or service-reference changes
require a human-confirmed identity-continuity assertion. Old names and service
references remain searchable. Identity retirement preserves the record and
its ID.

A rebrand event requires the existing Warder ID, explicit continuity and
official rebrand evidence, QA approval, human approval, and SHA-256 for all
previous and new transparent/black/white variants. The new triplet becomes the
proposed current artwork in the returned registry state while previous hashes
remain in artwork history. The helper never writes production Master assets.
An external OpenATV/Vhannibal graphic difference by itself is not a rebrand.

## Change Watch hook

`normalize_change_watch_event()` accepts `NEW_SERVICE`, `SERVICE_REMOVED`,
`NAME_CHANGE`, `PROVIDER_CHANGE`, `SERVICE_REFERENCE_CHANGE`,
`CONFIRMED_REBRAND`, and `SATELLITE_CHANGE` events with stable event IDs,
source references, timestamps, and evidence SHA-256. It only validates and
normalizes incoming evidence; it never applies changes to the registry or
Master automatically.

## Audit boundary

Before this registry was introduced the repository contained no historical
Warder ID records or Master approval ledger. The initial Git registry is
therefore deliberately empty; no IDs or approvals have been fabricated. The
app reads this tracked authority through `warder_identity_sync.py` and reports
the Git commit used. Migration from local Master data remains read-only until
each identity mapping has evidence. New or changed records are proposed as
reviewed changes to the development branch; concurrent updates must use the
expected parent HEAD and are rejected if the branch moved.
