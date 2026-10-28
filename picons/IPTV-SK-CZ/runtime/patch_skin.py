"""Derive the FullHDGlass host adapter without duplicating the downloader."""
from pathlib import Path
import shutil
R = Path(__file__).resolve().parent
s = (R/'current/warderRadio.py').read_text()
def change(old, new):
    global s
    assert s.count(old) == 1, (old, s.count(old))
    s = s.replace(old, new)
change('canonical shared Warder DAB engine', 'canonical shared Warder radio engine')
change('DAB_BINDING = {"package_selector": "DAB", "transport": "dab"}', '''DAB_BINDING = {"package_selector": "DAB", "transport": "dab"}
IPTV_BINDING = {"package_selector": "IPTV-SK-CZ", "transport": "iptv"}

def is_iptv(binding):
    return binding == IPTV_BINDING

def is_radio(binding):
    return is_dab(binding) or is_iptv(binding)

def selected(preferences):
    return bool(preferences.get("include_dab") or preferences.get("include_iptv"))

def label(preferences, translate=lambda value: value):
    return ", ".join(([translate("IPTV radios SK/CZ")] if preferences.get("include_iptv") else [])
                     + (["DAB / DAB+"] if preferences.get("include_dab") else []))''')
change('preferences.get("resolution") == "220x132"', '''preferences.get("resolution") in (("220x132",) if preferences.get("include_dab")
                else ("50x30", "220x132", "400x240"))''')
change('"""Run only DAB while retaining native position filtering for mixed tasks."""', '"""Run shared radio packages after the host completes its native tasks."""')
change('selected["dab_only"] = not bool(selected.get("positions"))', 'selected["dab_only"] = not bool(selected.get("positions") or selected.get("include_iptv"))')
change('raise ValueError("DAB / DAB+: 220x132")', 'raise ValueError("Unsupported radio picon preferences")')
change('self.preferences = dict(preferences, include_dab=True, dab_only=True)', '''dab = bool(preferences.get("include_dab"))
        iptv = bool(preferences.get("include_iptv"))
        if not (dab or iptv):
            raise ValueError("No radio package selected")
        self.preferences = dict(preferences, dab_only=dab and not iptv,
                                iptv_only=iptv and not dab, radio_only=dab and iptv)''')
(R/'patched/warderRadio.py').write_text(s)
print('Patched FullHDGlass radio host adapter')
