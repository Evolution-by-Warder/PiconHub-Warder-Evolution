# DAB+ GitHub Actions diagnosis (2026-10-27)

The `Universal radio parser` workflow passed on commit `36ebd153`. The `PiconHub plugin core` workflow failed because two **new DAB test modules** attempted to import scripts at `picons/DAB/build_catalog.py` and `picons/DAB/install_verified.py`, but those files were absent in its checkout. The paths computed by `Path(__file__).resolve().parents[2]` are correct for `plugin/tests` and should not be changed.

This is a **CI checkout/content availability issue**, not a demonstrated defect in radio parsing. Do not hide it by skipping tests. Compare the exact checked-out PR merge tree with the feature branch tree and check repository sparse-checkout, .gitignore and workflow trigger context before modifying test paths.

Release gate remains closed until **both** workflows pass on the same feature commit and receiver smoke tests succeed. Do not merge PR #11 or publish preview placeholders as verified MASTER V9 artwork.
