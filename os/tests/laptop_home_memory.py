"""Measure the packaged laptop home on a private 1920 × 1080 software background layer."""

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import time

from laptop_home_headless import PROGRAM, Headless, engines, headless_available, scratch, wait_for
from laptop_home_helper import StandIn, png
from test_aresos_laptop_home_page import PAGE, STUDY_FONTS, STUDY_PALETTE, generated_town

SIZE = '1920x1080'
FIELDS = ('Pss_Anon', 'Pss_File', 'Pss')
LAYER = dict(background=True, on_demand=True, anchored=True, output='HEADLESS-1')
WEBKIT = {'WebKitWebProcess', 'WebKitNetworkProcess'}
MAPPING = re.compile(r'^[\da-f]+-[\da-f]+\s+\S+\s+\S+\s+\S+\s+\d+\s*(.*)$')
READY = """document.documentElement.dataset.look === 'day' &&
    innerWidth === 1920 && innerHeight === 1080 && devicePixelRatio === 1 &&
    document.fonts.status === 'loaded' &&
    document.querySelectorAll('.house').length === 45 &&
    aresosHome.programs().length === 47 &&
    document.getAnimations().every(animation => animation.playState !== 'running') &&
    !document.querySelector('#stage').hidden"""
MOTION = """
const canvas = document.createElement('canvas');
canvas.width = innerWidth;
canvas.height = innerHeight;
Object.assign(canvas.style, {position: 'fixed', inset: 0, zIndex: 100, pointerEvents: 'none'});
document.body.append(canvas);
const ctx = canvas.getContext('2d');
const start = performance.now(), intervals = [];
let last;
return await new Promise(done => requestAnimationFrame(function draw(now) {
    if (last !== undefined) intervals.push(now - last);
    last = now;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const x = Math.floor((now - start) / 12) % (canvas.width - 80);
    ctx.fillStyle = '#a84d92';
    ctx.fillRect(x, 620, 80, 62);
    ctx.fillRect(x + 8, 682, 20, 18);
    ctx.fillRect(x + 52, 682, 20, 18);
    ctx.fillStyle = '#ffc88e';
    ctx.fillRect(x + 10, 632, 60, 12);
    if (now - start < 60000) requestAnimationFrame(draw);
    else {
        canvas.remove();
        done({seconds: (now - start) / 1000, frames: intervals.length + 1, intervals});
    }
}));
"""


def prerequisites():
    tools = ('wlr-randr', 'fc-match', 'bwrap')
    if not headless_available() or not all(shutil.which(tool, path='/usr/bin') for tool in tools):
        raise RuntimeError('need labwc, wlr-randr, fontconfig, bwrap, Mesa pins and GTK 4/WebKitGTK 6.0')
    if not all((STUDY_FONTS / f'{name}-Variable.ttf').is_file() for name in ('SpaceGrotesk', 'JetBrainsMono')):
        raise RuntimeError('need the study font files')


def sample(pid, name):
    proc = Path('/proc') / str(pid)
    rollup = {}
    for line in (proc / 'smaps_rollup').read_text().splitlines():
        key, _, value = line.partition(':')
        if key in FIELDS:
            rollup[key] = int(value.split()[0])
    if rollup.keys() != set(FIELDS):
        raise RuntimeError(f'missing PSS data for process {pid}')
    if any('nvidia' in line.lower() for line in (proc / 'maps').read_text().splitlines() if '/' in line):
        raise RuntimeError(f'NVIDIA library mapped by process {pid}')
    top = []
    for line in (proc / 'smaps').read_text().splitlines():
        if match := MAPPING.fullmatch(line):
            location = line.split(maxsplit=1)[0]
            mapping = match[1] or '[anonymous]'
        elif line.startswith('Pss:'):
            top.append((int(line.split()[1]), location, mapping))
    child = {}
    if name == 'WebKitWebProcess':
        status = dict(line.split(':', 1) for line in (proc / 'status').read_text().splitlines() if ':' in line)
        if status['Seccomp'].strip() != '2' or len(status['NSpid'].split()) < 2:
            raise RuntimeError(f'{name} is missing its seccomp filter or PID namespace')
        child = {'sandbox': True}
    return dict(name=name, pid=pid, **rollup, mappings=sorted(top, reverse=True)[:10], **child)


def ticks(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return int(fields[11]) + int(fields[12])


def motion(gui, pids):
    start = time.monotonic()
    before = {pid: ticks(pid) for pid in pids}
    result = gui.evaluate(MOTION, duration=75)
    duration = time.monotonic() - start
    result['fps'] = result['frames'] / result['seconds']
    result['p95_ms'] = sorted(result.pop('intervals'))[int((result['frames'] - 2) * 0.95)]
    result['cpu_percent'] = {
        name: (ticks(pid) - before[pid]) * 100 / (os.sysconf('SC_CLK_TCK') * duration)
        for pid, name in pids.items()
    }
    return result


def verify_fonts(gui):
    for family in ('Space Grotesk', 'JetBrains Mono'):
        expected = STUDY_FONTS / (family.replace(' ', '') + '-Variable.ttf')
        match = subprocess.check_output(['/usr/bin/fc-match', '-f', '%{file}', family], env=gui.env, text=True)
        if not match or Path(match).read_bytes() != expected.read_bytes():
            raise RuntimeError(f'fixture font {family} was not found by Fontconfig')


def measure(*, legacy=False, motion_check=False, native=False, program=PROGRAM, page=PAGE):
    prerequisites()
    with scratch() as tmp:
        root = Path(tmp)
        icon = root / 'icon.png'
        icon.write_bytes(png())
        helper = StandIn(root / 'shell.sock', page_size=4)
        helper.palette = STUDY_PALETTE
        helper.houses, helper.programs = generated_town((9, 7, 9, 20), icon)
        helper.programs = [row for row in helper.programs if row['id'] != 'test-archive']
        gui = Headless(root, helper.path, page=page, size=SIZE, font_dir=STUDY_FONTS,
                       legacy_renderers=legacy, isolate_drm=True, native=native, program=program)
        if not gui.expect_layer:
            raise RuntimeError('need gtk4-layer-shell or LAPTOP_HOME_TEST_LAYER_DIR pointing to its extracted lib64')
        if not native:
            verify_fonts(gui)
        with helper, gui:
            parent = gui.parent()
            if parent.get('layer') != LAYER:
                raise RuntimeError(f'expected the real background layer, got {parent.get("layer", "fullscreen fallback")}')
            pid = parent['pid']
            if not parent['drm_hidden']:
                raise RuntimeError('host graphics devices are visible inside the measurement')
            if not native:
                gui.until(READY)
                children = wait_for(lambda: found if WEBKIT <= set((found := engines(pid)).values()) else None)
                renderer = gui.evaluate('@renderer')
            else:
                if parent['size'] != [1920, 1080]:
                    raise RuntimeError(f'unexpected native town dimensions {parent["size"]}')
                children = {}
                renderer = parent['renderer']
            time.sleep(15)
            if engines(pid) != children:
                raise RuntimeError('WebKit process tree changed before the rest sample')
            pids = {pid: 'program', **children}
            processes = [sample(pid, name) for pid, name in pids.items()]
            result = dict(setup='S', surface='background', size=SIZE, renderer=renderer, processes=processes,
                          total=sum(process['Pss'] for process in processes))
            if motion_check:
                result['motion'] = motion(gui, {pid: name for pid, name in pids.items()
                                                if name in ('program', 'WebKitWebProcess')})
            return result


def describe(runs):
    samples = []
    for run in runs:
        by_name = defaultdict(int)
        for process in run['processes']:
            by_name[process['name']] += process['Pss']
        by_name['total'] = run['total']
        samples.append(by_name)
    summary = {}
    for name in sorted(set().union(*samples)):
        pss = [sample.get(name, 0) for sample in samples]
        summary[name] = dict(median=statistics.median(pss), min=min(pss), max=max(pss))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=5)
    parser.add_argument('--legacy-renderers', action='store_true', help='use the 53c harness renderer overrides')
    parser.add_argument('--motion', action='store_true', help='measure one minute of motion after the last PSS sample')
    parser.add_argument('--native', action='store_true', help='compare the native GTK 4 block town')
    parser.add_argument('--program', type=Path, default=PROGRAM, help='path to a comparison launch program')
    parser.add_argument('--page', type=Path, default=PAGE, help='directory containing a comparison page')
    args = parser.parse_args()
    if args.runs < 1 or (args.native and args.motion):
        parser.error('need at least one run, and motion is only available in the packaged WebKit view')
    runs = []
    signal.signal(signal.SIGTERM, terminate)
    for run in range(args.runs):
        results = measure(legacy=args.legacy_renderers,
                          motion_check=args.motion and run == args.runs - 1, native=args.native,
                          program=args.program, page=args.page)
        runs.append(results)
        print(json.dumps(results), flush=True)
    print(json.dumps(dict(summary_kib=describe(runs))), flush=True)


def terminate(_signum, _frame):
    raise SystemExit(143)


if __name__ == '__main__':
    main()
