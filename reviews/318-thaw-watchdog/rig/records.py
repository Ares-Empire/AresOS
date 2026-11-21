#!/usr/bin/python3
"""Package 318: read-only records around each run, and their public copies.

    records.py status <rig> <label>   the NVIDIA card's power/runtime_status now (card-status.jsonl)
    records.py final <rig> [<out>]    after cleanup: journal lines, `cardwire get`, sound lines, Gradle's exit value;
                                      then copies the run's package-318 records to <out>, with local paths redacted

Reading runtime_status doesn't wake the card (package 47). The journal copy keeps rtkit's lines that name the game's
PID or no process at all (its watchdog and demotion lines), every cardwired line, and kernel lines about OOM, NVRM or a
watchdog, for the run's window, without the hostname. Nothing is written outside the rig and out folders.
"""
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import time

PCI = re.compile(r'[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]')
WORKTREE = str(pathlib.Path(__file__).resolve().parents[3])
HOME = os.path.expanduser('~')
KERNEL = re.compile(r'oom|out of memory|killed process|NVRM|watchdog|rtkit', re.I)
SOUND = re.compile(r'openal|alsoft|sound engine|sound system|audio', re.I)
EXIT_VALUE = re.compile(r'exit value (\d+)')
PUBLIC = ('settings.txt', 'marks.txt', 'actions.jsonl', 'rt-freeze.json', 'rt-demote.json', 'rt-prethaw.json',
          'invalid.json', 'thaw-samples.csv', 'thaw-scan.jsonl', 'thaw.txt', 'exit.json', 'card-status.jsonl',
          'journal.txt', 'cardwire.txt', 'sound-lines.txt', 'terminal.json', 'health-failure.json', 'host-watch.jsonl',
          'host-start.json', 'host-end.json', 'faults-return.json', 'wake-input.jsonl', 'samples.csv', 'provenance.json')


def public(text):
    return text.replace(WORKTREE, '<worktree>').replace(HOME, '<home>')


def runtime_status(environ=os.environ):
    pci = environ.get('PKG318_GPU_PCI', '')
    if not PCI.fullmatch(pci):
        return None
    try:
        return pathlib.Path(f'/sys/bus/pci/devices/{pci}/power/runtime_status').read_text().strip()
    except OSError as error:
        return f'error: {error.strerror}'


def status(rig, label):
    line = {'monotonic_ns': time.monotonic_ns(), 'label': label, 'runtime_status': runtime_status()}
    with (pathlib.Path(rig) / 'card-status.jsonl').open('a') as sink:
        sink.write(json.dumps(line) + '\n')


def settings(rig):
    path = pathlib.Path(rig) / 'settings.txt'
    if not path.exists():
        return {}
    return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)


def keep_rtkit(line, game):
    """rtkit's lines about the game's PID, or about no process (its canary, watchdog and demotion lines)."""
    named = re.search(r'of process (\d+)', line)
    return named is None or named[1] == str(game)


def journal(since_epoch, game, run=subprocess.run):
    base = ['journalctl', '--no-pager', '--no-hostname', '-o', 'short-monotonic', f'--since=@{since_epoch}']
    lines = []
    units = run([*base, '-u', 'rtkit-daemon.service', '-u', 'cardwired.service'], capture_output=True, text=True, timeout=30)
    for line in units.stdout.splitlines():
        if 'rtkit-daemon' in line and not keep_rtkit(line, game):
            continue
        lines.append(line)
    kernel = run([*base, '-k'], capture_output=True, text=True, timeout=30)
    lines += ['kernel: ' + line for line in kernel.stdout.splitlines() if KERNEL.search(line)]
    errors = [p.stderr.strip() for p in (units, kernel) if p.returncode]
    return lines, errors


def gradle_exit(rig):
    """The game's exit value as Gradle printed it ("finished with non-zero exit value 137"), or None."""
    path = pathlib.Path(rig) / 'gradle.txt'
    if not path.exists():
        return None
    values = EXIT_VALUE.findall(path.read_text(errors='replace'))
    return int(values[-1]) if values else None


def final(rig, out=None, run=subprocess.run):
    rig = pathlib.Path(rig)
    facts = settings(rig)
    started = facts.get('started')
    since = int(datetime.datetime.fromisoformat(started).timestamp()) - 5 if started else int(time.time()) - 3600
    try:
        lines, errors = journal(since, facts.get('GAME_PID', ''), run)
        (rig / 'journal.txt').write_text('\n'.join(lines + [f'# journalctl error: {e}' for e in errors]) + '\n')
    except (OSError, subprocess.SubprocessError) as error:
        (rig / 'journal.txt').write_text(f'# journalctl failed: {error!r}\n')
    try:
        card = run(['cardwire', 'get'], capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL)
        (rig / 'cardwire.txt').write_text(f'# cardwire get: exit {card.returncode}\n{card.stdout}{card.stderr}')
    except (OSError, subprocess.SubprocessError) as error:
        (rig / 'cardwire.txt').write_text(f'# cardwire get failed: {error!r}\n')
    sound = []
    for name in ('game.txt', 'gradle.txt'):
        path = rig / name
        if path.exists():
            sound += [f'{name}: {line}' for line in path.read_text(errors='replace').splitlines() if SOUND.search(line)]
    (rig / 'sound-lines.txt').write_text('\n'.join(sound) + ('\n' if sound else ''))
    # The zombie's wait status is the first source; Gradle's exit value is the fallback (brief review 1, finding 5).
    exit_path = rig / 'exit.json'
    if exit_path.exists():
        record = json.loads(exit_path.read_text())
        value = gradle_exit(rig)
        record['gradle_exit_value'] = value
        if record.get('signal') is None and record.get('outcome') == 'exited' and value is not None and value > 128:
            record['signal'] = value - 128
            record['signal_source'] = 'gradle exit value'
        exit_path.write_text(json.dumps(record, indent=1) + '\n')
    if out:
        out = pathlib.Path(out)
        out.mkdir(parents=True, exist_ok=True)
        for name in PUBLIC:
            if (rig / name).exists():
                (out / name).write_text(public((rig / name).read_text(errors='replace')))
        for path in sorted(rig.glob('snap-*.json')):
            (out / path.name).write_text(public(path.read_text()))


if __name__ == '__main__':
    if sys.argv[1] == 'status':
        status(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'final':
        final(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        raise SystemExit('usage: records.py status <rig> <label> | final <rig> [<out>]')
