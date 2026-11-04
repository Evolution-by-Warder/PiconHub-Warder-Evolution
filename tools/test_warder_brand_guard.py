"""Regression tests: disconnected lettering is part of the coloured logo."""
import unittest
from types import SimpleNamespace
from PIL import Image
from warder_brand_guard import classify_and_render_guarded, BrandIntegrityError, is_coloured_logo


class Renderer:
    def __init__(self, change=None):
        self.change = change

    def center_rgba_layer(self, source, **kwargs):
        return SimpleNamespace(image=source, clipped=False, safe_area=True, centered=True)

    def classify_and_render(self, source, master, style, **kwargs):
        edited = source.copy()
        if self.change:
            point, value = self.change
            edited.putpixel(point, value)
        return SimpleNamespace(image=Image.alpha_composite(master, edited), status='AUTO-FIXED')


class WholeLogoTests(unittest.TestCase):
    def setUp(self):
        self.logo = Image.new('RGBA', (8, 8))
        self.logo.putpixel((1, 1), (240, 10, 40, 255))
        self.logo.putpixel((6, 6), (255, 255, 255, 255))
        self.master = Image.new('RGBA', (8, 8), (210, 210, 210, 255))

    def test_detached_neutral_letter_cannot_be_recoloured(self):
        with self.assertRaises(BrandIntegrityError):
            classify_and_render_guarded(Renderer(((6, 6), (0, 0, 0, 255))), self.logo, self.master, 'white')

    def test_unchanged_composite_allowed(self):
        result = classify_and_render_guarded(Renderer(), self.logo, self.master, 'white')
        self.assertEqual(result.image.tobytes(), Image.alpha_composite(self.master, self.logo).tobytes())

    def test_alpha_changes_blocked(self):
        with self.assertRaises(BrandIntegrityError):
            classify_and_render_guarded(Renderer(((6, 6), (255, 255, 255, 200))), self.logo, self.master, 'white')

    def test_faint_colour_locks_whole_logo(self):
        self.logo.putpixel((1, 1), (100, 101, 100, 1))
        self.assertTrue(is_coloured_logo(self.logo))
        with self.assertRaises(BrandIntegrityError):
            classify_and_render_guarded(Renderer(((6, 6), (0, 0, 0, 255))), self.logo, self.master, 'white')

    def test_invisible_colour_does_not_lock_monochrome(self):
        self.logo.putpixel((1, 1), (240, 10, 40, 0))
        self.assertFalse(is_coloured_logo(self.logo))
        classify_and_render_guarded(Renderer(((6, 6), (0, 0, 0, 255))), self.logo, self.master, 'white')

    def test_colour_lost_by_resize_still_locks_logo(self):
        fitted = self.logo.copy()
        fitted.putpixel((1, 1), (0, 0, 0, 0))
        with self.assertRaises(BrandIntegrityError):
            classify_and_render_guarded(Renderer(((6, 6), (0, 0, 0, 255))), fitted, self.master, 'white', original_source=self.logo)


if __name__ == '__main__':
    unittest.main()
