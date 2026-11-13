"""B2/B3/B10/B11: independent ledger vs real Tools entry points and captured ostree.

B2 is BLOCKED: its one-command destination invariant contradicts A4(b)/A6.
The assertion remains red; the counterexample test below pins the required A4
behavior. Do not call this a complete/green model or disable the assertion.

Only the environment is replaced: files, host processes, login sessions and time.
Expected results are computed BEFORE executing a command. Nothing returned by Tools
chooses the expected branch or a successor in the exploration queue.
"""
import contextlib
import copy
import io
import json
import pathlib
import time
import unittest
from collections import deque
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import test_owner_update as base  # library only; never runs that module's tests
from ways_back_keyboard import PowerCut, PROFILES, identity
from ways_back_host import Host, status, compact
from ways_back_ledger import Ledger, Journal, Trial, Result, starts, transition, events, invariants

owner = base.owner
ROOT = base.ROOT
RUN = ROOT / 'reviews/22c-ways-back-after-update/runs/reorder-probe-43470161858'
REFS = {'13': base.R13, '27': base.R21, '28': base.R30}


class MemoryPath:
    """Only Tools' private records; payload paths are real read-only repository files."""
    def __init__(self, files, name=''):
        self.files, self.name = files, name

    def __truediv__(self, name):
        return MemoryPath(self.files, name.removesuffix('.json'))

    def exists(self):
        return self.name in self.files

    is_file = exists

    def is_symlink(self):
        return False

    def unlink(self):
        del self.files[self.name]


class Driver:
    def __init__(self, tools, host):
        self.tools, self.host = tools, host
        self.ids = {name: list(identity(row)) for name, row in host.templates.items()}
        self.by_id = {tuple(value): name for name, value in self.ids.items()}
        self.by_digest = {row['container-image-reference-digest']: name for name, row in host.templates.items()}
        self.phase = ''
        self.files = {}
        tools.store = MemoryPath(self.files)
        tools.load = lambda name: copy.deepcopy(self.files[name]) if name in self.files else self.missing(name)
        tools.save = self.save
        tools.keyboard = host.keyboard
        tools.session = lambda: copy.deepcopy(self.session)
        self.saved = dict(state=dict(rpm=copy.deepcopy(base.VALUES['after-pin rpm-ostree-status']),
                                    bootc=copy.deepcopy(base.VALUES['after-pin bootc-status'])))
        self.saved['stock'] = copy.deepcopy(host.templates['S'])
        self.saved['stock_identity'] = self.ids['S']
        # The prepared state only determines which former stock entries are exempt.
        self.saved['state']['rpm']['deployments'] = [dict(host.templates['S'], booted=True, staged=False)]

    def missing(self, name):
        raise owner.Stop('Missing private ' + name + ' record')

    def save(self, name, value):
        self.files[name] = copy.deepcopy(value)
        if name == 'outcome-pending' and self.phase == ('intent' if value['status'] == 'intent' else 'record'):
            raise PowerCut('after journal ' + value['status'])
        if name == 'layout-pending' and value.get('finishing') and self.phase == 'intent':
            raise PowerCut('after layout finishing intent')

    def journal_record(self, j):
        if j is None:
            return None
        staged_intent = j.mode == 'staging' and j.phase == 'intent'
        reference = REFS.get(j.target, self.host.templates['S']['container-image-reference'].split('docker://')[-1])
        record = dict(schema='change1', mode=j.mode, word=j.word, status=j.phase,
                      boot='boot-2' if j.same_boot else 'boot-1', reference=reference,
                      digest=self.host.templates[j.target]['container-image-reference-digest'],
                      target=None if staged_intent else self.ids[j.target], running=self.ids[j.running],
                      before=[self.ids[r] for r in j.before],
                      intended=None if staged_intent else [self.ids[r] for r in j.intended()])
        if j.mode == 'staging' and j.phase == 'recorded':
            record['staged'] = [self.ids[r] for r in (j.target, *j.before)]
        return record

    def trial_record(self, t):
        if t is None:
            return None
        admin = dict(tty='tty3', session='original', boot='boot-2' if t.same_boot else 'boot-1', started_us=1)
        value = dict(deployment_identity=self.ids[t.row], old=PROFILES[t.old], new=PROFILES[t.new],
                     administrator=admin, began_us=10, proof=dict(admin, session='proof', tty='tty4', started_us=20) if t.proof else None)
        if t.reverted:
            value['reverted'] = True
        if t.finishing:
            value['finishing'] = True
            if t.reverted:
                value['finish_proof'] = dict(admin, session='proof', tty='tty4', started_us=20)
        return value

    def install(self, s):
        h, tools = self.host, self.tools
        rows = [dict(h.templates[r], booted=r == s.running, staged=r == s.stage) for r in s.rows]
        h.reset_disk(rows)
        h.settings = {tuple(self.ids[r]): dict(PROFILES[x], VConsoleKeymap=PROFILES[c]['VConsoleKeymap']) for r, c, x in s.settings}
        h.loaded, h.changes, h.trace, h.cut_keyboard, h.cut = s.loaded, [], [], False, ''
        tools.boot[0], tools.notes = 'boot-2', []
        tools.release['reference'] = REFS[s.bundle]
        tools.release['signature']['identity'] = base.IDENTITY
        tools._lineage = dict(tools_version=3, releases=base.H21 if s.bundle == '27' else base.H30)
        self.files.clear()
        self.files.update(prepared=copy.deepcopy(self.saved), disks={}, **{'network-verified': {},
                          'title': dict(state=copy.deepcopy(h.state), bls=h.entries())})
        if s.journal:
            self.files['outcome-pending'] = self.journal_record(s.journal)
        if s.trial:
            self.files['layout-pending'] = self.trial_record(s.trial)
        if s.repairs:
            self.files['layout-repair'] = dict(schema='layout-repair1', notes=[dict(deployment_identity=self.ids[r], old=PROFILES[o], new=PROFILES[n]) for r, o, n in s.repairs])
        self.session = dict(tty='tty3', session='fresh' if s.trial and s.trial.fresh else 'original', boot='boot-2',
                            started_us=20 if s.trial and s.trial.fresh else 1)

    def snapshot(self, bundle):
        h = self.host
        roles = tuple(self.by_id[identity(r)] for r in h.state['rpm']['deployments'])
        running = self.by_id[identity(h.running())]
        stage = next((self.by_id[identity(r)] for r in h.state['rpm']['deployments'] if r.get('staged')), '')
        j = self.files.get('outcome-pending')
        journal = None if j is None else Journal(j['word'], j['mode'], j['status'], self.by_digest[j['digest']],
            self.by_id[tuple(j['running'])], tuple(self.by_id[tuple(r)] for r in j['before']), j['boot'] == self.tools.boot[0])
        t = self.files.get('layout-pending')
        trial = None if t is None else Trial(self.by_id[tuple(t['deployment_identity'])], t['old']['VConsoleKeymap'],
            t['new']['VConsoleKeymap'], t['administrator']['boot'] == self.tools.boot[0],
            self.session != t['administrator'], bool(t['proof']), t.get('reverted', False), t.get('finishing', False))
        repairs = tuple(sorted((self.by_id[tuple(n['deployment_identity'])], n['old']['VConsoleKeymap'], n['new']['VConsoleKeymap'])
                              for n in self.files.get('layout-repair', {}).get('notes', [])))
        def profile(values):
            return 'de' if values['X11Layout'] == 'de' else 'us-intl' if values['X11Variant'] == 'intl' else 'us'
        settings = tuple(sorted((r, h.settings[tuple(self.ids[r])]['VConsoleKeymap'], profile(h.settings[tuple(self.ids[r])]))
                                for r in roles if r != stage))
        return Ledger(bundle, roles, running, stage, journal, trial, repairs, settings, h.loaded)

    def step(self, s, event, expected):
        self.install(s)
        tools, host = self.tools, self.host
        word, self.phase = event
        host.cut = self.phase
        host.cut_keyboard = word == 'finish' and self.phase == 'console'
        before_entries, before_rows = copy.deepcopy(host.entries()), copy.deepcopy(host.state['rpm']['deployments'])
        cut, error, lines = False, '', []
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                if word in ('restart', 'power-off'):
                    host.restart(None if self.phase == 'default' else tuple(self.ids[self.phase]), power_off=word == 'power-off')
                    tools.boot[0] = 'boot-3'
                    self.session = dict(tty='tty3', session='fresh', boot='boot-3', started_us=1)
                elif word == 'fresh-login':
                    self.session = dict(tty='tty3', session='fresh', boot='boot-2', started_us=20)
                elif word in ('begin', 'proof', 'revert', 'finish', 'abandon'):
                    if word == 'proof':
                        original = self.session
                        self.session = dict(tty='tty4', session='proof', boot=tools.boot[0], started_us=20)
                        try:
                            lines = tools.layout(word)
                        finally:
                            self.session = original
                    else:
                        lines = tools.layout(word, self.phase if word == 'begin' else None)
                else:
                    method = {'update': tools.update, 'previous': tools.previous, 'rollback': tools.recover,
                              'keep-stock': lambda: tools.recover(True), 'check': tools.check, 'title': tools.title,
                              'records': tools.records, 'reboot': tools.reboot}[word]
                    lines = method()
            except owner.Stop as problem:
                error = str(problem)
            except PowerCut:
                cut = True
        assert bool(error) == bool(expected.stop), ('accept/refuse', event, expected.stop, error)
        if error:
            assert expected.stop.lower() in error.lower(), ('STOP next step', event, expected.stop, error)
            assert host.state['rpm']['deployments'] == before_rows and host.entries() == before_entries, 'refusal mutated deployment/pin/entries'
        assert cut == expected.cut, ('cut', event, expected.cut, cut)
        found = self.snapshot(s.bundle)
        if word == 'restart' and s.stage:
            assert found.rows == (s.stage, s.running, 'S'), ('retention after finalize', found.rows)
        assert found == expected.state, ('ledger differs', event, expected.state, found)
        raw = self.files.get('outcome-pending')
        if raw:
            encoded = self.journal_record(expected.state.journal)
            # Ignore literal boot ids; their relationship to this boot is checked above.
            assert {k: v for k, v in raw.items() if k != 'boot'} == {k: v for k, v in encoded.items() if k != 'boot'}, ('journal fields', raw, encoded)
        archives = tuple(name.split('-outcome-')[1] for name in self.files if '-outcome-' in name)
        assert archives == expected.archives, ('archives', event, expected.archives, archives)
        text = '\n'.join(lines + tools.notes) + output.getvalue()
        assert ('confirmed after the restart' in text) == (expected.confirmation and not cut), ('premature/missing confirmation', event, text)
        if word == 'check' and expected.stop == 'layout':
            assert 'sudo /var/lib/ares/at layout ' in error, ('check has no executable next step', error)
        if expected.state.outcome() == 'selection-applied' and word in ('title', 'check', 'records') and not error:
            assert 'runs and now starts next; no restart is waiting' in text, text
        if expected.announcement:
            assert (REFS[expected.announcement] + ' is removed when the update finishes at shutdown' in text or
                    'At shutdown, this update removes ' in text and REFS[expected.announcement] in text), ('unannounced removal', event, expected.announcement, text)
        assert [self.by_id[identity(r)] for r in host.state['rpm']['deployments'] if r['pinned']] == ['S'], 'stock pin changed'
        return found


@contextlib.contextmanager
def driver(host_class=Host):
    with base.route(base.updated(), base.H30, host_class=host_class) as (tools, host, store), contextlib.ExitStack() as stack:
        d = Driver(tools, host)
        # Plain environment functions avoid retaining a mock call history for millions
        # of edges. None predicts acceptance, journals, or a deployment transition.
        stack.enter_context(patch.object(owner, 'boot_id', new=lambda: tools.boot[0]))
        stack.enter_context(patch.object(owner, 'resolved_bls', new=host.entries))
        stack.enter_context(patch.object(owner, 'sync_directory', new=lambda *a: None))
        stack.enter_context(patch.object(owner, 'finalizer_masks', new=lambda: []))
        stack.enter_context(patch.object(owner, 'disk_record', new=lambda *a: dict(target=dict(path='/dev/FIXTURE', serial='TARGET'), esp_guid='fixture')))
        stack.enter_context(patch.object(owner, 'runtime_state', new=lambda *a: {}))
        stack.enter_context(patch.object(owner, 'paused_state', new=lambda *a: {}))
        stack.enter_context(patch.object(owner, 'media_module', new=lambda *a: SimpleNamespace(find=lambda *a: None)))
        stack.enter_context(patch.object(owner.shutil, 'which', new=lambda *a, **k: '/usr/bin/cosign'))
        stack.enter_context(patch.object(owner.time, 'monotonic', new=lambda: .00001))
        stack.enter_context(patch('builtins.input', new=lambda *a: 'yz-/!ü'))
        yield d


class CaptureTest(unittest.TestCase):
    """B10: replay every committed stage-0 deployment/layout observation through Host.

    The initial immutable rows and entry bytes are fixture inputs. Every later
    order, slot, flag and link comes from an operation, never from its capture.
    This does not pretend to be a capture of finalize over three installed rows.
    """
    def captured(self, stage, kind):
        return json.loads((RUN / (stage + '-' + kind + '.json')).read_text())

    def replay(self, host_class=Host):
        first = self.captured('walk-0-start', 'deployments')
        h = host_class(status([compact(r) for r in first['rpm']['deployments']]))
        h.entry_files = {e['file']: e['content'] for e in first['bls']}
        h.settings = {identity(r): dict(PROFILES['de']) for r in h.state['rpm']['deployments']}
        visited = []

        def compare(stage):
            actual, layout = self.captured(stage, 'deployments'), self.captured(stage, 'layout')
            self.assertEqual(h.state['rpm']['deployments'], [compact(r) for r in actual['rpm']['deployments']], stage + ': order, identities, pins and stage')
            for name in ('booted', 'rollback', 'staged'):
                slot, expected = h.state['bootc']['status'][name], actual['bootc']['status'][name]
                for key in ('ostree', 'pinned'):
                    self.assertEqual((slot or {}).get(key), (expected or {}).get(key), stage + ': ' + name)
                self.assertEqual((slot or {}).get('image', {}).get('imageDigest'), (expected or {}).get('image', {}).get('imageDigest'), stage)
            self.assertEqual(h.state['bootc']['status']['rollbackQueued'], actual['bootc']['status']['rollbackQueued'], stage)
            self.assertEqual(h.state['bootc']['spec']['bootOrder'], actual['bootc']['spec']['bootOrder'], stage)
            # Capture arrays follow filesystem enumeration, not menu order; filenames
            # identify files. Compare every byte and resolved identity by filename.
            self.assertEqual({e['file']: (e['content'], e['target']) for e in h.entries()},
                             {e['file']: (e['content'], e['deployment']) for e in actual['bls']}, stage + ': boot entry bytes and identities')
            self.assertEqual(h.kernel_link_target(), layout['running'], stage + ': positional kernel link')
            self.assertEqual('boot.0.' + str(h.links), layout['ostree_boot_links']['boot.0'], stage)
            self.assertEqual(layout['loader_link'], 'loader.0')
            visited.append(stage)

        compare('walk-0-start')
        for i in range(1, 7):
            stage = 'walk-%d-moved' % i
            command = self.captured(stage, 'set-default')
            message = h.set_default(int(command['argv'][-1]))
            self.assertEqual(message + '\n', command['stdout'])
            self.assertEqual(h.ostree_journal, [r['MESSAGE'] for r in self.captured(stage, 'journal-after')])
            compare(stage)
            h.restart()
            compare('walk-%d-booted' % i)
        stock = next(identity(r) for r in h.state['rpm']['deployments'] if r['pinned'])
        h.restart(stock)
        compare('menu-stock')
        h.restart()
        compare('after-menu-booted')
        self.assertEqual(set(visited), {p.name.removesuffix('-deployments.json') for p in RUN.glob('*-deployments.json')})
        self.assertEqual(len(visited), 15)

    def test_every_probe_capture_matches_the_model_host(self):
        self.replay()

    def test_append_instead_of_prepend_fails_the_fixture(self):
        class Appends(Host):
            def set_default(self, index):
                rows = self.state['rpm']['deployments'][:]
                rows.append(rows.pop(index))
                self.write_list(rows)
                message = f'Transaction complete; bootconfig swap: no; bootversion: boot.0.{self.links}, deployment count change: 0'
                self.ostree_journal.append(message)
                return message
        with self.assertRaisesRegex(AssertionError, 'walk-1-moved: order'):
            self.replay(Appends)

    def test_prepared_pair_and_first_switch_slots_match_retained_captures(self):
        for stage in ('after-pin', 'after-switch-staged', 'aresos', 'after-rollback-queued', 'rollback'):
            rows = base.VALUES[stage + ' rpm-ostree-status']['deployments']
            result = status([compact(r) for r in rows])['bootc']['status']
            real = base.VALUES[stage + ' bootc-status']['status']
            with self.subTest(stage=stage):
                for slot in ('booted', 'staged', 'rollback'):
                    self.assertEqual((result[slot] or {}).get('ostree'), (real[slot] or {}).get('ostree'))
                self.assertEqual(result['rollbackQueued'], real['rollbackQueued'])
                self.assertEqual(status([compact(r) for r in rows])['bootc']['spec']['bootOrder'],
                                 base.VALUES[stage + ' bootc-status']['spec']['bootOrder'])


class FakeRulesTest(unittest.TestCase):
    def test_list_write_drops_nonfirst_stage_and_cleanup_removes_unpinned_preceding_rows(self):
        rows = [dict(compact(base.release_row(base.R30)), staged=True),
                compact(base.release_row(base.R21)), compact(base.stock_row()), compact(base.release_row(base.R13, booted=True))]
        h = Host(status(rows))
        h.set_default(1)
        self.assertEqual([identity(r) for r in h.state['rpm']['deployments']], [identity(r) for r in rows[1:]])
        h.reset_disk(rows)
        h.mutate('rpm-ostree', 'cleanup', '--pending')
        self.assertEqual([identity(r) for r in h.state['rpm']['deployments']], [identity(rows[2]), identity(rows[3])])

    def test_finalize_keeps_merge_and_other_stateroots_in_their_original_order(self):
        rows = [compact(base.release_row(base.R30, staged=True)), compact(base.release_row(base.R13, booted=True)),
                compact(base.stock_row()), compact(base.release_row(base.R21)),
                dict(compact(base.release_row(base.R99)), osname='other')]
        h = Host(status(rows))
        h.merge = identity(rows[3])
        h.finalize()
        self.assertEqual([identity(r) for r in h.state['rpm']['deployments']], [identity(r) for r in rows])
        self.assertFalse(any(r.get('staged') for r in h.state['rpm']['deployments']))

    def test_script_refusal_before_primitive_has_no_mutation(self):
        with driver() as d:
            d.install(starts()[2])
            before = copy.deepcopy(d.host.state), d.host.entries()
            with self.assertRaises(owner.Stop):
                d.tools.script('start-next', dict(CHECKSUM='f' * 64, SERIAL='0', DIGEST='sha256:' + 'e' * 64,
                                                REFERENCE='ostree-unverified-registry:' + base.R21))
            self.assertEqual((d.host.state, d.host.entries()), before)
            self.assertEqual(d.host.changes, [])
            self.assertFalse(any(r.get('mutation') for r in d.host.trace))


class RevertTest(unittest.TestCase):
    """B11: deliberately broken implementations must fail the same ledger assertions."""
    def path(self, d, s, events):
        for event in events:
            expected = transition(s, event)
            d.step(s, event, expected)
            s = expected.state
        return s

    def test_finalize_that_keeps_bootcs_rollback_fails_retention(self):
        class KeepsRollback(Host):
            def finalize(self):
                slot = self.state['bootc']['status']['rollback']['ostree']
                self.merge = slot['checksum'], slot['deploySerial'], slot['stateroot']
                super().finalize()
        with driver(KeepsRollback) as d:
            s = self.path(d, starts()[3], [('update', 'full')])
            with self.assertRaisesRegex(AssertionError, 'retention after finalize'):
                self.path(d, s, [('restart', 'default')])

    def test_side_check_before_resolution_fails_the_rollback_cut_path(self):
        real = owner.Tools.recover
        def side_first(tools, keep=False):
            if not keep and tools.host.running()['pinned']:
                raise owner.Stop('Use keep-stock')
            return real(tools, keep)
        with driver() as d:
            s = self.path(d, starts()[2], [('rollback', 'primitive'), ('restart', 'S')])
            with patch.object(owner.Tools, 'recover', side_first), self.assertRaisesRegex(AssertionError, 'ledger differs'):
                self.path(d, s, [('rollback', 'full')])

    def test_requiring_target_to_run_fails_a_boot_menu_start(self):
        real = owner.Tools.outcome
        def must_run(tools, state, retry=None):
            result = real(tools, state, retry)
            if result == 'elsewhere':
                raise owner.Stop('Recorded target did not run')
            return result
        with driver() as d:
            s = self.path(d, starts()[2], [('rollback', 'full'), ('restart', '27')])
            with patch.object(owner.Tools, 'outcome', must_run), self.assertRaisesRegex(AssertionError, 'accept/refuse'):
                self.path(d, s, [('check', 'full')])

    def test_the_four_found_defects_have_short_replaying_regressions(self):
        sequences = [
            (3, [('update', 'primitive'), ('restart', 'default')]),
            (0, [('begin', 'us'), ('check', 'full'), ('fresh-login', 'full'), ('abandon', 'full'), ('check', 'full')]),
            (0, [('begin', 'us'), ('proof', 'full'), ('finish', 'console'), ('revert', 'full'), ('fresh-login', 'full'), ('abandon', 'full')]),
            (2, [('begin', 'us'), ('proof', 'full'), ('finish', 'console'), ('restart', '13'), ('abandon', 'full'),
                 ('previous', 'full'), ('begin', 'us'), ('restart', '27'), ('abandon', 'full')]),
        ]
        with driver() as d:
            for start, sequence in sequences:
                with self.subTest(sequence=sequence):
                    self.path(d, starts()[start], sequence)


class ModelTest(unittest.TestCase):
    def test_brief_conflict_new_bundle_cannot_select_newest_installed_in_one_command(self):
        """A4(b)/A6 require this behavior; it contradicts B2's destination invariant.

        This is a counterexample, NOT a proof that that invariant holds.
        No rule is widened to invent a command that selects installed R27 here.
        """
        s = starts()[3]
        with driver() as d:
            for event in (('previous', 'full'), ('restart', 'default'), ('title', 'full')):
                expected = transition(s, event)
                d.step(s, event, expected)
                s = expected.state
            self.assertEqual((s.rows, s.running, s.outcome()), (('13', '27', 'S'), '13', 'none'))
            destinations = {}
            for word in ('update', 'previous', 'rollback', 'keep-stock'):
                expected = transition(s, (word, 'full'))
                found = d.step(s, (word, 'full'), expected)
                destinations[word] = 'STOP' if expected.stop else found.rows[0]
            self.assertEqual(destinations, dict(update='28', previous='13', rollback='S', **{'keep-stock': 'STOP'}))
            self.assertNotIn('27', destinations.values())

    def test_reachable_state_space(self):
        began = time.perf_counter()
        queue = deque(starts())
        parents = {s: None for s in queue}
        edges = 0
        processed = 0
        with driver() as d:
            while queue:
                s = queue.popleft()
                missing = invariants(s)
                if missing:
                    print('22c model blocked: %d discovered states, %d checked states, %d edges, %.3fs; closure NOT reached'
                          % (len(parents), processed, edges, time.perf_counter() - began), flush=True)
                self.assertFalse(missing, 'BLOCKED B2 destination invariant contradicts A4(b)/A6: '
                                 + repr(s) + '; no single command selects ' + repr(missing))
                processed += 1
                if processed % 10000 == 0:
                    print('22c model: %d processed, %d discovered' % (processed, len(parents)), flush=True)
                for event in events(s):
                    expected = transition(s, event)
                    try:
                        d.step(s, event, expected)
                    except AssertionError as error:
                        sequence = [event]
                        parent = s
                        while parents[parent] is not None:
                            parent, action = parents[parent]
                            sequence.append(action)
                        self.fail('Sequence from %r: %s\n%s' % (parent, list(reversed(sequence)), error))
                    edges += 1
                    if expected.state not in parents:
                        parents[expected.state] = s, event
                        queue.append(expected.state)
        print('22c model: %d states, %d edges, %.3fs; queue exhausted' % (len(parents), edges, time.perf_counter() - began), flush=True)
        self.assertGreater(len(parents), 100)


if __name__ == '__main__':
    unittest.main()
