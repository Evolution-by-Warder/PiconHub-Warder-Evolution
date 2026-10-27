#!/usr/bin/env python3
"""Render all unique station previews at their native size for visual review."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent

def build():
    catalog = json.loads((ROOT / 'catalog/authentic-preview.json').read_text())
    stations = {}
    for record in catalog['records']:
        stations.setdefault(record['station'], record)
    rows = list(stations.values())
    output = ROOT / 'preview/review'
    output.mkdir(parents=True, exist_ok=True)
    for page in range((len(rows) + 7) // 8):
        section = rows[page * 8:page * 8 + 8]
        sheet = Image.new('RGB', (860, 45 + len(section) * 145), '#263746')
        draw = ImageDraw.Draw(sheet)
        for index, style in enumerate(('transparent', 'white', 'black')):
            draw.text((180 + index * 220, 10), style.upper(), fill='white')
        for index, record in enumerate(section):
            y = 40 + index * 145
            draw.text((5, y + 50), record['station'], fill='white')
            for column, style in enumerate(('transparent', 'white', 'black')):
                with Image.open(ROOT / 'preview/authentic' / style / record['picon_filename']) as source:
                    source = source.convert('RGBA')
                    sheet.paste(source, (175 + column * 220, y), source)
        sheet.save(output / ('page-%02d.png' % (page + 1)))

if __name__ == '__main__':
    build()
