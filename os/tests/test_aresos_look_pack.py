"""The installed PNGs and look.json regenerate from the public component study."""
import json
from pathlib import Path
import runpy
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'os/config/usr/share/aresos/look'


class LookPackTest(unittest.TestCase):
    def test_pack_regenerates_file_for_file_and_pixel_for_pixel(self):
        try:
            from PIL import Image
        except ImportError as error:
            self.skipTest(f'look pack regeneration needs Pillow ({error})')
        generator = runpy.run_path(str(ROOT / 'os/look/make_pack.py'))
        with tempfile.TemporaryDirectory() as folder:
            regenerated = Path(folder)
            generator['generate'](regenerated)
            manifest = json.loads((PACK / 'look.json').read_text())
            expected = {'look.json', *(part['file'] for part in manifest['sprites'].values())}
            self.assertEqual(len(expected), 18)
            for tree in (PACK, regenerated):
                self.assertEqual({p.relative_to(tree).as_posix() for p in tree.rglob('*') if p.is_file()}, expected)
            self.assertEqual((PACK / 'look.json').read_bytes(), (regenerated / 'look.json').read_bytes())
            for sprite in manifest['sprites'].values():
                file = sprite['file']
                with self.subTest(file=file), Image.open(PACK / file) as actual, Image.open(regenerated / file) as made:
                    self.assertEqual((actual.mode, actual.size), ('RGBA', tuple(sprite['size'])))
                    self.assertEqual((actual.mode, actual.size, actual.tobytes()), (made.mode, made.size, made.tobytes()))


if __name__ == '__main__':
    unittest.main()
