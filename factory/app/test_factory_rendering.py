import unittest
from pathlib import Path
from PIL import Image
from engine import _compose_variant, _contrast_variant_art, _adjust_low_contrast_color
from artwork_preparation import extract_flat_edge_background


class FactoryRenderingTests(unittest.TestCase):
    def test_white_plaque_keeps_black_letters_on_both_templates(self):
        art = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(30, 90):
            for x in range(40, 160):
                art.putpixel((x, y), (255, 255, 255, 255))
        for y in range(48, 65):
            for x in range(65, 115):
                art.putpixel((x, y), (0, 0, 0, 255))
        for variant in ('white', 'black'):
            result = _contrast_variant_art(art, variant)
            self.assertEqual(result.getpixel((80, 55)), (0, 0, 0, 255))
            self.assertEqual(result.getpixel((45, 40)), (255, 255, 255, 255))

    def test_black_logo_plate_with_white_text_preserved_on_both_templates(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(50, 76):
            for x in range(40, 165):
                source.putpixel((x, y), (12, 12, 12, 255))
        for y in range(56, 68):
            for x in range(65, 130):
                source.putpixel((x, y), (238, 238, 238, 255))
        for bg in ('black', 'white'):
            result = _contrast_variant_art(source, bg)
            self.assertEqual(result.getpixel((50, 60)), (12, 12, 12, 255))
            self.assertEqual(result.getpixel((85, 60)), (238, 238, 238, 255))

    def test_chrome_gradient_on_white_keeps_shading(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        shades = (75, 105, 135, 165, 195, 225, 245)
        for idx, gray in enumerate(shades):
            for y in range(40, 55):
                for x in range(35 + idx * 10, 43 + idx * 10):
                    source.putpixel((x, y), (gray, gray, gray, 255))
        result = _contrast_variant_art(source, 'white')
        values = [result.getpixel((36 + idx * 10, 45))[0] for idx in range(len(shades))]
        self.assertEqual(values, sorted(values))
        self.assertGreater(len(set(values)), 4)
        self.assertLess(values[-1], shades[-1])
        self.assertEqual(source.getpixel((96, 45))[:3], (245, 245, 245))

    def test_gray_lettering_becomes_uniform_on_white(self):
        art = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for x, gray in zip(range(30, 35), (140, 160, 190, 220, 245)):
            art.putpixel((x, 40), (gray, gray, gray, 255))
        result = _contrast_variant_art(art, 'white')
        self.assertEqual({result.getpixel((x, 40))[:3] for x in range(30, 35)}, {(30, 30, 30)})

    def test_dark_lettering_becomes_uniform_on_black(self):
        art = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for x, gray in zip(range(30, 35), (15, 40, 70, 110, 140)):
            art.putpixel((x, 40), (gray, gray, gray, 255))
        result = _contrast_variant_art(art, 'black')
        self.assertEqual({result.getpixel((x, 40))[:3] for x in range(30, 35)}, {(238, 238, 238)})

    def test_black_text_on_white_plaque_preserved_on_black_template(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(35, 90):
            for x in range(35, 155):
                source.putpixel((x, y), (255, 255, 255, 255))
        for y in range(50, 68):
            for x in range(60, 120):
                source.putpixel((x, y), (15, 15, 15, 255))
        result = _compose_variant(source, 'black')
        self.assertEqual(result.getpixel((70, 55))[:3], (15, 15, 15))
        self.assertEqual(result.getpixel((45, 45))[:3], (255, 255, 255))

    def test_white_letters_inside_red_plate_preserved_in_composite(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(45, 85):
            for x in range(35, 150):
                source.putpixel((x, y), (225, 12, 35, 255))
        for y in range(55, 75):
            for x in range(65, 105):
                source.putpixel((x, y), (255, 255, 255, 255))
        result = _compose_variant(source, 'white')
        self.assertEqual(result.getpixel((75, 65))[:3], (255, 255, 255))
        self.assertEqual(result.getpixel((45, 65))[:3], (225, 12, 35))

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

    def test_large_standalone_white_word_darkens_on_white(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(30, 80):
            for x in range(30, 140):
                source.putpixel((x, y), (255, 255, 255, 255))
        result = _contrast_variant_art(source, 'white')
        self.assertEqual(result.getpixel((70, 50))[:3], (30, 30, 30))

    def test_black_lettering_on_white_kept(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(35, 75):
            for x in range(35, 135):
                source.putpixel((x, y), (255, 255, 255, 255))
        for y in range(45, 65):
            for x in range(55, 95):
                source.putpixel((x, y), (0, 0, 0, 255))
        result = _contrast_variant_art(source, 'white')
        self.assertEqual(result.getpixel((65, 55)), (0, 0, 0, 255))

    def test_black_text_inside_white_plaque_on_black_kept(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(35, 85):
            for x in range(35, 145):
                source.putpixel((x, y), (255, 255, 255, 255))
        for y in range(45, 70):
            for x in range(60, 100):
                source.putpixel((x, y), (0, 0, 0, 255))
        result = _contrast_variant_art(source, 'black')
        self.assertEqual(result.getpixel((75, 55)), (0, 0, 0, 255))

    def test_dark_lettering_on_black_lightens(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(50, 65):
            for x in range(45, 105):
                source.putpixel((x, y), (25, 25, 25, 255))
        result = _contrast_variant_art(source, 'black')
        self.assertEqual(result.getpixel((70, 55))[:3], (238, 238, 238))

    def test_large_colored_plate_unchanged(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(35, 85):
            for x in range(30, 150):
                source.putpixel((x, y), (250, 220, 20, 255))
        original = source.tobytes()
        result = _adjust_low_contrast_color(source, 'white')
        self.assertEqual(result.tobytes(), original)

    def test_small_chromatic_ink_adjusts(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        source.putpixel((45, 45), (255, 245, 20, 255))
        result = _adjust_low_contrast_color(source, 'white')
        self.assertNotEqual(result.getpixel((45, 45)), source.getpixel((45, 45)))

    def test_edge_matte_removed_without_changing_logo(self):
        source = Image.new('RGBA', (220, 132), (255, 255, 255, 255))
        for y in range(35, 95):
            for x in range(35, 180):
                source.putpixel((x, y), (20, 90, 190, 255))
        original = source.tobytes()
        extracted, did_extract = extract_flat_edge_background(source)
        self.assertTrue(did_extract)
        self.assertEqual(extracted.getpixel((0, 0))[3], 0)
        self.assertEqual(extracted.getpixel((70, 60)), (20, 90, 190, 255))
        self.assertEqual(source.tobytes(), original)

    def test_dark_brand_panel_not_extracted(self):
        source = Image.new('RGBA', (220, 132), (15, 17, 35, 255))
        for y in range(45, 85):
            for x in range(45, 175):
                source.putpixel((x, y), (235, 235, 245, 255))
        original = source.tobytes()
        extracted, did_extract = extract_flat_edge_background(source)
        self.assertFalse(did_extract)
        self.assertEqual(extracted.tobytes(), original)

    def test_brand_colored_matte_not_removed(self):
        source = Image.new('RGBA', (220, 132), (230, 20, 40, 255))
        for y in range(35, 95):
            for x in range(35, 180):
                source.putpixel((x, y), (255, 255, 255, 255))
        extracted, did_extract = extract_flat_edge_background(source)
        self.assertFalse(did_extract)
        self.assertEqual(extracted.tobytes(), source.tobytes())

    def test_dark_blue_news_word_on_black_is_lifted(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        # Separate narrow glyphs, as in small News/International captions.
        for x in range(50, 120, 12):
            for yy in range(90, 97):
                for xx in range(x, x + 4):
                    source.putpixel((xx, yy), (16, 35, 135, 255))
        result = _adjust_low_contrast_color(source, 'black')
        before = source.getpixel((51, 92))
        after = result.getpixel((51, 92))
        self.assertGreater(0.2126 * after[0] + 0.7152 * after[1] + 0.0722 * after[2],
                           0.2126 * before[0] + 0.7152 * before[1] + 0.0722 * before[2])
        self.assertEqual(source.getpixel((51, 92)), before)

    def test_large_blue_brand_symbol_remains_unchanged(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for yy in range(25, 55):
            for xx in range(35, 100):
                source.putpixel((xx, yy), (16, 35, 135, 255))
        result = _adjust_low_contrast_color(source, 'black')
        self.assertEqual(result.tobytes(), source.tobytes())

    def test_legible_red_stays_red(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        source.putpixel((50, 50), (190, 20, 30, 255))
        self.assertEqual(_adjust_low_contrast_color(source, 'white').getpixel((50, 50)), source.getpixel((50, 50)))


if __name__ == '__main__':
    unittest.main()
