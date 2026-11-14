"""The owner's password for Chrome changes that loosen a rule (final fixes F7).

chrome.sock checks only the peer's user id, so any process of the owner's user
can pose as the native host while Chrome is closed. Loosening (a "don't ask
again" entry, read-only off) therefore asks polkit for an admin password,
against the process that actually connected, once for each change. Listing,
revoking and turning read-only on stay without a prompt.
"""
import subprocess
import time

ACTION = 'org.aresos.control.chrome-loosen'
PKCHECK = '/usr/bin/pkcheck'
# The owner reads the change and types his password. The extension waits longer
# (background.js, LOOSEN_WAIT_MS), so its reply always carries this outcome.
TIMEOUT = 120.0
# polkit names these details when an earlier authorization was reused or would be
# kept. Only a fresh challenge for this one change counts as the owner's yes.
CACHED = (b'polkit.temporary_authorization_id', b'polkit.retains_authorization_after_challenge')
# pkcheck(1) exit codes.
REFUSALS = {1: 'the password was wrong or the request was denied',
            2: 'no password dialog could be shown (no authentication agent answered)',
            3: 'the password dialog was dismissed'}


def loosening(arguments):
    """Everything except listing, revoking and turning read-only on needs the password."""
    if not isinstance(arguments, dict):
        return True
    command = arguments.get('command')
    if command in {'list', 'revoke'}:
        return False
    return not (command == 'readonly' and arguments.get('enabled', True) is True)


def start_time(pid):
    """Field 22 of /proc/PID/stat. With the pid it names one process, even after pid reuse."""
    with open(f'/proc/{int(pid)}/stat', 'rb') as stream:
        data = stream.read()
    # The command name may contain spaces and brackets; fields resume after the last ')'.
    return int(data[data.rindex(b')') + 2:].split()[19])


def shown(value, limit=120):
    """Text for the system dialog: one line, no markup an agent could render, bounded."""
    text = ' '.join(str(value).split())
    text = ''.join(c if c.isprintable() and c not in '<>&`\\$' else '?' for c in text)
    return text[:limit] + ('…' if len(text) > limit else '')


def command(peer, change, pkcheck=PKCHECK):
    subject = f"{int(peer['pid'])},{int(peer['start'])},{int(peer['uid'])}"
    return [pkcheck, '--action-id', ACTION, '--process', subject, '--allow-user-interaction', '--detail', 'change', change]


class Ask:
    """One pkcheck run for one change. It never blocks the service's loop."""

    def __init__(self, peer, change, pkcheck=PKCHECK, timeout=TIMEOUT, clock=time.monotonic):
        self.clock = clock
        self.deadline = clock() + timeout
        self.process = subprocess.Popen(command(peer, change, pkcheck), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})

    def outcome(self):
        """None while the dialog is up; then (granted, reason). Only a clear yes grants."""
        code = self.process.poll()
        if code is None:
            if self.clock() < self.deadline:
                return None
            self.cancel()
            return False, 'the password dialog timed out'
        output, errors = self.process.communicate()
        if code == 0:
            if any(key in output for key in CACHED):
                return False, 'polkit reused an earlier confirmation; each change needs its own'
            return True, 'confirmed with the owner\'s password'
        detail = shown(errors.decode('utf-8', 'replace'), 200)
        return False, REFUSALS.get(code, 'polkit could not check the request') + (f' ({detail})' if detail else '')

    def cancel(self):
        # Ending pkcheck makes polkit drop its dialog: the caller left the bus.
        if self.process.poll() is None:
            self.process.kill()
        self.process.communicate()


def start(peer, change, pkcheck=PKCHECK, timeout=TIMEOUT, clock=time.monotonic):
    """Start the check, or return why it can't run. Nothing here writes."""
    if not peer or any(type(peer.get(key)) is not int for key in ('pid', 'uid', 'start')):
        return None, "the connecting process can't be identified"
    try:
        return Ask(peer, change, pkcheck, timeout, clock), None
    except OSError as exc:
        return None, f'polkit is unavailable ({shown(exc.strerror or exc, 80)})'
