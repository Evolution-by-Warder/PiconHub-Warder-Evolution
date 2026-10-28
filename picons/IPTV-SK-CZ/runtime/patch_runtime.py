from pathlib import Path
import shutil
R=Path(__file__).resolve().parent;out=R/'patched';out.mkdir(exist_ok=True)
def change(s,old,new,count=1):
 assert s.count(old)==count,(old,s.count(old));return s.replace(old,new)
s=(R/'current/warder_engine.py').read_text()
s=change(s,'from . import warder_dab as dab','from . import warder_dab as dab\nfrom . import warder_iptv as iptv')
s=change(s,'or dab.trusted_url(url)):', 'or dab.trusted_url(url) or iptv.trusted_url(url)):')
s=change(s,'if dab.trusted_url(url) and response.geturl() != url:', 'if (dab.trusted_url(url) or iptv.trusted_url(url)) and response.geturl() != url:')
anchor='    def run(self, preferences):'
method='''    def stage_iptv(self, prefs, stages):
        self.check_cancel()
        label = _(iptv.LABEL)
        self.event("stage", _("Načítavam katalóg") + " " + label)
        try:
            document = iptv.read_manifest(self.opener)
            planned = iptv.plan(document, prefs, self.enigma2_dir)
        except (ValueError, TypeError) as exc:
            raise PiconError(_("Neplatný katalóg: ") + label) from exc
        if planned is None:
            if prefs.get("iptv_only"):
                raise PiconError(label + _(" • zatiaľ nedostupné"))
            self.event("stage", label + _(" • zatiaľ nedostupné"))
            return
        queue, job = planned
        stage = Stage(queue)
        stages.append(stage)
        if shutil.disk_usage(stage.target).free < job["bytes"] * 3 + 8 * 1024 * 1024:
            raise PiconError(_("Na cieľovom úložisku nie je dosť voľného miesta."))
        archive = stage.work / "iptv-sk-cz.zip"
        self.download(job, archive)
        self.event("stage", _("Overujem a rozbaľujem ") + label)
        try:
            iptv.unpack(stage, archive, job, self.check_cancel)
        except (ValueError, TypeError, zipfile.BadZipFile) as exc:
            raise PiconError(_("Neplatný katalóg: ") + label) from exc
        self.event("processed", label)
        archive.unlink()

'''
s=change(s,anchor,method+anchor)
s=change(s,'        planned = dab.plan(document, prefs, self.enigma2_dir)', '        dab_preferences = dict(prefs)\n        if prefs.get("radio_only") and not prefs.get("positions"):\n            dab_preferences["dab_only"] = True\n        planned = dab.plan(document, dab_preferences, self.enigma2_dir)')
s=change(s,'all(p.get("dab_only") for p in preferences)', 'all(p.get("dab_only") or p.get("iptv_only") or p.get("radio_only") for p in preferences)')
s=change(s,'                    if prefs.get("dab_only"):', '''                    if prefs.get("radio_only"):
                        if prefs.get("include_dab"):
                            self.stage_dab(prefs, stages)
                        if prefs.get("include_iptv"):
                            self.stage_iptv(prefs, stages)
                        continue
                    if prefs.get("iptv_only"):
                        self.stage_iptv(prefs, stages)
                        continue
                    if prefs.get("dab_only"):''')
s=change(s,'                    if prefs.get("include_dab"):\n                        self.stage_dab(prefs, stages)', '                    if prefs.get("include_dab"):\n                        self.stage_dab(prefs, stages)\n                    if prefs.get("include_iptv"):\n                        self.stage_iptv(prefs, stages)')
(out/'warder_engine.py').write_text(s)
s=(R/'current/warder_model.py').read_text()
s=change(s,'SATELLITES = (("DAB", "DAB / DAB+"),)', 'SATELLITES = (("IPTV-SK-CZ", "IPTV rádiá SK/CZ"), ("DAB", "DAB / DAB+"))')
s=change(s,'return dict(SATELLITES).get(selector, str(selector))','return _(dict(SATELLITES).get(selector, str(selector)))')
s=change(s,'    include_dab = "DAB" in selectors','    include_dab = "DAB" in selectors\n    include_iptv = "IPTV-SK-CZ" in selectors')
s=change(s,'    bindings = [sync.task_binding_for_package_selector(value) for value in selectors if value != "DAB"]', '''    if include_iptv and profile.method.value == "sync_tv":
        raise ValueError(_("Vyberte režim aktualizácie.") + " " + _("IPTV rádiá SK/CZ") + ": " + _("Podľa TV a rádia"))
    bindings = [sync.task_binding_for_package_selector(value) for value in selectors if value not in ("DAB", "IPTV-SK-CZ")]''')
s=change(s,'    preferences.update(include_dab=include_dab, dab_only=include_dab and not bindings)', '''    preferences.update(include_dab=include_dab, include_iptv=include_iptv,
                       dab_only=include_dab and not include_iptv and not bindings,
                       iptv_only=include_iptv and not include_dab and not bindings,
                       radio_only=include_iptv and include_dab and not bindings)''')
(out/'warder_model.py').write_text(s)
s=(R/'current/warder_gui.py').read_text()
s=change(s,'        if not resolution or resolution == "220x132":available.add("DAB")','        if not resolution or resolution == "220x132":available.add("DAB")\n        available.add("IPTV-SK-CZ")')
s=change(s,'for s in values if s != "DAB"]','for s in values if s not in ("DAB", "IPTV-SK-CZ")]')
(out/'warder_gui.py').write_text(s)
shutil.copy2(R/'warder_iptv.py',out/'warder_iptv.py')
print('Patched 4 runtime modules')
