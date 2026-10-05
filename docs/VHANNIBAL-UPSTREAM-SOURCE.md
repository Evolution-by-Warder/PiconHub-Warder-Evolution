# Official Vhannibal upstream source

## Authority

Official upstream landing page:

https://www.vhannibal.net/

This page is the authoritative discovery point for the current Vhannibal packages used as a source-only enrichment input for Warder.

For a clean Vhannibal -> Warder assimilation run, discover the current download links from the official landing page rather than reusing an older locally named ZIP.

Required upstream inputs:

- current **Vhannibal Motor** settings package
- current **Picon Vhannibal Motor** package

## Policy

- Vhannibal is an upstream/source-only enrichment layer, not the Warder registry authority.
- Always resolve the current package links from the official landing page at the start of a new import.
- Record the observed upstream publication metadata and hashes of downloaded inputs in the import checkpoint.
- Never change an existing Warder ID merely because Vhannibal changed.
- Never overwrite Warder production automatically.
- New or changed candidates must pass Warder matching/QC and required manual review before integration.
- Every approved batch must be committed as a durable checkpoint before continuing to the next batch.

This document records the stable upstream discovery source. Individual download URLs may change and therefore are intentionally not pinned here.
