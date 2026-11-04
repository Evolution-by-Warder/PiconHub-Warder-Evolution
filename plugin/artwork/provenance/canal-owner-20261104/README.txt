CANAL+ – WARDER, 4. november 2026

STAV: NÁVRHY NA VIZUÁLNE SCHVÁLENIE, PRODUKCIA NEZMENENÁ.

4 dodané logá; 36 grafických variantov: 50x30, 220x132, 400x240 × transparent, WHITE, BLACK. Použité sú originálne zmrazené Warder MASTER pozadia. Kontrolné SHA256 sú v review-manifest.json.

Priame spracovanie pôvodných PNG neprešlo existujúcou kontrolou značky/panelov. Sú uložené bez zmien v originals/. Odvodené cleaned-proposals/ odstraňujú čierny podklad, farebný kompresný šum a izolované alfa čiary, zachovávajú tvar písmen a HD. Nejde o nové kreslenie ani náhradu fontu. Následné varianty prešli nezmeneným V9 rendererom a whole-logo guardom. Schválenie pôvodných obrázkov sa automaticky neprenáša na vyčistené návrhy.

review-only/package-deltas/ obsahuje 45 NÁVRHOV zmien pre aktuálne produkčné balíky na pozíciách 23.5E a 0.8W a providery CANALPLUS_SK, CANALPLUS_CZ a DIGI_TELLY. Sú to iba zmenové podklady, nie úplné inštalačné balíky. Presné referencie a väzby sú v routing-plan.json. 7 aktuálnych technických referencií a 4 existujúce legacy aliasy.

19.2E a holandská 23.5E vetva Action vyžadujú overenie regionálnej grafiky; SD a UHD/B2B služby sú vylúčené, pretože dodané logo má HD. Ostatné pozície ani providery sa nepridávajú hádaním.

Po prijatí presných návrhov treba obnoviť aktuálny katalóg, prestavať celé dotknuté archívy so zachovaním ostatných PNG, overiť oba runtime enginy a až potom aktivovať katalóg.
