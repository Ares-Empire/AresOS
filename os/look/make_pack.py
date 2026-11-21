#!/usr/bin/env python3
"""Generate the installed look A indicator pack from the component study (needs Pillow)."""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'os/config/usr/share/aresos/look'
sys.path.insert(0, str(ROOT / 'reviews/312-component-study/tools'))
from look import A_SPRITES, A_STEPS, PALETTE, P, LookA, a_step


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

    (destination / 'look.json').write_text(json.dumps(pack, indent=2, sort_keys=True) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=PACK)
    generate(parser.parse_args().output)
