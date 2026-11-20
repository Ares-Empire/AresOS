#!/usr/bin/python3
"""Package 318's runs, one per call, with fixed settings.

    schedule.py setup                     S0: the setup-flat creation run; its save becomes .work/pkg318/AresHub-base
    schedule.py trial <name> keep|demote  one cover-freeze trial: COVER=300 SHOTS=0 RECLAIM=600M FREEZE=1 RT=<mode>

Every run goes through retry.sh (exit 75: wait five minutes, at most six retries) and run.sh (the shared client-test
lock, the 6 GiB and owner-game guards). Which trials run, in which order, and what they mean is PLAN.md's, not this
script's. A name is never reused: an earlier attempt's records stay, and a repeat takes a new name (b1-repeat-2).
After each run it waits 30 s, so other lock holders get through.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WORK = HERE.parents[2] / '.work/pkg318'
BASE = WORK / 'AresHub-base'
TRIAL = ['COVER=300', 'SHOTS=0', 'RECLAIM=600M', 'FREEZE=1']


def fingerprint(base):
    digest = hashlib.sha256(); size = 0; count = 0
    for path in sorted(base.rglob('*')):
        if not path.is_file(): continue
        data = path.read_bytes(); size += len(data); count += 1
        digest.update(path.relative_to(base).as_posix().encode() + b'\0' + hashlib.sha256(data).hexdigest().encode() + b'\n')
    return {'aggregate_tree_sha256': digest.hexdigest(), 'files': count, 'bytes': size,
            'manifest': (base / 'aresos-home.properties').read_text()}


def run(name, settings):
    if not re.fullmatch(r'[a-z0-9-]+', name):
        raise SystemExit('name: lowercase letters, digits and dashes')
    if (ROOT / 'runs' / name).exists() or (WORK / 'rigs' / name).exists():
        raise SystemExit(f'{name} ran already; a repeat takes a new name')
    WORK.mkdir(parents=True, exist_ok=True)
    print(time.strftime('%Y-%m-%dT%H:%M:%S'), 'START', name, *settings, flush=True)
    with (WORK / (name + '.txt')).open('a') as log:
        code = subprocess.run([str(HERE / 'retry.sh'), str(HERE / 'run.sh'), name, *settings],
                              stdout=log, stderr=subprocess.STDOUT).returncode
    watch = ROOT / 'runs' / name / 'host-watch.jsonl'
    external = []
    if watch.exists():
        for line in watch.read_text().splitlines():
            row = json.loads(line)
            if any(p['kind'] in ('gradle', 'game') for p in row.get('external_java', [])):
                external.append({'monotonic_ns': row['monotonic_ns'], 'external_java': row['external_java']})
    attempt = {'attempt': name, 'settings': settings, 'exit': code, 'overlapped_by_other_java': bool(external),
               'interference_samples': external}
    if (ROOT / 'runs' / name).exists():
        (ROOT / 'runs' / name / 'attempt.json').write_text(json.dumps(attempt, indent=1) + '\n')
    print(time.strftime('%Y-%m-%dT%H:%M:%S'), 'END', name, 'exit', code,
          'OVERLAPPED: keep, mark and repeat' if external else '', flush=True)
    time.sleep(30)
    return code


def setup():
    if BASE.exists():
        raise SystemExit(f'{BASE} exists already')
    code = run('s0', ['MODE=create', 'CREATE_FLOW=automatic', 'QUIT=1', 'COVER=0', 'SHOTS=1'])
    world = WORK / 'rigs' / 's0' / 'world'
    if code or not world.is_dir():
        raise SystemExit(f's0: exit {code}; no base world')
    shutil.copytree(world, BASE)
    (ROOT / 'fixture-hashes.json').write_text(json.dumps({'flat': fingerprint(BASE)}, indent=2) + '\n')
    pictures = ROOT / 'screenshots'
    for file in ('home-south.png', 'above-south.png'):
        source = WORK / 'rigs' / 's0' / 'shots' / file
        if source.exists():
            pictures.mkdir(exist_ok=True)
            shutil.copy2(source, pictures / file)


def trial(name, mode):
    if mode not in ('keep', 'demote'):
        raise SystemExit('mode: keep or demote')
    if not BASE.is_dir():
        raise SystemExit('no base world: run "schedule.py setup" first')
    return run(name, [*TRIAL, f'RT={mode}'])


if __name__ == '__main__':
    if sys.argv[1:] == ['setup']:
        setup()
    elif len(sys.argv) == 4 and sys.argv[1] == 'trial':
        sys.exit(trial(sys.argv[2], sys.argv[3]))
    else:
        raise SystemExit(__doc__)
