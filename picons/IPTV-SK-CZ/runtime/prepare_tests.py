"""Prepare test-only imports from the same checkout's production shared core."""
from pathlib import Path
import shutil
R=Path(__file__).resolve().parent
repo=next((p for p in R.parents if (p/'plugin/src/Plugins/Extensions/WarderPiconHub').is_dir()),None)
if repo is None:
    raise SystemExit('Run inside the PiconHub repository checkout')
source=repo/'plugin/src/Plugins/Extensions/WarderPiconHub'
for name in ('warder_skin_sync.py','warder_dab.py','radio_references.py','warder_i18n.py'):
    shutil.copy2(source/name,R/'patched'/name)
shutil.copy2(source/'data/skin-menu.json',R/'patched/data/skin-menu.json')
print('Prepared tests with the production shared modules; no translation stub')
