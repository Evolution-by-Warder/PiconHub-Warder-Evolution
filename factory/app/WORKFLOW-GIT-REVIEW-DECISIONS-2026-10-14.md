# Git-native review decisions — 2026-10-14

## Change in v0.2.57

The embedded review gallery now routes explicit group decisions through the
existing Git transaction writer. A group is not removed from the active view
when the owner clicks a decision. It remains visible while the local batch is
PENDING/UNSAVED and is retired from the active view only after the Git writer
confirms a development-branch commit and its readback. The legacy local
group-decision ledger is no longer used by this GUI path.

This does not turn `APPROVED_FOR_REVIEW` into an identity or artwork approval.
Creating a Warder ID still requires an explicit owner-confirmed identity
decision. Master artwork still requires explicit artwork approval and a valid
transparent/black/white triplet. Registry, ledger, checkpoint, and approved
assets remain governed by the existing atomic writer and development-branch
compare-and-swap check.

## Evidence processed from the existing archive and workspace checkpoint

The previously verified five-volume `02-ORIGINALS` inventory is retained at
`diagnostic-checkpoints/originals-and-queue-audit-20261014.json`; it records
190,435 decoded PNG, 9,336 source-complete PiconHub triplets, 33,697 parsed
service references, 583 provider path labels, and 39 satellite path labels.
The uploaded Windows workspace snapshot records 9,932 pending review tasks
(4,054 identity, 5,877 artwork, 1 technical QA). This change did not re-run
the large archive scan or alter any source bytes.

The source inventory provides technical references, artwork hashes, source
families, and provider/satellite path labels. It does not provide an
authoritative broadcaster service list or dependable station names. The
read-only PiconHub Master snapshot maps artwork to service references but
does not supply a Warder identity/approval ledger. Therefore no logical
identity, Warder ID, historical approval, or artwork approval can be safely
inferred from this evidence alone. No Registry or approval event was added.
Repeated pixels across different service references remain separate identity
decisions.

The four fully transparent `ilsole24ore tv` source files remain a blocked
technical QA exception. The source bytes and all historical evidence remain
untouched. The archive inventory's pixel/hash duplicates are technical
deduplication opportunities, not approval evidence.

## Verification boundary

The regression tests exercise Git routing and the UNSAVED behavior in
isolation. Windows Actions must pass before this candidate is considered ready.
No action in this commit writes to `warder-master-production`, the production
Master, or the user's D: workspace. A real-PC decision and successful
GitHub write still need to be verified in the user's installed Factory.
