"""Package 22c, section A: the owner tools' rules, each pinned directly (brief B1, B4 to B7).

Shapes, the reorder script, the journal, staging and layout, over the modelled machine of
test_owner_update (imported as a library: nothing of that module runs here, so this module
runs on a machine that has the real rpm-ostree). The model over the whole state space (B2)
and the tools 2-to-3 compatibility tests (B8) are separate modules.

"Selection applied", "restart waiting" and "target boot confirmed" are three states here:
the list, the boot id, and a later boot that runs the target. No helper merges them.

One word per meaning (briefs/22c-forward-command.md): update stages the release of the tools
or changes nothing; forward selects the newest installed AresOS and never stages.
"""
import collections
import contextlib
import copy
import io
import inspect
import itertools
import json
import pathlib
import subprocess
import unittest
import time
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

import test_owner_update as base
from ways_back_keyboard import KeyboardMachine, PowerCut, PROFILES, identity, keyboard_sessions

owner, machine, route = base.owner, base.machine, base.route
R13, R21, R30, H21, H30 = base.R13, base.R21, base.R30, base.H21, base.H30
ROOT = base.ROOT
REFUSALS = (owner.Stop,)


def row(role, booted=False, staged=False):
    """A deployment by role: 'S' the pinned stock, otherwise a release reference."""
    return base.stock_row(booted) if role == 'S' else base.release_row(role, booted=booted, staged=staged)


def listed(order, running, staged=None):
    rows = [row(role, booted=role == running) for role in order]
    return machine(([row(staged, staged=True)] if staged else []) + rows)


def menu(state):
    """Boot entries as the probe captured them: the title carries the row's place, the file counts down."""
    rows = [d for d in state['rpm']['deployments'] if not d.get('staged')]
    return [dict(file='/boot/loader/entries/ostree-%d.conf' % (len(rows) - place),
                 content='title Bazzite (ostree:%d)\noptions quiet ostree=/ostree/boot.0/default/%s/%d\n' % (place, 'b' * 64, place),
                 title='Bazzite (ostree:%d)' % place, target='/sysroot/ostree/deploy/default/deploy/%s.%d' % (d['checksum'], d['serial']),
                 identity=[d['checksum'], d['serial'], d['osname']]) for place, d in enumerate(rows)]


@contextlib.contextmanager
def laptop(state, known=H21, **options):
    """Tools over the modelled machine, with boot entries as on the laptop."""
    with route(state, known, **options) as (tools, host, store):
        owner.resolved_bls.side_effect = lambda: menu(host.state)
        owner.disk_record.return_value.update(protected={}, partitions=[])
        tools.notes = []
        yield tools, host, store


def roles(host):
    names = {owner.BASE: 'S', R13.split('@')[1]: R13, R21.split('@')[1]: R21, R30.split('@')[1]: R30}
    rows = host.state['rpm']['deployments']
    return [names[d['container-image-reference-digest']] for d in rows], next(names[d['container-image-reference-digest']] for d in rows if d['booted'])


def restart(tools, host, choice=None, power_off=False):
    """A shutdown and a start: finalize keeps the new, pinned and booted rows (unless the power
    went first), then the first row runs, or the row chosen in the boot menu. A new boot id."""
    rows = copy.deepcopy(host.state['rpm']['deployments'])
    new = [d for d in rows if d.get('staged')]
    if new and not power_off:
        rows = [d for d in rows if d.get('staged') or d['pinned'] or d['booted']]
    else:
        rows = [d for d in rows if not d.get('staged')]
    for place, d in enumerate(rows):
        d.update(staged=False, booted=place == (choice or 0))
    host.state = machine(rows)
    tools.boot[0] = 'boot-%d' % (int(tools.boot[0].split('-')[1]) + 1)
    tools.notes = []


def journal(store):
    path = store / (owner.OUTCOME + '.json')
    return json.loads(path.read_text()) if path.exists() else None


def archived(store):
    return sorted(p.name.split('-outcome-')[1].removesuffix('.json') for p in store.glob('*-outcome-*.json'))


class Unchanged:
    def unchanged(self, host, method, message):
        """A refusal leaves the list, the pins and the changes as they were (judged by the machine's state)."""
        before, offset = copy.deepcopy(host.state), len(host.changes)
        with self.assertRaises(owner.Stop) as caught:
            method()
        self.assertIn(message, str(caught.exception))
        self.assertEqual((host.state, host.changes[offset:]), (before, []))


class ShapeTest(Unchanged, unittest.TestCase):
    """Rules 1 and 2: the set is fixed, its order and the running member are free."""

    def test_every_order_and_running_system_of_the_pair_and_the_triple_is_accepted(self):
        count = 0
        for members in ((R13, 'S'), (R21, R13, 'S')):
            for order in itertools.permutations(members):
                for running in members:
                    with self.subTest(order=order, running=running), laptop(listed(order, running)) as (tools, host, store):
                        lines = tools.title()
                        count += 1
                        self.assertEqual(lines[0].split(' runs')[0], owner.name(tools.shape, tools.shape['booted']))
                        if order[0] == running:
                            self.assertTrue(lines[0].endswith(' runs and starts next'))
                        else:
                            # No record: the facts, and no cause (rule 8).
                            self.assertTrue(lines[0].endswith('; this start was not the default'), lines[0])
                        self.assertIn('(ostree:0) ', lines[1])
                        self.assertEqual(lines[1].count(', starts next'), 1)
                        self.assertIn(', starts next; (ostree:1)', lines[1])
                        tools.reboot()
        self.assertEqual(count, 4 + 18)

    def test_the_names_are_roles_with_a_short_digest_and_the_row_map_follows_the_boot_entries(self):
        with laptop(listed((R13, 'S', R21), 'S')) as (tools, host, store):
            lines = tools.title()
            older, newer, stock = 'older AresOS ' + R13.split(':')[1][:12], 'newer AresOS ' + R21.split(':')[1][:12], 'plain Bazzite ' + owner.BASE.split(':')[1][:12]
            self.assertEqual(lines[:2], [stock + ' runs; ' + older + ' starts next; this start was not the default',
                'Boot menu at the next start: (ostree:0) ' + older + ', starts next; (ostree:1) ' + stock + '; (ostree:2) ' + newer])

    def test_version_2s_queued_pair_is_accepted_with_the_neutral_line(self):
        with laptop(listed(('S', R13), R13)) as (tools, host, store):
            self.assertTrue(host.state['bootc']['status']['rollbackQueued'])
            self.assertTrue(tools.title()[0].endswith('plain Bazzite ' + owner.BASE.split(':')[1][:12] + ' starts next; this start was not the default'))

    def test_wrong_sets_keep_refusing(self):
        extra = dict(base.stock_row(), serial=9, pinned=False)
        cases = {
            'third AresOS without a stage': (listed((R30, R21, R13, 'S'), R30), H30),
            'unknown release': (listed((base.R99, R13, 'S'), base.R99), H21),
            'foreign deployment': (machine([row(R21, True), row(R13), row('S'), extra]), H21),
            'pinned release': (machine([row(R21, True), dict(row(R13), pinned=True), row('S')]), H21),
            'unpinned stock': (machine([row(R21, True), row(R13), dict(row('S'), pinned=False)]), H21),
            'same release twice': (machine([row(R21, True), base.release_row(R21, checksum='d2' * 32), row('S')]), H21),
            'staged is not the target': (listed((R13, 'S'), R13, staged=R21), H30),
            'staged over a running system that is not first': (machine([row(R30, staged=True), row(R13), row(R21, True), row('S')]), H30),
            'two staged rows': (machine([row(R30, staged=True), row(R21, staged=True), row(R13, True), row('S')]), H30),
        }
        slots = listed((R21, R13, 'S'), R21)
        slots['bootc']['status']['rollbackQueued'] = True
        cases['bootc contradicts the order'] = (slots, H21)
        for name, (state, known) in cases.items():
            with self.subTest(name=name), laptop(state, known) as (tools, host, store):
                for method in (tools.title, tools.reboot, tools.update, tools.forward, tools.previous, tools.recover):
                    self.unchanged(host, method, '')

    def test_a_staged_row_on_running_stock_beside_aresos_says_rule_10_from_every_command(self):
        foreign = dict(base.stock_row(), checksum='f0' * 32, serial=0, pinned=False, staged=True,
                       **{'container-image-reference-digest': 'sha256:' + 'f1' * 32})
        for order in itertools.permutations((R21, R13, 'S')):
            for new in (foreign, row(R30, staged=True)):  # also when the staged row is the bundle's target
                state = machine([new, *[row(role, booted=role == 'S') for role in order]])
                with self.subTest(order=order, digest=new['container-image-reference-digest'][:12]), laptop(state, H30) as (tools, host, store):
                    for method in (tools.title, tools.check, tools.records, tools.reboot, tools.update, tools.forward,
                                   tools.previous, tools.recover, tools.login, tools.verify, tools.switch, tools.prepare,
                                   lambda: tools.recover(True), lambda: tools.layout('begin', 'us'), lambda: tools.layout('abandon')):
                        self.unchanged(host, method, 'A Bazzite update is waiting. Do not restart: the restart deletes both AresOS releases. Get help.')
        with laptop(machine([foreign, row(R13), row('S', True)])) as (tools, host, store):
            self.unchanged(host, tools.title, 'the restart deletes the installed AresOS')

    def test_before_the_first_switch_nothing_changes_and_rule_10_does_not_speak(self):
        saved = base.prepared()
        stock = saved['state']['rpm']['deployments']
        first = machine([row(R21, staged=True), *stock])
        owner.qualified_state(saved['state'], saved, R21, [R13, R21])
        self.assertIsNone(owner.qualified_state(first, saved, R21, [R13, R21]))
        foreign = machine([dict(copy.deepcopy(stock[0]), checksum='f0' * 32, booted=False, pinned=False, staged=True), *stock])
        with self.assertRaisesRegex(owner.Stop, 'Unexpected prepared deployment list/pending state'):
            owner.qualified_state(foreign, saved, R21, [R13, R21])
        with self.assertRaisesRegex(owner.Stop, 'Unexpected staged switch'):
            owner.qualified_state(machine([row(R13, staged=True), *stock]), saved, R21, [R13, R21])
        with laptop(saved['state']) as (tools, host, store):
            for method in (tools.update, tools.forward, tools.previous, tools.recover, lambda: tools.recover(True)):
                self.unchanged(host, method, '')
            self.assertEqual(tools.title()[0], 'stock ' + ' '.join(map(str, saved['stock_identity'])))

    def test_stock_updaters_warn_in_title_stop_keep_stock_and_never_block_the_way_off(self):
        with laptop(listed((R21, R13, 'S'), 'S')) as (tools, host, store):
            tools.paused.side_effect = owner.Stop('OS updater timer is not persistently disabled: uupd.timer')
            warning, = [line for line in tools.title() if line.startswith('WARNING: ')]
            self.assertIn('uupd.timer', warning)
            self.assertIn('run sudo /var/lib/ares/at forward to go back to AresOS, then get help', warning)
            self.unchanged(host, lambda: tools.recover(True), 'uupd.timer; nothing changed. Bazzite must not update while AresOS is '
                           'installed: run sudo /var/lib/ares/at forward to go back to AresOS, then get help')
            tools.reboot()
            self.assertEqual(tools.forward()[:2], ['Newer AresOS ' + R21.split(':')[1][:12] + ' already starts next; nothing changed',
                                                   'It does not run yet: it starts at the next restart'])
        # The way off is a real change too: forward reorders on stock while its updaters are on.
        with laptop(listed(('S', R21, R13), 'S')) as (tools, host, store):
            tools.paused.side_effect = owner.Stop('OS updater timer is not persistently disabled: uupd.timer')
            lines = tools.forward()
            self.assertEqual((lines[0], roles(host)), ('Newest installed AresOS starts next ' + R21, ([R21, 'S', R13], 'S')))
            self.assertTrue(any(line.startswith('WARNING: ') for line in lines))

    def test_install_survey_leaves_prepared_and_first_switch_checks_in_charge(self):
        saved = base.prepared()
        stock = saved['state']['rpm']['deployments']
        foreign = dict(copy.deepcopy(stock[0]), checksum='f0' * 32, booted=False, pinned=False, staged=True)
        for state in (saved['state'], machine([row(R21, staged=True), *stock]), machine([foreign, *stock])):
            with self.subTest(state=state), laptop(state) as (tools, host, store), patch.object(owner, 'account'):
                prepared = dict(saved, bls=menu(saved['state']))
                tools.save('prepared', prepared)
                with patch.object(tools, 'qualified', side_effect=AssertionError('Installed survey reached a pre-install state')):
                    if state == saved['state']:
                        self.assertEqual(tools.before_switch(), state)
                    else:
                        for method in (tools.login, tools.verify, tools.switch):
                            self.unchanged(host, method, 'Stock list/pin/pending/BLS changed before switch')
                    tools.survey_installed(state, prepared)
                self.assertEqual(host.changes, [])

    def test_one_helper_spells_every_command_as_commands_json_does(self):
        commands = json.loads((ROOT / 'os/owner-tools/commands.json').read_text())
        for name, text in commands.items():
            if name == 'install':
                continue
            words = ['layout', {'us': 'begin us', 'intl': 'begin us-intl', 'de': 'begin de'}.get(name[7:], name[7:])] if name.startswith('layout-') else [name]
            self.assertEqual(text.removeprefix('sudo -k; '), owner.typed(*' '.join(words).split()))
        source = (ROOT / 'os/owner-tools/owner.py').read_text()
        # No message spells a command by hand: the entry's path is quoted once, in the helper.
        self.assertEqual((source.count("'/var/lib/ares/at'"), source.count('sudo /var/lib/ares/at')), (1, 0))


class ScriptTest(unittest.TestCase):
    """B4: start-next.sh against a modelled list."""

    TARGET = dict(checksum='a' * 64, serial=1, booted=False, pinned=True,
                  **{'container-image-reference-digest': 'sha256:' + 'b' * 64, 'container-image-reference': 'ostree-image-signed:docker://example/stock:stable'})

    def run_script(self, rows, after=None, fails=False, expected=None):
        source = (ROOT / 'os/release/start-next.sh').read_text().split("<<'START_NEXT'\n", 1)[1].rsplit('\nSTART_NEXT', 1)[0]
        for name, value in (('CHECKSUM', 'a' * 64), ('SERIAL', '1'), ('DIGEST', 'sha256:' + 'b' * 64),
                            ('REFERENCE', 'ostree-image-signed:docker://example/stock:stable'),
                            ('BEFORE', json.dumps(rows if expected is None else expected).encode().hex())):
            source = source.replace('@' + name + '@', value)
        self.assertNotIn('@', source.replace('ostree-image-signed:docker://example', ''))
        model, self.calls = dict(rows=copy.deepcopy(rows)), []
        def read(argv, **kw):
            self.calls.append('read')
            return json.dumps(dict(deployments=model['rows']))
        def run(argv, **kw):
            self.assertEqual(kw, {'check': True})
            self.calls.append(' '.join(argv))
            if argv[0] == 'ostree':
                if fails:
                    raise subprocess.CalledProcessError(1, argv)
                index = int(argv[3])
                model['rows'] = after if after is not None else [model['rows'][index], *[r for i, r in enumerate(model['rows']) if i != index]]
        self.stderr = io.StringIO()
        with patch('subprocess.check_output', side_effect=read), patch('subprocess.run', side_effect=run), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(self.stderr):
            exec(compile(source, 'start-next.sh', 'exec'), {})

    def refused(self, rows, expected=None):
        """A refusal before any change: exit status 3 (review 2), one read, no ostree call."""
        with self.assertRaises(SystemExit) as caught:
            self.run_script(rows, expected=expected)
        self.assertEqual(caught.exception.code, owner.REFUSED_BEFORE_CHANGE)
        self.assertEqual(self.calls, ['read'])
        self.assertTrue(self.stderr.getvalue().startswith('STOP: '), self.stderr.getvalue())
        self.assertTrue(self.stderr.getvalue().endswith('; nothing was changed\n'), self.stderr.getvalue())
        return self.stderr.getvalue()

    def others(self):
        return [dict(self.TARGET, checksum='c' * 64, serial=0, pinned=False, booted=True), dict(self.TARGET, checksum='d' * 64, serial=0, pinned=False)]

    def test_reads_immediately_before_one_set_default_syncs_and_checks_the_result(self):
        for index in (1, 2):
            rows = self.others()
            rows.insert(index, self.TARGET)
            with self.subTest(index=index):
                self.run_script(rows)
                self.assertEqual(self.calls, ['read', 'ostree admin set-default %d' % index, 'sync', 'read'])

    def test_a_wrong_list_makes_no_ostree_call(self):
        a, b = self.others()
        cases = {'missing': [a, b], 'doubled': [a, self.TARGET, self.TARGET], 'other serial': [a, dict(self.TARGET, serial=2), b],
                 'other checksum': [a, dict(self.TARGET, checksum='e' * 64), b],
                 'other digest': [a, dict(self.TARGET, **{'container-image-reference-digest': 'sha256:' + 'e' * 64}), b],
                 'other reference': [a, dict(self.TARGET, **{'container-image-reference': 'ostree-image-signed:docker://example/other:stable'}), b],
                 'staged row': [dict(b, staged=True), a, self.TARGET], 'already first': [self.TARGET, a, b]}
        for name, rows in cases.items():
            with self.subTest(name=name):
                self.refused(rows)

    def test_fresh_read_must_equal_the_callers_snapshot_before_any_mutation(self):
        a, b = self.others()
        expected = [a, b, self.TARGET]
        cases = ([b, a, self.TARGET], [a, dict(b, pinned=True), self.TARGET],
                 [a, dict(b, serial=9), self.TARGET], [dict(a, booted=False), dict(b, booted=True), self.TARGET],
                 [dict(a, **{'requested-packages': ['outside-change']}), b, self.TARGET])
        for rows in cases:
            with self.subTest(rows=rows):
                self.assertIn('changed outside the tools', self.refused(rows, expected=expected))

    def test_removing_snapshot_guard_fails_the_outside_writer_regression(self):
        real = pathlib.Path.read_text
        def without_snapshot(path, *args, **kwargs):
            text = real(path, *args, **kwargs)
            if path.name == 'start-next.sh':
                before = ("if before != json.loads(bytes.fromhex('@BEFORE@')):\n"
                          "    refuse('deployment list changed outside the tools since the intent')")
                self.assertEqual(text.count(before), 1)
                return text.replace(before, 'pass')
            return text
        result = unittest.TestResult()
        with patch.object(pathlib.Path, 'read_text', without_snapshot):
            DestinationTest('test_outside_reorder_before_the_script_closes_the_intent_and_every_way_back_works').run(result)
        self.assertEqual(result.errors, [])
        # One failure per boot choice of the regression, each where the owner's reorder ran anyway.
        self.assertEqual(len(result.failures), 4)
        for _, failure in result.failures:
            self.assertIn('ostree admin set-default 2', failure)

    def test_the_host_reports_a_steps_own_exit_status(self):
        """owner.Host.script: a non-zero exit status travels with the STOP (Failed.code), so that
        start_next can tell the script's refusal before any change from every other failure."""
        class Ended:
            def __init__(self, reason, code):
                self.reason, self.process, self.stdout = reason, SimpleNamespace(returncode=code), ''
            def wait(self, timeout):
                return self.reason
            def stop(self):
                return True
            def record(self, *unused):
                return {}
        host = owner.Host()
        for reason, code, kind in (('failed', owner.REFUSED_BEFORE_CHANGE, owner.Failed), ('failed', 1, owner.Failed),
                                   ('failed', -9, owner.Failed), ('failed', 0, owner.Stop), ('timed out', None, owner.Stop)):
            with self.subTest(reason=reason, code=code), patch.object(host, 'start', lambda text, name: Ended(reason, code)), \
                    self.assertRaises(owner.Stop) as caught:
                host.script('', 'start-next')
            self.assertIs(type(caught.exception), kind)
            if kind is owner.Failed:
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(str(caught.exception), 'Shared step failed: start-next; preserve diagnostics and do not reboot')

    def test_a_wrong_list_afterwards_or_a_failed_call_fails(self):
        a, b = self.others()
        for name, after in (('appended', [a, b, self.TARGET]), ('others swapped', [self.TARGET, b, a]),
                            ('pin lost', [dict(self.TARGET, pinned=False), a, b]), ('row gone', [self.TARGET, a])):
            with self.subTest(name=name), self.assertRaises(AssertionError):
                self.run_script([a, b, self.TARGET], after=after)
            self.assertEqual(self.calls[-2:], ['sync', 'read'])
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_script([a, b, self.TARGET], fails=True)
        self.assertEqual(self.calls, ['read', 'ostree admin set-default 2'])


class DestinationTest(Unchanged, unittest.TestCase):
    """Rules 3 and 4: each word names a destination, reached by the one reorder."""

    def test_each_word_moves_only_its_target_to_the_front_from_every_order_and_system(self):
        words = {'forward': R21, 'previous': R13, 'stock': 'S'}
        for order in itertools.permutations((R21, R13, 'S')):
            for running in order:
                for word, target in words.items():
                    with self.subTest(order=order, running=running, word=word), laptop(listed(order, running)) as (tools, host, store):
                        before = copy.deepcopy(host.state['rpm']['deployments'])
                        method = {'forward': tools.forward, 'previous': tools.previous,
                                  'stock': lambda: tools.recover(keep=running == 'S')}[word]
                        lines = method()
                        if order[0] == target:
                            self.assertEqual((host.changes, journal(store)), ([], None))
                            self.assertIn('already starts next; nothing changed', lines[0])
                            self.assertEqual(lines[1], 'It runs now' if running == target else 'It does not run yet: it starts at the next restart')
                            continue
                        self.assertEqual(host.changes, ['ostree admin set-default %d' % order.index(target), 'sync'])
                        self.assertEqual(roles(host), ([target, *[r for r in order if r != target]], running))
                        # Nothing created, removed, pinned or unpinned: the same rows, reordered.
                        self.assertEqual(sorted(before, key=owner.key), sorted(host.state['rpm']['deployments'], key=owner.key))
                        value = journal(store)
                        self.assertEqual((value['schema'], value['mode'], value['status'], value['boot']), ('change1', 'reorder', 'recorded', 'boot-1'))
                        self.assertEqual(value['word'], {'stock': 'keep-stock' if running == 'S' else 'rollback'}.get(word, word))
                        self.assertEqual(tools.load('title')['state'], host.state)

    def test_outside_reorder_before_the_script_closes_the_intent_and_every_way_back_works(self):
        """Review 2, finding 1: rollback journals [R27*, R13, S] -> [S, R27*, R13]; an outside writer
        makes the list [R13, R27*, S] before the script reads it. The script refuses before
        set-default, which is certain, so the intent is closed. Then every command surveys the list
        as it is: at once, and after a restart on each boot choice."""
        drifted = listed((R13, R21, 'S'), R21)
        for choice in (None, 0, 1, 2):  # no restart yet; then a start of each row of the drifted list
            with self.subTest(choice=choice), laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
                original = copy.deepcopy(host.state['rpm']['deployments'])
                script = host.script
                def drift(text, name, mutation=True):
                    self.assertEqual(name, 'start-next')
                    self.assertEqual(journal(store)['before'], [list(owner.key(r)) for r in original])
                    host.state = copy.deepcopy(drifted)
                    return script(text, name, mutation)
                with patch.object(host, 'script', drift), self.assertRaises(owner.Stop) as caught:
                    tools.recover()
                self.assertEqual(host.changes, [])
                self.assertEqual(host.state, drifted)
                self.assertIsNone(journal(store), 'the refused intent is still open')
                self.assertEqual(archived(store), ['refused-before-change'])
                self.assertEqual(str(caught.exception), 'The deployment list changed outside the tools before the rollback to '
                    + owner.image_reference(row('S')) + '; nothing was changed and the change is closed; '
                    'run sudo /var/lib/ares/at check to see what runs and what starts next')
                if choice is not None:
                    restart(tools, host, choice)
                order, running = roles(host)
                lines = tools.title()
                self.assertEqual(tools.notes, [])  # nothing is left to resolve
                self.assertEqual(lines[0].endswith(' runs and starts next'), running == R13)
                tools.reboot()
                # Every destination is one command away, each from the same state.
                for destination, method in (('S', lambda: tools.recover(running == 'S')), (R13, tools.previous), (R21, tools.forward)):
                    kept = (copy.deepcopy(host.state), {q.name: q.read_bytes() for q in store.iterdir()})
                    method()
                    self.assertEqual(roles(host), ([destination, *[r for r in order if r != destination]], running))
                    host.state = kept[0]
                    for q in store.iterdir():
                        q.unlink()
                    for name, raw in kept[1].items():
                        (store / name).write_bytes(raw)
                # Recovery: the refused change typed again goes through, and its own target's start confirms it.
                tools.recover(running == 'S')
                self.assertEqual(roles(host), (['S', *[r for r in order if r != 'S']], running))
                restart(tools, host)
                self.assertEqual(roles(host)[1], 'S')
                self.assertTrue(any(line.endswith(' confirmed after the restart') for line in tools.title()))
                self.assertEqual(archived(store), ['confirmed', 'refused-before-change'])

    def test_a_script_failure_that_may_follow_the_change_keeps_the_intent_open(self):
        """Only exit status 3 closes the intent. Every other failure of the script (set-default,
        sync, the postcondition, a kill) may follow the change: the journal stays open, and rule 5
        resolves it from the list at the next command."""
        for made, code in ((True, 1), (False, 1), (True, -9), (False, owner.REFUSED_BEFORE_CHANGE + 1)):
            with self.subTest(made=made, code=code), laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
                def failing(text, name, mutation=True):
                    self.assertEqual(name, 'start-next')
                    if made:
                        host.state = listed(('S', R21, R13), R21)  # set-default ran; what failed came after it
                    raise owner.Failed('Shared step failed: start-next; preserve diagnostics and do not reboot', code)
                with patch.object(host, 'script', failing), self.assertRaises(owner.Stop) as caught:
                    tools.recover()
                self.assertEqual(archived(store), [])
                self.assertEqual(journal(store)['status'], 'intent')
                self.assertEqual((type(caught.exception), caught.exception.code), (owner.Failed, code))  # the step's STOP, unchanged
                tools.title()
                if made:
                    self.assertIn('had made its change; it is recorded now', tools.notes[0])
                    self.assertEqual((journal(store)['status'], archived(store)), ('recorded', []))
                else:
                    self.assertIn('was not applied', tools.notes[0])
                    self.assertEqual((journal(store), archived(store)), (None, ['not-applied']))

    def test_rollback_and_keep_stock_keep_their_sides_and_name_the_other_word(self):
        with laptop(listed((R21, R13, 'S'), 'S')) as (tools, host, store):
            self.unchanged(host, tools.recover, 'use sudo /var/lib/ares/at keep-stock (rollback is for a running AresOS); nothing changed')
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            self.unchanged(host, lambda: tools.recover(True), 'use sudo /var/lib/ares/at rollback (keep-stock is for running plain Bazzite); nothing changed')
            self.assertEqual(tools.recover()[0], 'Saved stock rollback queued')
        with laptop(listed((R13, 'S'), R13)) as (tools, host, store):
            self.unchanged(host, tools.previous, 'Only one AresOS is installed')

    def test_update_never_selects_an_installed_system(self):
        """One word per meaning: update stages the release of the tools, or changes nothing. Every
        order and running system of the pair and the triple, with that release installed (R21) and
        not installed (R30). Judged by the machine's state before and after."""
        seen = collections.Counter()
        for members in ((R21, 'S'), (R21, R13, 'S')):
            for order in itertools.permutations(members):
                for running in members:
                    for known in (H21, H30):
                        release = known[-1]['reference']
                        with self.subTest(order=order, running=running, release=release[-4:]), \
                                laptop(listed(order, running), known) as (tools, host, store):
                            before = copy.deepcopy(host.state)
                            if release not in order and running != 'S' and order[0] == running:
                                # Rule 6, as before: the only state where update changes anything.
                                seen['stages'] += 1
                                self.assertEqual(tools.update()[0], 'Signed exact release staged ' + release)
                                self.assertEqual(host.changes, ['bootc switch --retain ' + release])
                                self.assertEqual((journal(store)['word'], journal(store)['mode']), ('update', 'staging'))
                                self.assertEqual(roles(host), ([release, *order], running))
                            elif order[0] == running == release:
                                seen['nothing to do'] += 1
                                lines = tools.update()
                                label = owner.name(tools.shape, tools.shape['booted'])
                                self.assertEqual(lines, [label[0].upper() + label[1:] + ' already starts next; nothing changed', 'It runs now'])
                            else:
                                # Nothing to install here, or no staging from here: the refusal names forward.
                                message = owner.RELEASE_INSTALLED if release in order else owner.FORWARD_FIRST
                                seen['names forward: ' + ('installed' if release in order else 'not from here')] += 1
                                self.unchanged(host, tools.update, message)
                                self.assertIn('run sudo /var/lib/ares/at forward (it makes the newest installed AresOS the next start', message)
                                self.assertTrue(message.endswith('; nothing changed'))
                            if not host.changes:
                                self.assertEqual((host.state, journal(store), archived(store)), (before, None, []))
                            # Never a reorder: no set-default, and the installed rows are as before, in their order.
                            self.assertFalse([c for c in host.changes if c == 'sync' or c.startswith('ostree admin')])
                            self.assertEqual([d for d in host.state['rpm']['deployments'] if not d.get('staged')], before['rpm']['deployments'])
        self.assertEqual(seen, {'stages': 5, 'nothing to do': 3, 'names forward: installed': 19, 'names forward: not from here': 17})

    def test_forward_selects_the_newest_installed_aresos_from_anywhere_and_never_stages(self):
        """From plain Bazzite, the older AresOS and a start chosen in the boot menu, whether or not
        the release of the tools is installed: no login, no network, no signature check, no new or
        removed deployment. Judged by the machine's state before and after."""
        count = 0
        for members in ((R13, 'S'), (R21, R13, 'S')):
            newest = members[0]
            for order in itertools.permutations(members):
                for running in members:
                    for known in (H21, H30):
                        with self.subTest(order=order, running=running, release=known[-1]['reference'][-4:]), \
                                laptop(listed(order, running), known, login=False, signed={}) as (tools, host, store):
                            before = copy.deepcopy(host.state['rpm']['deployments'])
                            lines = tools.forward()
                            count += 1
                            self.assertFalse(any(t.get('script') in ('verify', 'update') for t in host.trace))
                            tools.validated.assert_not_called()
                            # The same deployments with the same flags and pins: nothing staged, created or removed.
                            self.assertEqual(sorted(before, key=owner.key), sorted(host.state['rpm']['deployments'], key=owner.key))
                            self.assertEqual(roles(host), ([newest, *[r for r in order if r != newest]], running))
                            self.assertFalse(any('at update' in line for line in lines), lines)  # it never sends him on to an update
                            if order[0] == newest:
                                self.assertEqual((host.changes, journal(store)), ([], None))
                                self.assertIn('already starts next; nothing changed', lines[0])
                                self.assertEqual(lines[1], 'It runs now' if running == newest else 'It does not run yet: it starts at the next restart')
                                continue
                            self.assertEqual(host.changes, ['ostree admin set-default %d' % order.index(newest), 'sync'])
                            self.assertEqual(lines[0], 'Newest installed AresOS starts next ' + newest)
                            value = journal(store)
                            self.assertEqual((value['schema'], value['mode'], value['word'], value['status']), ('change1', 'reorder', 'forward', 'recorded'))
        self.assertEqual(count, 2 * (4 + 18))

    def test_forward_never_touches_a_staged_update_or_continues_an_interrupted_one(self):
        with laptop(listed((R21, R13, 'S'), R21), H30) as (tools, host, store):
            tools.update()
            self.assertEqual(roles(host)[0][0], R30)
            self.unchanged(host, tools.forward, 'The update to ' + R30 + ' waits for the restart: restart first')
            self.assertEqual(journal(store)['word'], 'update')
        with laptop(listed((R21, R13, 'S'), R21), H30) as (tools, host, store):
            host.interrupt = ('update', 'observe')  # staged; the status read after it fails, so only the intent is written
            with self.assertRaises(OSError):
                tools.update()
            self.assertEqual((journal(store)['status'], roles(host)[0][0]), ('intent', R30))
            self.unchanged(host, tools.forward, 'run sudo /var/lib/ares/at update to continue it')
            self.assertEqual(journal(store)['status'], 'intent')
            self.assertEqual(tools.update()[0], 'Interrupted update recorded: ' + R30)

    def test_where_update_named_forward_forward_then_update_installs_the_release(self):
        """What moved from update to forward (the old reordering update with a newer bundle): update
        refuses with nothing changed; forward selects the newest installed AresOS and says nothing of
        an update; once that AresOS runs and starts next, update stages the release of the tools."""
        for order, running in (((R21, R13, 'S'), 'S'), ((R13, R21, 'S'), R21), (('S', R13, R21), R13)):
            with self.subTest(order=order, running=running), laptop(listed(order, running), H30) as (tools, host, store):
                self.unchanged(host, tools.update, owner.FORWARD_FIRST)
                lines = tools.forward()
                self.assertEqual(roles(host)[0][0], R21)
                self.assertNotIn('bootc switch --retain ' + R30, host.changes)
                self.assertFalse(any(R30 in line or 'newer still' in line for line in lines), lines)
                if running != R21:
                    self.unchanged(host, tools.update, 'restart first' if order[0] != R21 else owner.FORWARD_FIRST)
                    restart(tools, host)
                self.assertEqual(roles(host)[1], R21)
                self.assertEqual(tools.update()[0], 'Signed exact release staged ' + R30)

    def test_from_the_older_aresos_with_a_newer_bundle_each_installed_system_is_one_command_away(self):
        """B2 at its original strength, in the state of briefs/22c-b2-destination-invariant.md:
        [R13*, R21, S] with a bundle for R30. update stages R30 there (rule 6, unchanged); the newer
        installed AresOS is one command away again, with no boot-menu step."""
        for word, target in (('update', R30), ('forward', R21), ('rollback', 'S')):
            with self.subTest(word=word), laptop(listed((R13, R21, 'S'), R13), H30) as (tools, host, store):
                {'update': tools.update, 'forward': tools.forward, 'rollback': tools.recover}[word]()
                self.assertEqual(roles(host), ([target, *[r for r in (R13, R21, 'S') if r != target]], R13))
                self.assertEqual(bool(host.state['rpm']['deployments'][0].get('staged')), word == 'update')
                self.assertEqual(len(host.state['rpm']['deployments']), 4 if word == 'update' else 3)

    def test_login_refuses_where_update_would_refuse_or_has_nothing_to_install(self):
        for order, running, known, message in (((R13, R21, 'S'), R13, H21, owner.RELEASE_INSTALLED),
                                               ((R21, R13, 'S'), 'S', H21, 'Stock list/pin/pending/BLS changed before switch'),
                                               ((R21, R13, 'S'), R21, H21, owner.RELEASE_RUNS),
                                               (('S', R21, R13), R21, H30, owner.FORWARD_FIRST),
                                               ((R21, R13, 'S'), R13, H30, owner.FORWARD_FIRST)):
            with self.subTest(order=order, running=running, release=known[-1]['reference'][-4:]), \
                    laptop(listed(order, running), known) as (tools, host, store), patch.object(owner, 'account'):
                self.unchanged(host, tools.login, message)
                self.assertEqual((journal(store), archived(store)), (None, []))
        self.assertIn('needs no login', owner.RELEASE_RUNS)
        self.assertIn('sudo /var/lib/ares/at forward', owner.RELEASE_INSTALLED)

    def test_a_modified_aresos_a_trial_a_client_or_a_missing_boot_entry_refuse_every_reorder(self):
        modified = machine([dict(row(R21, True), **{'requested-packages': ['x']}), row(R13), row('S')])
        with laptop(modified) as (tools, host, store):
            for method in (tools.previous, tools.recover):
                self.unchanged(host, method, 'Modified AresOS')
            tools.title()
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            tools.save('layout-pending', {})
            self.unchanged(host, tools.previous, 'Layout trial is unfinished')
            (store / 'layout-pending.json').unlink()
            tools.processes = lambda: [dict(exe='/usr/bin/ostree', excluded_as_daemon=False)]
            self.unchanged(host, tools.recover, 'client active')
            tools.processes = lambda: []
            owner.resolved_bls.side_effect = lambda: menu(host.state)[:2]
            self.unchanged(host, tools.previous, 'Whole BLS/deployment identity list differs')
            self.assertIsNone(journal(store))


class JournalTest(Unchanged, unittest.TestCase):
    """Rule 5: the deployment list decides; applied, waiting and confirmed are three states."""

    def test_waits_for_the_restart_then_confirmed_by_a_later_boot_that_runs_the_target(self):
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            tools.recover()
            lines = tools.title()
            self.assertTrue(lines[0].endswith(' starts next, after the restart'), lines[0])
            self.assertIn('Rollback to ' + owner.image_reference(row('S')) + ' is not finished until the restart', lines)
            self.assertFalse(any('confirmed' in line for line in lines))
            tools.reboot()
            # A second change refuses: restart first. The destination already first changes nothing.
            for method in (tools.previous, tools.forward, lambda: tools.layout('begin', 'us')):
                self.unchanged(host, method, 'waits for the restart: restart first')
            # update has nothing to install here and selects nothing: it names forward.
            self.unchanged(host, tools.update, owner.RELEASE_INSTALLED)
            self.assertIn('already starts next; nothing changed', tools.recover()[0])
            restart(tools, host)
            lines = tools.title()
            self.assertIn('Rollback to ' + owner.image_reference(row('S')) + ' confirmed after the restart', lines)
            self.assertEqual((journal(store), archived(store)), (None, ['confirmed']))
            self.assertFalse(any('confirmed' in line for line in tools.title()))

    def test_applied_nothing_waits_is_its_own_outcome_and_the_next_start_decides(self):
        for choice, word in ((None, 'done'), (1, 'elsewhere')):
            with self.subTest(next_start=word), laptop(listed((R21, R13, 'S'), 'S')) as (tools, host, store):
                # Stock was taken in the boot menu; keep-stock makes it the default while it runs.
                self.assertEqual(tools.recover(True)[0], 'Saved stock is default')
                lines = tools.title()
                self.assertTrue(lines[0].endswith(' runs and now starts next; no restart is waiting'), lines[0])
                self.assertFalse(any('confirmed' in line or 'not finished' in line for line in lines))
                self.assertEqual(journal(store)['status'], 'recorded')
                tools.reboot()
                if choice is None:
                    restart(tools, host)
                    self.assertTrue(any(line.endswith('confirmed after the restart') for line in tools.title()))
                    self.assertEqual(archived(store), ['confirmed'])
                    continue
                # Every command works at once; a new change archives the record under its state.
                tools.previous()
                self.assertEqual(archived(store), ['applied-not-restarted'])
                self.assertEqual(roles(host), ([R13, 'S', R21], 'S'))

    def test_in_place_not_yet_started_blocks_nothing_and_never_says_failed(self):
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            tools.previous()
            restart(tools, host, choice=1)  # the R21 row, taken in the boot menu
            self.assertEqual(roles(host), ([R13, R21, 'S'], R21))
            for attempt in range(2):
                lines = tools.title()
                self.assertTrue(lines[0].endswith('; this start was not the default'))
                self.assertIn('Return to ' + R13 + ' is in place and has not started yet', lines)
                self.assertFalse(any('fail' in line.lower() or 'confirmed' in line for line in lines))
            self.assertEqual(journal(store)['status'], 'recorded')
            tools.reboot()
            # A later start of the target confirms it, with no command typed in between.
            restart(tools, host, choice=2)
            self.assertFalse(any('confirmed' in line for line in tools.title()))
            restart(tools, host)
            self.assertIn('Return to ' + R13 + ' confirmed after the restart', tools.title())

    def test_a_new_change_supersedes_an_in_place_record_and_forward_works_at_once(self):
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            tools.previous()
            restart(tools, host, choice=1)
            self.assertEqual(tools.forward()[0], 'Newest installed AresOS starts next ' + R21)
            self.assertEqual(archived(store), ['in-place-not-started'])
            self.assertTrue(tools.title()[0].endswith(' runs and now starts next; no restart is waiting'))
            restart(tools, host)
            self.assertIn('Forward to ' + R21 + ' confirmed after the restart', tools.title())

    def test_forward_keeps_applied_waiting_and_confirmed_apart(self):
        """Forward's three states, as every reorder has them: from a system that is not its target
        the selection is applied and a restart waits; on its target (taken in the boot menu) it is
        applied and nothing waits; only a later boot that runs the target confirms."""
        reference = 'Forward to ' + R21
        for running, choice in itertools.product(('S', R13, R21), (0, 1)):
            with self.subTest(running=running, next_start=choice), laptop(listed((R13, R21, 'S'), running)) as (tools, host, store):
                self.assertEqual(tools.forward()[0], 'Newest installed AresOS starts next ' + R21)
                self.assertEqual((journal(store)['status'], journal(store)['boot'], archived(store)), ('recorded', 'boot-1', []))
                lines = tools.title()
                self.assertFalse(any('confirmed' in line for line in lines), lines)
                if running == R21:
                    self.assertTrue(lines[0].endswith(' runs and now starts next; no restart is waiting'), lines[0])
                    self.assertFalse(any('not finished' in line for line in lines), lines)
                    tools.previous()  # every command works at once
                    self.assertEqual(archived(store), ['applied-not-restarted'])
                    continue
                self.assertTrue(lines[0].endswith('newer AresOS ' + R21.split(':')[1][:12] + ' starts next, after the restart'), lines[0])
                self.assertIn(reference + ' is not finished until the restart', lines)
                self.unchanged(host, tools.previous, 'The forward to ' + R21 + ' waits for the restart: restart first')
                self.assertEqual(tools.forward()[1], 'It does not run yet: it starts at the next restart')
                restart(tools, host, choice)
                lines = tools.title()
                if choice == 0:
                    self.assertIn(reference + ' confirmed after the restart', lines)
                    self.assertEqual((journal(store), archived(store)), (None, ['confirmed']))
                    self.assertFalse(any('confirmed' in line for line in tools.title()))
                else:
                    self.assertIn(reference + ' is in place and has not started yet', lines)
                    self.assertFalse(any('confirmed' in line or 'fail' in line.lower() for line in lines), lines)
                    self.assertEqual((journal(store)['status'], archived(store)), ('recorded', []))

    def test_every_cut_of_every_reorder_resolves_from_the_list_alone(self):
        cases = {'rollback': (R21, lambda t: t.recover(), 'S'), 'keep-stock': ('S', lambda t: t.recover(True), 'S'),
                 'previous': (R21, lambda t: t.previous(), R13), 'forward': (R13, lambda t: t.forward(), R21)}
        start = {'keep-stock': (R21, R13, 'S'), 'forward': (R13, R21, 'S')}
        for word, (running, command, target) in cases.items():
            order = start.get(word, (R21, R13, 'S'))
            for point in ('before', 'after', 'observe', 'record'):
                for choice in (None, 0, 1, 2):  # no restart yet; then a start of each row
                    with self.subTest(word=word, point=point, choice=choice), laptop(listed(order, running)) as (tools, host, store):
                        real_save = owner.Tools.save
                        def save(obj, name, value):
                            if point == 'record' and name == owner.OUTCOME and value.get('status') == 'recorded':
                                raise OSError('injected failure writing the record')
                            return real_save(obj, name, value)
                        if point != 'record':
                            host.interrupt = ('start-next', point)
                        with patch.object(owner.Tools, 'save', new=save), self.assertRaises((owner.Stop, OSError)):
                            command(tools)
                        self.assertEqual(journal(store)['status'], 'intent')
                        made = point != 'before'
                        self.assertEqual(roles(host)[0], [target, *[r for r in order if r != target]] if made else list(order))
                        if choice is not None:
                            restart(tools, host, choice)
                        sets = len([c for c in host.changes if c.startswith('ostree')])
                        lines = tools.title()  # check and records run this
                        self.assertEqual(len([c for c in host.changes if c.startswith('ostree')]), sets)  # no second set-default
                        if not made:
                            self.assertEqual((journal(store), archived(store)), (None, ['not-applied']))
                            self.assertIn('was not applied', tools.notes[0])
                        else:
                            self.assertIn('had made its change; it is recorded now', tools.notes[0])
                            runs_target = roles(host)[1] == target
                            if choice is None:
                                self.assertEqual(any('not finished until the restart' in l for l in lines), not runs_target)
                                self.assertFalse(any('confirmed' in l for l in lines))
                            else:
                                self.assertEqual(any(l.endswith('confirmed after the restart') for l in lines), runs_target)
                                self.assertEqual(any('is in place and has not started yet' in l for l in lines), not runs_target)
                        waits = made and choice is None and roles(host)[1] != target
                        # Every destination is one command away, unless a change waits for the restart.
                        for destination, method in (('S', lambda: tools.recover(roles(host)[1] == 'S')), (R13, tools.previous), (R21, tools.forward)):
                            # Each from the same state: the machine and the records are put back in between.
                            kept = (copy.deepcopy(host.state), {q.name: q.read_bytes() for q in store.iterdir()})
                            if waits and roles(host)[0][0] != destination:
                                self.unchanged(host, method, 'restart first')
                            else:
                                method()
                                self.assertEqual(roles(host)[0][0], destination)
                            host.state = kept[0]
                            for q in store.iterdir():
                                q.unlink()
                            for name, raw in kept[1].items():
                                (store / name).write_bytes(raw)

    def test_a_side_check_never_comes_before_the_resolution(self):
        # B11: rollback, a cut after set-default, a restart onto stock, then rollback typed there.
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            host.interrupt = ('start-next', 'after')
            with self.assertRaises(owner.Stop):
                tools.recover()
            restart(tools, host)
            self.assertEqual(roles(host), (['S', R21, R13], 'S'))
            self.unchanged(host, tools.recover, 'use sudo /var/lib/ares/at keep-stock')
            self.assertEqual(journal(store)['status'], 'recorded')
            self.assertTrue(any(line.endswith('confirmed after the restart') for line in tools.title()))

    def test_install_commands_resolve_the_installed_journal_before_their_own_refusals(self):
        for word in ('login', 'verify', 'switch', 'prepare'):
            for applied in (False, True):
                with self.subTest(word=word, applied=applied), laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
                    host.interrupt = ('start-next', 'after' if applied else 'before')
                    with self.assertRaises(owner.Stop):
                        tools.recover()
                    restart(tools, host, choice=0 if applied else 2)
                    self.assertEqual(roles(host)[1], 'S')
                    before = copy.deepcopy(host.state), list(host.changes)
                    with self.assertRaises(owner.Stop):
                        getattr(tools, word)()
                    self.assertEqual((host.state, host.changes), before)
                    if applied:
                        self.assertEqual(journal(store)['status'], 'recorded')
                        self.assertTrue(any('had made its change; it is recorded now' in line for line in tools.notes))
                    else:
                        self.assertIsNone(journal(store))
                        self.assertEqual(archived(store), ['not-applied'])
                        self.assertTrue(any('was not applied' in line for line in tools.notes))

    def test_removing_install_survey_fails_resolution_and_danger_warning_regressions(self):
        result = unittest.TestResult()
        with patch.object(owner.Tools, 'survey_installed', lambda *args, **kwargs: None):
            JournalTest('test_install_commands_resolve_the_installed_journal_before_their_own_refusals').run(result)
            ShapeTest('test_a_staged_row_on_running_stock_beside_aresos_says_rule_10_from_every_command').run(result)
        self.assertEqual(result.errors, [])
        self.assertGreaterEqual(len(result.failures), 8)
        self.assertTrue(any('intent' in failure for _, failure in result.failures))
        self.assertTrue(any('A Bazzite update is waiting' in failure for _, failure in result.failures))

    def test_any_other_list_stops_and_an_unknown_schema_refuses(self):
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            tools.previous()
            host.state = listed((R13, 'S', R21), R21)
            for method in (tools.title, tools.reboot, tools.update, tools.forward, tools.recover):
                self.unchanged(host, method, 'neither as before it nor as it intended')
            host.state = listed((R13, R21, 'S'), R21)
            tools.save(owner.OUTCOME, dict(journal(store), schema='change9'))
            for method in (tools.title, tools.update, tools.forward, tools.previous, tools.recover):
                self.unchanged(host, method, 'unknown tools (schema change9); nothing changed')


class StagingTest(Unchanged, unittest.TestCase):
    """Rule 6: staging stays strict; the journal follows the list here too."""

    def test_staging_from_the_older_aresos_prints_both_lines_and_finalize_keeps_three(self):
        with laptop(listed((R13, R21, 'S'), R13), H30) as (tools, host, store):
            lines = tools.update()
            self.assertIn('Newer AresOS ' + R21 + ' is removed when the update finishes at shutdown', lines)
            self.assertIn("The new release starts with this system's settings (Wi-Fi, passwords, layout), not newer AresOS "
                          + R21.split(':')[1][:12] + "'s", lines)
            title = [l for l in lines if l.startswith('Boot menu')]
            self.assertEqual(len(title), 1)
            self.assertTrue(title[0].startswith('Boot menu after the update finishes at shutdown (expected): (ostree:0) new AresOS '))
            value = journal(store)
            self.assertEqual((value['mode'], value['status'], value['running']), ('staging', 'recorded', list(owner.key(row(R13)))))
            self.unchanged(host, tools.previous, 'waits for the restart: restart first')
            restart(tools, host)
            self.assertEqual(roles(host), ([R30, R13, 'S'], R30))
            self.assertIn('Update to ' + R30 + ' confirmed after the restart', tools.title())

    def test_completion_is_right_with_the_stock_in_the_middle(self):
        with laptop(listed((R21, 'S', R13), R21), H30) as (tools, host, store):
            lines = tools.update()
            self.assertIn('Older AresOS ' + R13 + ' is removed when the update finishes at shutdown', lines)
            self.assertFalse(any("this system's settings" in line for line in lines))
            self.assertEqual(journal(store)['intended'][1:], [list(owner.key(row(R21))), list(owner.key(row('S')))])
            restart(tools, host)
            self.assertEqual(roles(host), ([R30, R21, 'S'], R30))
            self.assertIn('Update to ' + R30 + ' confirmed after the restart', tools.title())

    def test_a_power_off_before_the_shutdown_finished_is_not_applied_and_update_stages_again(self):
        with laptop(listed((R21, R13, 'S'), R21), H30) as (tools, host, store):
            tools.update()
            restart(tools, host, power_off=True)
            self.assertEqual(roles(host), ([R21, R13, 'S'], R21))
            tools.title()
            self.assertEqual((journal(store), archived(store)), (None, ['not-applied']))
            self.assertIn('Update to ' + R30 + ' was not applied', tools.notes[0])
            tools.update()
            self.assertEqual(roles(host)[0][0], R30)

    def test_a_finished_update_then_the_old_row_from_the_menu_is_in_place_and_previous_works(self):
        with laptop(listed((R21, 'S'), R21), H30) as (tools, host, store):
            tools.update()
            restart(tools, host, choice=1)
            self.assertEqual(roles(host), ([R30, R21, 'S'], R21))
            lines = tools.title()
            self.assertIn('Update to ' + R30 + ' is in place and has not started yet', lines)
            self.assertFalse(any('fail' in line.lower() for line in lines))
            tools.previous()
            self.assertEqual((roles(host)[0][0], archived(store)), (R21, ['in-place-not-started']))

    def test_staging_is_refused_with_a_repair_note_and_does_not_fall_back_to_a_reorder(self):
        with laptop(listed((R21, R13, 'S'), R21), H30) as (tools, host, store):
            tools.save('layout-repair', dict(schema='layout-repair1', notes=[dict(deployment_identity=list(owner.key(row(R21))), old=base.DE, new=base.DE)]))
            self.unchanged(host, tools.update, 'run sudo /var/lib/ares/at layout abandon first, then update again')
            tools.previous()  # reorders, checking and restarting stay available
            tools.title()
            tools.reboot()

    def test_the_stop_routine_deletes_nothing_when_another_row_comes_before_the_running_one(self):
        with laptop(listed((R21, R13, 'S'), R21), H30) as (tools, host, store):
            before = copy.deepcopy(host.state)
            host.state = machine([row(R30, staged=True), row(R13), row(R21, True), row('S')])
            saved = copy.deepcopy(host.state)
            with self.assertRaisesRegex(owner.Stop, 'nothing was deleted'):
                tools.reconcile_update(before, owner.agree(before), R30)
            self.assertEqual((host.state, host.changes), (saved, []))


class LayoutTest(Unchanged, unittest.TestCase):
    """B7: real layout entry points, independent persistent settings on all three rows."""

    def fresh(self, tools, current, tty='tty3'):
        current[0] = dict(tty=tty, session='fresh-' + str(time.monotonic_ns()), boot=tools.boot[0],
                          started_us=int(time.monotonic() * 1000000) + 1)

    def boot(self, tools, host, current, role):
        restart(tools, host, choice=roles(host)[0].index(role))
        host.loaded = host.keyboard()['VConsoleKeymap']
        self.fresh(tools, current)

    def finishing_cut(self, tools, host, current):
        admin = copy.deepcopy(current[0])
        tools.layout('begin', 'us-intl')
        self.fresh(tools, current, 'tty4')
        tools.layout('proof')
        current[0] = admin
        host.cut_keyboard = True
        with self.assertRaises(PowerCut):
            tools.layout('finish')
        self.assertEqual(host.keyboard(), dict(base.DE, VConsoleKeymap='us-intl'))
        self.assertTrue(tools.load('layout-pending')['finishing'])

    def test_every_restoration_cut_resumes_only_its_own_settings(self):
        for old, new in itertools.permutations(PROFILES, 2):
            for note in (False, True):
                for finish_cut in ('console', 'persistent'):
                    for abandon_cut in ('intent', 'console', 'persistent'):
                        with self.subTest(old=old, new=new, note=note, finish=finish_cut, abandon=abandon_cut), \
                                laptop(listed((R21, R13, 'S'), R21), host_class=KeyboardMachine) as (tools, host, store), \
                                keyboard_sessions(tools, host) as current:
                            host.settings[identity(host.running())] = dict(PROFILES[old])
                            host.loaded = old
                            untouched = copy.deepcopy(host.settings)
                            admin = copy.deepcopy(current[0])
                            tools.layout('begin', new)
                            self.fresh(tools, current, 'tty4')
                            tools.layout('proof')
                            current[0] = admin
                            mutate = host.mutate
                            def cut_finish(*command, **kwargs):
                                result = mutate(*command, **kwargs)
                                cut = 'set-keymap' if finish_cut == 'console' else 'set-x11-keymap'
                                if command[:3] == ('localectl', '--no-convert', cut):
                                    raise PowerCut('finish ' + finish_cut)
                                return result
                            with patch.object(host, 'mutate', cut_finish), self.assertRaises(PowerCut):
                                tools.layout('finish')
                            if note:
                                self.boot(tools, host, current, 'S')
                                tools.layout('abandon')
                                self.boot(tools, host, current, R21)
                            else:
                                self.fresh(tools, current)
                            save = tools.save
                            def cut_save(name, value):
                                save(name, value)
                                if abandon_cut == 'intent' and (name == 'layout-pending' and value.get('restoring')
                                        or name == 'layout-repair' and any(n.get('restoring') for n in value['notes'])):
                                    raise PowerCut('restoration intent')
                            def cut_restore(*command, **kwargs):
                                result = mutate(*command, **kwargs)
                                cut = 'set-keymap' if abandon_cut == 'console' else 'set-x11-keymap'
                                if abandon_cut != 'intent' and command[:3] == ('localectl', '--no-convert', cut):
                                    raise PowerCut('abandon ' + abandon_cut)
                                return result
                            with patch.object(tools, 'save', cut_save), patch.object(host, 'mutate', cut_restore), self.assertRaises(PowerCut):
                                tools.layout('abandon')
                            record = tools.load('layout-repair')['notes'][0] if note else tools.load('layout-pending')
                            self.assertIn('restoring', record)
                            self.boot(tools, host, current, R21)
                            tools.layout('abandon')
                            self.assertEqual(host.settings, untouched)
                            self.assertFalse((store / 'layout-pending.json').exists())
                            self.assertEqual(tools.repair_notes(), [])
                            tools.previous()

    def test_reverse_partial_without_a_restoration_intent_is_not_authorized(self):
        for note in (False, True):
            with self.subTest(note=note), laptop(listed((R21, R13, 'S'), R21), host_class=KeyboardMachine) as (tools, host, store), keyboard_sessions(tools, host) as current:
                self.finishing_cut(tools, host, current)
                if note:
                    self.boot(tools, host, current, 'S')
                    tools.layout('abandon')
                    self.boot(tools, host, current, R21)
                else:
                    self.fresh(tools, current)
                host.settings[identity(host.running())] = dict(PROFILES['us-intl'], VConsoleKeymap='de')
                before = copy.deepcopy(host.settings)
                self.unchanged(host, lambda: tools.layout('abandon'), 'Finished system layout changed')
                self.assertEqual(host.settings, before)

    def test_cut_during_note_transfer_then_restoration_updates_the_same_note(self):
        with laptop(listed((R21, R13, 'S'), R21), host_class=KeyboardMachine) as (tools, host, store), keyboard_sessions(tools, host) as current:
            admin = copy.deepcopy(current[0])
            tools.layout('begin', 'us')
            self.fresh(tools, current, 'tty4')
            tools.layout('proof')
            current[0] = admin
            mutate = host.mutate
            def cut_finish(*command, **kwargs):
                result = mutate(*command, **kwargs)
                if command[:3] == ('localectl', '--no-convert', 'set-x11-keymap'):
                    raise PowerCut('after finish persistence')
                return result
            with patch.object(host, 'mutate', cut_finish), self.assertRaises(PowerCut):
                tools.layout('finish')
            self.boot(tools, host, current, 'S')
            save = tools.save
            def cut_transfer(name, value):
                save(name, value)
                if name == 'layout-repair':
                    raise PowerCut('after note save, before pending trial clear')
            with patch.object(tools, 'save', cut_transfer), self.assertRaises(PowerCut):
                tools.layout('abandon')
            self.assertEqual(len(tools.repair_notes()), 1)
            self.assertTrue((store / 'layout-pending.json').exists())
            self.boot(tools, host, current, R21)
            host.cut_keyboard = True
            with self.assertRaises(PowerCut):
                tools.layout('abandon')
            intent = tools.load('layout-pending')['restoring']
            self.assertEqual(host.keyboard(), dict(PROFILES['us'], VConsoleKeymap='de'))
            self.boot(tools, host, current, 'S')
            tools.layout('abandon')
            self.assertEqual(tools.repair_notes(), [dict(deployment_identity=list(identity(row(R21))),
                old=PROFILES['de'], new=PROFILES['us'], restoring=intent)])
            self.boot(tools, host, current, R21)
            tools.layout('abandon')
            self.assertEqual(host.keyboard(), PROFILES['de'])
            self.assertEqual(tools.repair_notes(), [])

    def test_restoration_is_exclusive_and_finish_from_the_original_login_names_abandon(self):
        """Review 2, finding 2, with the original administrator login kept open: German to US proved;
        finish cut after its console write (US console, German X11); abandon from a fresh second login
        records that pair as its restoration intent and is cut after its console write (both German,
        the trial remains). Back in the original login, finish must refuse and name abandon: a renewed
        finish would write US/US, which that intent does not authorize, and strand the abandon."""
        with laptop(listed((R21, R13, 'S'), R21), host_class=KeyboardMachine) as (tools, host, store), keyboard_sessions(tools, host) as current:
            admin = copy.deepcopy(current[0])
            tools.layout('begin', 'us')
            self.fresh(tools, current, 'tty4')
            tools.layout('proof')
            current[0] = admin
            host.cut_keyboard = True
            with self.assertRaises(PowerCut):
                tools.layout('finish')
            self.assertEqual(host.keyboard(), dict(base.DE, VConsoleKeymap='us'))
            self.fresh(tools, current)
            host.cut_keyboard = True
            with self.assertRaises(PowerCut):
                tools.layout('abandon')
            self.assertEqual(host.keyboard(), base.DE)
            self.assertEqual(tools.load('layout-pending')['restoring'], dict(base.DE, VConsoleKeymap='us'))
            current[0] = admin  # the original login, still open
            before = copy.deepcopy(host.settings)
            self.unchanged(host, lambda: tools.layout('finish'), 'Layout abandon has begun restoring the settings from before '
                'this trial: from a fresh physical administrator login run sudo /var/lib/ares/at layout abandon to complete it; nothing changed')
            self.assertEqual(host.settings, before)
            self.assertIn('restoring', tools.load('layout-pending'))
            # The review's next steps: restart and abandon. Abandon completes, and a new trial works.
            self.boot(tools, host, current, R21)
            tools.layout('abandon')
            self.assertEqual((host.keyboard(), host.loaded), (base.DE, 'de'))
            self.assertFalse((store / 'layout-pending.json').exists())
            self.assertEqual(tools.repair_notes(), [])
            admin = copy.deepcopy(current[0])
            tools.layout('begin', 'us')
            self.fresh(tools, current, 'tty4')
            tools.layout('proof')
            current[0] = admin
            tools.layout('finish')
            self.assertEqual(host.keyboard(), PROFILES['us'])

    def test_duplicate_note_transfer_is_detected_by_the_same_cut_regression(self):
        source = textwrap.dedent(inspect.getsource(owner.Tools.layout))
        line = "notes[:] = [n for n in notes if n['deployment_identity'] != note['deployment_identity']]"
        self.assertEqual(source.count(line), 1)
        namespace = {}
        exec(compile(source.replace(line, 'pass'), '<note replacement removed>', 'exec'), owner.__dict__, namespace)
        result = unittest.TestResult()
        with patch.object(owner.Tools, 'layout', namespace['layout']):
            LayoutTest('test_cut_during_note_transfer_then_restoration_updates_the_same_note').run(result)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.failures), 1)
        self.assertIn('additional', result.failures[0][1])

    def test_begin_and_fresh_login_abandon_with_three_rows_preserve_every_etc(self):
        with laptop(listed((R21, R13, 'S'), R21), host_class=KeyboardMachine) as (tools, host, store), keyboard_sessions(tools, host) as current:
            before = copy.deepcopy(host.settings)
            tools.layout('begin', 'us')
            self.assertEqual((host.settings, host.loaded), (before, 'us'))
            self.unchanged(host, lambda: tools.layout('abandon'), 'fresh physical administrator login')
            self.fresh(tools, current)
            tools.layout('abandon')
            self.assertEqual((host.settings, host.loaded), (before, 'de'))
            self.assertFalse((store / 'layout-pending.json').exists())

    def test_begin_refuses_on_stock_when_not_default_and_with_a_change_waiting(self):
        for order, running, waiting, message in (
                ((R21, R13, 'S'), 'S', False, "German layout: no layout trial here; nothing changed; run sudo /var/lib/ares/at forward to go back to AresOS first"),
                ((R21, R13, 'S'), R13, False, 'does not start next: make it the next start first (sudo /var/lib/ares/at previous), then begin the trial'),
                ((R13, R21, 'S'), R21, False, 'does not start next: make it the next start first (sudo /var/lib/ares/at forward), then begin the trial'),
                (('S', R13), R13, False, 'does not start next: make it the next start first (sudo /var/lib/ares/at forward), then begin the trial'),
                ((R21, R13, 'S'), R21, True, 'restart first')):
            with self.subTest(running=running, waiting=waiting), laptop(listed(order, running), host_class=KeyboardMachine) as (tools, host, store), keyboard_sessions(tools, host):
                if waiting:
                    tools.previous()
                before = copy.deepcopy(host.settings)
                self.unchanged(host, lambda: tools.layout('begin', 'us'), message)
                self.assertEqual(host.settings, before)
                self.assertFalse((store / 'layout-pending.json').exists())

    def test_runtime_trial_abandoned_on_menu_stock_writes_neither_etc(self):
        with laptop(listed((R21, R13, 'S'), R21), host_class=KeyboardMachine) as (tools, host, store), keyboard_sessions(tools, host) as current:
            tools.layout('begin', 'us')
            self.boot(tools, host, current, 'S')
            before, offset = copy.deepcopy(host.settings), len(host.changes)
            tools.layout('abandon')
            self.assertEqual(host.settings, before)
            self.assertFalse(any(c[0] == 'localectl' for c in host.changes[offset:]))
            self.assertFalse((store / 'layout-repair.json').exists())

    def test_interrupted_finish_abandon_on_stock_return_restore_and_new_trial(self):
        with laptop(listed((R21, R13, 'S'), R21), host_class=KeyboardMachine) as (tools, host, store), keyboard_sessions(tools, host) as current:
            self.finishing_cut(tools, host, current)
            self.boot(tools, host, current, 'S')
            before, offset = copy.deepcopy(host.settings), len(host.changes)
            tools.layout('abandon')
            self.assertEqual(host.settings, before)
            self.assertFalse(any(c[0] == 'localectl' for c in host.changes[offset:]))
            self.assertEqual(tools.load('layout-repair')['notes'], [dict(deployment_identity=list(identity(row(R21))), old=base.DE, new=PROFILES['us-intl'])])
            self.boot(tools, host, current, R21)
            self.unchanged(host, lambda: tools.layout('begin', 'us'), 'layout abandon')
            tools.layout('abandon')
            self.assertEqual(host.keyboard(), base.DE)
            self.assertEqual(tools.load('layout-repair')['notes'], [])
            tools.layout('begin', 'us')

    def test_repair_blocks_staging_but_all_ways_back_work_then_whole_settings_are_inherited(self):
        for command in ('previous', 'rollback', 'check', 'reboot', 'repair-update'):
            with self.subTest(command=command), laptop(listed((R21, R13, 'S'), R21), H30, host_class=KeyboardMachine) as (tools, host, store), keyboard_sessions(tools, host) as current:
                self.finishing_cut(tools, host, current)
                self.boot(tools, host, current, 'S')
                tools.layout('abandon')
                self.boot(tools, host, current, R21)
                self.unchanged(host, tools.update, 'layout abandon first, then update again')
                if command == 'repair-update':
                    tools.layout('abandon')
                    tools.update()
                    inherited = copy.deepcopy(host.keyboard())
                    restart(tools, host)
                    host.settings[identity(host.running())] = inherited
                    self.assertEqual((roles(host)[1], host.keyboard()), (R30, base.DE))
                else:
                    tools.title()
                    {'previous': tools.previous, 'rollback': tools.recover, 'check': tools.check, 'reboot': tools.reboot}[command]()


if __name__ == '__main__':
    unittest.main()
