# PiconHub Server — Warder Evolution

Clean server structure for the new PiconHub plugin.

## Canonical layout

```text
picons/<satellite-position>/<provider>/<variant>/
```

Where `<variant>` is one of:

- `transparent`
- `white`
- `black`

There is no intermediate `satellite` directory and no `Satellite 0` layer.

## Server API

- `api/catalog.json` — server catalog data
- `api/latest_added.json` — latest added picons
- `api/news.json` — PiconHub news feed
- `api/schema.json` — structure/API version

## Plugin updates

Plugin release payloads are stored separately under `plugin/releases/` and are independent of the picon database.

The Enigma2 plugin keeps its own plugin version separate from the database version.

## Project

PiconHub by Warder
