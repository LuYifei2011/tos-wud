import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('package_check', Path(__file__).resolve().parents[1] / 'scripts/check.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class StoreRules(unittest.TestCase):
    def test_oversized_icon_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '50 KB'):
            check.validate_icon(b'x' * 50_001)

    def test_missing_viewbox_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'viewBox'):
            check.validate_icon(b'<svg xmlns="http://www.w3.org/2000/svg"/>')

    def test_active_svg_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Active SVG'):
            check.validate_icon(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><script/></svg>')

    def test_external_svg_resource_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'self-contained'):
            check.validate_icon(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><image href="https://example.com/icon.png"/></svg>')

    def test_incomplete_languages_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Missing TOS'):
            check.validate_languages(b'[en-us]\nname = WUD\n')


if __name__ == '__main__':
    unittest.main()
