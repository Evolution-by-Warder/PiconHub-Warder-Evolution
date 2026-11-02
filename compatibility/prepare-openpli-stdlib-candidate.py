#!/usr/bin/env python3
"""Stage an isolated receiver candidate after the source regression suite."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.1.39-test3'
NAME='PiconHub'
RUNTIME=ROOT/'plugin/src/Plugins/Extensions/WarderPiconHub'
notes={"sk":"OpenPLi: opravená inštalácia a štart aktualizácií bez modulu dataclasses. Zachované doterajšie opravy pre OpenATV/GLES/WQHD.",
       "en":"OpenPLi: install/start updater without dataclasses. Existing OpenATV/GLES/WQHD repairs retained."}
(RUNTIME/'version.txt').write_text(VERSION+'\n')
path=ROOT/'plugin/project.json';data=json.loads(path.read_text());data['development_version']=VERSION
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
path=ROOT/'plugin/update/RELEASE-NOTES.i18n.json';data=json.loads((ROOT/'compatibility/openpli-stdlib-previous-history.json').read_text())
data.update(version=VERSION,notes=notes)
data['entries']=[{'version':VERSION,'date':'02.11.2026','notes':notes}]+[entry for entry in data.get('entries',[]) if entry.get('version')!=VERSION]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print(NAME,VERSION,'staged; production manifests unchanged')
