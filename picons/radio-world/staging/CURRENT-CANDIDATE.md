# Warder Radio – overený pracovný kandidát cez dávku 43

Stav: Draft, bez produkčného merge. Testovaný pracovný commit 8b5d2baf95392483ebb592ae413832dec5b7190a.
CI: https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/42389598820 (SUCCESS).
Index SHA-256: b2018e346e88cef556b27290ff241d850cb01135855fc643dfe1d92965185d0e.

219 krajín: 125 dostupných = 12 úplných + 113 čiastočných; 94 nedostupných.
Pokrytých 3 010 / 35 560 krajinských referencií; zostáva 32 550.
27 666 PNG položiek vrátane aliasov = všetkých 10 332 pôvodných bez zmeny + 17 334 prijatých nových.
Úplné: SK, CZ, BT, TD, CX, GG, GW, KI, LR, MS, SM, KM.

Dávka 43 pridáva 140 referencií / 1 260 PNG položiek v 47 krajinských unionoch / 423 nových ZIPov: 113 Zeno + 24 primary + 3 doložené kontrastné opravy (Italo4you, Lahmacun, GLR). Nové prijaté položky majú skutočnú vizuálnu kontrolu všetkých deviatich variantov, nemenné originály a PNG commity.

Pôvodný source výber primary25 obsahoval HDF-only Stephansdom EF referenciu. Striktný gate ju zastavil pred country ZIP buildom; v aktuálnom katalógu neexistuje krajinský záznam presného ref ani názvu + URL. Krajinská eligibility je opravená na 24; HDF-only prípad aj jeho deväť skutočných source PNG zostali oddelené. Pôvodných 225 source PNG a historický export sa zachovali. Žiadna referenčná ani skupinová normalizácia naslepo.

15 regresných testov vizuálnej brány + 2 HDF regresie prešli v CI. HDF-only pôvodný záznam aj jeho kópia s ručne prepísanou skupinou Austria musia zlyhať; všetkých 140 prijatých country/name/URL/ref členstiev prešlo. Nový výber primary24 je presný nezmenený podvýber source25 mínus HDF. Finálny Zeno snapshot bol porovnaný so všetkými 113 prijatými source/API SHA a country/mount dôkazmi.

Downloader 0.1.9.2 je nezmenený: replay všetkých 125 dostupných krajín, tri pozadia 220×132, 372 verejných ZIP URL; na pozadie 3 009 presných inštalovaných PNG + 1 zachovaný vlastný picon, 0 zlyhaní, opakovaný beh 0 ZIP požiadaviek. Nastavenia, história, obľúbené a vlastné picony zachované. Fyzický prijímač nebol testovaný.

Inventár 1 116 nemenných URL balíkov všetkých deviatich variantov má presné SHA-256 a zhodný SHA256SUMS. Najväčší balík má 59 271 661 bajtov, pod limitom 64 MiB. V nových country unionoch bolo zachovaných 16 272 predchádzajúcich PNG položiek. Celý kandidát zachováva všetkých 10 332 produkčných PNG položiek vrátane aliasov.

Lokálny runtime prestal fungovať; integrácia 43 bola dokončená cez GitHub/CI. Neobnoviteľné novšie lokálne záznamy sa nezahodili: CI izolovalo presných 102 nových zdrojov (364 frozen mínus 262 publikovaných QA). Aktívnych nových metadata holds je 240 = 121 známych source holds + 102 technická karanténa + 17 primary holds. Technická karanténa nie je odmietnutie identity. Následne zachránené skutočné rozhodnutia sú na source113 vetve v receiptoch; samy nepredstavujú pripravené PNG.

Zeno1519 source freeze úspešne skončil: 419 logo-frozen / 1 096 metadata hold / 4 retrieval pending, final checkpoint 890c9edb644d676f5b33855268f39aefbad65be8. Zdrojové zmrazenie nie je grafické schválenie. Ďalších 54 lokálnych finálnych approve ID má zachránené hlasovanie, ale chýbajú kompletné PNG tuple väzby a nie sú country CI ready; ďalšie 3 sú iba source-pass. Nezapočítavajú sa do indexu.

Produkčný main, existujúce PNG/ZIP/IPK cesty a historická vetva work/radio-batch33-legacy-payload-20261106 ostávajú zachované. PR #67 a #68 sú Draft, žiadne nové IPK ani produkčné zlúčenie. Celosvetové pokrytie ešte nie je dokončené.
