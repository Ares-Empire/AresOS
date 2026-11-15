"""22c B8/B11: exact tools 2 code and bundle from 41b06513, read by tools 3.

Importing test_owner_update is library use only. No entry point, namespace,
privileged command, real keyboard or service is executed in this module.
The hosted suite runs it; the laptop does not run test_owner_update.
"""
import contextlib
import copy
import functools
import hashlib
import inspect
import itertools
import json
import pathlib
import subprocess
import sys
import textwrap
import time
import types
import unittest
from unittest.mock import patch

import test_owner_update as base
from ways_back_host import Host
from ways_back_keyboard import KeyboardMachine, PowerCut, PROFILES, identity

ROOT, owner = base.ROOT, base.owner
COMMIT = '41b06513'
V2_FINGERPRINT = '851eb742bfe20bd4b47370b9f2558494edf4b74056d7023cc0d412e32fee6f33'


@functools.lru_cache(maxsize=None)
def blob(path):
    # Like owner_vm.laptop_payload: immutable repository history, never the installed tools.
    return subprocess.check_output(['git', 'show', COMMIT + ':os/owner-tools/payload/' + path], cwd=ROOT)


@functools.lru_cache(maxsize=1)
def version2():
    module = types.ModuleType('owner_v2_41b06513')
    module.__file__ = str(ROOT / 'os/owner-tools/payload/owner.py')
    exec(compile(blob('owner.py'), COMMIT + ':owner.py', 'exec'), module.__dict__)
    return module


@functools.lru_cache(maxsize=1)
def old_files():
    rows = json.loads(blob('SHA256.json'))
    files = {r['path']: blob(r['path']) for r in rows}
    for row in rows:
        assert hashlib.sha256(files[row['path']]).hexdigest() == row['sha256']
    return files


HISTORY = json.loads(blob('history.json'))['releases']
LATEST = HISTORY[-1]['reference']
OLDER = HISTORY[0]['reference']


def row(reference, running=False, staged=False):
    if reference == 'S':
        return base.stock_row(running)
    value = base.release_row(base.R13 if reference == OLDER else base.R21, booted=running, staged=staged)
    value['container-image-reference'] = 'ostree-unverified-registry:' + reference
    value['container-image-reference-digest'] = reference.split('@')[1]
    return value


def listed(order, running, stage=None):
    rows = [row(ref, ref == running) for ref in order]
    return base.machine(([row(stage, staged=True)] if stage else []) + rows)


def first_switch():
    return base.machine([row(LATEST, staged=True), *base.prepared()['state']['rpm']['deployments']])


def candidates():
    yield 'prepared stock', base.prepared()['state']
    yield 'first switch staged', first_switch()
    for releases in ((OLDER,), (LATEST,), (OLDER, LATEST)):
        for order in itertools.permutations((*releases, 'S')):
            for running in order:
                yield repr((order, running)), listed(order, running)
    yield 'update staged over pair', listed((OLDER, 'S'), OLDER, LATEST)


def accepted_by_v2():
    old = version2()
    result = []
    for name, state in candidates():
        try:
            old.qualified_state(state, base.prepared(), LATEST, [r['reference'] for r in HISTORY])
        except old.Stop:
            continue
        result.append((name, state))
    return result


class HistoricalHost(Host):
    def script(self, text, name, mutation=True):
        # Only version 2's primitive differs; its executable script still runs.
        if name == 'previous':
            return base.Machine.script(self, text, name, mutation)
        return super().script(text, name, mutation)


@contextlib.contextmanager
def route(state):
    # The prepared lifecycle compares complete observations, before Host's installed-state projection.
    installed = any(r['container-image-reference-digest'] in {OLDER.split('@')[1], LATEST.split('@')[1]}
                    and not r.get('staged') for r in state['rpm']['deployments'])
    host_class = HistoricalHost if installed else KeyboardMachine
    with base.route(state, HISTORY, host_class=host_class) as (tools, host, store), contextlib.ExitStack() as stack:
        old_payload = store.parent / 'v2'
        paths = {r['path'] for r in json.loads((base.PAYLOAD / 'SHA256.json').read_text())}
        fingerprint = base.write_bundle(old_payload, extra=old_files(), drop=tuple(paths - set(old_files())))
        assert fingerprint == hashlib.sha256(blob('SHA256SUMS')).hexdigest()
        old = version2()
        legacy = old.Tools(old_payload, host, store)
        legacy.processes = tools.processes
        legacy.keyboard = tools.keyboard = host.keyboard
        legacy.session = tools.session = lambda: dict(tty='tty3', session='original', boot=tools.boot[0], started_us=1)
        if installed:
            owner.resolved_bls.side_effect = host.entries
        stack.enter_context(patch.object(old, 'boot_id', side_effect=lambda: tools.boot[0]))
        stack.enter_context(patch.object(old, 'disk_record', side_effect=owner.disk_record))
        stack.enter_context(patch.object(old, 'runtime_state', return_value={}))
        stack.enter_context(patch.object(old, 'paused_state', return_value={}))
        stack.enter_context(patch.object(old, 'resolved_bls', side_effect=lambda: owner.resolved_bls()))
        tools.notes = []
        yield tools, legacy, host, store


@contextlib.contextmanager
def installation(state):
    harness = base.ToolsUpdateTest()
    paths = {r['path'] for r in json.loads((base.PAYLOAD / 'SHA256.json').read_text())}
    # Exact v2 files, including its old scripts; no v3-only file sneaks into the installed bundle.
    installed = (None, None, tuple(paths - set(old_files())), old_files())
    with patch.object(sys, 'dont_write_bytecode', True), harness.installation(installed=installed, state=state) as values:
        home, run, fingerprint, previous, host = values
        assert previous == hashlib.sha256(blob('SHA256SUMS')).hexdigest()
        with patch.object(version2(), 'HOME', home):
            yield harness, *values


def write_old_change(legacy, kind, status='recorded'):
    before = listed((OLDER, 'S'), OLDER) if kind == 'update' else listed((LATEST, OLDER, 'S'), LATEST)
    target = None if kind == 'update' else list(identity(row(OLDER)))
    reference = LATEST if kind == 'update' else OLDER
    legacy.intend(kind, before, reference, target, None)
    if status == 'recorded':
        made = listed((OLDER, 'S'), OLDER, LATEST) if kind == 'update' else listed((OLDER, LATEST, 'S'), LATEST)
        legacy.finish(kind, made)
    return legacy.load(owner.OUTCOME)


def classified(tools, state, retry=None):
    try:
        return tools.qualified(state, retry=retry), ''
    except owner.Stop as error:
        return 'STOP', str(error)


class CompatibilityTest(unittest.TestCase):
    def test_exact_historical_code_payload_version_and_unchanged_release_history(self):
        self.assertEqual(hashlib.sha256(blob('SHA256SUMS')).hexdigest(), V2_FINGERPRINT)
        self.assertEqual(blob('owner.py'), subprocess.check_output(
            ['git', 'show', COMMIT + ':os/owner-tools/owner.py'], cwd=ROOT))
        self.assertEqual(json.loads(blob('history.json')), dict(tools_version=2, releases=HISTORY))
        self.assertEqual(owner.lineage(base.PAYLOAD), dict(tools_version=3, releases=HISTORY))
        self.assertEqual(version2().Tools.outcome.__code__.co_filename, COMMIT + ':owner.py')

    def test_version3_accepts_every_version2_shape_including_before_first_switch(self):
        accepted = accepted_by_v2()
        self.assertIn('prepared stock', dict(accepted))
        self.assertIn('first switch staged', dict(accepted))
        self.assertIn('update staged over pair', dict(accepted))
        # Six resting pairs, four resting triples, two install states, one update stage.
        self.assertEqual(len(accepted), 13)
        for name, state in accepted:
            with self.subTest(state=name), route(state) as (tools, legacy, host, store):
                self.assertEqual(classified(tools, host.state), (None, ''))
                old_lines = legacy.title()
                previous_title = legacy.load('title')
                self.assertEqual(tools.load('title'), previous_title)
                self.assertEqual(tools.load('prepared'), legacy.load('prepared'))
                new_lines = tools.title()
                if name in ('prepared stock', 'first switch staged'):
                    self.assertEqual(new_lines, old_lines, 'A1 preserves first-install text exactly')
                else:
                    self.assertTrue(any(line.startswith('title ') for line in new_lines))
                self.assertEqual(host.changes, [])
        print('B8: 13/13 historical shapes accepted; before-first-switch title text equal')

    def test_single_stock_prepared_and_first_switch_remain_accepted_and_updatable(self):
        saved = base.prepared()
        saved['state'] = base.machine([copy.deepcopy(saved['stock'])])
        states = [('prepared single stock', saved['state']),
                  ('first switch over single stock', base.machine([row(LATEST, staged=True), *saved['state']['rpm']['deployments']]))]
        for name, state in states:
            with self.subTest(state=name), route(state) as (tools, legacy, host, store):
                tools.save('prepared', saved)
                legacy.qualified(host.state)
                self.assertEqual(classified(tools, host.state), (None, ''))
                self.assertEqual(tools.title(), legacy.title())
                self.assertEqual(host.changes, [])
            with self.subTest(update=name), installation(state) as (harness, home, run, fingerprint, previous, host):
                writer = object.__new__(owner.Tools)
                writer.store = home / 'records'
                writer.save('prepared', saved)
                self.assertEqual(run()[0], 'Tools updated from version 2 to 3')
                harness.updated(home, fingerprint, previous)

    def test_modified_releases_version2_reads_remain_readable(self):
        for field in (*owner.MODIFIED, 'unlocked'):
            state = listed((LATEST, OLDER, 'S'), LATEST)
            state['rpm']['deployments'][0][field] = 'development' if field == 'unlocked' else ['fixture']
            with self.subTest(field=field):
                version2().qualified_state(state, base.prepared(), LATEST, [r['reference'] for r in HISTORY])
                with route(state) as (tools, legacy, host, store):
                    self.assertEqual(classified(tools, host.state), (None, ''))
                    tools.title()
                    self.assertEqual(host.changes, [])
                with installation(state) as (harness, home, run, fingerprint, previous, host):
                    self.assertEqual(run()[0], 'Tools updated from version 2 to 3')
                    harness.updated(home, fingerprint, previous)
                    self.assertEqual(host.state, state)

    def test_tools_update_runs_over_every_historical_resting_and_staged_shape(self):
        for name, state in accepted_by_v2():
            with self.subTest(state=name), installation(state) as (harness, home, run, fingerprint, previous, host):
                before = copy.deepcopy(host.state)
                try:
                    lines = run()
                except owner.Stop as error:
                    self.fail('new tools refused historical ' + name + ': ' + str(error))
                self.assertEqual(lines[0], 'Tools updated from version 2 to 3')
                harness.updated(home, fingerprint, previous)
                self.assertEqual(host.state, before)
                self.assertFalse(any(t.get('mutation') for t in host.trace))
        print('B8: tools update over all 13 historical shapes, no deployment mutation')

    def test_tools_update_on_both_named_stuck_states_with_each_old_previous_form(self):
        states = {
            'stock taken in boot menu beside two releases': listed((LATEST, OLDER, 'S'), 'S'),
            'R13 after previous': listed((OLDER, LATEST, 'S'), OLDER),
            'stock after previous and menu choice': listed((OLDER, LATEST, 'S'), 'S'),
        }
        for name, state in states.items():
            with self.assertRaises(version2().Stop) if 'stock' in name else contextlib.nullcontext():
                version2().qualified_state(state, base.prepared(), LATEST, [r['reference'] for r in HISTORY])
            for status in (None, 'intent', 'recorded'):
                with self.subTest(state=name, record=status), installation(state) as (harness, home, run, fingerprint, previous, host):
                    legacy = version2().Tools(home / 'tools', host, home / 'records')
                    with patch.object(version2(), 'boot_id', return_value='old-boot'):
                        if status:
                            write_old_change(legacy, 'previous', status)
                    with patch.object(owner, 'boot_id', return_value='new-boot'):
                        try:
                            lines = run()
                        except owner.Stop as error:
                            self.fail(name + ' with ' + str(status) + ': ' + str(error))
                    self.assertEqual(lines[0], 'Tools updated from version 2 to 3')
                    harness.updated(home, fingerprint, previous)
                    record = home / 'records' / (owner.OUTCOME + '.json')
                    if status and name.startswith('stock taken'):
                        self.assertFalse(record.exists())
                        self.assertEqual(len(list((home / 'records').glob('*-outcome-not-applied.json'))), 1)
                    elif status:
                        self.assertTrue(record.exists())
                        checker = owner.Tools(home / ('tools-' + fingerprint), host, home / 'records')
                        with patch.object(owner, 'boot_id', return_value='new-boot'):
                            self.assertEqual(checker.outcome(host.state), 'done' if name == 'R13 after previous' else 'elsewhere')
                    self.assertFalse(any(t.get('mutation') for t in host.trace))

    def test_tools_update_with_previous_open_in_both_boots_and_every_running_row(self):
        for order, running, status, same in itertools.product(
                ((LATEST, OLDER, 'S'), (OLDER, LATEST, 'S')), (LATEST, OLDER, 'S'), ('intent', 'recorded'), (False, True)):
            state = listed(order, running)
            with self.subTest(order=order, running=running, status=status, same=same), installation(state) as (harness, home, run, fingerprint, previous, host):
                legacy = version2().Tools(home / 'tools', host, home / 'records')
                with patch.object(version2(), 'boot_id', return_value='old-boot'):
                    write_old_change(legacy, 'previous', status)
                boot = 'old-boot' if same else 'new-boot'
                with patch.object(owner, 'boot_id', return_value=boot):
                    self.assertEqual(run()[0], 'Tools updated from version 2 to 3')
                    checker = owner.Tools(home / ('tools-' + fingerprint), host, home / 'records')
                    expected = (None if order[0] == LATEST else
                        ('applied' if running == OLDER else 'pending') if same else
                        ('done' if running == OLDER else 'elsewhere'))
                    self.assertEqual(checker.outcome(host.state), expected)
                harness.updated(home, fingerprint, previous)
                self.assertFalse(any(t.get('mutation') for t in host.trace))

    def test_old_intents_and_records_obey_the_explicit_journal_outcome_table(self):
        for kind, status in itertools.product(('update', 'previous'), ('intent', 'recorded')):
            for phase, running in [('before', None), ('same', None), ('later', LATEST), ('later', OLDER), ('later', 'S')]:
                before = listed((OLDER, 'S'), OLDER) if kind == 'update' else listed((LATEST, OLDER, 'S'), LATEST)
                with self.subTest(kind=kind, status=status, phase=phase, running=running), route(before) as (tools, legacy, host, store):
                    original = write_old_change(legacy, kind, status)
                    self.assertNotIn('schema', original)
                    if phase == 'before':
                        expected = 'STOP' if kind == 'update' else None
                    elif phase == 'same':
                        host.state = (listed((OLDER, 'S'), OLDER, LATEST) if kind == 'update'
                                      else listed((OLDER, LATEST, 'S'), LATEST))
                        expected = 'STOP' if kind == 'update' and status == 'intent' else 'pending'
                    else:
                        tools.boot[0] = 'boot-2'
                        order = (LATEST, OLDER, 'S') if kind == 'update' else (OLDER, LATEST, 'S')
                        host.state = listed(order, running)
                        expected = 'done' if running == (LATEST if kind == 'update' else OLDER) else 'elsewhere'
                    old_result = None
                    try:
                        old_result = legacy.qualified(host.state)
                    except version2().Stop:
                        old_result = 'STOP'
                    result, message = classified(tools, host.state)
                    self.assertEqual(result, expected)
                    if old_result in ('pending', 'done'):
                        self.assertEqual(result, old_result, 'A9 keeps every outcome v2 accepted')
                    if result == 'STOP':
                        self.assertEqual(tools.load(owner.OUTCOME), original)
                        if status == 'intent':
                            self.assertIn('run sudo /var/lib/ares/at update', message)
                    elif result is None:
                        self.assertFalse((store / (owner.OUTCOME + '.json')).exists())
                        self.assertEqual(len(list(store.glob('*-outcome-not-applied.json'))), 1)
                    else:
                        lines = tools.title()
                        if expected == 'done':
                            self.assertIn('confirmed after the restart', ' '.join(lines))
                            self.assertFalse((store / (owner.OUTCOME + '.json')).exists())
                        else:
                            self.assertNotIn('confirmed', ' '.join(lines))
                            self.assertTrue((store / (owner.OUTCOME + '.json')).exists())
                    self.assertEqual(host.changes, [], 'reading an old intent never repeats its primitive')

    def test_legacy_staging_retry_and_lost_after_restart_and_unknown_list(self):
        for status in ('intent', 'recorded'):
            for case in ('unmade', 'staged', 'lost', 'still-staged-after-restart', 'foreign-list'):
                with self.subTest(status=status, case=case), route(listed((OLDER, 'S'), OLDER)) as (tools, legacy, host, store):
                    write_old_change(legacy, 'update', status)
                    if case in ('staged', 'still-staged-after-restart'):
                        host.state = listed((OLDER, 'S'), OLDER, LATEST)
                    if case in ('lost', 'still-staged-after-restart'):
                        tools.boot[0] = 'boot-2'
                    if case == 'foreign-list':
                        host.state = listed(('S', OLDER), OLDER)
                        tools.boot[0] = 'boot-2'
                    expected = ('retry' if case == 'unmade' else 'complete') if status == 'intent' and case in ('unmade', 'staged') else (
                        None if case == 'lost' else 'pending' if case == 'staged' else 'STOP')
                    result, _ = classified(tools, host.state, retry='update')
                    self.assertEqual(result, expected)
                    self.assertEqual(host.changes, [])

    def test_old_layout_trials_proof_revert_finish_and_abandon(self):
        for phase in ('begin', 'reverted', 'proof', 'finishing-console', 'finishing-both'):
            for finish_with in ('finish', 'abandon'):
                with self.subTest(phase=phase, ending=finish_with), route(listed((OLDER, 'S'), OLDER)) as (tools, legacy, host, store):
                    admin = legacy.session()
                    legacy.layout('begin', 'us-intl')
                    if phase == 'reverted':
                        legacy.layout('revert')
                    if phase in ('proof', 'finishing-console', 'finishing-both'):
                        proof = dict(admin, tty='tty4', session='proof', started_us=int(time.monotonic() * 1e6) + 1)
                        with patch.object(legacy, 'session', return_value=proof), patch('builtins.input', return_value='yz-/!ü'):
                            legacy.layout('proof')
                    if phase.startswith('finishing'):
                        host.cut_keyboard = phase == 'finishing-console'
                        if phase == 'finishing-both':
                            save = legacy.save
                            def cut_save(name, value):
                                if name == 'layout-completed':
                                    raise PowerCut('after persistent writes before completion record')
                                return save(name, value)
                            with patch.object(legacy, 'save', side_effect=cut_save), self.assertRaises(PowerCut):
                                legacy.layout('finish')
                        else:
                            with self.assertRaises(PowerCut):
                                legacy.layout('finish')
                    pending = legacy.load('layout-pending')
                    self.assertNotIn('finish_proof', pending)
                    self.assertEqual(tools.load('layout-pending'), pending)
                    if phase.startswith('finishing') and finish_with == 'finish':
                        with self.assertRaisesRegex(owner.Stop, 'Finished system settings changed'):
                            tools.layout('finish')
                    if finish_with == 'abandon' or phase.startswith('finishing'):
                        fresh = dict(admin, session='fresh', started_us=int(time.monotonic() * 1e6) + 1)
                        with patch.object(tools, 'session', return_value=fresh):
                            tools.layout('abandon')
                        expected = PROFILES['de']
                    else:
                        if not pending['proof']:
                            proof = dict(admin, tty='tty4', session='v3-proof', started_us=int(time.monotonic() * 1e6) + 1)
                            with patch.object(tools, 'session', return_value=proof), patch('builtins.input', return_value='yz-/!ü'):
                                tools.layout('proof')
                        tools.layout('finish')
                        expected = PROFILES['de' if phase == 'reverted' else 'us-intl']
                    self.assertEqual(host.keyboard(), expected)
                    self.assertFalse((store / 'layout-pending.json').exists())

    def test_old_completed_and_abandoned_layout_records_and_titles_remain_readable(self):
        for ending in ('finish', 'abandon'):
            with self.subTest(ending=ending), route(listed((OLDER, 'S'), OLDER)) as (tools, legacy, host, store):
                admin = legacy.session()
                legacy.layout('begin', 'us-intl')
                fresh = dict(admin, tty='tty4', session='fresh', started_us=int(time.monotonic() * 1e6) + 1)
                if ending == 'finish':
                    with patch.object(legacy, 'session', return_value=fresh), patch('builtins.input', return_value='yz-/!ü'):
                        legacy.layout('proof')
                    legacy.layout('finish')
                else:
                    with patch.object(legacy, 'session', return_value=fresh):
                        legacy.layout('abandon')
                name = 'layout-completed' if ending == 'finish' else 'layout-abandoned'
                record = legacy.load(name)
                self.assertEqual(tools.load(name), record)
                self.assertEqual(tools.load('title'), legacy.load('title'))
                self.assertIn('Loaded y/z map, cmdline and all retained BLS maps passed', tools.check())
                self.assertEqual(tools.load(name), record)
                self.assertFalse((store / 'layout-pending.json').exists())

    def test_old_interrupted_finish_then_v3_revert_preserves_finish_proof_beside_null_proof(self):
        with route(listed((OLDER, 'S'), OLDER)) as (tools, legacy, host, store):
            admin = legacy.session()
            legacy.layout('begin', 'us-intl')
            proof = dict(admin, tty='tty4', session='proof', started_us=int(time.monotonic() * 1e6) + 1)
            with patch.object(legacy, 'session', return_value=proof), patch('builtins.input', return_value='yz-/!ü'):
                legacy.layout('proof')
            host.cut_keyboard = True
            with self.assertRaises(PowerCut):
                legacy.layout('finish')
            tools.layout('revert')
            pending = tools.load('layout-pending')
            self.assertIsNone(pending['proof'])
            self.assertEqual(pending['finish_proof'], proof)
            with patch.object(tools, 'session', return_value=dict(admin, session='fresh', started_us=int(time.monotonic() * 1e6) + 1)):
                tools.layout('abandon')
            self.assertEqual(host.keyboard(), PROFILES['de'])
            self.assertFalse((store / 'layout-pending.json').exists())

    def test_unknown_schema_refuses_read_and_tools_update_without_writes(self):
        with route(listed((LATEST, OLDER, 'S'), LATEST)) as (tools, legacy, host, store):
            old = write_old_change(legacy, 'previous')
            tools.save(owner.OUTCOME, dict(old, schema='change99', mode='reorder'))
            before = {p.name: p.read_bytes() for p in store.iterdir()}
            self.assertEqual(classified(tools, host.state)[0], 'STOP')
            self.assertEqual(before, {p.name: p.read_bytes() for p in store.iterdir()})
            self.assertEqual(host.changes, [])
        with installation(listed((LATEST, OLDER, 'S'), LATEST)) as (harness, home, run, fingerprint, previous, host):
            records = owner.Tools(home / 'tools', host, home / 'records')
            records.save(owner.OUTCOME, dict(schema='change99', mode='reorder'))
            before = harness.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, 'unknown tools'):
                run()
            self.assertEqual(harness.snapshot(home), before)


class PublicationTest(unittest.TestCase):
    @contextlib.contextmanager
    def observed(self, home, stop=None):
        seen = []
        copy2, replace, save = owner.shutil.copy2, pathlib.Path.replace, owner.Tools.save
        def hit(kind):
            journal = home / (owner.TOOLS_JOURNAL + '.json')
            phase = json.loads(journal.read_text())['phase'] if journal.exists() else None
            seen.append((kind, phase))
            if stop == len(seen):
                raise PowerCut('before publication, event ' + str(stop))
        def copied(*args, **kwargs):
            result = copy2(*args, **kwargs)
            hit('copy')
            return result
        def replaced(path, target):
            result = replace(path, target)
            hit('replace')
            return result
        def saved(obj, name, value):
            result = save(obj, name, value)
            hit('save')
            return result
        with patch.object(owner.shutil, 'copy2', side_effect=copied), patch.object(pathlib.Path, 'replace', replaced), \
                patch.object(owner.Tools, 'save', saved):
            yield seen

    def test_readiness_does_not_migrate_legacy_intents_before_publication(self):
        state = listed((OLDER, LATEST, 'S'), OLDER)
        with installation(state) as (harness, home, run, fingerprint, previous, host):
            legacy = version2().Tools(home / 'tools', host, home / 'records')
            with patch.object(version2(), 'boot_id', return_value='old-boot'):
                original = write_old_change(legacy, 'previous', 'intent')
            save = owner.Tools.save
            def cut(obj, name, value):
                result = save(obj, name, value)
                if name == owner.TOOLS_JOURNAL:
                    raise PowerCut('first v3 tools journal, before publication')
                return result
            with patch.object(owner, 'boot_id', return_value='new-boot'), patch.object(owner.Tools, 'save', cut), self.assertRaises(PowerCut):
                owner.update_tools(home.parent / 'usb/ares-tools', fingerprint, host, None)
            version2().settle_tools()
            self.assertEqual(legacy.load(owner.OUTCOME), original, 'readiness made the restored v2 tools unable to read their intent')
            with patch.object(version2(), 'boot_id', return_value='new-boot'):
                self.assertEqual(legacy.qualified(host.state, retry='previous'), 'complete')
            self.assertEqual(run()[0], 'Tools updated from version 2 to 3')
            harness.updated(home, fingerprint, previous)

    def test_not_applied_is_archived_and_reported_only_after_publication(self):
        with installation(listed((LATEST, OLDER, 'S'), LATEST)) as (harness, home, run, fingerprint, previous, host):
            legacy = version2().Tools(home / 'tools', host, home / 'records')
            with patch.object(version2(), 'boot_id', return_value='old-boot'):
                write_old_change(legacy, 'previous')
            phases = []
            archive = owner.Tools.archive
            def archived(obj, name, value):
                journal = home / (owner.TOOLS_JOURNAL + '.json')
                phases.append(json.loads(journal.read_text())['phase'] if journal.exists() else None)
                return archive(obj, name, value)
            with patch.object(owner, 'boot_id', return_value='new-boot'), patch.object(owner.Tools, 'archive', archived):
                lines = run()
            self.assertEqual(phases, ['retire'], 'readiness must leave the old tools their old records until publication')
            self.assertTrue(any('was not applied' in line for line in lines))
            harness.updated(home, fingerprint, previous)

    @contextlib.contextmanager
    def publication_case(self, versioned, open_change):
        state = listed((OLDER, LATEST, 'S'), OLDER) if open_change else listed((OLDER, 'S'), OLDER)
        with installation(state) as values, contextlib.ExitStack() as stack:
            harness, home, run, fingerprint, previous, host = values
            old_name = 'tools-' + previous if versioned else 'tools'
            if versioned:
                (home / 'tools').rename(home / old_name)
                owner.switch_entry(old_name)
            legacy = version2().Tools(home / old_name, host, home / 'records')
            original = None
            if open_change:
                with patch.object(version2(), 'boot_id', return_value='old-boot'):
                    original = write_old_change(legacy, 'previous', 'intent')
            stack.enter_context(patch.object(owner, 'boot_id', return_value='new-boot'))
            stack.enter_context(patch.object(version2(), 'boot_id', return_value='new-boot'))
            yield (*values, old_name, legacy, original)

    def test_version2_settles_every_v3_cut_before_publication_and_v3_resumes(self):
        for versioned, open_change in itertools.product((False, True), repeat=2):
            with self.publication_case(versioned, open_change) as (harness, home, run, fingerprint, previous, host, old_name, legacy, original):
                with self.observed(home) as seen:
                    owner.update_tools(home.parent / 'usb/ares-tools', fingerprint, host, None)
                cuts = [i for i, (_, phase) in enumerate(seen, 1) if phase in ('copy', 'publish')]
                self.assertTrue(cuts)
                self.assertTrue({'copy', 'publish'} <= {seen[i - 1][1] for i in cuts})
                self.assertTrue({'copy', 'replace', 'save'} <= {seen[i - 1][0] for i in cuts})
            for cut in cuts:
                with self.subTest(versioned=versioned, open_change=open_change, cut=cut), self.publication_case(versioned, open_change) as (
                        harness, home, run, fingerprint, previous, host, old_name, legacy, original):
                    with self.observed(home, cut), self.assertRaises(PowerCut):
                        owner.update_tools(home.parent / 'usb/ares-tools', fingerprint, host, None)
                    raw = json.loads((home / (owner.TOOLS_JOURNAL + '.json')).read_text())
                    self.assertEqual(raw['schema'], 'tools-update1')
                    self.assertEqual(raw['previous_version'], 2)
                    self.assertEqual(raw['tools_version'], 3)
                    self.assertIn(raw['phase'], ('copy', 'publish'))
                    settled = version2().settle_tools()
                    self.assertEqual(settled, raw)
                    self.assertEqual(owner.entry_toolset(), old_name)
                    self.assertEqual(version2().checked_bundle(home / old_name), previous)
                    self.assertFalse((home / 'retired-tools' / previous).exists())
                    if open_change:
                        self.assertEqual(legacy.load(owner.OUTCOME), original, 'pre-publication migration broke the old reader')
                        self.assertEqual(legacy.qualified(host.state, retry='previous'), 'complete')
                    self.assertEqual(run()[0], 'Tools updated from version 2 to 3')
                    harness.updated(home, fingerprint, previous)
            print('B8: v2 settle_tools read v3 tools-update1 at', len(cuts), 'pre-publication cuts; versioned=', versioned,
                  'open_previous_intent=', open_change)


def mutated(function, before, after):
    source = textwrap.dedent(inspect.getsource(function))
    assert source.count(before) == 1
    namespace = {}
    exec(compile(source.replace(before, after), '<22c B8 rule removed>', 'exec'), owner.__dict__, namespace)
    return namespace[function.__name__]


class CompatibilityRevertsTest(unittest.TestCase):
    def detected(self, name):
        result = unittest.TestResult()
        CompatibilityTest(name).run(result)
        self.assertEqual(result.errors, [], 'an unrelated exception is not a compatibility proof')
        self.assertTrue(result.failures, name + ' did not detect the reverted rule')

    def test_records_writing_before_resolution_fails_the_unchanged_record_assertion(self):
        changed = mutated(owner.Tools.records, 'self.survey()', 'pass')
        with patch.object(owner.Tools, 'records', changed):
            result = unittest.TestResult()
            base.IntentTest('test_every_interruption_resolves_by_list_except_same_boot_staging').run(result)
            self.assertEqual(result.errors, [], 'an unrelated exception is not a records-order proof')
            self.assertTrue(result.failures, 'record-c write before resolution went unnoticed')

    def test_removing_legacy_record_reading_fails_the_outcome_table(self):
        # Deliberately reject legacy data with Stop, rather than an unrelated KeyError.
        real = owner.journalled
        def no_legacy(value):
            if 'schema' not in value:
                raise owner.Stop('Legacy journal no longer accepted')
            return real(value)
        with patch.object(owner, 'journalled', no_legacy):
            self.detected('test_old_intents_and_records_obey_the_explicit_journal_outcome_table')

    def test_restoring_old_shape_gate_fails_acceptance_of_named_stuck_states(self):
        real = owner.qualified_state
        def pair_and_direction_gate(state, saved, release, history=None):
            try:
                version2().qualified_state(state, saved, release, history)
            except version2().Stop as error:
                raise owner.Stop(str(error)) from None
            return real(state, saved, release, history)
        with patch.object(owner, 'qualified_state', pair_and_direction_gate):
            self.detected('test_tools_update_on_both_named_stuck_states_with_each_old_previous_form')

    def test_persisting_readiness_before_publication_breaks_old_intent_recovery(self):
        changed = mutated(owner.update_tools, 'if not resolve:', 'if False:')
        with patch.object(owner, 'update_tools', changed):
            result = unittest.TestResult()
            PublicationTest('test_readiness_does_not_migrate_legacy_intents_before_publication').run(result)
            self.assertEqual(result.errors, [], 'an unrelated exception is not a publication proof')
            self.assertTrue(result.failures, 'legacy-record byte equality did not detect premature migration')

    def test_changing_tools_update_schema_breaks_v2_recovery(self):
        changed = mutated(owner.update_tools, "dict(schema='tools-update1'", "dict(schema='tools-update3'")
        with installation(listed((OLDER, 'S'), OLDER)) as (harness, home, run, fingerprint, previous, host):
            save = owner.Tools.save
            def cut(obj, name, value):
                result = save(obj, name, value)
                if name == owner.TOOLS_JOURNAL:
                    raise PowerCut('first v3 tools journal')
                return result
            with patch.object(owner.Tools, 'save', cut), self.assertRaises(PowerCut):
                changed(home.parent / 'usb/ares-tools', fingerprint, host, None)
            before = harness.snapshot(home)
            with self.assertRaisesRegex(version2().Stop, 'Invalid tools update journal'):
                version2().settle_tools()
            self.assertEqual(before, harness.snapshot(home))


if __name__ == '__main__':
    unittest.main()
