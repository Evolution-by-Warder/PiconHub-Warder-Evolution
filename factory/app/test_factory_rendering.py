import unittest
from pathlib import Path
from PIL import Image
from engine import _compose_variant, _contrast_variant_art, _adjust_low_contrast_color


class FactoryRenderingTests(unittest.TestCase):
    def test_templates_present(self):
        root = Path(__file__).resolve().parent / 'templates' / 'picons'
        for name in ('black-sablona.png', 'white-sablona.png'):
            with Image.open(root / name) as image:
                self.assertEqual(image.size, (220, 132))

    def test_transparent_source_unchanged(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        source.putpixel((50, 50), (250, 240, 20, 255))
        original = source.tobytes()
        self.assertEqual(_compose_variant(source, 'transparent').tobytes(), original)
        _compose_variant(source, 'white')
        _compose_variant(source, 'black')
        self.assertEqual(source.tobytes(), original)

    def test_bright_yellow_on_white_darkens(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        source.putpixel((50, 50), (255, 245, 20, 255))
        result = _adjust_low_contrast_color(source, 'white')
        self.assertLess(sum(result.getpixel((50, 50))[:3]), sum(source.getpixel((50, 50))[:3]))

    def test_white_lettering_on_red_plate_preserved(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(45, 75):
            for x in range(40, 130):
                source.putpixel((x, y), (235, 10, 40, 255))
        for y in range(52, 68):
            for x in range(60, 85):
                source.putpixel((x, y), (255, 255, 255, 255))
        result = _contrast_variant_art(source, 'white')
        self.assertEqual(result.getpixel((70, 60)), (255, 255, 255, 255))

    def test_free_white_lettering_darkens(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(52, 68):
            for x in range(60, 85):
                source.putpixel((x, y), (255, 255, 255, 255))
        result = _contrast_variant_art(source, 'white')
        self.assertEqual(result.getpixel((70, 60))[:3], (30, 30, 30))

    def test_legible_red_stays_red(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        source.putpixel((50, 50), (190, 20, 30, 255))
        self.assertEqual(_adjust_low_contrast_color(source, 'white').getpixel((50, 50)), source.getpixel((50, 50)))


if __name__ == '__main__':
    unittest.main()
