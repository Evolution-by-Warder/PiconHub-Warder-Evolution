"""FullHDGlass host adapter for the canonical shared Warder radio engine."""
import queue
import threading
from .warderRadioCore import warder_engine as engine

DAB_BINDING = {"package_selector": "DAB", "transport": "dab"}
IPTV_BINDING = {"package_selector": "IPTV-SK-CZ", "transport": "iptv"}

def is_iptv(binding):
    return binding == IPTV_BINDING

def is_radio(binding):
    return is_dab(binding) or is_iptv(binding)

def selected(preferences):
    return bool(preferences.get("include_dab") or preferences.get("include_iptv"))

def label(preferences, translate=None):
    return ", ".join(([engine._("IPTV rádiá SK/CZ")] if preferences.get("include_iptv") else [])
                     + (["DAB / DAB+"] if preferences.get("include_dab") else []))

def is_dab(binding):
    return binding == DAB_BINDING

def ready(preferences):
    return bool(preferences.get("resolution") in (("220x132",) if preferences.get("include_dab")
                else ("50x30", "220x132", "400x240"))
                and preferences.get("style") in ("transparent", "white", "black")
                and preferences.get("update_mode") in (engine.sync.UPDATE_MODE_SYNC_TV_RADIO,
                    engine.sync.UPDATE_MODE_INCREMENTAL, engine.sync.UPDATE_MODE_REPLACE_ALL)
                and engine.sync.validate_destination(preferences.get("destination")))

class DABRunner(engine.PiconRunner):
    """Run shared radio packages after the host completes its native tasks."""
    def stage_dab(self, preferences, stages):
        selected = dict(preferences)
        selected["dab_only"] = not bool(selected.get("positions") or selected.get("include_iptv"))
        return super().stage_dab(selected, stages)

class Worker:
    def __init__(self, preferences, opener=engine.network_open, enigma2_dir="/etc/enigma2", lock_path="/tmp/piconhub-picons.lock"):
        if not ready(preferences):
            raise ValueError("Unsupported radio picon preferences")
        dab = bool(preferences.get("include_dab"))
        iptv = bool(preferences.get("include_iptv"))
        if not (dab or iptv):
            raise ValueError("No radio package selected")
        self.preferences = dict(preferences, dab_only=dab and not iptv,
                                iptv_only=iptv and not dab, radio_only=dab and iptv)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.runner = DABRunner(opener=opener, event=lambda *value: self.events.put(("event", value)),
                                cancel=self.cancel, enigma2_dir=enigma2_dir, lock_path=lock_path)

    def run(self):
        try:
            result = self.runner.run([self.preferences])
        except Exception as error:
            self.events.put(("error", str(error)))
        else:
            self.events.put(("done", result))

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def drain(self):
        result = []
        while True:
            try:
                result.append(self.events.get_nowait())
            except queue.Empty:
                return result
