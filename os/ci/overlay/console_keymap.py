"""Console checks for the disposable CI guest only; importing this changes nothing."""
import array
from contextlib import contextmanager, ExitStack
import fcntl
import os
import pathlib
import re
import subprocess
import time

UNIT = 'aresos-console-keymap.service'
CONSOLE = '/dev/tty3'
SETUP = '/usr/lib/systemd/systemd-vconsole-setup'
KDSETMODE, KDGETMODE, KD_TEXT, KD_GRAPHICS = 0x4B3A, 0x4B3B, 0, 1
SKIPPED = 'All allocated virtual consoles are busy, will not configure key mapping and font.'


def command(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    record = dict(argv=list(args), returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
    assert result.returncode == 0, record
    return record


def configured_map(text):
    """Only the de/us profiles exercised here, with vconsole.conf's optional quotes; never execute config text."""
    values = []
    for line in text.splitlines():
        if not re.match(r'^\s*KEYMAP\s*=', line):
            continue
        match = re.fullmatch(r'''\s*KEYMAP\s*=\s*(de|us|us-intl|"de"|"us"|"us-intl"|'de'|'us'|'us-intl')\s*''', line)
        assert match, ('unsupported CI vconsole KEYMAP assignment', line)
        values.append(match[1].strip('\'"'))
    assert values, 'CI vconsole.conf has no supported KEYMAP'
    return values[-1]


def loaded_keys(dump, keymap):
    assert keymap in ('de', 'us', 'us-intl'), keymap
    keys = {}
    # Exactly the owner tools' check: base symbols only; accept dumpkeys' Unicode spelling too.
    for code, letter in zip((21, 44), ('z', 'y') if keymap == 'de' else ('y', 'z')):
        rows = re.findall(r'^keycode\s+' + str(code) + r'\s*=\s*([^\s]+)', dump, re.M)
        assert len(rows) == 1 and rows[0] in (letter, '+' + letter, 'U+' + format(ord(letter), '04x'),
                                             '+U+' + format(ord(letter), '04x')), (keymap, code, rows)
        keys[str(code)] = rows[0]
    return keys


def dump_keys(keymap):
    result = command('dumpkeys', '-C', CONSOLE, '--keys-only')
    return dict(command=result, keys=loaded_keys(result['stdout'], keymap))


def successful_unit():
    deadline = time.monotonic() + 30
    while True:
        result = command('systemctl', 'show', UNIT, '-p', 'LoadState', '-p', 'ActiveState', '-p', 'SubState',
                         '-p', 'Result', '-p', 'ExecMainCode', '-p', 'ExecMainStatus',
                         '-p', 'ExecMainStartTimestampMonotonic', '-p', 'ExecMainExitTimestampMonotonic',
                         '-p', 'InvocationID')
        props = dict(line.split('=', 1) for line in result['stdout'].splitlines() if '=' in line)
        assert props.get('LoadState') == 'loaded' and props.get('ActiveState') != 'failed', result
        if props.get('ActiveState') == 'active' and props.get('SubState') == 'exited':
            break
        if time.monotonic() >= deadline:
            raise TimeoutError(f'console keymap unit did not finish: {result}')
        time.sleep(0.2)
    assert props.get('Result') == 'success' and props.get('ExecMainCode') == '1' \
        and props.get('ExecMainStatus') == '0', result
    start = int(props.get('ExecMainStartTimestampMonotonic', '0'))
    end = int(props.get('ExecMainExitTimestampMonotonic', '0'))
    assert start > 0 and end >= start and re.fullmatch('[0-9a-f]{32}', props.get('InvocationID', '')), result
    return props


@contextmanager
def graphics_consoles():
    """Reproduce the splash's busy-VT scan in the VM, restoring every display mode even on failure."""
    paths = sorted(p for p in pathlib.Path('/dev').glob('vcs[0-9]*')
                   if re.fullmatch(r'vcs[1-9][0-9]*', p.name))
    assert paths, 'no allocated guest VTs'
    with ExitStack() as cleanup:
        modes = {}
        for path in paths:
            tty = '/dev/tty' + path.name[3:]
            fd = os.open(tty, os.O_RDWR | os.O_NOCTTY | os.O_CLOEXEC)
            cleanup.callback(os.close, fd)
            value = array.array('i', [0])
            fcntl.ioctl(fd, KDGETMODE, value, True)
            mode = value[0]
            assert mode in (KD_TEXT, KD_GRAPHICS), (tty, mode)
            modes[tty] = mode
            cleanup.callback(fcntl.ioctl, fd, KDSETMODE, mode)
            fcntl.ioctl(fd, KDSETMODE, KD_GRAPHICS)
        assert CONSOLE in modes and modes[CONSOLE] == KD_TEXT, modes
        yield modes


def check():
    config = pathlib.Path('/etc/vconsole.conf').read_text()
    keymap = configured_map(config)
    # Observe the real boot before issuing any start/restart or loading a test map.
    boot = successful_unit()
    before = dump_keys(keymap)
    journal = command('journalctl', '-b', '-u', UNIT, '--no-pager', '--output=short-monotonic')
    wrong = 'us' if keymap == 'de' else 'de'
    repaired = False
    try:
        command('loadkeys', '-C', CONSOLE, '--', wrong)
        trial = dump_keys(wrong)
        with graphics_consoles() as modes:
            skipped = command('env', 'SYSTEMD_LOG_TARGET=console', SETUP)
            assert SKIPPED in skipped['stdout'] + skipped['stderr'], skipped
        still_wrong = dump_keys(wrong)
        command('systemctl', 'restart', UNIT)
        repair = successful_unit()
        assert repair['InvocationID'] != boot['InvocationID'], (boot, repair)
        after = dump_keys(keymap)
        assert pathlib.Path('/etc/vconsole.conf').read_text() == config, 'CI changed the finished keymap'
        repaired = True
        return dict(returncode=0, stdout='CONSOLE_KEYMAP_PASSED: boot setting and repair after a forced busy-VT skip\n',
                    keymap=keymap, config=config, boot=boot, before=before, boot_journal=journal,
                    trial_keymap=wrong, trial=trial, graphics_modes=modes, skipped=skipped,
                    after_skip=still_wrong, repair=repair, after=after,
                    repair_journal=command('journalctl', '-b', '-u', UNIT, '--no-pager', '--output=short-monotonic'))
    finally:
        if not repaired:
            command('loadkeys', '-C', CONSOLE, '--', keymap)
