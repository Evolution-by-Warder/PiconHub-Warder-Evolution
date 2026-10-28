# IPTV rádiá SK/CZ — pracovná príprava

Stav: rozpracované, nie produkčné vydanie. Vlastník chce obnoviť približne 1–2 roky staré slovenské a české sekcie svojho rádio bouquetu a pripraviť zodpovedajúce Warder picony aj spoločnú ponuku v PiconHube a FullHDGlass.

Pôvodný výrez obsahuje 49 SK a 163 CZ streamov. Ostatné krajiny sa pri úprave celého bouquetu musia zachovať. Pôvodné nenulové referencie staníc zachovávame; nové musia dostať jedinečné referencie. Typ internetového rádia je `4097:0:2`, nie televízny typ 1.

Podklady: vlastníkom dodaný bouquet a 4 SK + 12 CZ PDF z FMStreamu; katalógy Radia.sk, radia.cz a aktuálne objavovacie záznamy Radio Browser. FMStream HTTP je z prostredia blokovaný 403. PDF obsahujú aj duplicitné kvality, adresy bez názvu a položky prekryté prehrávačom, preto počet záznamov nie je počet jedinečných overených staníc.

Aktuálne výsledky sú kandidáti. `refresh-candidate.json` nesmie byť vyhlásený za finálny bouquet bez kontroly identít a streamov. Zlyhanie priameho testu zo servera nie je dôkaz, že stanica prestala vysielať. Historický titul „Cesky rozhlas 2 - Praha“ znamená Dvojku/cro2, nesmie sa zameniť s Radio Praha/cro7.

Logá: iba oficiálne alebo vlastníkom schválené identity. Použiť zmrazené Warder MASTER pozadia, proporcionálny fit, 50×30, 220×132 a 400×240, transparent/white/black. Nevymýšľať logá, neopravovať farby hrubými maskami. Sporné identity a kontrast vyžadujú vizuálne preverenie; chýbajúce logo nenahrádzať logom podobnej stanice.

Dokončiť: rozšírenie a kontrola aktuálneho SK/CZ katalógu, aktualizovaný kompletný bouquet, finálne priradenie piconov, generovanie a vizuálna kontrola deviatich balíkov, integrácia `IPTV rádiá SK/CZ` do oboch aplikácií, cielené testy, štandardné produkčné vydanie a dokumentácia skutočných výsledkov.
