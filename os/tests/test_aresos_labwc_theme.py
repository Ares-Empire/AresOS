"""The shipped labwc theme uses the study's frame cells and settings."""
import json
from pathlib import Path
import runpy
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SHARE = ROOT / 'os/config/usr/share'
PACK = SHARE / 'aresos/look'
THEME = SHARE / 'themes/AresOS/labwc'
STUDY = ROOT / 'docs/design/components/sprites/frame'

# labwc-theme(5), BUTTONS
BUTTONS = ('close', 'iconify', 'max', 'max_toggled', 'menu', 'shade', 'shade_toggled', 'desk', 'desk_toggled')
PNG_NAMES = {f'{button}{hover}-{state}.png' for button in BUTTONS
             for hover in ('', '_hover') for state in ('active', 'inactive')}

# COMPONENTS.md 4.2, the two menu widths in the brief, then 4.4 and 4.3 in theme order.
EXPECTED = '''\
border.width: 2
window.active.border.color: #cfa24f
window.inactive.border.color: #0d0d10
window.titlebar.padding.width: 0
window.titlebar.padding.height: 0
window.active.title.bg: Solid
window.active.title.bg.color: #2b2832
window.inactive.title.bg: Solid
window.inactive.title.bg.color: #1a181f
window.active.label.text.color: #f3f1ea
window.inactive.label.text.color: #a6a39a
window.label.text.justify: Left
window.button.width: 48
window.button.height: 40
window.button.spacing: 0
window.active.shadow.size: 24
window.active.shadow.color: #0000008c
window.inactive.shadow.size: 12
window.inactive.shadow.color: #0000005a
menu.border.width: 2
menu.border.color: #0d0d10
menu.items.padding.x: 8
menu.items.padding.y: 0
menu.items.bg.color: #2b2832
menu.items.text.color: #f3f1ea
menu.items.active.bg.color: #3a3644
menu.items.active.text.color: #edca77
menu.separator.width: 2
menu.separator.padding.width: 8
menu.separator.padding.height: 4
menu.separator.color: #504b5c
menu.width.min: 200
menu.width.max: 400
osd.bg.color: #2b2832
osd.border.color: #0d0d10
osd.border.width: 2
osd.label.text.color: #f3f1ea
osd.window-switcher.style-thumbnail.width.max: 80%
osd.window-switcher.style-thumbnail.padding: 8
osd.window-switcher.style-thumbnail.item.width: 280
osd.window-switcher.style-thumbnail.item.height: 208
osd.window-switcher.style-thumbnail.item.padding: 8
osd.window-switcher.style-thumbnail.item.active.border.width: 4
osd.window-switcher.style-thumbnail.item.active.border.color: #edca77
osd.window-switcher.style-thumbnail.item.active.bg.color: #3a3644
osd.window-switcher.style-thumbnail.item.icon.size: 32
osd.window-switcher.preview.border.width: 2
osd.window-switcher.preview.border.color: #0d0d10,#edca77,#0d0d10
snapping.overlay.region.bg.enabled: yes
snapping.overlay.edge.bg.enabled: yes
snapping.overlay.region.border.enabled: yes
snapping.overlay.edge.border.enabled: yes
snapping.overlay.region.bg.color: #cfa24f40
snapping.overlay.edge.bg.color: #cfa24f40
snapping.overlay.region.border.width: 2
snapping.overlay.edge.border.width: 2
snapping.overlay.region.border.color: #0d0d10,#edca77,#0d0d10
snapping.overlay.edge.border.color: #0d0d10,#edca77,#0d0d10
'''


def settings(text):
    return [tuple(line.split(': ', 1)) for line in text.splitlines() if line and not line.startswith('#')]


class LabwcThemeTest(unittest.TestCase):
    def test_themerc_matches_the_design(self):
        self.assertEqual(settings((THEME / 'themerc').read_text()), settings(EXPECTED))

    def test_every_theme_png_is_a_doubled_cell_from_the_study(self):
        manifest = json.loads((PACK / 'look.json').read_text())
        self.assertEqual(manifest['frame_sprites'], {name: f'sprites/frame/{name}' for name in PNG_NAMES})
        self.assertEqual({file.name for file in THEME.iterdir()}, {'themerc', *PNG_NAMES})
        for name, file in sorted(manifest['frame_sprites'].items()):
            with self.subTest(file=name), Image.open(STUDY / name) as study, Image.open(PACK / file) as cell:
                self.assertEqual((study.mode, study.size), ('RGBA', (24, 20)))
                self.assertEqual((cell.mode, cell.size, cell.tobytes()), (study.mode, study.size, study.tobytes()))
                with Image.open(THEME / name) as button:
                    self.assertEqual((button.mode, button.size), ('RGBA', (48, 40)))
                    cell_pixels, button_pixels = cell.load(), button.load()
                    self.assertEqual([button_pixels[x, y] for y in range(button.height) for x in range(button.width)],
                                     [cell_pixels[x // 2, y // 2] for y in range(button.height) for x in range(button.width)])

    def test_theme_regenerates_from_a_fresh_pack(self):
        make_pack = runpy.run_path(str(ROOT / 'os/look/make_pack.py'))['generate']
        make_theme = runpy.run_path(str(ROOT / 'os/look/make_labwc_theme.py'))['generate']
        with tempfile.TemporaryDirectory() as folder:
            pack, theme = Path(folder) / 'pack', Path(folder) / 'theme'
            make_pack(pack)
            make_theme(pack, theme)
            self.assertEqual((pack / 'look.json').read_bytes(), (PACK / 'look.json').read_bytes())
            self.assertEqual((theme / 'themerc').read_bytes(), (THEME / 'themerc').read_bytes())
            self.assertEqual({file.name for file in theme.iterdir()}, {'themerc', *PNG_NAMES})
            for name in sorted(PNG_NAMES):
                with self.subTest(file=name), Image.open(THEME / name) as actual, Image.open(theme / name) as made:
                    self.assertEqual((actual.mode, actual.size, actual.tobytes()), (made.mode, made.size, made.tobytes()))
