# Kontrola Factory release pri spusteni

- GitHub Releases latest: iba presny tag factory-vX.Y.Z.
- Zodpovedajuci ZIP asset musi mat presny nazov, velkost a oficialnu GitHub URL.
- Ostatne release (napr. Enigma2 plugin) sa ignoruju.
- Kontrola ma timeout 6 sekund a pri chybe neblokuje spracovanie.
- Ziadna instalacia, prepis ani GitHub zapis sa nevykonava.
- Nasledujuca etapa: distribucny manifest s podpisom, atomicka instalacia, rollback a Windows test.
