"""Measure the native laptop home at rest on a private 1920 x 1080 software background layer (set-up S).

Adapted from 53e's sampler (branch pkg/53e-home-memory): the same fixture town (45 houses on four streets of 9, 7,
9 and 20, 47 catalogue entries, the study's fonts matched by fontconfig) and /dev masked before labwc starts.

53f measures the resting state after at least one redraw (the clock redraws every minute, and any input does): after
the first complete draw the channel asks for one redraw, and the sample is taken 15 s after that frame. A Wayland
client holds a second buffer from its second frame on, so the first draw alone is the best case (--first-draw, step
A's method). --prototype runs 53e's bare GTK 4 and Cairo block town as the control; it has no channel, so it
redraws once by itself 0.5 s after its first frame.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import time

from laptop_home_headless import Headless, headless_available, scratch, wait_for
from laptop_home_helper import STUDY_FONTS, STUDY_PALETTE, StandIn, generated_town, png

LAYER = dict(background=True, on_demand=True, anchored=True, output='HEADLESS-1')
FIELDS = ('Pss_Anon', 'Pss_File', 'Pss')
MAPPING = re.compile(r'^[\da-f]+-[\da-f]+\s+\S+\s+\S+\s+\S+\s+\d+\s*(.*)$')
DRIVERS = ('libegl_', 'libglx_', 'libvulkan_', 'libgallium', 'libllvm', 'nvidia', '/dri/')


def sample(pid):
    proc = Path('/proc') / str(pid)
    rollup = {}
    for line in (proc / 'smaps_rollup').read_text().splitlines():
        key, _, value = line.partition(':')
        if key in FIELDS:
            rollup[key] = int(value.split()[0])
    maps = (proc / 'maps').read_text().lower().splitlines()
    if any(name in line for line in maps if '/' in line for name in DRIVERS):
        raise RuntimeError(f'a GPU driver is mapped by process {pid}')
    top = []
    for line in (proc / 'smaps').read_text().splitlines():
        if match := MAPPING.fullmatch(line):
            location, mapping = line.split(maxsplit=1)[0], match[1] or '[anonymous]'
        elif line.startswith('Pss:'):
            top.append((int(line.split()[1]), location, mapping))
    # The window's shared-memory buffers (about 8,100 KiB each at 1920 x 1080) and the main heap.
    buffers = [pss for pss, _, mapping in top if 'gdk-wayland' in mapping and pss]
    heap = sum(pss for pss, _, mapping in top if mapping == '[heap]')
    files = defaultdict(int)
    for pss, _, mapping in top:
        files[mapping] += pss
    return dict(pid=pid, **rollup, buffers=len(buffers), buffers_kib=sum(buffers), heap_kib=heap,
                mappings=sorted(top, reverse=True)[:10],
                files=sorted(([pss, name] for name, pss in files.items()), reverse=True)[:400])


def verify_fonts(gui):
    for family in ('Space Grotesk', 'JetBrains Mono'):
        expected = STUDY_FONTS / (family.replace(' ', '') + '-Variable.ttf')
        match = subprocess.check_output(['/usr/bin/fc-match', '-f', '%{file}', family], env=gui.env, text=True)
        if not match or Path(match).read_bytes() != expected.read_bytes():
            raise RuntimeError(f'fixture font {family} was not found by fontconfig')


def measure(prototype=False, redraw=True):
    if not headless_available() or not shutil.which('fc-match', path='/usr/bin'):
        raise RuntimeError('need labwc, bwrap, wlr-randr, fontconfig, Mesa pins, GTK 4, Pango and Cairo')
    with scratch() as tmp:
        root = Path(tmp)
        icon = root / 'icon.png'
        icon.write_bytes(png())
        helper = StandIn(root / 'shell.sock', page_size=4)
        helper.palette = STUDY_PALETTE
        helper.houses, helper.programs = generated_town((9, 7, 9, 20), icon)
        helper.programs = [row for row in helper.programs if row['id'] != 'test-archive']
        gui = Headless(root, helper.path, font_dir=STUDY_FONTS, prototype=prototype, redraw=redraw)
        if not gui.expect_layer:
            raise RuntimeError('need gtk4-layer-shell or LAPTOP_HOME_TEST_LAYER_DIR pointing to its lib64')
        verify_fonts(gui)
        with helper, gui:
            parent = gui.parent()
            if not parent['drm_hidden']:
                raise RuntimeError('host graphics devices are visible inside the measurement')
            if prototype:
                renderer = parent['renderer']['gsk']
                if parent['size'] != [1920, 1080] or parent['layer'] != LAYER:
                    raise RuntimeError('unexpected prototype surface')
            else:
                gui.until(lambda scene: scene['online'] and scene['size'] == [1920, 1080] and sum(
                    len(street['houses']) for street in scene['streets']) == 45)
                wait_for(lambda: gui.request('counters')['first'])
                renderer = gui.request('renderer')
                if parent.get('layer') != LAYER:
                    raise RuntimeError(f'expected the background layer, got {parent.get("layer")}')
            draws = None if prototype else gui.request('counters')['draws']
            if redraw and not prototype:
                gui.request('set', state={})
                wait_for(lambda: gui.request('counters')['draws'] > draws)
                draws = gui.request('counters')['draws']
            time.sleep(15.5 if redraw and prototype else 15)
            result = dict(setup='S', program='prototype' if prototype else 'native', renderer=renderer,
                          redrawn=redraw, **sample(parent['pid']))
            if not prototype:
                result['draws_at_rest'] = gui.request('counters')['draws'] - draws
            return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--prototype', action='store_true', help="53e's native block town, the control")
    parser.add_argument('--first-draw', action='store_true', help="step A's method: sample without a redraw")
    args = parser.parse_args()
    runs = []
    for _ in range(args.runs):
        runs.append(measure(args.prototype, redraw=not args.first_draw))
        print(json.dumps(runs[-1]), flush=True)
    summary = defaultdict(dict)
    for field in (*FIELDS, 'buffers_kib', 'heap_kib'):
        values = [run[field] for run in runs]
        summary[field] = dict(median=statistics.median(values), min=min(values), max=max(values))
    print(json.dumps(dict(summary_kib=summary)), flush=True)


if __name__ == '__main__':
    main()
