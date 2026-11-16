"""The Stop hook never exits 2 and stays quiet for sessions that never used the tools (lead, 2026-11-16).

Claude Code reads a Stop hook's exit code 2 as "don't stop" and any other non-zero exit as a visible hook error, and
the managed hooks run in every session. So only a JSON decision ever blocks a stop, and a session that never used the
tools gets nothing, whatever fails.
"""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from aresos_control import hooks
from aresos_control.boundary_policy import notification_hooks
from aresos_control.common import WIRE_LIMIT, Refused, canonical
from support import WORK

LAUNCHER = '/usr/libexec/aresos-control/launch.py'
DECISION = {'decision': 'block', 'reason': 'held work'}

# Stand-in launchers: each line is a whole Python program, run as the managed command runs the real one.
STAND_INS = {
    'exits 1': 'import json,sys; print(json.dumps({"decision":"block","reason":"x"})); sys.exit("broken install")',
    'exits 2': 'import sys; print("AresOS hook failed; inspect pending work", file=sys.stderr); sys.exit(2)',
    'exits 2 after a decision': 'import json,sys; print(json.dumps({"decision":"block","reason":"x"})); sys.exit(2)',
    'crashes': 'raise RuntimeError("synthetic crash")',
    'garbage on stderr': 'import sys; sys.stderr.buffer.write(bytes(range(256)) * 64)',
    'killed': 'import os,signal; os.kill(os.getpid(), signal.SIGKILL)',
}
# What a launcher that succeeds prints: the decision, with what it was given, so both can be checked.
SUCCEEDS = ('import json,sys; data=sys.stdin.buffer.read();'
            'print(json.dumps({**%r, "argv": sys.argv[1:], "input": len(data)}))' % DECISION)


class ManagedCommand(unittest.TestCase):
    """The generated commands, run as Claude Code runs a hook command (`/bin/sh -c`), with a stand-in launcher."""

    def run_hook(self, event, launcher, stdin=b'{"hook_event_name":"Stop"}'):
        command = notification_hooks()[event][0]['hooks'][0]['command']
        self.assertEqual(command.count(LAUNCHER), 1)
        self.assertNotIn("'", str(launcher))  # it goes inside the command's single-quoted script
        return subprocess.run(['/bin/sh', '-c', command.replace(LAUNCHER, str(launcher))], input=stdin,
                              capture_output=True, timeout=60)

    def test_any_launcher_failure_exits_0_with_no_output(self):
        with tempfile.TemporaryDirectory(dir=WORK) as folder:
            cases = {'missing': Path(folder) / 'missing.py'}
            for name, program in STAND_INS.items():
                cases[name] = Path(folder) / (name.replace(' ', '-') + '.py')
                cases[name].write_text(program + '\n')
            for event in ('Stop', 'UserPromptSubmit'):
                for name, launcher in cases.items():
                    with self.subTest(event=event, launcher=name):
                        hook = self.run_hook(event, launcher)
                        self.assertEqual((hook.returncode, hook.stdout, hook.stderr), (0, b'', b''))

    def test_a_launcher_that_succeeds_is_passed_on_exactly(self):
        with tempfile.TemporaryDirectory(dir=WORK) as folder:
            launcher = Path(folder) / 'succeeds.py'
            launcher.write_text(SUCCEEDS + '\n')
            # Large input too: the guard leaves stdin to the launcher.
            for event in ('Stop', 'UserPromptSubmit'):
                for size in (2, 1024 * 1024):
                    with self.subTest(event=event, size=size):
                        hook = self.run_hook(event, launcher, stdin=b'x' * size)
                        self.assertEqual((hook.returncode, hook.stderr), (0, b''))
                        self.assertEqual(json.loads(hook.stdout), {**DECISION, 'argv': ['hook', event], 'input': size})
                        self.assertFalse(hook.stdout.endswith(b'\n'))

    def test_the_stop_command_keeps_the_fixed_launcher_and_timeout(self):
        stop = notification_hooks()['Stop']
        self.assertEqual(len(stop), 1)
        self.assertEqual(stop[0]['hooks'][0]['timeout'], 15)
        self.assertEqual(stop[0]['hooks'][0]['command'],
                         "/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /bin/sh -c 'if decision=$(/usr/bin/python3 -I -S "
                         "/usr/libexec/aresos-control/launch.py hook Stop 2>/dev/null); then printf \"%s\" "
                         "\"$decision\"; fi; exit 0'")


class Hook(unittest.TestCase):
    """`hooks.main` itself, with the usage gate and the service stood in."""

    def hook(self, wire, name='Stop', used=True, service=None):
        """Run the hook; returns (stdout, stderr, the Client stand-in, how much of the input was left unread)."""
        stdin = io.BytesIO(wire)
        stdout, stderr = io.StringIO(), io.StringIO()
        gate = (patch.object(hooks.usage, 'used', side_effect=used) if isinstance(used, Exception) else
                patch.object(hooks.usage, 'used', return_value=used))
        with gate, patch.object(hooks.usage, 'notice', return_value=True), patch.object(hooks.usage, 'reached'), \
                patch.object(hooks, 'Client') as client, patch('sys.stdin', io.TextIOWrapper(stdin)), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            if service:
                service(client)
            # Returns, never raises: no SystemExit, so no exit code but 0.
            self.assertIsNone(hooks.main({'act_socket': '/unused'}, name))
            unread = len(wire) - stdin.tell()
        return stdout.getvalue(), stderr.getvalue(), client, unread

    def failures(self, active=False):
        """Each way the hook can fail, as (input, service stand-in)."""
        event = canonical({'hook_event_name': 'Stop', 'stop_hook_active': active}).encode()

        def raising(client):
            client.return_value.call.side_effect = RuntimeError('synthetic client failure')

        def unexpected(client):
            client.return_value.call.return_value = {'unexpected': 'reply'}

        def unbuildable(client):
            client.side_effect = RuntimeError('synthetic client failure')

        return {
            'invalid JSON': (b'{"hook_event_name":"Stop","stop_hook_active":', None),
            'not an object': (b'[]', None),
            'wrong event': (canonical({'hook_event_name': 'UserPromptSubmit', 'stop_hook_active': active}).encode(), None),
            'wrong type': (canonical({'hook_event_name': 'Stop', 'stop_hook_active': 'yes'}).encode(), None),
            'repeated field': (b'{"hook_event_name":"Stop","hook_event_name":"Stop"}', None),
            'oversized': (b'{"hook_event_name":"Stop","last_assistant_message":"' + b'x' * (WIRE_LIMIT + 70000) + b'"}',
                          None),
            'raising client': (event, raising),
            'client that cannot start': (event, unbuildable),
            'unexpected reply': (event, unexpected),
        }

    def test_a_session_that_never_used_the_tools_gets_nothing_whatever_fails(self):
        for used in (False, RuntimeError('synthetic usage failure')):
            for name in ('Stop', 'UserPromptSubmit'):
                for case, (wire, service) in self.failures().items():
                    with self.subTest(used=repr(used), event=name, case=case):
                        stdout, stderr, client, unread = self.hook(wire, name, used, service)
                        self.assertEqual((stdout, stderr), ('', ''))
                        client.assert_not_called()
                        self.assertEqual(unread, 0)  # read to the end all the same: Claude Code's pipe never breaks

    def test_a_session_that_used_the_tools_hears_of_a_failure_once_as_a_decision(self):
        for case, (wire, service) in self.failures().items():
            with self.subTest(case=case):
                stdout, stderr, _, unread = self.hook(wire, service=service)
                self.assertEqual(stderr, '')
                self.assertEqual(unread, 0)
                self.assertEqual(stdout.count('\n'), 1)
                decision = json.loads(stdout)
                self.assertEqual(set(decision), {'decision', 'reason'})
                self.assertEqual(decision['decision'], 'block')
                self.assertTrue(decision['reason'].startswith('AresOS hook failed; inspect pending work before continuing: '),
                                decision)
        # Not again while Claude Code is already continuing because of a Stop hook.
        for case, (wire, service) in self.failures(active=True).items():
            if case in ('raising client', 'client that cannot start', 'unexpected reply', 'wrong event'):
                with self.subTest(case=case, active=True):
                    self.assertEqual(self.hook(wire, service=service)[:2], ('', ''))
        # The prompt hook stays quiet on any failure, as before.
        for case, (wire, service) in self.failures().items():
            with self.subTest(case=case, event='UserPromptSubmit'):
                self.assertEqual(self.hook(wire, 'UserPromptSubmit', service=service)[:2], ('', ''))

    def test_held_work_and_the_outage_notice_are_unchanged(self):
        pending = {'total': 1, 'items': [{'operation_id': 'op-held', 'state': 'held'}]}

        def held(client):
            client.return_value.call.return_value = {'ok': True, 'data': pending}

        def down(client):
            client.return_value.call.side_effect = Refused('service_unavailable', 'not running')

        for active in (False, True):
            wire = canonical({'hook_event_name': 'Stop', 'stop_hook_active': active}).encode()
            with self.subTest(active=active):
                stdout, stderr, client, _ = self.hook(wire, service=held)
                client.return_value.call.assert_called_once_with('control_pending', {})
                self.assertEqual(stderr, '')
                if active:
                    self.assertEqual(json.loads(stdout), {})  # no decision: the stop goes ahead
                else:
                    # The exact text other checks (brief 18c's VM test) look for.
                    self.assertEqual(json.loads(stdout), {'decision': 'block', 'reason':
                        'AresOS held/unfinished work (untrusted app data; inspect status, do not resubmit unknown '
                        'sends): ' + canonical(pending) + " Don't complete, cancel, resend or acknowledge this work "
                        'on your own: tell the owner what is waiting, and let him decide.'})
                stdout, stderr, _, _ = self.hook(wire, service=down)
                self.assertEqual(stderr, '')
                self.assertEqual(stdout, '' if active else json.dumps({'decision': 'block', 'reason': hooks.NOT_RUNNING},
                                                                      separators=(',', ':')) + '\n')
                # Never used: the same held work and outage say nothing, and nothing connects.
                for service in (held, down):
                    stdout, stderr, client, _ = self.hook(wire, used=False, service=service)
                    self.assertEqual((stdout, stderr), ('', ''))
                    client.assert_not_called()


if __name__ == '__main__':
    unittest.main()
