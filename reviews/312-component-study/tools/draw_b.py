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

from PIL import Image, ImageDraw  # noqa: E402

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

    def __init__(self, jar, jersey=None, title_font='jersey'):
        """`jersey` is version A's look, whose font labwc can use; `title_font` 'game' draws titles in the game's
        letters instead, which labwc could only show after a font file is built from them (section 5, way b)."""
        self.jar = jar
        self.font = GameFont(jar)
        self.jersey, self.title_font = jersey, title_font
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

    # ---- the window frame (step 2): a chest window. The game's container grey with its unshadowed dark label,
    # the white outline the game gives a focused widget, inventory slots as buttons, a gold nugget for the menu.

    white, label = (255, 255, 255, 255), (64, 64, 64, 255)

    def frame_colours(self, active):
        if active:
            return dict(bar=(198, 198, 198, 255), title=self.label, border=self.white)
        return dict(bar=(139, 139, 139, 255), title=self.label, border=(0, 0, 0, 255))

    def menu_colours(self):
        """The game's tooltip: its colours read from the tooltip sprites, the chosen row lit like a hovered slot."""
        bg = self.sprite('gui/sprites/tooltip/background')
        frame = self.sprite('gui/sprites/tooltip/frame')
        face = bg.getpixel((bg.width // 2, bg.height // 2))[:3] + (255,)
        lit = Image.alpha_composite(Image.new('RGBA', (1, 1), face), Image.new('RGBA', (1, 1), (255, 255, 255, 96)))
        return dict(bg=face, text=self.white, chosen_bg=lit.getpixel((0, 0)), chosen_text=self.value,
                    border=frame.getpixel((frame.width // 2, 0))[:3] + (255,), separator=(85, 85, 85, 255))

    def title_width(self, text):
        return self.font.width(text) if self.title_font == 'game' else self.jersey.text_width(text)

    def title(self, image, x, text, colour):
        if self.title_font == 'game':
            self.font.draw(image, x, 6, text, colour, shadow=False)  # the game's 7-unit capitals, centred
        else:
            self.jersey.title(image, x, text, colour)

    def _highlight(self, cell, layer, x, y):
        """The game's own light over a hovered slot (a 16 x 16 square inside a 24 x 24 sprite)."""
        cell.alpha_composite(self.sprite(f'gui/sprites/container/slot_highlight_{layer}').crop((4, 4, 20, 20)), (x, y))

    def title_button(self, kind, state):
        cell = Image.new('RGBA', (kit.CELL_W, kit.TITLE_H), (0, 0, 0, 0))
        hover, active = state.startswith('hover'), state == 'active'
        if kind == 'menu':
            nugget = self.sprite('item/gold_nugget')
            if hover:
                self._highlight(cell, 'back', 4, 2)
            elif not active:
                nugget = nugget.copy()
                nugget.putalpha(nugget.getchannel('A').point(lambda v: v * 2 // 5))
            cell.alpha_composite(nugget, (4, 2))
            return cell
        cell.alpha_composite(self.sprite('gui/sprites/container/slot'), (3, 1))
        if hover:
            self._highlight(cell, 'back', 4, 2)
        colour = self.red if hover and kind == 'close' else self.white if hover or active else self.label
        lit = hover or active
        cell.alpha_composite(kit.glyph(kind, colour, tuple(c // 4 for c in colour[:3]) + (255,) if lit else None),
                             (8, 6))
        if hover:
            self._highlight(cell, 'front', 4, 2)
        return cell

    # ---- layouts and switching (step 3): labwc's menu, Alt+Tab and snapping preview, in the game's colours.

    def layout_icon(self, rects):
        """The pictogram as the game would draw a map of slots: black screen, grey edge, the slot white."""
        return kit.pictogram(rects, self.quiet, (0, 0, 0, 255), self.white)

    def switcher_colours(self):
        """Alt+Tab in the tooltip's colours, as the menus; the chosen window framed in white, as the game frames the
        chosen world in its list of worlds."""
        menu = self.menu_colours()
        return dict(bg=menu['bg'], border=menu['border'], text=self.white, chosen_border=self.white,
                    chosen_bg=menu['chosen_bg'], outline=((0, 0, 0, 255), self.white, (0, 0, 0, 255)))

    def snap_colours(self):
        """The preview lit like a hovered slot: white at about a third, framed in white."""
        return dict(fill=(255, 255, 255, 80), lines=((0, 0, 0, 255), self.white, (0, 0, 0, 255)))

    # ---- the overview (step 4): our own program, so B can use the game's textures here, not only its colours.

    def veil(self, width, height):
        """The game's own background for a screen opened over the world, tiled. The game also blurs the world
        behind it; labwc has no blur, so a dark layer lies under the tiles instead."""
        tile = self.sprite('gui/inworld_menu_background')
        image = Image.new('RGBA', (width, height), (0, 0, 0, 170))
        for x in range(0, width, tile.width):
            for y in range(0, height, tile.height):
                image.alpha_composite(tile, (x, y))
        return image

    def card(self, width, height):
        """The game's popup panel, nine-sliced by its own border of 6."""
        return kit.nine_slice(self.sprite('gui/sprites/popup/background'), width, height, 6)

    def icon_slot(self, image, x, y, sprite):
        image.alpha_composite(self.sprite('gui/sprites/container/slot'), (x + 1, y + 1))
        image.alpha_composite(sprite, (x + 2, y + 2))

    def count_badge(self, image, x, y, count):
        """The game's own stack count: white with its shadow, at the bottom right of the item."""
        text = str(count)
        self.text(image, x + 19 - self.text_width(text), y + 11, text, self.white)

    def overview_colours(self):
        return dict(text=self.white, quiet=self.quiet, hint=self.quiet)

    def overview_row(self, width, state):
        """Lit like a hovered slot; the chosen row framed in white, as the game frames the chosen world."""
        if state == 'normal':
            return None
        row = Image.new('RGBA', (width, 20), (255, 255, 255, 48))
        if state == 'chosen':
            ImageDraw.Draw(row).rectangle((0, 0, width - 1, 19), outline=self.white)
        return row

    def close_button(self, state):
        cell = Image.new('RGBA', (14, 14), (0, 0, 0, 0))
        colour = self.red if state == 'hover' else self.white
        cell.alpha_composite(kit.glyph('close', colour, tuple(c // 4 for c in colour[:3]) + (255,)), (3, 3))
        return cell

    def home_picture(self):
        return kit.home_picture()  # always our own drawing: never the game's world or a picture of it

    # ---- the password window (step 4): its inside is version A in every look (COMPONENTS.md 4.6).

    def password_look(self):
        return self.jersey

    # ---- the settings screen (step 4): the mod draws it with the game's option buttons.

    def settings_button(self, width, label, state='button'):
        face = {'button': 'button', 'button-hover': 'button_highlighted', 'button-disabled': 'button_disabled'}[state]
        image = kit.nine_slice(self.sprite(f'gui/sprites/widget/{face}'), width, 20, 3)
        self.text(image, (width - self.text_width(label)) // 2, 6, label, self.white)
        return image


class LookC(LookB):
    """Version C: the game's own buttons, with signs from the game's font where it has them. Elsewhere C is B."""

    name = 'C'
    letters = {'iconify': '_', 'max': '□', 'close': '×'}

    def title_button(self, kind, state):
        if kind == 'menu':
            return super().title_button(kind, state)
        cell = Image.new('RGBA', (kit.CELL_W, kit.TITLE_H), (0, 0, 0, 0))
        hover, active = state.startswith('hover'), state == 'active'
        face, inset = (('widget/button_highlighted', 3) if hover else ('widget/button', 3) if active
                       else ('widget/button_disabled', 1))
        cell.alpha_composite(kit.nine_slice(self.sprite(f'gui/sprites/{face}'), 22, 20, inset), (1, 0))
        colour = self.white if hover or active else self.dim
        if kind in self.letters:
            text = self.letters[kind]
            self.font.draw(cell, 1 + (22 - self.font.width(text)) // 2, 6, text, colour)
        elif kind == 'max_toggled':  # the font has no restore sign: two of its squares, one behind the other
            x = 1 + (22 - self.font.width('□')) // 2
            self.font.draw(cell, x + 1, 5, '□', colour)
            self.font.draw(cell, x - 1, 7, '□', colour)
        else:  # shade and desk: the font has nothing, so B's pictogram on the game's button
            cell.alpha_composite(kit.glyph(kind, colour, tuple(c // 4 for c in colour[:3]) + (255,)), (8, 6))
        return cell

    def overview_row(self, width, state):
        """C: every window's row is one of the game's buttons, highlighted when chosen or under the pointer."""
        face = 'button_highlighted' if state in ('chosen', 'hover') else 'button'
        return kit.nine_slice(self.sprite(f'gui/sprites/widget/{face}'), width, 20, 3)

    def close_button(self, state):
        """C: the game's own small cross button."""
        return self.sprite('gui/sprites/widget/cross_button_highlighted' if state == 'hover'
                           else 'gui/sprites/widget/cross_button').copy()


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


def title_bars_sheet(a, b, b_game, c):
    """The same title bar in every look: active, pointer on close, inactive, at 2x."""
    rows = (('A: our own art (public pictures A-09 to A-11)', a),
            ('B: the game\'s textures, the title in Jersey 10 as labwc can show it now', b),
            ('B with the game\'s own letters in the title: needs a font file built from them on his machine', b_game),
            ('C: the game\'s own buttons, signs from its font; everything else as B', c))
    sheet = Image.new('RGBA', (1920, 40 + len(rows) * 124), SKY)
    y = 20
    for name, look in rows:
        sheet.alpha_composite(caption(b, name), (30, y))
        for index, (active, hover) in enumerate(((True, None), (True, 'close'), (False, None))):
            bar = kit.window_frame(look, 300, kit.TITLE_H + 2, 'Einkaufsliste.txt - Editor', active, hover=hover)
            sheet.alpha_composite(kit.up(bar, 2), (30 + index * 620, y + 34))
        y += 124
    return sheet


def menus_and_switchers_sheet(a, b):
    """Step 3's sheet to choose from: the layout menu with its submenu, and Alt+Tab's panel, in A and in B."""
    world = kit.world_scene(a)
    sheet = Image.new('RGBA', (1920, 1290), SKY)
    for column, (name, look) in enumerate((('A: our own art', a), ('B: the game\'s colours (C uses B here)', b))):
        x = 30 + column * 960
        sheet.alpha_composite(caption(b, name), (x, 20))
        menus, _ = kit.layout_menu_open(look)
        sheet.alpha_composite(kit.up(menus, 2), (x, 60))
    for row, (name, look) in enumerate((('A: Alt+Tab', a), ('B: Alt+Tab', b))):
        y = 660 + row * 310
        sheet.alpha_composite(caption(b, name), (30, y))
        sheet.alpha_composite(kit.switcher_panel(look, world), (30, y + 36))
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


def overview_sheet(a, b, c):
    """Step 4's sheet to choose from: Home, the editor's card and Chrome's card in A, B and C, at 2x on the veil."""
    sheet = Image.new('RGBA', (1920, 1000), SKY)
    for column, (name, look) in enumerate((('A: our own art', a), ('B: the game\'s textures and font', b),
                                           ('C: the game\'s buttons as rows', c))):
        x = 30 + column * 630
        sheet.alpha_composite(caption(b, name), (x, 20))
        sheet.alpha_composite(kit.up(look.veil(290, 470), 2), (x, 56))
        y = 66
        cards = [kit.home_card(look)]
        for app, icon, windows in kit.OVERVIEW_APPS:
            if app in ('Editor', 'Chrome'):
                cards.append(kit.overview_card(look, app, kit.APP_ICONS[icon], windows,
                                               chosen=1 if app == 'Editor' else None,
                                               hover=1 if app == 'Chrome' else None)[0])
        for card in cards:
            sheet.alpha_composite(kit.up(card, 2), (x + 10, y))
            y += card.height * 2 + 16
    return sheet


def password_sheet(b, c):
    """The password window under B's and C's frames: the frame follows the look, the inside stays A."""
    sheet = Image.new('RGBA', (1920, 560), SKY)
    for column, (name, look) in enumerate((('B: B\'s frame, the inside in A', b), ('C: C\'s frame, the inside in A', c))):
        x = 30 + column * 940
        sheet.alpha_composite(caption(b, name), (x, 20))
        sheet.alpha_composite(kit.up(kit.password_window(look, kit.OWNER_LABEL), 2), (x, 60))
    note = 'In every look the inside comes from the image\'s own files, never from the game or his home folder.'
    sheet.alpha_composite(caption(b, note), (30, 500))
    return sheet


INDEX = '''# Version B's mockups (package 312): private

Every picture here contains Minecraft's textures or font. Nothing in this folder is ever committed, attached to a
pull request or put on a public page. The lead (`linux-desktop`) shows them to the owner on a private page.
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
| B-07 | `B-07-frame-buttons.png` | Step 2, the window frame in B: every labwc title-bar image at 2x (menu, minimize, maximize, restore, close, and the unused shade and all-desktops), active, pointer on it, inactive. Buttons are the game's inventory slot with our pictograms in the game's white; the pointer lights the slot with the game's own slot light; close turns its sign red; the menu button is a gold nugget. | A-09 |
| B-08 | `B-08-frame-buttons-c.png` | The same in C: the game's own 20-unit button, highlighted under the pointer, dark on an inactive window, with signs from the game's font (`_`, a square, a multiplication sign; restore as two squares). | A-09 |
| B-09 | `B-09-frame-windows.png` | B on the drawn noon scene at 1920 x 1080, 2x: an inactive terminal behind, the active editor in front with the pointer on close. The bar is the game's chest-window grey with its dark label colour; the active window has the game's white focus outline. Titles in Jersey 10. | A-10 |
| B-10 | `B-10-frame-windows-c.png` | The same scene in C. | A-10 |
| B-11 | `B-11-frame-a-b-c.png` | One title bar in A, B, B with the game's letters in the title, and C: active, pointer on close, inactive, at 2x. The sheet to choose from. | A-09 |
| B-12 | `B-12-frame-maximized-menu.png` | B maximized (no border, restore shown) with the layout menu a right-click on maximize opens, in the game's tooltip colours: step 3's rows with their pictograms (black screens, the slot in white), "Share the screen with" chosen and its submenu open on the left. | A-11 |
| B-13 | `B-13-half-and-world.png` | Step 3, layouts in B: the editor in the left half with the drawn world in the right half, and a terminal dragged to the right edge, where labwc's preview shows the half it will fill, lit white like a hovered slot. 1920 x 1080 at 2x. | A-13 |
| B-14 | `B-14-switcher.png` | Alt+Tab in B: the panel in the tooltip's colours, the chosen window framed in white as the game frames the chosen world in its world list; the chosen terminal brought forward with a black-white-black outline. Titles in Jersey 10 (labwc's font). | A-14 |
| B-15 | `B-15-menus-and-switchers-a-b.png` | The layout menu with its submenu, and the Alt+Tab panel, in A and in B side by side. C uses B for both. The sheet to choose from for step 3. | A-11, A-14 |
| B-16 | `B-16-overview.png` | Step 4, the overview in B over the drawn scene at 1920 x 1080, 2x: the game's in-world screen background as the veil, the game's popup panel as each card, item-style stack counts, the game's font; the chosen row framed in white, the hovered row lit with its close sign red. The Home picture is our own drawing in every look. | A-15 |
| B-17 | `B-17-overview-a-b-c.png` | Home, the editor's card and Chrome's card in A, B and C side by side, at 2x. In C every window row is one of the game's buttons and close is the game's small cross button. The sheet to choose from for the overview. | A-15 |
| B-18 | `B-18-password-b-c.png` | The password window under B's and under C's frame, at 2x: the title bar follows the look, the inside stays A in every look (section 4.6). | A-17, A-18 |
| B-19 | `B-19-settings.png` | The settings screen as the mod draws it, with the game's option buttons and font over its in-world background, at 3x; the pointer on "Look", and B's indicator shown once at the top centre as the preview of a change. | A-19 |

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
    b = LookB(zipfile.ZipFile(GAME_JAR), jersey=a)

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

    # Step 2: the window frame in B and C.
    c = LookC(zipfile.ZipFile(GAME_JAR), jersey=a)
    b_game = LookB(zipfile.ZipFile(GAME_JAR), jersey=a, title_font='game')
    save(kit.frame_buttons_sheet(b, lambda text: caption(b, text),
                                 'Version B: every title-bar image at 2x (inventory slots and the slot light)'),
         'B-07-frame-buttons.png')
    save(kit.frame_buttons_sheet(c, lambda text: caption(b, text),
                                 'Version C: the game\'s own buttons with signs from its font, at 2x'),
         'B-08-frame-buttons-c.png')
    save(kit.frame_scene(b, hotbar, scene_look=a), 'B-09-frame-windows.png')
    save(kit.frame_scene(c, hotbar, scene_look=a), 'B-10-frame-windows-c.png')
    save(title_bars_sheet(a, b, b_game, c), 'B-11-frame-a-b-c.png')
    save(kit.maximized_scene(b), 'B-12-frame-maximized-menu.png')

    # Step 3: layouts and switching in B. The game has no control of its own for a menu, a switcher or a
    # snapping preview, so C uses B for all three; its windows would wear C's frame, as in B-10.
    save(kit.half_scene(b, hotbar, scene_look=a), 'B-13-half-and-world.png')
    save(kit.switcher_scene(b, hotbar, scene_look=a), 'B-14-switcher.png')
    save(menus_and_switchers_sheet(a, b), 'B-15-menus-and-switchers-a-b.png')

    # Step 4: the overview, the password window and the settings screen. The game has its own buttons, so C
    # differs from B in the overview's rows; the password window's inside is A in every look.
    save(kit.overview_scene(b, hotbar, scene_look=a), 'B-16-overview.png')
    save(overview_sheet(a, b, c), 'B-17-overview-a-b-c.png')
    save(password_sheet(b, c), 'B-18-password-b-c.png')
    save(kit.settings_scene(b, hotbar, ('Minecraft textures', 'Top centre', 'Medium'),
                            kit.indicator(b, kit.INDICATOR_STATES[3][1], b.icons), scene_look=a), 'B-19-settings.png')

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
