#!/usr/bin/env python3
"""Generate the installed look A pack from the component study (needs Pillow)."""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'os/config/usr/share/aresos/look'
FONT = ROOT / 'os/config/usr/share/fonts/aresos/Jersey10-Regular.ttf'
sys.path.insert(0, str(ROOT / 'reviews/312-component-study/tools'))
from look import A_SPRITES, A_STEPS, FRAME_BUTTONS, FRAME_STATES, PALETTE, P, LookA, a_step, labwc_file


def hex_colour(rgba):
    return '#' + bytes(rgba if rgba[3] < 255 else rgba[:3]).hex()


def add_frame(pack, sprites):
    look = LookA(FONT)
    frame = sprites / 'frame'
    frame.mkdir(parents=True, exist_ok=True)
    pack['frame_sprites'] = {}
    for button in FRAME_BUTTONS:
        for state in FRAME_STATES:
            name = labwc_file(button, state)
            look.title_button(button, state).save(frame / name)
            pack['frame_sprites'][name] = f'sprites/frame/{name}'

    active = dict(look.frame_colours(True), shadow=(0, 0, 0, 140))
    inactive = dict(look.frame_colours(False), shadow=(0, 0, 0, 90))
    switcher = look.switcher_colours()
    outline = switcher.pop('outline')
    snap = look.snap_colours()
    lines = snap.pop('lines')
    pack['frame_colours'] = {
        group: {role: hex_colour(colour) for role, colour in colours.items()}
        for group, colours in (('active', active), ('inactive', inactive), ('menu', look.menu_colours()),
                               ('switcher', switcher), ('snap', snap))
    }
    pack['frame_colours']['switcher']['outline'] = [hex_colour(colour) for colour in outline]
    pack['frame_colours']['snap']['lines'] = [hex_colour(colour) for colour in lines]


def generate(destination):
    sprites = destination / 'sprites'
    sprites.mkdir(parents=True, exist_ok=True)
    colours = {name: colour for name, colour, _ in PALETTE}
    colours.update(value=colours['gold-300'], quiet=colours['ink-quiet'], warn=colours['red-300'])
    pack = {
        'look': 'A',
        'colours': colours,
        'font': {'family': 'Jersey 10', 'em': [1400, 75]},
        'sizes': {**{size: getattr(LookA, size) for size in
                     ('cap', 'line_gap', 'pad', 'gap', 'row_gap', 'icon_box', 'bar_w', 'bar_h')},
                  'shadow_offset': 1, 'step_gap': 1, 'top_margin': 8, 'bottom_margin': 64},
        'sprites': {},
    }

    def sprite(name, image, inset=0, **states):
        file = f'sprites/{name}.png'
        image.save(destination / file)
        pack['sprites'][name] = {'file': file, 'size': list(image.size), 'insets': [inset] * 4, 'states': states}

    sprite('plate', A_SPRITES['plate'], 3)
    sprite('slot', A_SPRITES['slot'], 2)
    for kind in A_STEPS:
        sprite(f'step-{kind}', a_step(kind))
    for name in ('sun', 'speaker', 'speaker-muted', 'microphone', 'microphone-off'):
        icon = A_SPRITES[name]
        grey = f'{name}-unavailable'
        sprite(name, icon, unavailable=grey)
        unavailable = Image.new('RGBA', icon.size, P['stone-400'])
        unavailable.putalpha(icon.getchannel('A'))
        sprite(grey, unavailable)

    add_frame(pack, sprites)
    (destination / 'look.json').write_text(json.dumps(pack, indent=2, sort_keys=True) + '\n',
                                          encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PACK)
    generate(parser.parse_args().output)
