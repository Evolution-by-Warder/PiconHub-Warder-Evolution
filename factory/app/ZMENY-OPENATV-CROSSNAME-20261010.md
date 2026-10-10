# OpenATV: presná SHA-256 zhoda medzi rôznymi názvami

- `openatv_crossname.py` vytvára len neoverené kandidátne väzby medzi názvami s identickými bajtmi PNG.
- Konfliktné kandidátne service-reference sú označené ako AMBIGUOUS_EXACT_SHA.
- Nepriraďuje service-reference, nemení klasifikáciu ani produkčný Warder Master.
- `openatv_triage.py` zobrazuje kandidátne väzby v existujúcom reporte.
- `engine.py` zaznamená počty a uloží ich do registry-matches JSON.
- Zámerne nejde o riešenie staníc bez akéhokoľvek dôkazu identity.
- 171 lokálnych testov úspešných; výsledok na Windows zdrojoch zatiaľ neoverený.
