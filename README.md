# PiconHub Server — Warder Evolution

Clean server structure for the new PiconHub plugin.

## Canonical picon layout

```text
picons/<satellite-position>/<provider>/<variant>/
```

Where `<variant>` is one of:

- `transparent`
- `white`
- `black`

There is no intermediate `satellite` directory and no `Satellite 0` layer.

## Canonical manifest layout

```text
manifests/<satellite-position>/<provider>/<variant>.json
```

`manifests/build.py` generates SHA-256 manifests from the canonical picon tree. GitHub Actions rebuilds them when picons or the manifest generator change.

## Server API

- `api/index.json` — Warder Evolution endpoint index
- `api/catalog.json` — server catalog data
- `api/latest_added.json` — latest added picons
- `api/news.json` — PiconHub news feed
- `api/schema.json` — structure/API version
- `manifests/index.json` — generated satellite/provider/variant manifest index

## Plugin updates

Plugin updates are completely independent from picon/database updates.

- `plugin/latest.json` — Warder Evolution full-IPK self-update endpoint
- `plugin/releases/manifest.json` — legacy compatibility endpoint only

A published plugin update contains the plugin version, IPK location, SHA-256 checksum and changelog. The Enigma2 plugin warns the user before installation that, after a successful plugin update, the GUI will restart automatically. User settings and user picons are preserved.

The plugin version and database version are separate values.

## Project

PiconHub by Warder
