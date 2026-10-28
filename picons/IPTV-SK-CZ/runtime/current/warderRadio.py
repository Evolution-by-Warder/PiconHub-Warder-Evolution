"""FullHDGlass host adapter for the canonical shared Warder DAB engine."""
import queue
import threading
from .warderRadioCore import warder_engine as engine

DAB_BINDING = {"package_selector": "DAB", "transport": "dab"}

def is_dab(binding):
    return binding == DAB_BINDING

def ready(preferences):
    return bool(preferences.get("resolution") == "220x132"
                and preferences.get("style") in ("transparent", "white", "black")
                and preferences.get("update_mode") in (engine.sync.UPDATE_MODE_SYNC_TV_RADIO,
                    engine.sync.UPDATE_MODE_INCREMENTAL, engine.sync.UPDATE_MODE_REPLACE_ALL)
                and engine.sync.validate_destination(preferences.get("destination")))

class DABRunner(engine.PiconRunner):
    """Run only DAB while retaining native position filtering for mixed tasks."""
    def stage_dab(self, preferences, stages):
        selected = dict(preferences)
        selected["dab_only"] = not bool(selected.get("positions"))
        return super().stage_dab(selected, stages)

class Worker:
    def __init__(self, preferences, opener=engine.network_open, enigma2_dir="/etc/enigma2", lock_path="/tmp/piconhub-picons.lock"):
        if not ready(preferences):
            raise ValueError("DAB / DAB+: 220x132")
        self.preferences = dict(preferences, include_dab=True, dab_only=True)
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
