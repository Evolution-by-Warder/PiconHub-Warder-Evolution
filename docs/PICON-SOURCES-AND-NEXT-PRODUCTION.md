# Warder external picon sources and production roadmap

## Authority

The **Warder Master Registry and Warder QC/assimilation policy** remain authoritative for service identity, Warder IDs, accepted artwork and maintained outputs.

External projects are candidate sources only. No upstream source is automatically considered correct or better than the current Warder master.

## Candidate sources

### Vhannibal

Official discovery page: https://www.vhannibal.net/

Use current Vhannibal Motor picons as source artwork/candidates. The matching Motor settings package may be used as supporting metadata for service references, names, providers and satellite positions.

### OpenATV picon ecosystem

OpenATV/OpenATV-picons/picons ecosystem is an additional candidate source for expanding and improving the Warder collection.

Current intended use is **transparent picon artwork**. This fits the Warder pipeline because transparent artwork is the source/master layer from which Warder creates and maintains its own presentation variants/backgrounds.

OpenATV material is not authoritative. A candidate is useful when it:
- represents a service missing from Warder;
- contains a newer/current logo;
- is demonstrably cleaner or higher quality than the current Warder artwork;
- helps identify a service or artwork change that needs review.

## Assimilation pipeline

External transparent candidate -> identify/match service -> compare with current Warder transparent master -> classify (same/new/changed/better/problematic) -> automatic QC -> manual review only where required -> accepted Warder transparent master -> Warder-generated transparent/black/white outputs.

Rules:
- preserve the existing Warder ID for an existing service;
- never replace production automatically;
- never accept an upstream logo merely because it is newer;
- do not manufacture identity matches when evidence is ambiguous;
- record source provenance and input hashes;
- commit every manually approved batch as a durable checkpoint before proceeding.

## Next project task

The next major PiconHub task is to start the **real multi-source audit and production pipeline** rather than further planning:

1. establish a clean current Warder baseline;
2. ingest current external candidate data, beginning with current Vhannibal and OpenATV transparent sources;
3. build deterministic inventory and service matching;
4. classify existing/new/changed/better/missing/ambiguous candidates;
5. run image/QC comparison;
6. present only candidates requiring human visual judgement;
7. immediately commit each approved batch with provenance and hashes;
8. generate/maintain Warder presentation variants from the accepted transparent masters;
9. integrate into Registry/Production only through the controlled Warder process.

Historical/lost Vhannibal working material must not be treated as trusted current input. New assimilation runs start from current upstream inputs and the current Warder baseline.
