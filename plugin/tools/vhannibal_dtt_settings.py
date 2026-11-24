"""Match exact Italian Enigma2 service references against the current Motor/DTT settings."""
import hashlib
from io import BytesIO
import re
from urllib.request import urlopen
from zipfile import ZipFile

URL = "https://www.vhannibal.net/download_setting.php?id=13&action=download"
REF = re.compile(r"1_0_[0-9A-F]{1,4}(?:_[0-9A-F]{1,4}){3}_[0-9A-F]{1,8}_0_0_0", re.I)
BOUQUETS = {"01": ("Digitale Terrestre", 0xEEEE), "59": ("Italia Dtt Nazionali", 90),
            "60": ("Italia Dtt Regionali", 90), "81": ("Italia Dtt Nazionali", 3550),
            "82": ("Italia Dtt Regionali", 3550)}


def normalize(ref):
    return "_".join(format(int(v, 16), "X") for v in ref.split("_"))


def settings_index(raw):
    refs = {}
    with ZipFile(BytesIO(raw)) as archive:
        names = archive.namelist()
        databases = [n for n in names if re.fullmatch(r"Vhannibal Motor Dtt Italia [^/]+/lamedb", n, re.I)]
        if len(databases) != 1 or len(names) != len(set(names)):
            raise ValueError("Ambiguous Motor DTT Italia settings")
        folder = databases[0].rsplit("/", 1)[0] + "/"

        def lines(name):
            info = archive.getinfo(folder + name)
            if info.file_size > 8_000_000:
                raise ValueError("Oversized settings file")
            return archive.read(info).decode("utf-8", "replace").splitlines()

        db = lines("lamedb")
        if db[0] != "eDVB services /4/":
            raise ValueError("Unsupported lamedb format")
        records = db[db.index("services") + 1:]
        end = records.index("end")
        if end % 3:
            raise ValueError("Incomplete lamedb services")
        services = {}
        for i in range(0, end, 3):
            sid, ns, tsid, onid, typ, *_ = records[i].split(":")
            ref = normalize(f"1_0_{int(typ):X}_{sid}_{tsid}_{onid}_{ns}_0_0_0")
            services[ref] = records[i + 1]
        for number, (title, orbital) in BOUQUETS.items():
            rows = lines("userbouquet.dbe" + number + ".tv")
            if rows[0].strip().casefold() != ("#NAME " + title).casefold():
                raise ValueError("Bouquet identity changed")
            found = 0
            for line in rows:
                if not line.startswith("#SERVICE 1:0:"):
                    continue
                ref = line.split(" ", 1)[1].rstrip(":").replace(":", "_")
                if not REF.fullmatch(ref):
                    raise ValueError("Unexpected DVB reference in Italian bouquet")
                ref = normalize(ref)
                if int(ref.split("_")[6], 16) >> 16 != orbital:
                    raise ValueError("Italian bouquet orbital position changed")
                if ref not in services:
                    raise ValueError("Bouquet service missing from lamedb")
                refs[ref] = services[ref]
                found += 1
            if not found:
                raise ValueError("Empty Italian bouquet")
    return hashlib.sha256(raw).hexdigest(), refs


def current_settings():
    with urlopen(URL, timeout=40) as response:
        raw = response.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError("Oversized settings archive")
    return settings_index(raw)
