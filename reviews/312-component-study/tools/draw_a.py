#!/usr/bin/env python3
"""Draw version A's sprites and step 1's mockups into docs/design/components/.

    python3 -I reviews/312-component-study/tools/draw_a.py --font /path/to/Jersey10-Regular.ttf

Jersey 10 is not in the repo (the study commits no font): download it from Google Fonts' ofl/jersey10 into a
folder outside the checkout. Its SHA-256 is checked. Everything drawn here is our own: flat colours, the pixel
maps in look.py and that font.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402

import look as kit  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
OUT = os.path.join(ROOT, 'docs', 'design', 'components')
SHEET = kit.rgb('#17161c')
SKY, PAGE = kit.rgb('#8fb3f3'), kit.rgb('#f6f6f4')


def save(image, name):
    path = os.path.join(OUT, name)
    image.convert('RGB').save(path, optimize=True)
    print(f'{name}: {image.width} x {image.height}, {os.path.getsize(path) // 1024 + 1} KB')


def line(look, text, colour, factor=2, shadow=True):
    image = Image.new('RGBA', (look.text_width(text) + 2, look.cap + 8), (0, 0, 0, 0))
    look.text(image, 0, 4, text, colour, shadow=shadow)
    return kit.up(image, factor)


def palette_sheet(look):
    row, factor = 20, 2
    hex_x = 40 + max(look.text_width(name) for name, _, _ in kit.PALETTE) + 10
    use_x = hex_x + max(look.text_width(colour) for _, colour, _ in kit.PALETTE) + 10
    width = use_x + max(look.text_width(use) for _, _, use in kit.PALETTE) + 10
    sheet = Image.new('RGBA', (width, 12 + row * len(kit.PALETTE)), SHEET)
    for index, (name, colour, use) in enumerate(kit.PALETTE):
        y = 8 + row * index
        swatch = Image.new('RGBA', (26, 14), kit.P['outline'])
        swatch.paste(kit.rgb(colour), (1, 1, 25, 13))
        sheet.alpha_composite(swatch, (8, y))
        look.text(sheet, 40, y + 2, name, look.ink)
        look.text(sheet, hex_x, y + 2, colour, look.value)
        look.text(sheet, use_x, y + 2, use, look.quiet)
    return kit.up(sheet, factor)


def font_sheet(look):
    lines = ('Laptop screen 75%   Speakers 40%   Microphone off',
             'Lautstärke · Helligkeit · Kopfhörer · Größe · ÄÖÜ äöü ß',
             '0123456789  abcdef  dcbc375f  0O 1lI 8B 6b 5S',
             'Enter SSH Credentials   Password:   OK   Cancel')
    blocks = []
    for factor, note in ((2, '2x: capitals 20 px, small letters 16 px, line 40 px'),
                         (3, '3x: capitals 30 px, small letters 24 px, line 60 px')):
        blocks.append(line(look, note, look.value, 2))
        blocks.extend(line(look, text, look.ink, factor) for text in lines)
    sheet = Image.new('RGBA', (max(block.width for block in blocks) + 48, sum(block.height + 10 for block in blocks)
                               + 38), SHEET)
    y = 24
    for block in blocks:
        sheet.alpha_composite(block, (24, y))
        y += block.height + 10
    return sheet


def sprite_sheet(look):
    sheet = Image.new('RGBA', (1500, 760), SHEET)

    def put(image, x, y, caption=None, factor=1):
        sheet.alpha_composite(kit.up(image, factor), (x, y))
        if caption:
            sheet.alpha_composite(line(look, caption, look.quiet, 2), (x, y + image.height * factor + 4))

    sheet.alpha_composite(line(look, 'Nine-slice sources at 8x (1 square = 1 GUI unit)', look.value, 2), (24, 14))
    x = 24
    for name, caption in (('plate', 'plate 9x9, inset 3'), ('slot', 'slot 7x7, inset 2'),
                          ('button', 'button 9x9'), ('button-hover', 'hover'), ('button-pressed', 'pressed'),
                          ('button-disabled', 'disabled')):
        put(kit.A_SPRITES[name], x, 56 + (9 - kit.A_SPRITES[name].height) * 8, caption, 8)
        x += 232
    sheet.alpha_composite(line(look, 'Built from them at 3x', look.value, 2), (24, 176))
    put(look.plate(80, 30), 24, 218, 'plate 80 x 30', 3)
    put(look.slot(20, 20), 290, 218, 'slot 20', 3)
    x = 400
    for state, label in (('button', 'OK'), ('button-hover', 'Cancel'), ('button-pressed', 'OK'),
                         ('button-disabled', 'Cancel')):
        put(look.button(72, label, state), x, 218, None, 3)
        x += 232
    sheet.alpha_composite(line(look, 'buttons 72 x 20: normal, pointer on it, pressed, not available', look.quiet, 2), (400, 286))
    sheet.alpha_composite(line(look, 'Icons, 16 x 16, at 6x: sun, speaker, speaker muted, microphone, microphone off,'
                                     ' and one drawn as "not there"', look.value, 2), (24, 360))
    x = 24
    for name in ('sun', 'speaker', 'speaker-muted', 'microphone', 'microphone-off'):
        tile = Image.new('RGBA', (20, 20))
        look.icon(tile, 0, 0, name)
        put(tile, x, 402, None, 6)
        x += 140
    tile = Image.new('RGBA', (20, 20))
    look.icon(tile, 0, 0, 'speaker', off=True)
    put(tile, x, 402, None, 6)
    sheet.alpha_composite(line(look, 'Bar steps, 6 x 4, at 8x: lit, unlit, muted, part step, at the limit',
                               look.value, 2), (24, 548))
    x = 24
    for kind in ('lit', 'unlit', 'muted', 'part', 'limit'):
        tile = Image.new('RGBA', (8, 6), kit.P['stone-900'])
        tile.alpha_composite(kit.a_step(kind), (1, 1))
        put(tile, x, 590, None, 8)
        x += 80
    for index, (level, muted) in enumerate(((75, False), (40, True))):
        bar = Image.new('RGBA', (look.bar_w, look.bar_h))
        look.bar(bar, 0, 0, level, muted=muted)
        put(bar, 460, 590 + index * 44, None, 3)
    sheet.alpha_composite(line(look, 'the bar, 143 x 8, at 3x: 75 %, and 40 % muted', look.quiet, 2), (460, 684))
    return sheet


def states_sheet(look, icons, title):
    """Every state at 3x, over the world's sky colour and over a white page."""
    pitch, factor = 140, 3
    sheet = Image.new('RGBA', (1500, 70 + pitch * len(kit.INDICATOR_STATES)), SKY)
    sheet.paste(PAGE, (750, 0, 1500, sheet.height))
    sheet.alpha_composite(line(look, title, kit.P['outline'], 2, shadow=False), (30, 14))
    for index, (caption, state) in enumerate(kit.INDICATOR_STATES):
        y = 64 + pitch * index
        sheet.alpha_composite(line(look, caption, kit.P['outline'], 2, shadow=False), (30, y))
        piece = kit.up(kit.indicator(look, state, icons), factor)
        sheet.alpha_composite(piece, (30, y + 34))
        sheet.alpha_composite(piece, (780, y + 34))
    return sheet


def scales_sheet(look, icons):
    state = kit.INDICATOR_STATES[0][1]
    piece = kit.indicator(look, state, icons)
    sheet = Image.new('RGBA', (1920, 470), SKY)
    sheet.paste(PAGE, (960, 0, 1920, 470))
    y = 20
    for factor in (2, 3, 4):
        big = kit.up(piece, factor)
        note = f'{factor}x: {big.width} x {big.height} px of the 1920 x 1080 screen'
        sheet.alpha_composite(line(look, note, kit.P['outline'], 2, shadow=False), (30, y))
        sheet.alpha_composite(big, (30, y + 32))
        sheet.alpha_composite(big, (990, y + 32))
        y += big.height + 62
    return sheet


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--font', required=True, help='Jersey10-Regular.ttf, kept outside the repo')
    arguments = parser.parse_args()
    look = kit.LookA(arguments.font)
    os.makedirs(os.path.join(OUT, 'sprites'), exist_ok=True)
    for name, sprite in kit.A_SPRITES.items():
        sprite.save(os.path.join(OUT, 'sprites', f'{name}.png'), optimize=True)
    for kind in kit.A_STEPS:
        kit.a_step(kind).save(os.path.join(OUT, 'sprites', f'step-{kind}.png'), optimize=True)
    icons = kit.ICONS_A
    save(palette_sheet(look), 'A-01-palette.png')
    save(font_sheet(look), 'A-02-font.png')
    save(sprite_sheet(look), 'A-03-sprites.png')
    save(states_sheet(look, icons, 'Version A: the brightness and volume indicator, every state, at 3x'),
         'A-04-indicator-states.png')
    save(scales_sheet(look, icons), 'A-05-indicator-scales.png')
    volume = kit.indicator(look, kit.INDICATOR_STATES[3][1], icons)
    brightness = kit.indicator(look, kit.INDICATOR_STATES[0][1], icons)
    for name, where in (('A-06-indicator-top.png', 'top'), ('A-07-indicator-bottom.png', 'bottom')):
        scene = kit.world_scene(look)
        bar = kit.hotbar_stand_in(look)
        scene.alpha_composite(bar, ((1920 - bar.width) // 2, 1080 - bar.height))
        save(kit.place(scene, volume, 3, where), name)
    title_font = os.path.join(ROOT, 'os', 'config', 'usr', 'share', 'fonts', 'aresos', 'SpaceGrotesk-Variable.ttf')
    save(kit.place(kit.app_scene(title_font), brightness, 3, 'top'), 'A-08-indicator-over-app.png')


if __name__ == '__main__':
    main()
