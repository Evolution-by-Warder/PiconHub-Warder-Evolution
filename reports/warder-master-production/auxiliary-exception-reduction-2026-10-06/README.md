# Auxiliary exception reduction

Derived from the accepted checkpoint `71957fdfdc2ad7deac4908ae3dff2ee588330b73`. This is a read-only clustering of its saved report, candidate PNGs and legacy source ZIPs. No rendering, candidate editing, approval, publication, or engine changes were performed.

- Exceptions: 1431 (REVIEW 1041; SOURCE-UNRESOLVED 390)
- Exact reason entries across five inventory fields: 1318
- Review families: 903
- Source-unresolved families: 320
- Total human-review families: 1223
- Reduced sheets: 306 pages, covering 1223 representative families
- HARMONIC: AUX-RF-0301 (2 identities)
- HELLASAT geometry: PASS

Files: `reason-inventory-{source,transparent,black,white,final}.json`, `family-manifest-01..11.jsonl` (one family object per line), `identity-family-map.csv`, `duplicate-hash-families.json`, `summary.json`, and `reduced-review-sheets/`.

Cause categories are machine-cause tags and may overlap when one identity has more than one affected variant. Families remain grouped only by exact source/output hashes and exact engine status/reason signatures. The sheets contain one representative per family; source-unresolved families show legacy Black/White references and explicitly mark transparent/output as missing.
