"""GUI-independent menu, profile and clock rules for the Warder interface."""
from .warder_i18n import _, normalize_language
import datetime
import json
import pathlib

from . import warder_skin_sync as sync

ROOT = pathlib.Path(__file__).parent
MENU = json.loads((ROOT / "data/skin-menu.json").read_text())["selectors"]
SATELLITES = (("DAB", "DAB / DAB+"),) + tuple((row["selector"], row["label"]) for row in MENU if row["position"] == "DTT") + tuple((row["selector"], row["label"]) for row in MENU if row["position"] != "DTT")
RESOLUTIONS = tuple((value, label.split(" - ")[0]) for value, label in sync.CHANNEL_RESOLUTION_CHOICES)
STYLES = (("transparent", "Transparent"), ("white", "Biele"), ("black", "Čierne"))
METHODS = (("sync_tv", "Podľa TV bouquetov"), ("sync_tv_radio", "Podľa TV a rádia"),
           ("all_inc", "Doplniť a aktualizovať všetky"), ("all", "Úplne nahradiť vybrané pozície"))
METHOD_MAP = dict(zip(("sync_tv", "sync_tv_radio", "all_inc", "all"),
                      (sync.UPDATE_MODE_SYNC_TV, sync.UPDATE_MODE_SYNC_TV_RADIO,
                       sync.UPDATE_MODE_INCREMENTAL, sync.UPDATE_MODE_REPLACE_ALL)))
DESTINATIONS = tuple(zip((path for path, label in sync.PICON_DESTINATIONS),
                        ("Pamäť prijímača", "Pevný disk", "USB", "SD karta", "MMC", "Priečinok /picon")))
PROVIDERS = {"FREESAT", "DIGI_TELLY", "ANTIKSAT", "CANALPLUS_SK", "CANALPLUS_CZ"}


def selector_display_label(selector):
    """Display stable bindings without exposing technical archive IDs."""
    if selector in PROVIDERS:
        return dict(SATELLITES).get(selector, selector)
    position = sync.canonical_position_for_selector(selector)
    if position and position != "dtt":
        return position.upper()
    return _(dict(SATELLITES).get(selector, str(selector)))


class PickerState:
    def __init__(self, choices, selected=(), multiple=False):
        self.choices = tuple(choices)
        self.multiple = multiple
        self.selected = set(selected)
        self.allowed = {value for value, label in self.choices}

    def toggle(self, value):
        if value not in self.allowed:
            raise ValueError("Unknown selection")
        if value in self.selected:
            self.selected.remove(value)
        else:
            self.selected.add(value)

    def apply(self):
        return [value for value, label in self.choices if value in self.selected]


def initial_selectors(profile):
    if getattr(profile, "warder_selectors", None) and profile.warder_selectors.value:
        # Retired internet-radio collections must not keep profiles invalid
        # after removal; preserve all satellite, DAB and terrestrial choices.
        return [item for item in profile.warder_selectors.value.split()
                if not item.startswith("IPTV-")]
    result = []
    for position in profile.sats.value.split():
        selector = sync.selector_id_for_position(position.lower())
        if selector and selector not in result:
            result.append(selector)
    return result


def profile_preferences(profile):
    selectors = initial_selectors(profile)
    if not selectors or any(selector not in dict(SATELLITES) for selector in selectors):
        raise ValueError(_("Vyberte podporované satelity alebo poskytovateľov."))
    if profile.resolution.value not in dict(RESOLUTIONS):
        raise ValueError(_("Vyberte rozlíšenie 50×30, 220×132 alebo 400×240."))
    if profile.background.value not in dict(STYLES):
        raise ValueError(_("Vyberte pozadie Transparent, Biele alebo Čierne."))
    if profile.method.value not in METHOD_MAP:
        raise ValueError(_("Vyberte režim aktualizácie."))
    include_dab = "DAB" in selectors
    if include_dab and profile.resolution.value != "220x132":
        raise ValueError("DAB / DAB+: 220×132")
    if include_dab and profile.method.value == "sync_tv":
        raise ValueError(_("Vyberte režim aktualizácie.") + " DAB / DAB+: " + _("Podľa TV a rádia"))
    bindings = [sync.task_binding_for_package_selector(value) for value in selectors if value != "DAB"]
    preferences = sync.set_task_position_bindings(sync.default_preferences(), bindings)
    preferences.update(style=profile.background.value, resolution=profile.resolution.value,
                       update_mode=METHOD_MAP[profile.method.value],
                       destination=(profile.picon_folder_user.value if profile.picon_folder.value == "user_defined"
                                    else profile.picon_folder.value))
    preferences.update(include_dab=include_dab, dab_only=include_dab and not bindings)
    return preferences


def profile_selection(profile):
    """Restore a fresh working copy without changing this or another profile."""
    return {
        'satellites': initial_selectors(profile) or None,
        'resolution': profile.resolution.value if profile.resolution.value in dict(RESOLUTIONS) else None,
        'style': profile.background.value if profile.background.value in dict(STYLES) else None,
        'method': profile.method.value if profile.method.value in METHOD_MAP else None,
        'destination': profile.picon_folder_user.value if profile.picon_folder.value=='user_defined' else profile.picon_folder.value,
    }


def clock_text(now=None, language="sk"):
    now = now or datetime.datetime.now()  # Receiver's local timezone, including DST.
    languages = {
        "sk": (("Pondelok", "Utorok", "Streda", "Štvrtok", "Piatok", "Sobota", "Nedeľa"),
               ("januára", "februára", "marca", "apríla", "mája", "júna", "júla", "augusta", "septembra", "októbra", "novembra", "decembra")),
        "cs": (("Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"),
               ("ledna", "února", "března", "dubna", "května", "června", "července", "srpna", "září", "října", "listopadu", "prosince")),
    }
    languages.update({
        "en": (("Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"),
               ("January","February","March","April","May","June","July","August","September","October","November","December")),
        "de": (("Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag"),
               ("Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember")),
        "pl": (("Poniedziałek","Wtorek","Środa","Czwartek","Piątek","Sobota","Niedziela"),
               ("stycznia","lutego","marca","kwietnia","maja","czerwca","lipca","sierpnia","września","października","listopada","grudnia")),
    })
    languages.update({
        "hu": (("Hétfő","Kedd","Szerda","Csütörtök","Péntek","Szombat","Vasárnap"),
               ("január","február","március","április","május","június","július","augusztus","szeptember","október","november","december")),
        "ru": (("Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"),
               ("января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря")),
        "fr": (("Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"),
               ("janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre")),
        "it": (("Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"),
               ("gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre")),
        "es": (("Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"),
               ("enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre")),
    })
    languages.update({
        "al": (("E hënë","E martë","E mërkurë","E enjte","E premte","E shtunë","E diel"),
               ("janar","shkurt","mars","prill","maj","qershor","korrik","gusht","shtator","tetor","nëntor","dhjetor")),
        "el": (("Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"),
               ("Ιανουαρίου","Φεβρουαρίου","Μαρτίου","Απριλίου","Μαΐου","Ιουνίου","Ιουλίου","Αυγούστου","Σεπτεμβρίου","Οκτωβρίου","Νοεμβρίου","Δεκεμβρίου")),
        "et": (("Esmaspäev","Teisipäev","Kolmapäev","Neljapäev","Reede","Laupäev","Pühapäev"),
               ("jaanuar","veebruar","märts","aprill","mai","juuni","juuli","august","september","oktoober","november","detsember")),
        "fa": (("دوشنبه","سه‌شنبه","چهارشنبه","پنجشنبه","جمعه","شنبه","یکشنبه"),
               ("ژانویه","فوریه","مارس","آوریل","مه","ژوئن","ژوئیه","اوت","سپتامبر","اکتبر","نوامبر","دسامبر")),
        "lt": (("Pirmadienis","Antradienis","Trečiadienis","Ketvirtadienis","Penktadienis","Šeštadienis","Sekmadienis"),
               ("sausio","vasario","kovo","balandžio","gegužės","birželio","liepos","rugpjūčio","rugsėjo","spalio","lapkričio","gruodžio")),
        "nl": (("Maandag","Dinsdag","Woensdag","Donderdag","Vrijdag","Zaterdag","Zondag"),
               ("januari","februari","maart","april","mei","juni","juli","augustus","september","oktober","november","december")),
        "pt": (("Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado","Domingo"),
               ("janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro")),
        "ro": (("Luni","Marți","Miercuri","Joi","Vineri","Sâmbătă","Duminică"),
               ("ianuarie","februarie","martie","aprilie","mai","iunie","iulie","august","septembrie","octombrie","noiembrie","decembrie")),
        "tr": (("Pazartesi","Salı","Çarşamba","Perşembe","Cuma","Cumartesi","Pazar"),
               ("Ocak","Şubat","Mart","Nisan","Mayıs","Haziran","Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık")),
        "uk": (("Понеділок","Вівторок","Середа","Четвер","П’ятниця","Субота","Неділя"),
               ("січня","лютого","березня","квітня","травня","червня","липня","серпня","вересня","жовтня","листопада","грудня")),
        "zh": (("星期一","星期二","星期三","星期四","星期五","星期六","星期日"),
               ("1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月")),
    })
    code = normalize_language(language)
    names = languages.get(code,languages["en"])
    if names:
        day, date = names[0][now.weekday()], "%d. %s %d" % (now.day, names[1][now.month - 1], now.year)
    else:
        day, date = now.strftime("%A"), now.strftime("%d. %B %Y")
    if code == "hu":
        date = "%d. %s %d." % (now.year,names[1][now.month-1],now.day)
    elif code in ("ru","fr","it","al","el","fa","nl","ro","tr","uk"):
        date = "%d %s %d" % (now.day,names[1][now.month-1],now.year)
    elif code in ("es", "pt"):
        date = "%d de %s de %d" % (now.day,names[1][now.month-1],now.year)
    elif code == "zh":
        date = "%d年%d月%d日" % (now.year, now.month, now.day)
    elif code == "lt":
        date = "%d m. %s %d d." % (now.year, names[1][now.month-1], now.day)
    return day, date, now.strftime("%H:%M"), now.strftime("%S")

