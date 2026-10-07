# Auxiliary coverage impact

Pinned current runtime archive inventory compared by auxiliary filename identity with strict publishable safe triads.

- Provider: 1335 current identities; 172 safe; 1163 absent from safe-only tree.
- Satellite: 269 current identities; 1 safe; 268 absent from safe-only tree.
- Safe-only migration: NOT VIABLE. Hybrid fallback: REQUIRED.
- B (`LEGACY-ONLY-IF-SAFE-TREE`) is the exclusion umbrella; C and D subtypes separate those with a current transparent file from black/white-only identities.

The hybrid document is a proposal only. Current FullHDGlass consumer behavior is preserved by placing safe triads in the `*_220x132/` priority directory and leaving base legacy directories intact as fallback. No production ZIPs, downloads manifests, or consumer code were changed.
