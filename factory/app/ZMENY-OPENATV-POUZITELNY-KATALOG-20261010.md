# OpenATV – použiteľný lokálny katalóg grafík

Táto dávka vytvára v `06-OUTPUT/OPENATV-NAME-CATALOG` fyzické, obsahovo deduplikované PNG súbory z OpenATV. Ide o samostatný, neprodukčný katalóg: názov stanice NIE JE service reference, žiadne Warder ID sa nevytvára ani nemení. Jedinečné grafiky sa ukladajú raz pre každú kombináciu názvu a SHA-256; opakované behy ich neprepisujú. Úplne priehľadné alebo neplatné PNG sa nevkladajú. Manifest `catalog.json` obsahuje cestu, zdrojový názov a SHA. Zdrojové súbory, PiconHub a produkčný GitHub sa nemenia.

Katalóg je okamžite použiteľný na ďalšie bezpečné spracovanie a kurátorstvo nových grafík. Nejde o automatické priradenie 33 100 OpenATV PNG k existujúcim service reference. Publikovanie z tohto katalógu pod Warder ID je zakázané, kým identita nie je overená.
