"""Package 22c, section A: the owner tools' rules, each pinned directly (brief B1, B4 to B7).

Shapes, the reorder script, the journal, staging and layout, over the modelled machine of
test_owner_update (imported as a library: nothing of that module runs here, so this module
runs on a machine that has the real rpm-ostree). The model over the whole state space (B2)
and the tools 2-to-3 compatibility tests (B8) are separate modules.

"Selection applied", "restart waiting" and "target boot confirmed" are three states here:
the list, the boot id, and a later boot that runs the target. No helper merges them.
"""
import contextlib
import copy
import io
import itertools
import json
import pathlib
import subprocess
import unittest
from unittest.mock import patch

import test_owner_update as base

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
                for method in (tools.title, tools.reboot, tools.update, tools.previous, tools.recover):
                    self.unchanged(host, method, '')

    def test_a_staged_row_on_running_stock_beside_aresos_says_rule_10_from_every_command(self):
        foreign = dict(base.stock_row(), checksum='f0' * 32, serial=0, pinned=False, staged=True,
                       **{'container-image-reference-digest': 'sha256:' + 'f1' * 32})
        for order in itertools.permutations((R21, R13, 'S')):
            for new in (foreign, row(R30, staged=True)):  # also when the staged row is the bundle's target
                state = machine([new, *[row(role, booted=role == 'S') for role in order]])
                with self.subTest(order=order, digest=new['container-image-reference-digest'][:12]), laptop(state, H30) as (tools, host, store):
                    for method in (tools.title, tools.records, tools.reboot, tools.update, tools.previous, tools.recover,
                                   lambda: tools.recover(True), lambda: tools.layout('abandon')):
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
            for method in (tools.update, tools.previous, tools.recover, lambda: tools.recover(True)):
                self.unchanged(host, method, '')
            self.assertEqual(tools.title()[0], 'stock ' + ' '.join(map(str, saved['stock_identity'])))

    def test_stock_updaters_warn_in_title_stop_keep_stock_and_never_block_the_way_off(self):
        with laptop(listed((R21, R13, 'S'), 'S')) as (tools, host, store):
            tools.paused.side_effect = owner.Stop('OS updater timer is not persistently disabled: uupd.timer')
            warning, = [line for line in tools.title() if line.startswith('WARNING: ')]
            self.assertIn('uupd.timer', warning)
            self.assertIn('run sudo /var/lib/ares/at update to go back to AresOS, then get help', warning)
            self.unchanged(host, lambda: tools.recover(True), 'uupd.timer; nothing changed')
            tools.reboot()
            self.assertEqual(tools.update()[:2], ['Newer AresOS ' + R21.split(':')[1][:12] + ' already starts next; nothing changed',
                                                  'It does not run yet: it starts at the next restart'])

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

    def run_script(self, rows, after=None, fails=False):
        source = (ROOT / 'os/release/start-next.sh').read_text().split("<<'START_NEXT'\n", 1)[1].rsplit('\nSTART_NEXT', 1)[0]
        for name, value in (('CHECKSUM', 'a' * 64), ('SERIAL', '1'), ('DIGEST', 'sha256:' + 'b' * 64),
                            ('REFERENCE', 'ostree-image-signed:docker://example/stock:stable')):
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
        with patch('subprocess.check_output', side_effect=read), patch('subprocess.run', side_effect=run), \
                contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source, 'start-next.sh', 'exec'), {})

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
            with self.subTest(name=name), self.assertRaises(AssertionError):
                self.run_script(rows)
            self.assertEqual(self.calls, ['read'])

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
        words = {'update': R21, 'previous': R13, 'stock': 'S'}
        for order in itertools.permutations((R21, R13, 'S')):
            for running in order:
                for word, target in words.items():
                    with self.subTest(order=order, running=running, word=word), laptop(listed(order, running)) as (tools, host, store):
                        before = copy.deepcopy(host.state['rpm']['deployments'])
                        method = {'update': tools.update, 'previous': tools.previous,
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

    def test_rollback_and_keep_stock_keep_their_sides_and_name_the_other_word(self):
        with laptop(listed((R21, R13, 'S'), 'S')) as (tools, host, store):
            self.unchanged(host, tools.recover, 'use sudo /var/lib/ares/at keep-stock (rollback is for a running AresOS); nothing changed')
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            self.unchanged(host, lambda: tools.recover(True), 'use sudo /var/lib/ares/at rollback (keep-stock is for running plain Bazzite); nothing changed')
            self.assertEqual(tools.recover()[0], 'Saved stock rollback queued')
        with laptop(listed((R13, 'S'), R13)) as (tools, host, store):
            self.unchanged(host, tools.previous, 'Only one AresOS is installed')

    def test_update_with_a_newer_bundle_reorders_where_it_may_not_stage_and_says_what_is_next(self):
        for order, running, tail in (((R21, R13, 'S'), 'S', 'restart, then run sudo /var/lib/ares/at update again'),
                                     ((R13, R21, 'S'), R21, 'run sudo /var/lib/ares/at update again'),
                                     (('S', R13, R21), R13, 'restart, then run sudo /var/lib/ares/at update again')):
            with self.subTest(order=order, running=running), laptop(listed(order, running), H30) as (tools, host, store):
                lines = tools.update()
                self.assertEqual(roles(host)[0][0], R21)
                self.assertNotIn('bootc switch --retain ' + R30, host.changes)
                self.assertTrue(lines[-1].endswith(tail), lines[-1])
                self.assertIn(R30, lines[-1])

    def test_login_refuses_where_update_needs_no_download(self):
        with laptop(listed((R13, R21, 'S'), R13)) as (tools, host, store):
            self.unchanged(host, tools.login, 'update needs no login')

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
            for method in (tools.previous, tools.update, lambda: tools.layout('begin', 'us')):
                self.unchanged(host, method, 'waits for the restart: restart first')
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

    def test_a_new_change_supersedes_an_in_place_record_and_update_works_at_once(self):
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            tools.previous()
            restart(tools, host, choice=1)
            self.assertEqual(tools.update()[0], 'Newest AresOS starts next ' + R21)
            self.assertEqual(archived(store), ['in-place-not-started'])
            self.assertTrue(tools.title()[0].endswith(' runs and now starts next; no restart is waiting'))
            restart(tools, host)
            self.assertIn('Update to ' + R21 + ' confirmed after the restart', tools.title())

    def test_every_cut_of_every_reorder_resolves_from_the_list_alone(self):
        cases = {'rollback': (R21, lambda t: t.recover(), 'S'), 'keep-stock': ('S', lambda t: t.recover(True), 'S'),
                 'previous': (R21, lambda t: t.previous(), R13), 'update': (R13, lambda t: t.update(), R21)}
        start = {'keep-stock': (R21, R13, 'S'), 'update': (R13, R21, 'S')}
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
                        for destination, method in (('S', lambda: tools.recover(roles(host)[1] == 'S')), (R13, tools.previous), (R21, tools.update)):
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

    def test_any_other_list_stops_and_an_unknown_schema_refuses(self):
        with laptop(listed((R21, R13, 'S'), R21)) as (tools, host, store):
            tools.previous()
            host.state = listed((R13, 'S', R21), R21)
            for method in (tools.title, tools.reboot, tools.update, tools.recover):
                self.unchanged(host, method, 'neither as before it nor as it intended')
            host.state = listed((R13, R21, 'S'), R21)
            tools.save(owner.OUTCOME, dict(journal(store), schema='change9'))
            for method in (tools.title, tools.update, tools.previous, tools.recover):
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


if __name__ == '__main__':
    unittest.main()
