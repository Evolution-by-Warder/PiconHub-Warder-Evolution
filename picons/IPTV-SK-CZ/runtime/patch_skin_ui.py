"""Prepare reviewed UI edits separately from the production skin source."""
from pathlib import Path
R = Path(__file__).resolve().parent
source = R.parents[1]/'radio-artwork-work/source/package-root/usr/lib/enigma2/python/Plugins/Extensions/setupGlass17/plugin.py'
s = source.read_text()
def change(old, new, count=1):
    global s
    assert s.count(old) == count, (old, s.count(old))
    s = s.replace(old, new)
change('not self.warderPiconPrefs.get("include_dab"):', 'not warderRadio.selected(self.warderPiconPrefs):')
change('bool(self.warderPiconPrefs.get("include_dab") and not warderPiconSync.valid_task_selection(self.warderPiconPrefs))', 'bool(warderRadio.selected(self.warderPiconPrefs) and not warderPiconSync.valid_task_selection(self.warderPiconPrefs))')
change('(self.warderPiconPrefs.get("include_dab") and not warderRadio.ready(self.warderPiconPrefs))', '(warderRadio.selected(self.warderPiconPrefs) and not warderRadio.ready(self.warderPiconPrefs))')
change('bool(prepared and self.warderPiconPrefs.get("include_dab"))', 'bool(prepared and warderRadio.selected(self.warderPiconPrefs))')
change('if prefs.get("include_dab"):\n\t\t\tlabels["wp-pos"] = _("Satellite positions") + ": DAB / DAB+"', 'if warderRadio.selected(prefs):\n\t\t\tlabels["wp-pos"] = _("Satellite positions") + ": " + warderRadio.label(prefs, _)')
change('if self.warderPiconPrefs.get("include_dab"):selected.append(dict(warderRadio.DAB_BINDING))', 'if self.warderPiconPrefs.get("include_dab"):selected.append(dict(warderRadio.DAB_BINDING))\n\t\t\tif self.warderPiconPrefs.get("include_iptv"):selected.append(dict(warderRadio.IPTV_BINDING))')
change('include_dab = any(warderRadio.is_dab(item) for item in answer)', 'include_dab = any(warderRadio.is_dab(item) for item in answer)\n\t\tinclude_iptv = any(warderRadio.is_iptv(item) for item in answer)')
change('native = [item for item in answer if not warderRadio.is_dab(item)]', 'native = [item for item in answer if not warderRadio.is_radio(item)]')
change('self.warderPiconPrefs["include_dab"] = include_dab', 'self.warderPiconPrefs["include_dab"] = include_dab\n\t\tself.warderPiconPrefs["include_iptv"] = include_iptv')
change('elif include_dab:\n\t\t\tlabel = _("Satellite positions") + ": DAB / DAB+"', 'elif include_dab or include_iptv:\n\t\t\tlabel = _("Satellite positions") + ": " + warderRadio.label(self.warderPiconPrefs, _)')
change('if positions or include_dab:', 'if positions or include_dab or include_iptv:')
change('self.dwnJob = "DAB / DAB+"', 'self.dwnJob = warderRadio.label(self.warderDABTaskSnapshot or {}, _)')
change('_("ERROR") + ": DAB / DAB+: "', '_("ERROR") + ": " + self.dwnJob + ": "', 2)
change('"DAB / DAB+: %d%%" % percent', 'self.dwnJob + ": %d%%" % percent')
change('if not warderRadio.is_dab(item)]))', 'if not warderRadio.is_radio(item)]))')
change('if any(warderRadio.is_dab(item) for item in (selected or [])):self.selected.add("DAB")', 'if any(warderRadio.is_dab(item) for item in (selected or [])):self.selected.add("DAB")\n\t\tif any(warderRadio.is_iptv(item) for item in (selected or [])):self.selected.add("IPTV-SK-CZ")')
change('self.list.addSelection("DAB / DAB+", dict(warderRadio.DAB_BINDING), 0,', 'self.list.addSelection(warderRadio.label({"include_iptv": True}), dict(warderRadio.IPTV_BINDING), -1, "IPTV-SK-CZ" in self.selected, PLUGINPATH + "images/selectors/IPTV-SK-CZ.png")\n\t\tself.list.addSelection("DAB / DAB+", dict(warderRadio.DAB_BINDING), 0,')
compile(s, str(source), 'exec')
(R/'patched/skin-plugin.py').write_text(s)
print('Prepared skin picker, mixed selection and progress UI')
