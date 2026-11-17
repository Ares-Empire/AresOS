"""D2 rows 0–10, D3's guard and D4's announcement/record boundary, on modelled hosts only."""
import contextlib
import copy
import io
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_owner_update as base
from test_release27 import UPDATE_STUBS

ROOT, owner = base.ROOT, base.owner
NEWEST = 'sudo /var/lib/ares/at newest'
GUARD = ('A newer AresOS than the running one is installed, and this command installs a release '
         'only from the newest; nothing changed')
INSTALL = 'Update: installing the latest version, AresOS 21. Restart to finish'
FORWARD = 'Update: switching to the latest installed version, AresOS 21 (already downloaded). Restart to finish'
LATER = 'These tools also carry a newer version, AresOS 30. After the restart, ' + NEWEST + ' installs it'
FAILED = 'The last update did not finish, so nothing changed. See Help before trying again'


class MaskCheckMachine(base.Machine):
    """Run update's real shell preflight against fixture units and command stubs."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.check_setup = None
        self.check_calls, self.check_links = [], {}

    def script(self, text, name, mutation=True):
        if name != 'update-preflight':
            return super().script(text, name, mutation)
        assert not mutation
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory:
            root = pathlib.Path(directory)
            for folder in ('units', 'policy', 'bin'):
                (root / folder).mkdir()
            for policy in ('masked-system-units.txt', 'masked-user-units.txt'):
                shutil.copyfile(ROOT / 'os/policy' / policy, root / 'policy' / policy)
            for unit in owner.FINALIZERS:
                os.symlink('/dev/null', root / 'units' / unit)
            for file in ('calls', 'system-unmasked', 'user-unmasked'):
                (root / file).write_text('')
            (root / 'auth.json').write_text('{}\n')
            (root / 'state.json').write_text(json.dumps(self.state['bootc']))
            # Even an accidental fall-through cannot run a deployment command.
            stubs = dict(UPDATE_STUBS, bootc='#!/bin/bash\n'
                'printf "bootc %s\\n" "$*" >> "$FIXTURE_CALLS"\n'
                '[[ $* == "status --json" ]] || exit 97\ncat "$FIXTURE_ROOT/state.json"\n',
                python3='#!/bin/bash\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
            for command, source in stubs.items():
                (root / 'bin' / command).write_text(source)
                (root / 'bin' / command).chmod(0o755)
            if self.check_setup is not None:
                self.check_setup(root)
            before = {p.name: os.readlink(p) if p.is_symlink() else p.read_bytes()
                      for p in (root / 'units').iterdir()}
            for old, new in (('test -r /etc/ostree/auth.json', 'test -r "$FIXTURE_ROOT/auth.json"'),
                             ('policy=/usr/share/aresos/policy\n', 'policy="$FIXTURE_ROOT/policy"\n'),
                             ('units=/etc/systemd/system\n', 'units="$FIXTURE_ROOT/units"\n')):
                assert text.count(old) == 1, old
                text = text.replace(old, new)
            result = subprocess.run(['bash', '--noprofile', '--norc', '-seu'], input=text, text=True,
                capture_output=True, timeout=15, cwd=root,
                env=dict(os.environ, PATH=str(root / 'bin') + os.pathsep + os.environ['PATH'],
                    FIXTURE_ROOT=str(root), FIXTURE_CALLS=str(root / 'calls')))
            self.check_calls = (root / 'calls').read_text().splitlines()
            self.check_links = {p.name: os.readlink(p) if p.is_symlink() else p.read_bytes()
                                for p in (root / 'units').iterdir()}
            assert self.check_links == before, 'read-only preflight changed unit files'
            assert not any('daemon-reload' in call or call.startswith('bootc switch') for call in self.check_calls)
        self.trace.append(dict(script=name, mutation=False, returncode=result.returncode,
                               stdout=result.stdout, stderr=result.stderr))
        if result.returncode:
            raise owner.Failed('Shared step failed: ' + name + '; preserve diagnostics and do not reboot', result.returncode)
        return result.stdout


@contextlib.contextmanager
def route(*args, **kwargs):
    kwargs.setdefault('host_class', MaskCheckMachine)
    with base.route(*args, **kwargs) as values, patch.object(owner, 'finalizer_masks', return_value=[]):
        yield values


def journal(tools, state, word, target=None):
    tools.intend(word, state, None, target)


def interrupted_update(tools, host, complete=False):
    journal(tools, host.state, 'update')
    if complete:
        host.state = base.machine([base.release_row(base.R30 if tools.release['reference'] == base.R30 else base.R21,
            staged=True), *host.state['rpm']['deployments']])


class NewestTest(unittest.TestCase):
    def call(self, tools, host, chosen, first=None, stop=None):
        output, before = io.StringIO(), copy.deepcopy(host.state)
        with contextlib.redirect_stdout(output):
            if stop is None:
                lines = tools.newest()
            else:
                with self.assertRaises(owner.Stop) as caught:
                    tools.newest()
                self.assertIn(stop, str(caught.exception))
                self.assertEqual(host.state, before)
                lines = []
        self.assertEqual(tools.chosen, chosen)
        said = output.getvalue().splitlines()
        if first:
            self.assertEqual((said + lines)[0], first)
        for line in [*tools.said, *lines]:
            self.assertNotIn(owner.typed('update'), line)
            self.assertNotIn(owner.typed('forward'), line)
        return lines, said

    def test_row0_unknown_deployment_and_bazzite_update_stop_before_announcement(self):
        states = [base.machine([base.release_row(base.R99, booted=True), base.release_row(base.R13), base.stock_row()]), base.machine([base.release_row(base.R21, staged=True),
            base.stock_row(True), base.release_row(base.R13)])]
        for state in states:
            with self.subTest(state=state), route(state) as (tools, host, store):
                self.call(tools, host, None, stop='Unknown deployment' if state == states[0] else 'A Bazzite update is waiting')
                self.assertEqual(tools.said, [])
                self.assertFalse(host.changes)

    def test_row1_no_installed_aresos(self):
        with route(base.prepared()['state']) as (tools, host, store):
            self.call(tools, host, None, stop=owner.NOT_INSTALLED)
            self.assertEqual(tools.said, [])

    def test_row2_failed_update_says_only_once_and_next_run_acts(self):
        for old in (False, True):
            with self.subTest(old=old), route(base.returned() if old else base.pair(),
                    base.H30 if old else base.H21) as (tools, host, store):
                interrupted_update(tools, host)
                tools.boot[0] = 'boot-2'
                before = copy.deepcopy(host.state)
                lines, said = self.call(tools, host, None)
                self.assertEqual(lines, [FAILED])
                self.assertEqual(said, ['Update to ' + tools.release['reference']
                    + ' was not applied: the deployments are as before it, and nothing is waiting'])
                self.assertEqual(tools.said, said)
                self.assertEqual(tools.notes, [])
                self.assertEqual(host.state, before)
                self.assertFalse((store / (owner.OUTCOME + '.json')).exists())
                self.call(tools, host, 'forward' if old else 'update', first=FORWARD if old else INSTALL)

    def test_row2_reorder_note_comes_first_then_choice_continues(self):
        with route(base.returned(), base.H30) as (tools, host, store):
            journal(tools, host.state, 'forward', host.state['rpm']['deployments'][1])
            lines, said = self.call(tools, host, 'forward')
            self.assertIn('Forward to ' + base.R21 + ' was not applied', said[0])
            self.assertEqual(said[1], FORWARD)
            self.assertEqual(tools.notes, [])
            self.assertEqual(lines[-1], LATER)
            self.assertEqual(tools.load(owner.OUTCOME)['word'], 'forward')

    def test_check_then_newest_repeats_the_failed_update_in_that_run(self):
        with route(base.pair()) as (tools, host, store):
            interrupted_update(tools, host)
            tools.boot[0] = 'boot-2'
            tools.check()
            self.assertEqual(sum('was not applied' in line for line in tools.notes), 1)
            # main prints notes for check; a later invocation has a fresh Tools object.
            tools.notes = []
            self.call(tools, host, 'update', first=INSTALL)
            self.assertIn('bootc switch --retain ' + base.R21, host.changes)

    def test_row3_records_only_on_newest_and_on_older_running_release(self):
        for old in (False, True):
            with self.subTest(old=old), route(base.returned() if old else base.pair(),
                    base.H30 if old else base.H21) as (tools, host, store):
                interrupted_update(tools, host, complete=True)
                before = copy.deepcopy(host.state)
                number = 30 if old else 21
                lines, said = self.call(tools, host, 'update', first='Update: AresOS ' + str(number)
                    + ' is already downloaded and ready. Saving the record of the interrupted update. Restart to finish')
                expected = [said[0], 'This run downloads nothing']
                if old:
                    expected += ['AresOS 21 will be removed when the update finishes at shutdown',
                        "AresOS 30 will start with this system's settings (Wi-Fi, passwords, layout), not AresOS 21's"]
                self.assertEqual(said, expected)
                self.assertEqual(host.state, before)
                self.assertFalse(host.changes)
                self.assertEqual(tools.load(owner.OUTCOME)['status'], 'recorded')
                self.assertTrue(lines[0].startswith('Interrupted update recorded: '))

    def test_rows4_and5_retry_only_from_the_newest_running_aresos(self):
        with route(base.pair()) as (tools, host, store):
            interrupted_update(tools, host)
            with patch.object(tools, 'newest_guard', wraps=tools.newest_guard) as guard:
                self.call(tools, host, 'update', first='Update: continuing the interrupted update to AresOS 21. Restart to finish')
            self.assertEqual(guard.call_count, 2)
            self.assertEqual(host.changes, ['bootc switch --retain ' + base.R21])
        with route(base.returned(), base.H30) as (tools, host, store):
            interrupted_update(tools, host)
            before = (store / (owner.OUTCOME + '.json')).read_bytes()
            self.call(tools, host, None, stop='The update to ' + base.R30
                + ' was begun on an older AresOS and interrupted; this command does not continue it; '
                'nothing changed; do not reboot; get help: EMERGENCY Failed or bad update')
            self.assertEqual(tools.said, [])
            self.assertEqual((store / (owner.OUTCOME + '.json')).read_bytes(), before)

    def test_row6_each_pending_change_is_a_noop_with_no_announcement(self):
        for word, first in (
            ('update', 'The update to AresOS 21 is ready. Restart to finish'),
            ('forward', 'The switch to AresOS 21 is ready. Restart to finish'),
            ('previous', 'The return to the previous version, AresOS 13, is ready. This command changes nothing before the restart. Restart to finish'),
            ('rollback', 'The return to plain Bazzite is ready. This command changes nothing before the restart. Restart to finish')):
            with self.subTest(word=word), route(base.pair() if word == 'update' else base.returned()
                    if word == 'forward' else base.updated(), wheel=word in ('previous', 'rollback')) as (tools, host, store):
                with contextlib.redirect_stdout(io.StringIO()):
                    (tools.recover if word == 'rollback' else getattr(tools, word))()
                before = (store / (owner.OUTCOME + '.json')).read_bytes(), copy.deepcopy(host.state), list(host.changes)
                lines, said = self.call(tools, host, None, first=first)
                self.assertEqual(said, [])
                if word in ('previous', 'rollback'):
                    self.assertEqual(lines[1], 'After the restart, ' + NEWEST
                        + ' switches back to the latest installed version, AresOS 21')
                self.assertEqual(((store / (owner.OUTCOME + '.json')).read_bytes(), host.state, host.changes), before)

    def test_keep_stock_is_applied_and_row10_switches_back_without_staging(self):
        state = base.machine([base.release_row(base.R21), base.stock_row(True), base.release_row(base.R13)])
        with route(state) as (tools, host, store):
            tools.recover(True)
            self.call(tools, host, 'forward', first='Update: switching from plain Bazzite to the latest installed version, '
                'AresOS 21 (already downloaded). Restart to finish')
            self.assertFalse(any('bootc switch' in str(c) for c in host.changes))

    def test_rows7_and8_install_and_current_tools_version_line(self):
        with route(base.pair()) as (tools, host, store):
            lines, said = self.call(tools, host, 'update', first=INSTALL)
            self.assertEqual(said, [INSTALL, 'This downloads AresOS 21'])
            self.assertEqual(tools.load(owner.OUTCOME)['word'], 'update')
            self.assertEqual(host.changes, ['bootc switch --retain ' + base.R21])
        with route(base.updated(), wheel=True) as (tools, host, store):
            lines, said = self.call(tools, host, None, first='AresOS is up to date (AresOS 21)')
            self.assertEqual(lines, ['AresOS is up to date (AresOS 21)',
                'AresOS 21 is running and will start next. It is the latest version these tools know. Nothing changed',
                'Owner tools version 3: ' + owner.checked_bundle(tools.payload)[:8],
                'A newer version comes with newer owner tools after the maintainer announces it. '
                'docs/OWNER-TOOLS.md on GitHub lists the current tools'])
            self.assertRegex(lines[2], r'^Owner tools version [0-9]+: [0-9a-f]{8}$')
            self.assertRegex((ROOT / 'docs/OWNER-TOOLS.md').read_text().splitlines()[0],
                             r'^Owner tools version [0-9]+: [0-9a-f]{8}$')
            self.assertFalse(host.changes)
            self.assertFalse((store / (owner.OUTCOME + '.json')).exists())

    def test_row9_old_aresos_and_stock_running_with_and_without_newer_tools(self):
        for stock in (False, True):
            for carry in (False, True):
                state = base.machine([base.release_row(base.R21), base.stock_row(stock), base.release_row(base.R13, booted=not stock)])
                with self.subTest(stock=stock, carry=carry), route(state, base.H30 if carry else base.H21) as (tools, host, store):
                    lines, said = self.call(tools, host, None, first='AresOS 21 will start next. Nothing changed')
                    self.assertEqual(lines, ['AresOS 21 will start next. Nothing changed',
                        'It is not running yet. Restart to finish'] + ([LATER] if carry else []))
                    self.assertEqual(said, [])
                    self.assertFalse(host.changes)

    def test_row10_all_three_wordings_and_both_later_install_endings(self):
        for kind, first in (
            ('old', FORWARD),
            ('stock', 'Update: switching from plain Bazzite to the latest installed version, AresOS 21 (already downloaded). Restart to finish'),
            ('newest', 'Update: AresOS 21 is the latest installed version and is running. Making it start next again instead of '
                'AresOS 13. No restart is needed for this change'),
            ('newest-stock-next', 'Update: AresOS 21 is the latest installed version and is running. Making it start next again instead of '
                'plain Bazzite. No restart is needed for this change')):
            for carry in (False, True):
                state = (base.returned() if kind == 'old' else
                    base.machine([base.stock_row(True), base.release_row(base.R21), base.release_row(base.R13)]) if kind == 'stock' else
                    base.queued_previous() if kind == 'newest' else
                    base.machine([base.stock_row(), base.release_row(base.R21, booted=True), base.release_row(base.R13)]))
                with self.subTest(kind=kind, carry=carry), route(state, base.H30 if carry else base.H21,
                        wheel=kind.startswith('newest')) as (tools, host, store):
                    lines, said = self.call(tools, host, 'forward', first=first)
                    self.assertEqual(said, [first, 'This downloads nothing and removes nothing'])
                    self.assertEqual(tools.load(owner.OUTCOME)['word'], 'forward')
                    self.assertEqual(host.changes, ['ostree admin set-default 1', 'sync'])
                    self.assertEqual({owner.key(d) for d in state['rpm']['deployments']},
                                     {owner.key(d) for d in host.state['rpm']['deployments']})
                    if carry:
                        self.assertEqual(lines[-1], ('These tools also carry a newer version, AresOS 30. No restart is needed first. The next '
                            + NEWEST + ' installs it') if kind.startswith('newest') else LATER)
                        if kind.startswith('newest'):
                            self.call(tools, host, 'update', first='Update: installing the latest version, AresOS 30. Restart to finish')

    def test_forward_closing_uses_inner_installed_set_including_already_first(self):
        for installed_before in (False, True):
            for already_first in (False, True):
                before = base.machine([base.stock_row(), base.release_row(base.R21, booted=True),
                    base.release_row(base.R30 if installed_before else base.R13)])
                # REVIEW-5: R21 runs, stock starts next, and unbooted R13 is
                # replaced by R30. Also exercise the inverse and already-first paths.
                target = base.R21 if installed_before else base.R30
                rows = [base.stock_row(), base.release_row(base.R21, booted=True),
                    base.release_row(base.R13 if installed_before else base.R30)]
                if already_first:
                    rows.sort(key=lambda row: owner.image_reference(row) != target)
                after = base.machine(rows)
                with self.subTest(installed_before=installed_before, already_first=already_first), \
                        route(before, base.H30, wheel=True) as (tools, host, store):
                    original, reads = tools.survey, []
                    def survey(*args, **kwargs):
                        reads.append(True)
                        if len(reads) == 2:
                            host.state = copy.deepcopy(after)
                        return original(*args, **kwargs)
                    with patch.object(tools, 'survey', side_effect=survey):
                        lines, said = self.call(tools, host, 'forward')
                    suffix = [line for line in lines if line.startswith('These tools also carry')]
                    if installed_before:
                        self.assertEqual(suffix, ['These tools also carry a newer version, AresOS 30. '
                            'No restart is needed first. The next ' + NEWEST + ' installs it'])
                    else:
                        self.assertEqual(suffix, [])
                        if already_first:
                            self.assertEqual(lines[1], 'It does not run yet: it starts at the next restart')
                        else:
                            self.assertEqual(said[0], 'Update: switching to the latest installed version, '
                                'AresOS 30 (already downloaded). Restart to finish')
                            self.assertTrue(any('is not finished until the restart' in line for line in lines))
                    self.assertEqual(owner.image_reference(host.state['rpm']['deployments'][0]), target)
                    if already_first:
                        self.assertEqual(said, [])
                        self.assertEqual(host.changes, [])
                        self.assertFalse((store / (owner.OUTCOME + '.json')).exists())
                    else:
                        self.assertEqual(len(host.changes), 2)

    def test_real_shell_mask_and_finalizer_refusals_precede_announcement(self):
        def regular(root):
            path = root / 'units' / owner.FINALIZERS[0]
            path.unlink()
            path.write_text('[Service]\n')

        def elsewhere(root):
            path = root / 'units' / owner.FINALIZERS[1]
            path.unlink()
            os.symlink('/dev/zero', path)

        for kind, setup, refusal in (
                ('system updater', lambda root: (root / 'system-unmasked').write_text('uupd.timer\n'),
                 'STOP: updater uupd.timer is not masked'),
                ('user updater', lambda root: (root / 'user-unmasked').write_text('flatpak-update.timer\n'),
                 'STOP: user updater flatpak-update.timer is not masked'),
                ('finalizer file', regular, 'STOP: ' + owner.FINALIZERS[0] + ' is neither the image'),
                ('finalizer link', elsewhere, 'STOP: ' + owner.FINALIZERS[1] + ' is neither the image')):
            for retry in (False, True):
                with self.subTest(kind=kind, retry=retry), route(base.pair()) as (tools, host, store):
                    if retry:
                        interrupted_update(tools, host)
                    record = (store / (owner.OUTCOME + '.json'))
                    before = record.read_bytes() if record.exists() else None
                    host.check_setup = setup
                    with patch.object(tools, 'intend', wraps=tools.intend) as intend:
                        lines, said = self.call(tools, host, 'update', stop='Shared step failed: update-preflight')
                    self.assertEqual(said, [])
                    self.assertEqual(tools.said, [])
                    self.assertFalse(host.changes)
                    intend.assert_not_called()
                    self.assertEqual(record.read_bytes() if record.exists() else None, before)
                    self.assertEqual([t['script'] for t in host.trace if 'script' in t], ['update-preflight'])
                    self.assertIn(refusal, host.trace[-1]['stderr'])

    def test_readonly_refusals_before_announcements_and_failures_allowed_after(self):
        for kind in ('login', 'network', 'cosign', 'layout', 'busy', 'staged'):
            with self.subTest(kind=kind), route(base.staged_update() if kind == 'staged' else base.pair(),
                    login=kind != 'login') as (tools, host, store), contextlib.ExitStack() as stack:
                if kind == 'network':
                    stack.enter_context(patch.object(owner, 'validate_login', side_effect=owner.Stop(owner.LOGIN_REFUSAL)))
                if kind == 'cosign':
                    stack.enter_context(patch.object(owner.shutil, 'which', return_value=None))
                if kind == 'layout':
                    tools.save('layout-pending', dict(administrator=dict(boot='boot-1')))
                if kind == 'busy':
                    tools.processes = lambda: [dict(exe='/usr/bin/bootc', excluded_as_daemon=False)]
                with self.assertRaises(owner.Stop), contextlib.redirect_stdout(io.StringIO()):
                    tools.newest()
                self.assertEqual(tools.said, [])
                self.assertFalse(host.changes)
        for kind in ('signature', 'busy', 'changed'):
            with self.subTest(after=kind), route(base.pair(), signed={} if kind == 'signature' else None) as (tools, host, store):
                if kind == 'busy':
                    host.during_verify = lambda: setattr(tools, 'processes', lambda: [dict(exe='/usr/bin/bootc', excluded_as_daemon=False)])
                if kind == 'changed':
                    # Still valid and stageable, with a different retained list: the comparison's own refusal.
                    host.during_verify = lambda: setattr(host, 'state', base.returned())
                with self.assertRaises(owner.Stop) as caught, contextlib.redirect_stdout(io.StringIO()):
                    tools.newest()
                self.assertEqual(tools.said[0], INSTALL)
                if kind == 'changed':
                    self.assertEqual(str(caught.exception), 'Deployments changed during verification; nothing was staged; get help')
                self.assertFalse(host.changes)

    def test_guard_directly_and_after_each_update_preflight_only_through_newest(self):
        with route(base.returned(), base.H30) as (tools, host, store):
            _, shape, _ = tools.survey()
            with self.assertRaisesRegex(owner.Stop, GUARD):
                tools.newest_guard(shape)
            tools.chosen, tools.said = 'update', []
            with self.assertRaisesRegex(owner.Stop, GUARD), contextlib.redirect_stdout(io.StringIO()):
                tools.update(tools.announce_update)
            self.assertEqual(tools.said, [])
        for outer in (False, True):
            with self.subTest(newest=outer), route(base.pair()) as (tools, host, store):
                _, shape, _ = tools.survey()
                tools.newest_guard(shape)
                with patch.object(tools, 'newest_guard', wraps=tools.newest_guard) as guard, contextlib.redirect_stdout(io.StringIO()):
                    (tools.newest if outer else tools.update)()
                self.assertEqual(guard.call_count, 2 if outer else 0)

    def test_forward_preflights_and_complete_record_check_precede_announcement(self):
        for kind in ('layout', 'busy', 'disk', 'bls', 'modified'):
            with self.subTest(kind=kind), route(base.returned(), base.H30) as (tools, host, store), contextlib.ExitStack() as stack:
                if kind == 'layout':
                    tools.save('layout-pending', dict(administrator=dict(boot='boot-1')))
                elif kind == 'busy':
                    tools.processes = lambda: [dict(exe='/usr/bin/bootc', excluded_as_daemon=False)]
                elif kind == 'disk':
                    stack.enter_context(patch.object(owner, 'disk_record', side_effect=owner.Stop('Wrong target')))
                elif kind == 'bls':
                    stack.enter_context(patch.object(owner, 'validate_bls', side_effect=owner.Stop('Wrong BLS')))
                else:
                    host.state['rpm']['deployments'][0]['requested-packages'] = ['fixture-layer']
                self.call(tools, host, 'forward', stop='Layout trial' if kind == 'layout' else 'rpm-ostree/bootc/ostree client active'
                    if kind == 'busy' else 'Wrong target' if kind == 'disk' else 'Wrong BLS'
                    if kind == 'bls' else 'Modified AresOS')
                self.assertEqual(tools.said, [])
                self.assertFalse(host.changes)
        with route(base.pair()) as (tools, host, store):
            interrupted_update(tools, host, complete=True)
            state, shape, _ = tools.survey(retry='update')
            value = tools.load(owner.OUTCOME)
            value['reference'], value['digest'] = base.R30, base.R30.split('@')[1]
            tools.save(owner.OUTCOME, value)
            tools.said = []
            with patch.object(tools, 'survey', return_value=(state, shape, 'complete')), \
                    self.assertRaisesRegex(owner.Stop, 'another release'):
                tools.update(tools.announce_update)
            self.assertEqual(tools.said, [])

    def test_a_forward_step_may_refuse_after_the_announcement_when_the_list_changes(self):
        with route(base.returned(), base.H30) as (tools, host, store):
            original = tools.script
            def script(name, replacements=None):
                if name == 'start-next':
                    self.assertEqual(tools.said[0], FORWARD)
                    raise owner.Failed('fixture refused before change', owner.REFUSED_BEFORE_CHANGE)
                return original(name, replacements)
            with patch.object(tools, 'script', side_effect=script):
                self.call(tools, host, 'forward', first=FORWARD, stop='The deployment list changed outside the tools')
            self.assertFalse(host.changes)
            self.assertFalse((store / (owner.OUTCOME + '.json')).exists())

    def test_announcement_uses_inner_read_and_precedes_intent_and_first_change(self):
        for forward in (False, True):
            with self.subTest(forward=forward), route(base.returned() if forward else base.pair(), base.H30) as (tools, host, store):
                original, events = tools.intend, []
                def intend(*args, **kw):
                    events.append(list(tools.said))
                    self.assertTrue(tools.said[0].startswith('Update:'))
                    self.assertFalse(host.changes)
                    return original(*args, **kw)
                with patch.object(tools, 'intend', side_effect=intend):
                    self.call(tools, host, 'forward' if forward else 'update')
                self.assertEqual(len(events), 1)
        # Choose from an older running release, then the inner read sees stock running instead.
        with route(base.returned(), base.H30) as (tools, host, store):
            original, count = tools.survey, [0]
            def survey(*args, **kw):
                count[0] += 1
                if count[0] == 2:
                    host.state = base.machine([base.stock_row(True), base.release_row(base.R21), base.release_row(base.R13)])
                return original(*args, **kw)
            with patch.object(tools, 'survey', side_effect=survey):
                self.call(tools, host, 'forward', first='Update: switching from plain Bazzite to the latest installed version, '
                    'AresOS 21 (already downloaded). Restart to finish')

    def test_interrupted_mismatch_names_newest_only_for_newest(self):
        for outer in (False, True):
            with self.subTest(newest=outer), route(base.pair(), base.H30) as (tools, host, store):
                interrupted_update(tools, host)
                value = tools.load(owner.OUTCOME)
                value['before'][0][1] += 10
                tools.save(owner.OUTCOME, value)
                with self.assertRaises(owner.Stop) as caught:
                    (tools.newest if outer else tools.title)()
                self.assertIn('run ' + owner.typed('newest' if outer else 'update') + ' to continue it', str(caught.exception))

    def test_main_pass_and_stop_records_keep_chosen_said_and_single_survey_note(self):
        for stopped in (False, True):
            with self.subTest(stopped=stopped), route(base.returned(), base.H30) as (tools, host, store):
                journal(tools, host.state, 'forward', host.state['rpm']['deployments'][1])
                home = tools.payload.parent
                home.chmod(0o700)
                if stopped:
                    tools.processes = lambda: [dict(exe='/usr/bin/bootc', excluded_as_daemon=False)]
                output, stops = io.StringIO(), []
                with patch.object(owner.os, 'geteuid', return_value=0), patch.object(owner, 'HOME', home), \
                        patch.object(owner, '__file__', str(tools.payload / 'owner.py')), \
                        patch.object(owner, 'owner_lock', return_value=None), patch.object(owner, 'settle_tools'), \
                        patch.object(owner, 'private_tree'), base.common.private_metadata(home), patch.object(owner, 'Tools', return_value=tools), \
                        patch.object(owner, 'Host', return_value=host), patch.object(sys, 'argv', ['owner.py', 'newest']), \
                        patch.object(owner, 'refusal_record', side_effect=lambda host, value: stops.append(copy.deepcopy(value))), \
                        contextlib.redirect_stdout(output):
                    if stopped:
                        with self.assertRaises(owner.Stop):
                            owner.main()
                    else:
                        owner.main()
                if stopped:
                    record, = stops
                    self.assertEqual(record['status'], 'stopped')
                else:
                    record, = [json.loads(p.read_text()) for p in store.glob('*-newest.json')]
                    self.assertEqual(record['status'], 'passed')
                    self.assertIn('PASS newest\n', output.getvalue())
                self.assertEqual(record['chosen'], 'forward')
                self.assertEqual(record['said'], tools.said)
                self.assertEqual(output.getvalue().count('was not applied'), 1)
                if not stopped:
                    self.assertLess(output.getvalue().index('was not applied'), output.getvalue().index(FORWARD))
                    self.assertLess(output.getvalue().index(FORWARD), output.getvalue().index('PASS newest'))


if __name__ == '__main__':
    unittest.main()
