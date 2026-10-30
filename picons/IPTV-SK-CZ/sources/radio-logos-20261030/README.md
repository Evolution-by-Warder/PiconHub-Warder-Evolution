# SK/CZ radio logo candidates — 30 October 2026

Prepared for visual review. Production catalogue, bouquets, IPKs and update feeds are unchanged.

The owner supplied 26 images in `Warder Radio Streams.ZIP`. Twenty-three usable station graphics map to 26 currently missing service references. The generic R/play symbols are not station artwork. The supplied Czech Dance Radio graphic is not assigned to the legacy `stream.danceradio.nl:9920` service.

The requested dabplus.cz directory was read and all 78 unique station images were checked (86 table labels, 210 rows). Its thumbnails are too small for the larger Warder variants. Official station originals were retrieved for Pigy Pohádky, Pigy Disko Trysko and WORLDRADIO, adding four service references. Official Pigy programme-specific graphics are used rather than a generic parent logo.

All 30 references are checked against both current bouquets. The 270 candidate PNGs cover three sizes and three styles. Existing picons and masters are preserved; no production package was changed. Thirty additions would increase coverage from 248 to 278 entries and leave 43 entries uncovered.

The soft Dance Club JPEG retains its original white field and requires visual source-quality acceptance. Historical Crystal, Dragon, Hitradio FM, Rock Radio Gold and Rock Rádio Šumava identities remain outside this candidate until their stream/programme identity is confirmed; a shared parent logo alone is insufficient.

Reproduce from the repository root with Pillow 12.3.0:

```sh
python picons/IPTV-SK-CZ/tools/build_radio_logo_candidate.py --output /tmp/warder-radio-logo-review
```

The canonical source hashes and complete semantic contrast masks are frozen in `prepared-artwork.json`. Reproduction uses no network, thresholds, guessed components, sharpening, outlines or new artwork. The existing 220×132 MASTER templates are copied unchanged. Other resolutions proportionally resample the finished canonical picon.

Discovery: https://www.dabplus.cz/rozhlasove-stanice.html
Official additional sources: https://www.pigy.cz/radia/ and https://worldradio.eu/
