#!/usr/bin/env python3
"""Draw version B's mockups: the same pieces as version A, with the game's own textures and font.

    python3 -I reviews/312-component-study/tools/draw_b.py --font /path/to/Jersey10-Regular.ttf

PRIVATE OUTPUT. Every picture this script makes contains the game's pixels, and the repo is public. So it writes to
one fixed folder outside the checkout and nowhere else, and there is no option to change that:

    ~/.local/state/aresos-dev/312-look-b/

It reads the game read-only from the mod's development copy (the brief's source for the study), never from
~/.minecraft, a launcher's folder or a download. If that copy is missing it stops and draws nothing.
This file itself holds no game pixels: only the names of the game's files.
"""

import argparse
import io
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402

import look as kit  # noqa: E402

PRIVATE = os.path.expanduser('~/.local/state/aresos-dev/312-look-b')
GAME_JAR = os.path.expanduser('~/.gradle/caches/fabric-loom/26.2/minecraft-client.jar')
TEXTURES = 'assets/minecraft/textures/'
SKY, PAGE = kit.rgb('#8fb3f3'), kit.rgb('#f6f6f4')


class GameFont:
    """The game's default font: three bitmap sheets and the table in font/include/default.json."""

    def __init__(self, jar):
        self.glyphs = {}
        table = json.loads(jar.read('assets/minecraft/font/include/default.json'))
        for provider in table['providers']:
            if provider['type'] != 'bitmap':
                continue
            space, path = provider['file'].split(':')
            sheet = Image.open(io.BytesIO(jar.read(f'assets/{space}/textures/{path}'))).convert('RGBA')
            rows = provider['chars']
            cell_w, cell_h = sheet.width // len(rows[0]), sheet.height // len(rows)
            assert provider.get('height', 8) == cell_h, (path, cell_h)  # drawn at its own size, never scaled
            for row_index, row in enumerate(rows):
                for column, letter in enumerate(row):
                    if letter in ('\u0000', ' ') or letter in self.glyphs:
                        continue
                    alpha = sheet.crop((column * cell_w, row_index * cell_h, (column + 1) * cell_w,
                                        (row_index + 1) * cell_h)).getchannel('A').point(lambda v: 255 if v else 0)
                    box = alpha.getbbox()
                    if box:
                        self.glyphs[letter] = (alpha, box[2], provider['ascent'])

    def width(self, text):
        return sum(4 if letter == ' ' else self.glyphs[letter][1] + 1 for letter in text) - 1

    def draw(self, image, x, y, text, colour, shadow=True):
        """The capitals' top row at y. The shadow is the colour at a quarter, one unit down and right."""
        passes = (((1, 1), tuple(c // 4 for c in colour[:3]) + (255,)), ((0, 0), colour)) if shadow \
            else (((0, 0), colour),)
        for (ox, oy), ink in passes:
            pen = x
            for letter in text:
                if letter == ' ':
                    pen += 4
                    continue
                mask, width, ascent = self.glyphs[letter]
                image.paste(ink, (pen + ox, y + 7 - ascent + oy), mask)
                pen += width + 1


class LookB:
    """The game's art for the same pieces: a toast as the plate, a boss bar with 20 notches, items as icons."""

    name = 'B'
    cap, line_gap = 7, 4
    pad, gap, row_gap = 7, 5, 6
    icon_box = 16
    bar_w, bar_h = 182, 5
    ink, value, quiet, dim, red = ((255, 255, 255, 255), (255, 255, 85, 255), (170, 170, 170, 255),
                                   (160, 160, 160, 255), (255, 85, 85, 255))
    # The game has no sun, loudspeaker or microphone picture of the right size. These items stand in.
    icons = {'brightness': ('item/lantern',), 'volume': ('item/bell',), 'volume-muted': ('item/bell', 'item/barrier'),
             'microphone': ('gui/sprites/social_interactions/mute_button',),
             'microphone-off': ('gui/sprites/social_interactions/unmute_button',)}

    def __init__(self, jar):
        self.jar = jar
        self.font = GameFont(jar)
        self._cache = {}

    def sprite(self, name):
        if name not in self._cache:
            self._cache[name] = Image.open(io.BytesIO(self.jar.read(f'{TEXTURES}{name}.png'))).convert('RGBA')
        return self._cache[name]

    def text_width(self, text):
        return self.font.width(text)

    def text(self, image, x, y, text, colour, shadow=True):
        self.font.draw(image, x, y, text, colour, shadow)

    def plate(self, width, height):
        return kit.nine_slice(self.sprite('gui/sprites/toast/now_playing'), width, height, 4)

    def icon(self, image, x, y, names, off=False):
        for name in names:
            sprite = self.sprite(name)
            if off:
                sprite = sprite.copy()
                sprite.putalpha(sprite.getchannel('A').point(lambda v: v * 2 // 5))
            image.alpha_composite(sprite, (x + (self.icon_box - sprite.width) // 2,
                                           y + (self.icon_box - sprite.height) // 2))

    def bar(self, image, x, y, level, muted=False, limit=False):
        colour = 'white' if muted else 'yellow'
        filled = round(self.bar_w * min(level, 100) / 100)
        for layer in (f'{colour}_background', 'notched_20_background'):
            image.alpha_composite(self.sprite(f'gui/sprites/boss_bar/{layer}'), (x, y))
        if filled:
            for layer in (f'{colour}_progress', 'notched_20_progress'):
                image.alpha_composite(self.sprite(f'gui/sprites/boss_bar/{layer}').crop((0, 0, filled, 5)), (x, y))

    def slider_form(self, state):
        """The other way B could go: the game's own option slider or button, text inside, no plate and no icon."""
        if state['kind'] == 'level':
            image = self.sprite('gui/sprites/widget/slider').copy()
            image.alpha_composite(self.sprite('gui/sprites/widget/slider_handle'),
                                  (round((200 - 8) * min(state['level'], 100) / 100), 0))
            text = f'{state["label"]}: ' + ('muted' if state.get('muted') else f'{state["level"]}%')
            colour = self.quiet if state.get('muted') else self.ink
        else:
            image = self.sprite('gui/sprites/widget/button_disabled' if state.get('off')
                                else 'gui/sprites/widget/button').copy()
            text = f'{state["label"]}: {state["status"]}'
            colour = self.dim if state.get('off') else self.ink
        self.text(image, (200 - self.text_width(text)) // 2, 6, text, colour)
        return image


def caption(look, text, factor=2):
    image = Image.new('RGBA', (look.text_width(text) + 2, look.cap + 6), (0, 0, 0, 0))
    look.text(image, 0, 2, text, (20, 20, 24, 255), shadow=False)
    return kit.up(image, factor)


def states_sheet(look, draw, title):
    pitch = 140
    sheet = Image.new('RGBA', (1500, 70 + pitch * len(kit.INDICATOR_STATES)), SKY)
    sheet.paste(PAGE, (750, 0, 1500, sheet.height))
    sheet.alpha_composite(caption(look, title), (30, 16))
    for index, (note, state) in enumerate(kit.INDICATOR_STATES):
        y = 64 + pitch * index
        sheet.alpha_composite(caption(look, note), (30, y))
        piece = kit.up(draw(state), 3)
        sheet.alpha_composite(piece, (30, y + 34))
        sheet.alpha_composite(piece, (780, y + 34))
    return sheet


def comparison_sheet(a, b):
    pitch = 150
    sheet = Image.new('RGBA', (1920, 80 + pitch * len(kit.INDICATOR_STATES)), SKY)
    columns = ((20, 'A: our own art'), (575, 'B: the game\'s textures and font, same layout'),
               (1260, 'B: as the game\'s own option slider'))
    for x, title in columns:
        sheet.alpha_composite(caption(b, title), (x, 20))
    for index, (note, state) in enumerate(kit.INDICATOR_STATES):
        y = 70 + pitch * index
        sheet.alpha_composite(caption(b, note), (20, y))
        for (x, _), piece in zip(columns, (kit.indicator(a, state, kit.ICONS_A), kit.indicator(b, state, b.icons),
                                           b.slider_form(state))):
            sheet.alpha_composite(kit.up(piece, 3), (x, y + 30))
    return sheet


def same_glyphs(a, b):
    """How many printable ASCII letters have the same bitmap in Jersey 10 and in the game's font."""
    same = []
    for code in range(33, 127):
        letter = chr(code)
        ours = a.glyph_mask(letter)
        theirs = b.font.glyphs[letter][0]
        theirs = theirs.crop(theirs.getbbox())
        if ours is not None and ours.size == theirs.size and ours.tobytes() == theirs.tobytes():
            same.append(letter)
    return same


INDEX = '''# Version B's mockups (package 312): private

Every picture here contains Minecraft's textures or font. Nothing in this folder is ever committed, attached to a
pull request or put on a public page. The lead (`linux-desktop`) shows them to Patrik on a private page.
Made by `reviews/312-component-study/tools/draw_b.py` from the mod's development copy of the game, read-only.
All values are made up.

| ID | File | What it shows | Pairs with |
|---|---|---|---|
| B-01 | `B-01-indicator-states.png` | The brightness and volume indicator in every state at 3x, in version A's layout: the game's "now playing" toast as the plate, a yellow boss bar with 20 notches, the game's font, and game items as icons (lantern, bell, bell with the barrier sign, the chat-bubble mute buttons). Left over the sky colour, right over a white page. | A-04 |
| B-02 | `B-02-indicator-slider-form.png` | The other way B could go: each state as the game's own option slider or button, 200 x 20 units, the text inside it, no plate and no icon. At 3x. | A-04 |
| B-03 | `B-03-indicator-a-and-b.png` | A and both B forms side by side for every state, at 3x. The sheet to choose from. | A-04 |
| B-04 | `B-04-indicator-top.png` | B's indicator top centre on the drawn noon scene at 1920 x 1080, with the game's hotbar at 3x. | A-06 |
| B-05 | `B-05-indicator-over-app.png` | B's indicator top centre over a light program at 1920 x 1080. | A-08 |
| B-06 | `B-06-indicator-scales.png` | B's indicator at 2x, 3x and 4x in real screen pixels. | A-05 |

`work/parts.png` is a working sheet of the game sprites that were looked at; it is not a mockup.

Font check, step 1: {font_check}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--font', required=True, help='Jersey10-Regular.ttf, kept outside the repo (for the A column)')
    arguments = parser.parse_args()
    if not os.path.isfile(GAME_JAR):
        raise SystemExit('The development copy of the game is not there: draw no B mockups and tell the lead.')
    if not os.path.isdir(PRIVATE) or os.stat(PRIVATE).st_mode & 0o077:
        raise SystemExit(f'{PRIVATE} must exist and be closed to everyone else (mode 700).')
    a = kit.LookA(arguments.font)
    b = LookB(zipfile.ZipFile(GAME_JAR))

    def save(image, name):
        path = os.path.join(PRIVATE, name)
        image.convert('RGB').save(path, optimize=True)
        os.chmod(path, 0o600)
        print(f'{name}: {image.width} x {image.height}')

    save(states_sheet(b, lambda state: kit.indicator(b, state, b.icons),
                      'Version B: the indicator in every state, at 3x (the game\'s textures and font)'),
         'B-01-indicator-states.png')
    save(states_sheet(b, b.slider_form, 'Version B, the other form: the game\'s own slider and button, at 3x'),
         'B-02-indicator-slider-form.png')
    save(comparison_sheet(a, b), 'B-03-indicator-a-and-b.png')
    scene = kit.world_scene(a)
    hotbar = kit.up(b.sprite('gui/sprites/hud/hotbar'), 3)
    scene.alpha_composite(hotbar, ((1920 - hotbar.width) // 2, 1080 - hotbar.height))
    save(kit.place(scene, kit.indicator(b, kit.INDICATOR_STATES[3][1], b.icons), 3, 'top'), 'B-04-indicator-top.png')
    title_font = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'os',
                                               'config', 'usr', 'share', 'fonts', 'aresos',
                                               'SpaceGrotesk-Variable.ttf'))
    save(kit.place(kit.app_scene(title_font), kit.indicator(b, kit.INDICATOR_STATES[0][1], b.icons), 3, 'top'),
         'B-05-indicator-over-app.png')
    piece = kit.indicator(b, kit.INDICATOR_STATES[0][1], b.icons)
    sheet = Image.new('RGBA', (1920, 500), SKY)
    sheet.paste(PAGE, (960, 0, 1920, 500))
    y = 20
    for factor in (2, 3, 4):
        big = kit.up(piece, factor)
        sheet.alpha_composite(caption(b, f'{factor}x: {big.width} x {big.height} px of the 1920 x 1080 screen'), (30, y))
        sheet.alpha_composite(big, (30, y + 30))
        sheet.alpha_composite(big, (990, y + 30))
        y += big.height + 60
    save(sheet, 'B-06-indicator-scales.png')

    same = same_glyphs(a, b)
    capital = b.font.glyphs['H'][0]
    font_check = (f'of the 94 printable ASCII letters, {len(same)} have the same bitmap in Jersey 10 and in the '
                  f'game\'s font{" (" + " ".join(same) + ")" if same else ""}. Capitals are {a.glyph_mask("H").height} '
                  f'units high in Jersey 10 and {capital.getbbox()[3] - capital.getbbox()[1]} in the game\'s font.')
    print(font_check)
    with open(os.path.join(PRIVATE, 'B-INDEX.md'), 'w', encoding='utf-8') as index:
        index.write(INDEX.format(font_check=font_check))
    os.chmod(os.path.join(PRIVATE, 'B-INDEX.md'), 0o600)


if __name__ == '__main__':
    main()
