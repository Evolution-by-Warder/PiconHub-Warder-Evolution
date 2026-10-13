import unittest
import tempfile
import hashlib
from pathlib import Path
from PIL import Image
from engine import _compose_variant, _contrast_variant_art, _adjust_low_contrast_color, repair_variant_task, qa_png_task
from artwork_preparation import extract_flat_edge_background


class FactoryRenderingTests(unittest.TestCase):
    def test_batch_pale_art_does_not_force_full_dark_outline(self):
        source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
        for y in range(50, 75):
            for x in range(60, 150):
                source.putpixel((x, y), (255, 255, 255, 255))
        original = source.tobytes()
        result = _compose_variant(source, 'white')
        self.assertEqual(source.tobytes(), original)
        self.assertEqual(result.size, (220, 132))
        self.assertEqual(result.getpixel((80, 60))[3], 255)
        # A large uniform dark perimeter must not be added indiscriminately.
        self.assertGreater(max(result.getpixel((59, 60))[:3]), 90)

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

    def test_render_rebuilds_stale_transparent_even_when_valid_png(self):
        from engine import render_png_task, RENDER_REVISION
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
            source.putpixel((100, 60), (255, 20, 40, 255))
            original = root / 'source.png'
            source.save(original)
            sha = hashlib.sha256(original.read_bytes()).hexdigest()
            output = root / 'output'
            folder = output / sha[:2] / sha
            folder.mkdir(parents=True)
            stale = Image.new('RGBA', (220, 132), (5, 5, 5, 255))
            stale.save(folder / 'transparent.png')
            ok, created, error = render_png_task((str(original), str(output), sha))
            self.assertTrue(ok, error)
            self.assertEqual(created, 3)
            with Image.open(folder / 'transparent.png') as image:
                self.assertEqual(image.getpixel((100, 60)), (255, 20, 40, 255))
            self.assertEqual((folder / 'transparent.render-revision').read_text(), RENDER_REVISION)
            ok, created, error = render_png_task((str(original), str(output), sha))
            self.assertTrue(ok, error)
            self.assertEqual(created, 0)

    def test_engine_rejects_empty_alpha_source_without_outputs(self):
        from engine import render_png_task
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'empty.png'
            Image.new('RGBA', (220, 132), (0, 0, 0, 0)).save(source)
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            output = root / 'output'
            ok, created, error = render_png_task((str(source), str(output), sha))
            self.assertFalse(ok)
            self.assertEqual(created, 0)
            self.assertIn('FULLY_TRANSPARENT', error)
            self.assertFalse((output / sha[:2] / sha).exists())

    def test_engine_rejects_empty_background_extraction(self):
        from unittest.mock import patch
        from engine import render_png_task
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'opaque.png'
            Image.new('RGBA', (220, 132), (100, 110, 120, 255)).save(source)
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            output = root / 'output'
            empty = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
            with patch('artwork_preparation.extract_flat_edge_background',
                       return_value=(empty, True)):
                ok, created, error = render_png_task((str(source), str(output), sha))
            self.assertFalse(ok)
            self.assertEqual(created, 0)
            self.assertIn('EMPTY_AFTER_BACKGROUND_EXTRACTION', error)
            self.assertFalse((output / sha[:2] / sha).exists())

    def test_cache_rejects_stale_transparent_revision(self):
        from unittest.mock import patch
        from engine import _output_signature
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sha = 'a' * 64
            folder = root / sha[:2] / sha
            folder.mkdir(parents=True)
            for name in ('transparent', 'black', 'white'):
                Image.new('RGBA', (220, 132), (1, 2, 3, 255)).save(folder / (name + '.png'))
            with patch('engine.OUTPUT', root):
                self.assertIsNone(_output_signature(sha))

    def test_engine_rejects_mismatched_content_hash(self):
        from engine import render_png_task
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'art.png'
            Image.new('RGBA', (220, 132), (200, 30, 30, 255)).save(source)
            output = root / 'output'
            ok, created, error = render_png_task((str(source), str(output), '0' * 64))
            self.assertFalse(ok)
            self.assertEqual(created, 0)
            self.assertIn('SOURCE_SHA256_MISMATCH', error)
            self.assertFalse(output.exists())

    def test_engine_rejects_malformed_cache_key(self):
        from engine import render_png_task
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'art.png'
            Image.new('RGBA', (220, 132), (200, 30, 30, 255)).save(source)
            output = root / 'output'
            for bad_sha in ('../outside', 'G' * 64, 'a' * 63, ''):
                ok, created, error = render_png_task((str(source), str(output), bad_sha))
                self.assertFalse(ok)
                self.assertEqual(created, 0)
                self.assertIn('INVALID_SOURCE_SHA256', error)
            self.assertFalse(output.exists())

    def test_engine_writes_complete_verified_triplet(self):
        from engine import render_png_task, _output_signature_for_folder
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'real-render.png'
            artwork = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
            for y in range(40, 90):
                for x in range(55, 165):
                    artwork.putpixel((x, y), (200, 20, 30, 255))
            artwork.save(source)
            source_bytes = source.read_bytes()
            sha = hashlib.sha256(source_bytes).hexdigest()
            output = root / 'output'
            ok, created, error = render_png_task((str(source), str(output), sha))
            self.assertTrue(ok, error)
            self.assertEqual(created, 3)
            folder = output / sha[:2] / sha
            self.assertTrue(_output_signature_for_folder(folder))
            self.assertEqual(source.read_bytes(), source_bytes)
            for variant in ('transparent', 'black', 'white'):
                with Image.open(folder / (variant + '.png')) as rendered:
                    self.assertEqual(rendered.size, (220, 132))
                    self.assertEqual(rendered.mode, 'RGBA')
            (folder / 'white.render-revision').unlink()
            self.assertIsNone(_output_signature_for_folder(folder))

    def test_render_validator_rejects_invisible_or_translucent_variants(self):
        from engine import render_png_task, _output_signature_for_folder
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'art.png'
            image = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
            for y in range(42, 85):
                for x in range(60, 150):
                    image.putpixel((x, y), (225, 40, 20, 255))
            image.save(source)
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            output = root / 'output'
            ok, _, error = render_png_task((str(source), str(output), sha))
            self.assertTrue(ok, error)
            folder = output / sha[:2] / sha
            self.assertTrue(_output_signature_for_folder(folder))
            transparent = folder / 'transparent.png'
            with Image.open(transparent) as original:
                saved = original.copy()
            Image.new('RGBA', (220, 132), (0, 0, 0, 0)).save(transparent)
            self.assertIsNone(_output_signature_for_folder(folder))
            saved.save(transparent)
            black = folder / 'black.png'
            with Image.open(black) as original:
                damaged = original.copy()
            damaged.putpixel((0, 0), (0, 0, 0, 0))
            damaged.save(black)
            self.assertIsNone(_output_signature_for_folder(folder))

    def test_render_repairs_corrupt_cached_alpha_without_touching_source(self):
        from engine import render_png_task, _output_signature_for_folder
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.png'
            art = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
            for y in range(35, 90):
                for x in range(55, 170):
                    art.putpixel((x, y), (210, 30, 30, 255))
            art.save(source)
            before = source.read_bytes()
            sha = hashlib.sha256(before).hexdigest()
            output = root / 'output'
            ok, _, error = render_png_task((str(source), str(output), sha))
            self.assertTrue(ok, error)
            folder = output / sha[:2] / sha
            Image.new('RGBA', (220, 132), (0, 0, 0, 0)).save(folder / 'transparent.png')
            with Image.open(folder / 'white.png') as white:
                broken = white.copy()
            broken.putpixel((0, 0), (255, 255, 255, 0))
            broken.save(folder / 'white.png')
            self.assertIsNone(_output_signature_for_folder(folder))
            ok, created, error = render_png_task((str(source), str(output), sha))
            self.assertTrue(ok, error)
            self.assertEqual(created, 2)
            self.assertTrue(_output_signature_for_folder(folder))
            self.assertEqual(source.read_bytes(), before)

    def test_scan_cache_invalidates_alpha_corruption(self):
        from unittest.mock import patch
        from engine import render_png_task, _output_signature
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'input.png'
            art = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
            art.paste((220, 40, 50, 255), (50, 35, 170, 95))
            art.save(source)
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            output = root / 'output'
            ok, _, error = render_png_task((str(source), str(output), sha))
            self.assertTrue(ok, error)
            folder = output / sha[:2] / sha
            with patch('engine.OUTPUT', output):
                self.assertIsNotNone(_output_signature(sha))
                Image.new('RGBA', (220, 132), (0, 0, 0, 0)).save(folder / 'transparent.png')
                self.assertIsNone(_output_signature(sha))
                ok, _, error = render_png_task((str(source), str(output), sha))
                self.assertTrue(ok, error)
                self.assertIsNotNone(_output_signature(sha))
                with Image.open(folder / 'black.png') as original:
                    damaged = original.copy()
                damaged.putpixel((0, 0), (0, 0, 0, 0))
                damaged.save(folder / 'black.png')
                self.assertIsNone(_output_signature(sha))
                ok, _, error = render_png_task((str(source), str(output), sha))
                self.assertTrue(ok, error)
                self.assertIsNotNone(_output_signature(sha))

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


    def test_low_contrast_repair_checks_composed_white_output(self):
        # Regression: repair must pass final PNG QA, not just change some pixels.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
            for y in range(42, 75):
                for x in range(55, 165):
                    source.putpixel((x, y), (255, 255, 255, 255))
            source_path = root / 'source.png'
            source.save(source_path)
            sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
            output = root / 'output'
            folder = output / sha[:2] / sha
            folder.mkdir(parents=True)
            source.save(folder / 'transparent.png')
            _compose_variant(source, 'black').save(folder / 'black.png')
            # Deliberately leave white-on-white pixels to exercise repair.
            _compose_variant(source, 'white').save(folder / 'white.png')
            ok, changed, error = repair_variant_task(
                (str(source_path), str(output), sha, ['LOW_CONTRAST_WHITE'],
                 str(root / 'backups')))
            self.assertTrue(ok, error)
            self.assertEqual(changed, 1)
            _, issues = qa_png_task((sha, str(output)))
            self.assertNotIn('LOW_CONTRAST_WHITE', issues)
            with Image.open(folder / 'transparent.png') as original:
                self.assertEqual(original.convert('RGBA').tobytes(), source.tobytes())


    def test_repository_picons_repair_white_on_disposable_copy(self):
        # Real committed artwork, never the production picon directory.
        repo_root = Path(__file__).resolve().parents[2]
        cases = (
            'picons/9.0e/global/transparent/1_0_1_138C_50E1_217C_5A0000_0_0_0.png',
            'picons/4.8e/slm/transparent/1_0_19_19A0_107B_55_300000_0_0_0.png',
        )
        for relative in cases:
            with self.subTest(source=relative), tempfile.TemporaryDirectory() as temp:
                source_path = repo_root / relative
                self.assertTrue(source_path.is_file(), relative)
                source_bytes = source_path.read_bytes()
                sha = hashlib.sha256(source_bytes).hexdigest()
                with Image.open(source_path) as image:
                    art = image.convert('RGBA')
                output = Path(temp) / 'output'
                folder = output / sha[:2] / sha
                folder.mkdir(parents=True)
                _compose_variant(art, 'transparent').save(folder / 'transparent.png')
                _compose_variant(art, 'black').save(folder / 'black.png')
                _compose_variant(art, 'white').save(folder / 'white.png')
                before = {name: (folder / (name + '.png')).read_bytes()
                          for name in ('transparent', 'black')}
                ok, changed, error = repair_variant_task(
                    (str(source_path), str(output), sha, ['LOW_CONTRAST_WHITE'],
                     str(Path(temp) / 'backups')))
                self.assertTrue(ok, error)
                self.assertEqual(changed, 1)
                _, issues = qa_png_task((sha, str(output)))
                self.assertNotIn('LOW_CONTRAST_WHITE', issues)
                for name in ('transparent', 'black'):
                    self.assertEqual((folder / (name + '.png')).read_bytes(),
                                     before[name], name)
                self.assertEqual(source_path.read_bytes(), source_bytes)


    def test_new_reference_triage_deduplicates_sources_without_approval(self):
        from registry_triage import new_reference_artwork_triage
        ref_a = '1_0_1_2_3_4_5_6_7_8'
        ref_b = '1_0_1_2_3_4_5_6_7_9'
        def item(ref, sha, path, classification='NEW'):
            return {'classification': classification, 'service_reference': ref,
                    'candidate_sha256': sha, 'candidate_source': path}
        matches = [
            item(ref_a, 'a'*64, r'D:\\SOURCE-INGEST\\originals\\openatv8\\a.png'),
            item(ref_a, 'a'*64, r'D:\\SOURCE-INGEST\\originals\\vhannibal\\b.png'),
            item(ref_b, 'b'*64, r'D:\\SOURCE-INGEST\\originals\\openatv8\\c.png'),
            item(ref_b, 'c'*64, r'D:\\SOURCE-INGEST\\originals\\vhannibal\\d.png'),
            item(ref_a, 'd'*64, 'master.png', 'IDENTICAL'),
        ]
        result = new_reference_artwork_triage(matches)
        self.assertEqual(result['new_references'], 2)
        self.assertEqual(result['single_artwork_references'], 1)
        self.assertEqual(result['conflicting_artwork_references'], 1)
        self.assertEqual(result['identity_approval'], 'NONE')
        self.assertEqual(len(result['source_evidence']), 4)
        self.assertEqual(result['source_evidence_count'], 4)
        self.assertEqual(result['single_artwork'][0]['artwork_observations'], 2)
        self.assertEqual({row['sha256'] for row in result['source_evidence']}, {'a'*64, 'b'*64, 'c'*64})
        self.assertEqual(result['schema'], 2)
        from registry_triage import new_reference_review_batches
        pages = new_reference_review_batches(result, batch_size=1)
        self.assertEqual(pages['conflict_batches'], 1)
        self.assertEqual(pages['single_batches'], 1)
        self.assertEqual(pages['review_batches'][0]['category'], 'CONFLICT')
        self.assertEqual(pages['review_batches'][0]['item_count'], 1)
        self.assertEqual(pages['review_batches'][0]['distinct_artwork_count'], 2)
        self.assertEqual(pages['review_batches'][0]['items'][0]['review_item_id'], 'NEW-SRP-' + ref_b)
        larger_pages = new_reference_review_batches(result, batch_size=10)
        self.assertEqual({item['review_item_id'] for page in pages['review_batches'] for item in page['items']},
                         {item['review_item_id'] for page in larger_pages['review_batches'] for item in page['items']})
        self.assertEqual(pages['review_batches'][0]['status'], 'PENDING_HUMAN_REVIEW')
        self.assertEqual(pages['review_batches'][0]['identity_approval'], 'NONE')
        self.assertEqual(sum(len(p['items']) for p in pages['review_batches']), result['new_references'])
        with self.assertRaises(ValueError):
            new_reference_review_batches(result, batch_size=0)
        invalid = [item(ref_a, 'not-a-sha', 'bad.png'),
                   item(ref_a, 'A'*64, 'upper.png'),
                   item(ref_a, 'a'*64, 'lower.png')]
        canonical = new_reference_artwork_triage(invalid)
        self.assertEqual(canonical['new_references'], 1)
        self.assertEqual(canonical['single_artwork_references'], 1)
        self.assertEqual(canonical['single_artwork'][0]['artwork_sha256'], ['a'*64])
        self.assertEqual(canonical['source_evidence_count'], 2)
        self.assertEqual({row['source'] for row in result['source_evidence']}, {m['candidate_source'] for m in matches if m['classification'] == 'NEW'})
        self.assertEqual(result['single_artwork'][0]['source_origins'], ['openatv8', 'vhannibal'])
        self.assertEqual(result['single_artwork'][0]['source_observations'], 2)
        self.assertEqual(result['conflicting_artwork'][0]['artwork_sha256'], ['b'*64, 'c'*64])


if __name__ == '__main__':
    unittest.main()
