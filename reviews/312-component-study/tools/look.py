"""Package 312's drawing kit: one layout per piece, one Look per set of art.

The study's rule is that a piece's function (what it shows, where its parts go) is separate from its look (colours,
sprites, font). This file follows that rule so the mockups prove it: `indicator()` is the piece and knows no colour
or pixel; `LookA` is AresOS's own art, made here from flat colours and small pixel maps. Version B's look
(`draw_b.py`) reads the game's files at run time and draws the same pieces through the same functions.

Everything is drawn at one image pixel per GUI unit and enlarged with `up()` in whole steps, so it stays on the grid.
Nothing in this file comes from the game.
"""

import hashlib

from PIL import Image, ImageDraw, ImageFont

# Jersey 10, SIL Open Font License 1.1, from Google Fonts' ofl/jersey10. Not committed: pass its path to the scripts.
JERSEY10_SHA256 = 'db9cbd091617048a145d249daa2b815fe7083be6ab66ac26626e21a4e01c3e82'


def rgb(value, alpha=255):
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


# Version A's palette. (name, colour, what it is for.) COMPONENTS.md section 2 explains where each comes from.
PALETTE = (
    ('outline', '#0d0d10', 'hard outline, text shadow (the Crown wall)'),
    ('stone-950', '#121117', 'sunken edge, top and left'),
    ('stone-900', '#1a181f', 'slot and trough floor'),
    ('stone-800', '#221f28', 'unlit step, pressed button, lip'),
    ('stone-700', '#2b2832', 'plate face (the road\'s paving)'),
    ('stone-600', '#3a3644', 'button face'),
    ('stone-500', '#504b5c', 'raised edge of a plate'),
    ('stone-400', '#6c6779', 'raised edge of a button, switched-off icons'),
    ('stone-300', '#948fa0', 'muted steps'),
    ('ink', '#f3f1ea', 'text and icons'),
    ('ink-quiet', '#a6a39a', 'second line, muted icon'),
    ('ink-dim', '#6f6b62', 'text of something not available'),
    ('gold-100', '#f7e2a6', 'highlight on gold'),
    ('gold-300', '#edca77', 'values, the chosen thing, hover'),
    ('gold-500', '#cfa24f', 'lit steps'),
    ('gold-700', '#94702f', 'shade on gold'),
    ('gold-900', '#5b431b', 'a part step'),
    ('red-300', '#ff6257', 'muted, off, close'),
    ('red-600', '#b63a32', 'shade on red'),
)
P = {name: rgb(colour) for name, colour, _ in PALETTE}


def up(image, factor):
    """Enlarge in whole steps without smoothing."""
    return image.resize((image.width * factor, image.height * factor), Image.Resampling.NEAREST)


def pix(rows, key):
    """A sprite from rows of letters; '.' is see-through."""
    width = len(rows[0])
    assert all(len(row) == width for row in rows), rows
    image = Image.new('RGBA', (width, len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, letter in enumerate(row):
            if letter != '.':
                image.putpixel((x, y), key[letter])
    return image


def nine_slice(sprite, width, height, inset):
    """Corners stay, edges and middle repeat (they are tiled, never stretched, as the game does)."""
    left, top, right, bottom = (inset,) * 4 if isinstance(inset, int) else inset
    out = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    columns = ((0, left, 0, left), (left, sprite.width - right, left, width - right),
               (sprite.width - right, sprite.width, width - right, width))
    rows = ((0, top, 0, top), (top, sprite.height - bottom, top, height - bottom),
            (sprite.height - bottom, sprite.height, height - bottom, height))
    for sx0, sx1, dx0, dx1 in columns:
        for sy0, sy1, dy0, dy1 in rows:
            if dx1 <= dx0 or dy1 <= dy0 or sx1 <= sx0 or sy1 <= sy0:
                continue
            part = sprite.crop((sx0, sy0, sx1, sy1))
            area = Image.new('RGBA', (dx1 - dx0, dy1 - dy0), (0, 0, 0, 0))
            for x in range(0, area.width, part.width):
                for y in range(0, area.height, part.height):
                    area.paste(part, (x, y))
            out.paste(area, (dx0, dy0))
    return out


# ---------------------------------------------------------------- version A's sprites

A_KEY = {'O': P['outline'], 'L': P['stone-500'], 'F': P['stone-700'], 'D': P['stone-900'], 'M': P['stone-700'],
         'S': P['stone-900'], 'E': P['stone-950'], 'H': P['stone-400'], 'B': P['stone-600'], 'P': P['stone-800'],
         'h': P['stone-300'], 'b': P['stone-500'], 'Y': P['gold-300'],
         'i': P['ink'], 'q': P['ink-quiet'], 'g': P['gold-300'], 'G': P['gold-500'], 'd': P['gold-700'],
         'r': P['red-300']}

A_SPRITES = {
    # A raised plate: outline, light edge top and left, dark edge bottom and right. Nine-slice inset 3.
    'plate': pix(['.OOOOOOO.', 'OLLLLLLMO', 'OLFFFFFDO', 'OLFFFFFDO', 'OLFFFFFDO', 'OLFFFFFDO', 'OLFFFFFDO',
                  'OMDDDDDDO', '.OOOOOOO.'], A_KEY),
    # A sunken slot, the plate's edges the other way round. Nine-slice inset 2. Also the bar's trough.
    'slot': pix(['EEEEEEM', 'ESSSSSL', 'ESSSSSL', 'ESSSSSL', 'ESSSSSL', 'ESSSSSL', 'MLLLLLL'], A_KEY),
    # Buttons, 20 units high: nine-slice insets left 3, top 3, right 3, bottom 4. A first pass; step 2 owns them.
    'button': pix(['.OOOOOOO.', 'OHHHHHHHO', 'OHBBBBBFO', 'OHBBBBBFO', 'OHBBBBBFO', 'OHBBBBBFO', 'OFFFFFFFO',
                   'OPPPPPPPO', '.OOOOOOO.'], A_KEY),
    'button-hover': pix(['.YYYYYYY.', 'YhhhhhhhY', 'YhbbbbbBY', 'YhbbbbbBY', 'YhbbbbbBY', 'YhbbbbbBY', 'YBBBBBBBY',
                         'YPPPPPPPY', '.YYYYYYY.'], A_KEY),
    'button-pressed': pix(['.OOOOOOO.', 'OPPPPPPPO', 'OPFFFFFFO', 'OPFFFFFFO', 'OPFFFFFFO', 'OPFFFFFFO', 'OPFFFFFFO',
                           'OFFFFFFFO', '.OOOOOOO.'], A_KEY),
    'button-disabled': pix(['.OOOOOOO.', 'OPPPPPPPO', 'OPPPPPPPO', 'OPPPPPPPO', 'OPPPPPPPO', 'OPPPPPPPO', 'OPPPPPPPO',
                            'OPPPPPPPO', '.OOOOOOO.'], A_KEY),
    'sun': pix(['.......gg.......', '.......GG.......', '..g..........g..', '...G........G...', '.....gggggg.....',
                '....ggGGGGGG....', '....gGGGGGGd....', 'gG..gGGGGGGd..Gd', 'gG..gGGGGGGd..Gd', '....gGGGGGGd....',
                '....GGGGGGdd....', '.....dddddd.....', '...G........G...', '..d..........d..', '.......GG.......',
                '.......dd.......'], A_KEY),
    'speaker': pix(['................', '................', '.......i........', '......ii....i...', '.....iii.....i..',
                    '.iiiiiii..i..i..', '.iiiiiii...i.i..', '.iiiiiii...i.i..', '.iiiiiii...i.i..',
                    '.iiiiiii...i.i..', '.iiiiiii..i..i..', '.....iii.....i..', '......ii....i...',
                    '.......i........', '................', '................'], A_KEY),
    'speaker-muted': pix(['................', '................', '.......q........', '......qq........',
                          '.....qqq........', '.qqqqqqq..r....r', '.qqqqqqq...r..r.', '.qqqqqqq....rr..',
                          '.qqqqqqq....rr..', '.qqqqqqq...r..r.', '.qqqqqqq..r....r', '.....qqq........',
                          '......qq........', '.......q........', '................', '................'], A_KEY),
    'microphone': pix(['................', '.......ii.......', '......iiii......', '......iiii......',
                       '......iiii......', '......iiii......', '....i.iiii.i....', '....i.iiii.i....',
                       '....i.iiii.i....', '....i..ii..i....', '.....i....i.....', '......iiii......',
                       '.......ii.......', '.......ii.......', '.....iiiiii.....', '................'], A_KEY),
}


def _microphone_off():
    image = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    source = A_SPRITES['microphone']
    for x in range(16):
        for y in range(16):
            if source.getpixel((x, y))[3]:
                image.putpixel((x, y), P['ink-quiet'])
    for step in range(13):  # a red stroke two pixels wide, bottom left to top right
        for x in (2 + step, 3 + step):
            image.putpixel((x, 14 - step), P['red-300'])
    return image


A_SPRITES['microphone-off'] = _microphone_off()

# One step of the bar is 6 x 4 units; four rows, top to bottom.
A_STEPS = {
    'lit': ('gold-300', 'gold-500', 'gold-500', 'gold-700'),
    'unlit': ('stone-800',) * 4,
    'muted': ('stone-300', 'stone-400', 'stone-400', 'stone-500'),
    'part': ('gold-700', 'gold-900', 'gold-900', 'gold-900'),
    'limit': ('ink', 'gold-100', 'gold-100', 'gold-300'),
}


def a_step(kind):
    image = Image.new('RGBA', (6, 4))
    for y, name in enumerate(A_STEPS[kind]):
        for x in range(6):
            image.putpixel((x, y), P[name])
    return image


class LookA:
    """AresOS's own art: dark stone plates, sunken slots, gold for what is lit, Jersey 10 on its own grid."""

    name = 'A'
    cap, line_gap = 10, 3              # capital height; rows between two lines of text
    pad, gap, row_gap = 4, 4, 4        # plate edge to content; icon to text; text to bar
    icon_box = 20                      # the slot the icon sits in
    bar_w, bar_h = 143, 8              # 20 steps of 6 + 1, in a trough with a 1-unit edge
    ink, value, quiet, dim, red = P['ink'], P['gold-300'], P['ink-quiet'], P['ink-dim'], P['red-300']

    def __init__(self, font_path):
        with open(font_path, 'rb') as source:
            found = hashlib.sha256(source.read()).hexdigest()
        if found != JERSEY10_SHA256:
            raise SystemExit(f'{font_path} is not the Jersey 10 file the study measured (SHA-256 {found})')
        # Jersey 10 has 1400 units per em and is drawn in pixels of 75 units, so one of its pixels is exactly
        # 3 screen pixels at 56 px. Every third pixel of that rendering is the font's own bitmap.
        self._font = ImageFont.truetype(font_path, 56, layout_engine=ImageFont.Layout.BASIC)
        self._glyphs = {}

    def _glyph(self, letter):
        if letter not in self._glyphs:
            step, x0, y0 = 3, 30, 90
            canvas = Image.new('L', (160, 140), 0)
            ImageDraw.Draw(canvas).text((x0, y0), letter, font=self._font, fill=255, anchor='ls')
            box = canvas.getbbox()
            advance = self._font.getlength(letter) / step
            if box is None:
                self._glyphs[letter] = (None, 0, 0, advance)
            else:
                left, top, right, bottom = box
                mask = Image.new('L', (round((right - left) / step), round((bottom - top) / step)), 0)
                for y in range(mask.height):
                    for x in range(mask.width):
                        if canvas.getpixel((left + step * x + 1, top + step * y + 1)) >= 128:
                            mask.putpixel((x, y), 255)
                self._glyphs[letter] = (mask, round((left - x0) / step), round((top - y0) / step), advance)
        return self._glyphs[letter]

    def _layout(self, text):
        pen, placed, right = 0.0, [], 0
        for letter in text:
            mask, dx, dy, advance = self._glyph(letter)
            if mask is not None:
                x = round(pen) + dx
                placed.append((mask, x, dy))
                right = max(right, x + mask.width)
            pen += advance
        return placed, right

    def glyph_mask(self, letter):
        return self._glyph(letter)[0]

    def text_width(self, text):
        return self._layout(text)[1]

    def text(self, image, x, y, text, colour, shadow=True):
        """Write with the capitals' top row at y. Each letter lands on a whole unit."""
        placed, _ = self._layout(text)
        passes = (((1, 1), P['outline']), ((0, 0), colour)) if shadow else (((0, 0), colour),)
        for (ox, oy), ink in passes:
            for mask, dx, dy in placed:
                image.paste(ink, (x + dx + ox, y + self.cap + dy + oy), mask)

    def plate(self, width, height):
        return nine_slice(A_SPRITES['plate'], width, height, 3)

    def slot(self, width, height):
        return nine_slice(A_SPRITES['slot'], width, height, 2)

    def button(self, width, label, state='button'):
        image = nine_slice(A_SPRITES[state], width, 20, (3, 3, 3, 4))
        colour = self.dim if state == 'button-disabled' else self.ink
        self.text(image, (width - self.text_width(label)) // 2, 6 if state == 'button-pressed' else 5, label, colour,
                  shadow=state != 'button-disabled')
        return image

    def icon(self, image, x, y, name, off=False):
        """The icon in its slot. `off` draws it as something that is not there."""
        image.alpha_composite(self.slot(self.icon_box, self.icon_box), (x, y))
        sprite = A_SPRITES[name]
        if off:
            grey = Image.new('RGBA', sprite.size, P['stone-400'])
            grey.putalpha(sprite.getchannel('A'))
            sprite = grey
        image.alpha_composite(sprite, (x + 2, y + 2))

    def bar(self, image, x, y, level, muted=False, limit=False):
        """Twenty steps of 5 %. A level between two steps lights the next one as a part step."""
        image.alpha_composite(self.slot(self.bar_w, self.bar_h), (x, y))
        full = min(int(level) // 5, 20)
        for index in range(20):
            kind = 'unlit'
            if index < full:
                kind = 'muted' if muted else 'lit'
            elif index == full and level % 5:
                kind = 'unlit' if muted else 'part'
            if limit and index == 19 and full == 20:
                kind = 'limit'
            image.alpha_composite(a_step(kind), (x + 2 + 7 * index, y + 2))


# ---------------------------------------------------------------- the piece: the level indicator

# Made-up values. `kind` level: icon, label, value, bar. `kind` note: icon, label, one status line.
INDICATOR_STATES = (
    ('Brightness key', dict(kind='level', what='brightness', label='Laptop screen', level=75)),
    ('Brightness up at the top: the last step flashes', dict(kind='level', what='brightness', label='Laptop screen',
                                                              level=100, limit=True)),
    ('Brightness at its lowest (the screen never goes black)', dict(kind='level', what='brightness',
                                                                     label='Laptop screen', level=1)),
    ('Volume key', dict(kind='level', what='volume', label='Speakers', level=40)),
    ('Volume key with headphones plugged in', dict(kind='level', what='volume', label='Headphones', level=65)),
    ('Mute key: the level stays readable', dict(kind='level', what='volume', label='Speakers', level=40,
                                                 muted=True)),
    ('Microphone key: on', dict(kind='note', what='microphone', label='Microphone', status='on', tone='value')),
    ('Microphone key: off', dict(kind='note', what='microphone-off', label='Microphone', status='off', tone='red')),
    ('Brightness key on a machine without a backlight', dict(kind='note', what='brightness', off=True,
                                                             label='Brightness', status='not available here',
                                                             tone='quiet')),
    ('Volume key with no sound output', dict(kind='note', what='volume', off=True, label='Sound',
                                             status='no output found', tone='quiet')),
)

ICONS_A = {'brightness': 'sun', 'volume': 'speaker', 'volume-muted': 'speaker-muted', 'microphone': 'microphone',
           'microphone-off': 'microphone-off'}


def indicator(look, state, icons):
    """The brightness and volume indicator at one pixel per GUI unit. It asks the look for every colour and part."""
    height = look.pad + look.cap + look.row_gap + look.bar_h + look.pad
    icon_y = (height - look.icon_box) // 2
    text_x = look.pad + look.icon_box + look.gap
    what = state['what'] + ('-muted' if state.get('muted') else '')
    if state['kind'] == 'level':
        image = look.plate(text_x + look.bar_w + look.pad, height)
        look.icon(image, look.pad, icon_y, icons[what])
        look.text(image, text_x, look.pad, state['label'], look.ink)
        value, colour = ('muted', look.red) if state.get('muted') else (f'{state["level"]}%', look.value)
        look.text(image, text_x + look.bar_w - look.text_width(value), look.pad, value, colour)
        look.bar(image, text_x, look.pad + look.cap + look.row_gap, state['level'], muted=state.get('muted', False),
                 limit=state.get('limit', False))
        return image
    width = max(look.text_width(state['label']), look.text_width(state['status']))
    image = look.plate(text_x + width + look.pad + 1, height)
    look.icon(image, look.pad, icon_y, icons[what], off=state.get('off', False))
    top = (height - 2 * look.cap - look.line_gap) // 2
    look.text(image, text_x, top, state['label'], look.ink)
    look.text(image, text_x, top + look.cap + look.line_gap, state['status'], getattr(look, state['tone']))
    return image


# ---------------------------------------------------------------- backdrops, drawn here from flat colours

def _bands(draw, x0, x1, y0, y1, first, last, count):
    for index in range(count):
        mix = index / (count - 1)
        colour = tuple(round(a + (b - a) * mix) for a, b in zip(first, last))
        draw.rectangle((x0, y0 + (y1 - y0) * index // count, x1 - 1, y0 + (y1 - y0) * (index + 1) // count - 1),
                       fill=colour)


def name_plate(look, text, colour, factor):
    """A dark plate with a name on it, as names stand in the world."""
    image = Image.new('RGBA', (look.text_width(text) + 7, look.cap + 7), rgb('#0d0d10', 215))
    look.text(image, 3, 3, text, colour)
    return up(image, factor)


def world_scene(look):
    """1920 x 1080: the noon home as a flat drawing of our own (sky, grass, a road, two block fronts, name plates).

    It stands for the world behind a piece. The sky and grass colours are the laptop home's day colours
    (LAPTOP-HOME.md 11.3). No game texture is used.
    """
    image = Image.new('RGBA', (1920, 1080))
    draw = ImageDraw.Draw(image)
    _bands(draw, 0, 1920, 0, 600, rgb('#6f9df0'), rgb('#aecbf8'), 10)
    _bands(draw, 0, 1920, 600, 1080, rgb('#668845'), rgb('#537236'), 8)
    draw.polygon([(924, 600), (996, 600), (1290, 1080), (630, 1080)], fill=rgb('#2b2832'))
    draw.polygon([(956, 600), (964, 600), (990, 1080), (930, 1080)], fill=rgb('#fed83d'))
    cell = 20
    for x0, face, side, motif, name, short in ((330, '#31407f', '#252f5e', '#f3f1ea', 'Notes', '/notes'),
                                               (1350, '#1d1b22', '#121117', '#cfa24f', 'Terminal', '/term')):
        y0 = 600 - 12 * cell
        draw.rectangle((x0 + 12 * cell, y0 + 8, x0 + 12 * cell + 11, 599), fill=rgb(side))
        draw.rectangle((x0, y0, x0 + 12 * cell - 1, 599), fill=rgb(face))
        draw.rectangle((x0 + 3 * cell, y0 + 2 * cell, x0 + 9 * cell - 1, y0 + 7 * cell - 1), fill=rgb(motif))
        draw.rectangle((x0 + 4 * cell, y0 + 3 * cell, x0 + 8 * cell - 1, y0 + 6 * cell - 1), fill=rgb(face))
        draw.rectangle((x0 + 5 * cell, 600 - 3 * cell, x0 + 7 * cell - 1, 599), fill=rgb('#0d0d10'))
        for text, colour, y in ((name, look.ink, y0 - 84), (short, look.value, y0 - 44)):
            plate = name_plate(look, text, colour, 2)
            image.alpha_composite(plate, (x0 + 6 * cell - plate.width // 2, y))
    word = name_plate(look, 'SYSTEM & TOOLS', look.ink, 3)
    image.alpha_composite(word, (960 - word.width // 2, 300))
    return image


def hotbar_stand_in(look):
    """Nine of version A's slots where the game's hotbar sits, at 3x. A stand-in of our own, not the game's bar."""
    strip = Image.new('RGBA', (182, 22), P['outline'])
    for index in range(9):
        strip.alpha_composite(look.slot(20, 20), (1 + 20 * index, 1))
    ImageDraw.Draw(strip).rectangle((0, 0, 21, 21), outline=P['gold-300'])
    return up(strip, 3)


def app_scene(title_font_path):
    """1920 x 1080: a maximized light program under today's Ares-Crown bar, drawn schematically."""
    image = Image.new('RGBA', (1920, 1080), rgb('#ffffff'))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1919, 35), fill=rgb('#0d0d10'))
    draw.ellipse((13, 13, 23, 23), fill=rgb('#edca77'))
    draw.text((38, 18), 'notes.txt - Editor', font=ImageFont.truetype(title_font_path, 17), fill=rgb('#f3f1ea'),
              anchor='lm')
    for index, glyph in enumerate(('min', 'max', 'close')):
        cx = 1920 - 44 * (3 - index) + 22
        if glyph == 'min':
            draw.line((cx - 6, 18, cx + 6, 18), fill=rgb('#f3f1ea'), width=1)
        elif glyph == 'max':
            draw.rectangle((cx - 6, 12, cx + 6, 24), outline=rgb('#f3f1ea'))
        else:
            draw.line((cx - 6, 12, cx + 6, 24), fill=rgb('#f3f1ea'), width=1)
            draw.line((cx - 6, 24, cx + 6, 12), fill=rgb('#f3f1ea'), width=1)
    draw.rectangle((0, 36, 1919, 83), fill=rgb('#f1f1f1'))
    draw.rounded_rectangle((420, 46, 1500, 74), radius=14, fill=rgb('#ffffff'), outline=rgb('#d9d9d9'))
    draw.line((0, 84, 1919, 84), fill=rgb('#d9d9d9'))
    for row, width in enumerate((620, 0, 880, 940, 760, 0, 900, 540, 0, 820, 870, 300)):
        if width:
            draw.rectangle((330, 150 + row * 34, 330 + width, 150 + row * 34 + 11), fill=rgb('#d5d5d5'))
    return image


def place(scene, piece, factor, where, bottom_clear=64):
    """Put a piece on a 1920 x 1080 scene: top centre, 8 units from the edge, or bottom centre above the hotbar."""
    big = up(piece, factor)
    x = (scene.width - big.width) // 2
    y = 8 * factor if where == 'top' else scene.height - bottom_clear * factor - big.height
    scene.alpha_composite(big, (x, y))
    return scene
