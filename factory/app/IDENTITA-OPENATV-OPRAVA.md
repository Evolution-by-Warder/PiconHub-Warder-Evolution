# Oprava identifikácie OpenATV

Predošlá verzia klasifikovala všetky PNG bez overiteľnej service reference ako REVIEW (odlišný artwork), aj keď neexistoval dôkaz o zhode služby. Teraz ich označuje UNMAPPED. Tento stav je oddelený od skutočného rozdielu grafiky (REVIEW), od nových služieb (NEW) a od identických obrázkov (IDENTICAL).

UNMAPPED **nie je automaticky spárovaná služba** a nesmie byť publikovaná bez mapovania. Originálne názvy a zdroje sa nemenia. Report registry-matches obsahuje `unmapped` a rozpis po zdrojoch. Rozhodovací front sa nezahlcuje každým nemapovaným súborom.

Táto oprava ešte nerieši získanie presnej service reference pre UTF8SNP obrázky. Na bezpečné priradenie je potrebná autoritatívna tabuľka názov→service reference, nie heuristika názvu. Nie je overené na dátach používateľa.
