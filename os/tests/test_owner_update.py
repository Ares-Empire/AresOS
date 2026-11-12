"""Update route: shapes, at update/previous/check, and tools updating themselves.

Deployment lists start from the retained package 13 AresOS/stock pair. Newer
releases are synthetic digests; bootc's own staging and rollback list rules are
modelled in ordinary JSON. The real release-script bodies execute against that
model. No registry, credential, privilege, disk or boot setting is touched.
"""
import base64
import contextlib
import copy
import hashlib
import io
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import time
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_owner_tools as common
from guest_shell import syntax
from test_owner_devices import FixtureHost, fixture

ROOT, owner = common.ROOT, common.owner
PAYLOAD = ROOT / 'os/owner-tools/payload'
VALUES = {r['kind']: r['value'] for r in json.loads((ROOT / 'os/tests/fixtures/owner-tools/retained-parsers.json').read_text())}
# The modelled machine runs release 13, the laptop's release; R21 and R30 are
# synthetic newer releases. The pinned release (27) is checked separately.
RELEASE = json.loads((ROOT / 'os/manifest/releases/13.json').read_text())
PINNED = json.loads((ROOT / 'os/manifest/release.json').read_text())
R13 = RELEASE['reference']
R21 = 'ghcr.io/ares-empire/aresos@sha256:' + '21' * 32
R30 = 'ghcr.io/ares-empire/aresos@sha256:' + '30' * 32
R99 = 'ghcr.io/ares-empire/aresos@sha256:' + '99' * 32
IDENTITY = 'https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/main'
BASE_STATE = dict(rpm=VALUES['aresos rpm-ostree-status'], bootc=VALUES['aresos bootc-status'])
R13_ROW = next(d for d in BASE_STATE['rpm']['deployments'] if d['booted'])
STOCK_ROW = next(d for d in BASE_STATE['rpm']['deployments'] if d['pinned'])
CHECKSUMS = {R13: R13_ROW['checksum'], R21: 'c1' * 32, R30: 'c3' * 32, R99: 'c9' * 32}
DE = dict(VConsoleKeymap='de', VConsoleKeymapToggle='', X11Layout='de', X11Model='pc105', X11Variant='', X11Options='')


def record(reference, wheel, identity=IDENTITY):
    return dict(reference=reference, identity=RELEASE['signature']['identity'] if reference == R13 else identity, daily_wheel=wheel)


H13 = [record(R13, False)]
H21 = [record(R13, False), record(R21, True)]
H30 = [*H21, record(R30, True)]


def release_row(reference, booted=False, staged=False, checksum=None):
    row = copy.deepcopy(R13_ROW)
    row.update(checksum=checksum or CHECKSUMS[reference], serial=0, booted=booted, staged=staged, pinned=False,
               **{'container-image-reference': 'ostree-unverified-registry:' + reference,
                  'container-image-reference-digest': reference.split('@')[1]})
    return row


def stock_row(booted=False):
    return dict(copy.deepcopy(STOCK_ROW), booted=booted)


def slot(row):
    return dict(ostree=dict(checksum=row['checksum'], deploySerial=row['serial'], stateroot=row['osname']),
                pinned=row['pinned'], image=dict(image=dict(image=owner.image_reference(row), transport='registry'),
                                                  imageDigest=row['container-image-reference-digest']))


def machine(rows):
    """rpm-ostree rows in deployment order, with bootc's slots derived by its rules.

    Staged first; rollback is the first other deployment; it is queued when it
    precedes the booted one (bootc status, as in the retained fixtures).
    """
    rows = copy.deepcopy(rows)
    booted = next(i for i, r in enumerate(rows) if r['booted'])
    staged = [r for r in rows if r.get('staged')]
    others = [i for i, r in enumerate(rows) if not r.get('staged') and i != booted]
    bootc = copy.deepcopy(BASE_STATE['bootc'])
    bootc['status'].update(booted=slot(rows[booted]), staged=slot(staged[0]) if staged else None,
                           rollback=slot(rows[others[0]]) if others else None,
                           rollbackQueued=bool(others) and others[0] < booted)
    return dict(rpm=dict(copy.deepcopy(BASE_STATE['rpm']), deployments=rows), bootc=bootc)


def pair(reference=R13):
    return machine([release_row(reference, booted=True), stock_row()])


def staged_update():
    return machine([release_row(R21, staged=True), release_row(R13, booted=True), stock_row()])


def updated():
    return machine([release_row(R21, booted=True), release_row(R13), stock_row()])


def queued_previous():
    return machine([release_row(R13), release_row(R21, booted=True), stock_row()])


def returned():
    return machine([release_row(R13, booted=True), release_row(R21), stock_row()])


def staged_later():
    return machine([release_row(R30, staged=True), release_row(R21, booted=True), release_row(R13), stock_row()])


def prepared():
    state = dict(rpm=copy.deepcopy(VALUES['after-pin rpm-ostree-status']), bootc=copy.deepcopy(VALUES['after-pin bootc-status']))
    stock = owner.agree(state)
    return dict(state=state, stock=copy.deepcopy(stock), stock_identity=list(owner.key(stock)))


def bls_for(state):
    entries = []
    for number, row in enumerate([d for d in state['rpm']['deployments'] if not d.get('staged')], 1):
        name = ('Bazzite stock ' if row['container-image-reference-digest'] == owner.BASE else 'AresOS ') + row['checksum'][:8]
        entries.append(dict(file='/boot/loader/entries/ostree-%d.conf' % number,
            content='title %s\noptions quiet ostree=/ostree/boot.1/default/%s/%d\n' % (name, row['checksum'], row['serial']),
            title=name, target='/sysroot/ostree/deploy/default/deploy/%s.%d' % (row['checksum'], row['serial']),
            identity=[row['checksum'], row['serial'], row['osname']]))
    return entries


def write_bundle(destination, history=None, target=None, drop=(), extra=None):
    """Reviewed payload bytes with only release data replaced; manifests regenerated."""
    files = {row['path']: (PAYLOAD / row['path']).read_bytes() for row in json.loads((PAYLOAD / 'SHA256.json').read_text())}
    if history is not None:
        files['history.json'] = (json.dumps(history, indent=2) + '\n').encode()
    if target is None and 'history.json' in drop:
        # A history-less (15f) bundle targets release 13, as on the laptop.
        files['release.json'] = (ROOT / 'os/manifest/releases/13.json').read_bytes()
    if target is not None:
        release = copy.deepcopy(RELEASE)
        release['reference'], release['signature']['identity'] = target['reference'], target['identity']
        files['release.json'] = (json.dumps(release, indent=2) + '\n').encode()
    for name in drop:
        files.pop(name)
    files.update(extra or {})
    destination = pathlib.Path(destination)
    destination.mkdir(parents=True)
    rows = []
    for name in sorted(files):
        (destination / name).parent.mkdir(parents=True, exist_ok=True)
        (destination / name).write_bytes(files[name])
        rows.append(dict(sha256=hashlib.sha256(files[name]).hexdigest(), path=name))
    raw = (json.dumps(rows, indent=2) + '\n').encode()
    sums = ''.join(r['sha256'] + '  ' + r['path'] + '\n' for r in rows) + hashlib.sha256(raw).hexdigest() + '  SHA256.json\n'
    (destination / 'SHA256.json').write_bytes(raw)
    (destination / 'SHA256SUMS').write_text(sums)
    assert owner.checked_bundle(destination) == hashlib.sha256(sums.encode()).hexdigest()
    return hashlib.sha256(sums.encode()).hexdigest()


def history(rows, version=3):
    return dict(tools_version=version, releases=rows)


class Machine(owner.Host):
    """Host adapter over an ordinary JSON machine; mutations only change that model."""

    def __init__(self, state, wheel=False, signed=None):
        super().__init__()
        self.state, self.wheel, self.signed = copy.deepcopy(state), wheel, signed or {}
        self.changes = []
        self.during_verify = None
        self.interrupt = None  # (script name, 'before' | 'after' | 'observe')

    def read(self, *command, **unused):
        self.trace.append(dict(command=list(command), mutation=False))
        if command == ('id', '-u', 'ares'):
            return '1001\n'
        if command == ('id', '-nG', 'ares'):
            return 'ares wheel\n' if self.wheel else 'ares\n'
        if command[0] == 'pgrep':
            return '4242\n'
        if command[0] == 'dumpkeys':
            return json.loads((ROOT / 'os/tests/fixtures/owner-tools/dumpkeys-de.json').read_text())
        if command == ('efibootmgr', '-v'):
            return 'BootCurrent: 0001\n'
        raise AssertionError('Unmodelled read: ' + repr(command))

    def json(self, *command):
        self.trace.append(dict(command=list(command), mutation=False))
        if self.interrupt == 'reading':
            self.interrupt = None
            raise OSError('injected status read failure after the change')
        if command == ('rpm-ostree', 'status', '--json'):
            return copy.deepcopy(self.state['rpm'])
        if command == ('bootc', 'status', '--json'):
            return copy.deepcopy(self.state['bootc'])
        raise AssertionError('Unmodelled query: ' + repr(command))

    def mutate(self, *command, **unused):
        self.trace.append(dict(command=list(command), mutation=True))
        self.changes.append(command)
        if command == ('rpm-ostree', 'cleanup', '--pending'):
            # As rpm-ostree does: the staged deployment goes, everything else stays.
            self.state = machine([r for r in self.state['rpm']['deployments'] if not r.get('staged')])

    def start(self, text, name):
        return ModelStep(self, text, name)

    def script(self, text, name, mutation=True):
        syntax(name, text)
        self.trace.append(dict(script=name, mutation=mutation))
        if name == 'verify':
            if self.during_verify:
                self.during_verify()
            # cosign: only a signature by the recorded identity verifies.
            identity = re.search(r"--certificate-identity '([^']+)'", text)[1]
            reference = re.findall(r"'([^']+)'", text.strip().splitlines()[-1])[-1]
            if self.signed.get(reference) != identity:
                raise owner.Stop('Shared step failed: verify; preserve diagnostics and do not reboot')
            return ''
        marker = text.split("<<'", 1)[1].split("'", 1)[0]
        body = text.split("<<'" + marker + "'\n", 1)[1].split('\n' + marker + '\n', 1)[0]
        tail = text.split('\n' + marker + '\n', 1)[1].strip()
        answer = lambda argv, **kw: json.dumps(self.state['bootc' if argv[0] == 'bootc' else 'rpm'])
        with patch('subprocess.check_output', side_effect=answer), contextlib.redirect_stdout(io.StringIO()):
            try:
                exec(compile(body, name, 'exec'), {'__name__': 'owner_shared_step'})
            except AssertionError:
                raise owner.Stop('Shared step failed: ' + name + '; preserve diagnostics and do not reboot') from None
        if self.interrupt == (name, 'before'):
            self.interrupt = None
            raise owner.Stop('Shared step failed: ' + name + '; injected before the change')
        rows = self.state['rpm']['deployments']
        # The one transaction after the shell checks (update.sh first unmasks
        # the staging finalizers; test_release27.UpdateFinalizerTest runs that part).
        tail, = [line for line in tail.splitlines() if line.startswith(('bootc switch --retain ', 'bootc rollback'))]
        if tail.startswith('bootc switch --retain '):
            reference = tail.split()[-1]
            self.state = machine([release_row(reference, staged=True), *rows])
        elif tail == 'bootc rollback':
            booted = next(i for i, r in enumerate(rows) if r['booted'])
            other = next(i for i, r in enumerate(rows) if not r.get('staged') and i != booted)
            self.state = machine([rows[other], rows[booted], *[r for i, r in enumerate(rows) if i not in (other, booted)]])
        else:
            raise AssertionError('Unmodelled shared step: ' + tail)
        self.changes.append(tail)
        if self.interrupt == (name, 'after'):
            self.interrupt = None
            raise owner.Stop('Shared step failed: ' + name + '; injected after the change')
        if self.interrupt == (name, 'observe'):
            self.interrupt = 'reading'
        return ''


class ModelStep:
    """The update step on the modelled machine: Machine.script's model, reported as owner.Step does."""

    def __init__(self, host, text, name):
        self.host, self.text, self.name = host, text, name
        self.stdout = self.stderr = ''
        self.process = SimpleNamespace(returncode=None)

    def wait(self, timeout, signals=None):
        try:
            self.host.script(self.text, self.name)
        except owner.Stop:
            self.process.returncode = 1
            return 'failed'
        self.process.returncode = 0
        return 'done'

    def stop(self):
        return True

    def record(self, mutation, stopped=None, gone=None):
        # Machine.script already traced the step itself.
        return dict(step=self.name, mutation=mutation, stopped=stopped, group_gone=gone)


@contextlib.contextmanager
def route(state, bundle_history=H21, target=None, wheel=False, signed=None, login=True, host_class=None):
    """Tools over a synthetic target bundle and a modelled running machine."""
    target = target or bundle_history[-1]
    with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary, contextlib.ExitStack() as stack:
        root = pathlib.Path(temporary)
        payload = root / 'home/tools'
        write_bundle(payload, history(bundle_history), target)
        store = root / 'home/records'
        store.mkdir()
        host = (host_class or Machine)(state, wheel, {R21: IDENTITY, R30: IDENTITY} if signed is None else signed)
        tools = owner.Tools(payload, host, store)
        tools.processes = lambda: []
        tools.keyboard = lambda: dict(DE)
        tools.save('prepared', prepared())
        tools.save('disks', dict(target='TARGET', protected='KEEP'))
        tools.save('network-verified', {})
        tools.boot = ['boot-1']
        stack.enter_context(patch.object(owner, 'boot_id', side_effect=lambda: tools.boot[0]))
        auth = root / 'auth.json'
        if login:
            encoded = base64.b64encode(b'synthetic:fixture-only').decode()
            auth.write_text(json.dumps(dict(auths={'ghcr.io': dict(auth=encoded)})))
        stack.enter_context(patch.object(owner, 'AUTH', auth))
        stack.enter_context(patch.object(owner, 'authentication'))
        tools.validated = stack.enter_context(patch.object(owner, 'validate_login'))
        stack.enter_context(patch.object(owner, 'disk_record', return_value=dict(target=dict(path='/dev/FIXTURE', serial='TARGET'), esp_guid='fixture')))
        stack.enter_context(patch.object(owner, 'resolved_bls', side_effect=lambda: bls_for(host.state)))
        stack.enter_context(patch.object(owner, 'runtime_state', return_value={}))
        stack.enter_context(patch.object(owner, 'media_module', return_value=Mock(find=Mock(return_value=None))))
        real_which = shutil.which
        stack.enter_context(patch.object(owner.shutil, 'which',
            side_effect=lambda name, *a, **kw: '/usr/bin/cosign' if name == 'cosign' else real_which(name, *a, **kw)))
        original = pathlib.Path.read_text
        stack.enter_context(patch.object(pathlib.Path, 'read_text',
            lambda p, *a, **kw: 'BOOT_IMAGE=fixture quiet\n' if str(p) == '/proc/cmdline' else original(p, *a, **kw)))
        yield tools, host, store


class ShapeTest(unittest.TestCase):
    def accept(self, state, known):
        refs = [row['reference'] for row in known]
        owner.qualified_state(state, prepared(), refs[-1], refs)

    def refuse(self, state, known, message=None):
        refs = [row['reference'] for row in known]
        with self.assertRaises(owner.Stop) as caught:
            owner.qualified_state(state, prepared(), refs[-1], refs)
        if message:
            self.assertIn(message, str(caught.exception))

    def test_model_reproduces_the_retained_pair_and_bootc_slots_of_every_retained_stage(self):
        self.assertEqual(pair()['rpm']['deployments'], BASE_STATE['rpm']['deployments'])
        self.assertEqual(owner.key(owner.agree(pair())), owner.key(owner.agree(BASE_STATE)))
        for stage in ('after-pin', 'after-switch-staged', 'aresos', 'after-rollback-queued', 'rollback'):
            real = VALUES[stage + ' bootc-status']['status']
            model = machine(VALUES[stage + ' rpm-ostree-status']['deployments'])['bootc']['status']
            with self.subTest(stage=stage):
                for name in ('booted', 'staged', 'rollback'):
                    self.assertEqual((model[name] or {}).get('ostree'), (real[name] or {}).get('ostree'))
                self.assertEqual(model['rollbackQueued'], real['rollbackQueued'])

    def test_every_update_shape_is_accepted(self):
        for name, state, known in (('pair before update', pair(), H21), ('staged update', staged_update(), H21),
                                   ('after the reboot', updated(), H21), ('queued previous', queued_previous(), H21),
                                   ('previous booted', returned(), H21), ('later update staged', staged_later(), H30),
                                   ('updated, newer bundle', updated(), H30), ('pair, current tools', pair(), H13)):
            with self.subTest(name=name):
                self.accept(state, known)

    def test_wrong_shapes_are_refused(self):
        def rows(state):
            return copy.deepcopy(state['rpm']['deployments'])
        cases = {
            'staged older release': (machine([release_row(R13, staged=True, checksum='d1' * 32), release_row(R21, booted=True), stock_row()]), H21),
            'staged not the target': (staged_update(), H30),
            'unknown running release': (machine([release_row(R99, booted=True), release_row(R13), stock_row()]), H21),
            'unknown pair release': (pair(R99), H21),
            'stock not last': (machine([release_row(R21, booted=True), stock_row(), release_row(R13)]), H21),
            'stock booted beside two releases': (machine([release_row(R21), release_row(R13), stock_row(True)]), H21),
            'four deployments': (machine([release_row(R30, booted=True), release_row(R21), release_row(R13), stock_row()]), H30),
            'two staged rows': (machine([release_row(R30, staged=True), release_row(R21, staged=True), release_row(R13, booted=True), stock_row()]), H30),
            'same release twice': (machine([release_row(R21, booted=True), release_row(R21, checksum='d2' * 32), stock_row()]), H21),
            'extra deployment beside a staged update': (machine([release_row(R30, staged=True), release_row(R21, booted=True),
                                                                 release_row(R13), stock_row(), dict(stock_row(), serial=9, pinned=False)]), H30),
        }
        for change in ('pinned release', 'unpinned stock', 'stock digest', 'origin', 'queued staged', 'wrong rollback slot', 'running not default'):
            state = updated() if change not in ('queued staged',) else staged_update()
            if change == 'pinned release':
                state = machine([dict(rows(state)[0]), dict(rows(state)[1], pinned=True), rows(state)[2]])
            elif change == 'unpinned stock':
                state = machine([*rows(state)[:2], dict(rows(state)[2], pinned=False)])
            elif change == 'stock digest':
                state = machine([*rows(state)[:2], dict(rows(state)[2], **{'container-image-reference-digest': 'sha256:' + 'e' * 64})])
            elif change == 'origin':
                state = machine([dict(rows(state)[0], **{'container-image-reference': 'ostree-unverified-registry:ghcr.io/other/aresos@' + R21.split('@')[1]}), *rows(state)[1:]])
            elif change == 'queued staged':
                state['bootc']['status']['rollbackQueued'] = True
            elif change == 'wrong rollback slot':
                state['bootc']['status']['rollback'] = slot(rows(state)[2])
            else:
                state = machine([release_row(R13), release_row(R21, booted=True), stock_row()])
                state['bootc']['status']['rollbackQueued'] = False
            cases[change] = (state, H21)
        for name, (state, known) in cases.items():
            with self.subTest(name=name):
                self.refuse(state, known)

    def test_recovery_and_layout_pair_accepts_any_known_release_but_only_the_pair(self):
        saved = prepared()
        refs = [row['reference'] for row in H21]
        self.assertEqual(owner.key(owner.preflight_recovery(pair(), [], saved, R21, history=refs)), tuple(saved['stock_identity']))
        for state in (updated(), staged_update(), pair(R99)):
            with self.subTest(state=state['bootc']['status']['booted']['image']['imageDigest'][:16]):
                with self.assertRaises(owner.Stop):
                    owner.preflight_recovery(state, [], saved, R21, history=refs)
        with self.assertRaisesRegex(owner.Stop, 'Wrong AresOS target'):
            owner.preflight_recovery(pair(), [], saved, R21)


class HistoryTest(unittest.TestCase):
    def test_reviewed_history_ends_with_the_pinned_release_and_r13_is_not_wheel(self):
        value = owner.lineage(PAYLOAD)
        self.assertEqual(value['tools_version'], 2)
        # Package 27 appended release 27, whose daily account is an administrator.
        self.assertEqual(value['releases'][:1], H13)
        self.assertEqual(value['releases'][-1], dict(reference=PINNED['reference'], identity=PINNED['signature']['identity'],
                                                     daily_wheel=True))
        self.assertEqual(len(value['releases']), 2)
        self.assertIs(value['releases'][0]['daily_wheel'], False)
        self.assertEqual((ROOT / 'os/owner-tools/history.json').read_bytes(), (PAYLOAD / 'history.json').read_bytes())

    def test_every_release_declares_exactly_one_account_rule_and_history_stays_strict(self):
        good = history(H21)
        mutations = {
            'either': lambda v: v['releases'][1].update(daily_wheel=None),
            'string rule': lambda v: v['releases'][1].update(daily_wheel='either'),
            'missing rule': lambda v: v['releases'][1].pop('daily_wheel'),
            'extra field': lambda v: v['releases'][1].update(note='x'),
            'old version': lambda v: v.update(tools_version=1),
            'empty': lambda v: v.update(releases=[]),
            'duplicate digest': lambda v: v['releases'].append(dict(v['releases'][1])),
            'stock digest': lambda v: v['releases'].append(record('ghcr.io/ares-empire/aresos@' + owner.BASE, True)),
            'other registry': lambda v: v['releases'][1].update(reference='ghcr.io/other/aresos@' + R21.split('@')[1]),
            'other identity': lambda v: v['releases'][1].update(identity='https://github.com/someone/AresOS/.github/workflows/x.yml@refs/heads/main'),
            'quoted identity': lambda v: v['releases'][1].update(identity=IDENTITY + "'"),
        }
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            root = pathlib.Path(temporary)
            write_bundle(root / 'good', good, H21[-1])
            self.assertEqual(owner.lineage(root / 'good')['releases'], H21)
            for name, change in mutations.items():
                value = copy.deepcopy(good)
                change(value)
                with self.subTest(name=name), self.assertRaises((owner.Stop, KeyError)):
                    target = H21[-1] if name not in ('duplicate digest', 'stock digest') else value['releases'][-1]
                    write_bundle(root / name.replace(' ', '-'), value, target)
                    owner.lineage(root / name.replace(' ', '-'))
            write_bundle(root / 'mismatch', good, record(R30, True))
            with self.assertRaisesRegex(owner.Stop, 'newest history record'):
                owner.lineage(root / 'mismatch')
            (root / 'dup').mkdir()
            shutil.copy(PAYLOAD / 'release.json', root / 'dup/release.json')
            (root / 'dup/history.json').write_text('{"tools_version": 2, "tools_version": 3, "releases": []}')
            with self.assertRaisesRegex(owner.Stop, 'Duplicate JSON key'):
                owner.lineage(root / 'dup')

    def test_installed_history_must_be_a_prefix_and_legacy_tools_are_only_the_15f_bundle(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            old = write_bundle(pathlib.Path(temporary) / 'legacy', drop=('history.json',))
            with patch.object(owner, 'LEGACY_TOOLS', (old,)):
                version, legacy = owner.installed_lineage(pathlib.Path(temporary) / 'legacy', old)
        self.assertEqual((version, legacy), (1, H13))
        self.assertIs(legacy[0]['daily_wheel'], False)
        self.assertTrue(owner.extends(legacy, H21))
        self.assertFalse(owner.extends(legacy, [record(R13, True), record(R21, True)]))
        self.assertTrue(owner.extends(H21, H30))
        self.assertFalse(owner.extends(H30, H21))
        self.assertFalse(owner.extends([record(R13, True)], H21))
        self.assertFalse(owner.extends([record(R21, True)], H21))
        report = (ROOT / 'reviews/15f-lenovo-firmware-entry/REPORT.md').read_text()
        self.assertEqual(owner.LEGACY_TOOLS, (re.search(r'fingerprint: `([0-9a-f]{64})`', report)[1],))


class UpdateCommandTest(unittest.TestCase):
    def unchanged(self, tools, host, store, method, message):
        before = (copy.deepcopy(host.state), {p.name: p.read_bytes() for p in store.iterdir()})
        offset = len(host.changes)
        with self.assertRaises(owner.Stop) as caught:
            method()
        self.assertIn(message, str(caught.exception))
        self.assertEqual(host.changes[offset:], [])
        self.assertEqual(before, (host.state, {p.name: p.read_bytes() for p in store.iterdir()}))
        return caught.exception

    def test_update_verifies_then_stages_keeping_running_release_and_pinned_stock(self):
        with route(pair()) as (tools, host, store):
            lines = tools.update()
            self.assertEqual(host.state['rpm']['deployments'], staged_update()['rpm']['deployments'])
            self.assertEqual([t.get('script') for t in host.trace if t.get('script')], ['verify', 'update'])
            tools.validated.assert_called_once_with('synthetic', 'fixture-only', R21)
            self.assertEqual(lines[:2], ['Signed exact release staged ' + R21, 'Running release stays as rollback ' + R13])
            self.assertIn('Title is provisional until the next boot; refresh after boot', lines)
            title = tools.load('title')
            self.assertEqual(title['state'], host.state)
            self.assertEqual(title['title']['identity'], prepared()['stock_identity'])
            self.assertFalse(any('older AresOS' in line.lower() for line in lines))
            outcome = tools.load(owner.OUTCOME)
            staged = [list(owner.key(d)) for d in host.state['rpm']['deployments']]
            self.assertEqual((outcome['kind'], outcome['boot'], outcome['reference'], outcome['booted']),
                             ('update', 'boot-1', R21, staged[0]))
            self.assertEqual(outcome['pending'], staged)
            self.assertEqual(outcome['expected'], [list(owner.key(d)) for d in updated()['rpm']['deployments']])
            self.assertEqual(outcome['before'], [list(owner.key(d)) for d in pair()['rpm']['deployments']])

    def test_later_update_names_the_older_release_ostree_removes_at_shutdown(self):
        with route(updated(), H30) as (tools, host, store):
            lines = tools.update()
            self.assertEqual(host.state['rpm']['deployments'], staged_later()['rpm']['deployments'])
            self.assertIn('Older AresOS ' + R13 + ' is removed when the update finishes at shutdown', lines)

    def test_refusals_before_any_change(self):
        cases = [
            ('staged deployment', staged_update(), H21, {}, 'staged deployment already exists'),
            ('queued stock rollback', machine([stock_row(), release_row(R13, booted=True)]), H21, {}, 'rollback is queued'),
            ('queued previous', queued_previous(), H30, {}, 'rollback is queued'),
            ('nothing newer', pair(), H13, {}, 'already running; nothing to update'),
            ('booted stock', machine([stock_row(True), release_row(R13)]), H21, {}, 'running AresOS release'),
            ('target already deployed', returned(), H21, {}, 'already deployed'),
            ('running release unknown (bundle older)', updated(), H13, {}, 'Final pair has extra/missing deployments'),
            ('layered packages', machine([dict(release_row(R13, booted=True), **{'requested-packages': ['x']}), stock_row()]), H21, {}, 'Modified AresOS'),
            ('unlocked', machine([dict(release_row(R13, booted=True), unlocked='development'), stock_row()]), H21, {}, 'Modified AresOS'),
            ('missing login', pair(), H21, dict(login=False), owner.LOGIN_REFUSAL),
            ('unsigned', pair(), H21, dict(signed={}), 'Shared step failed: verify'),
            ('wrong identity', pair(), H21, dict(signed={R21: IDENTITY.replace('main', 'pkg/evil')}), 'Shared step failed: verify'),
        ]
        for name, state, known, options, message in cases:
            with self.subTest(name=name), route(state, known, **options) as (tools, host, store):
                self.unchanged(tools, host, store, tools.update, message)

    def test_expired_login_points_to_login_and_never_records_the_secret(self):
        with route(pair()) as (tools, host, store):
            tools.validated.side_effect = owner.Stop('Private release read failed')
            error = self.unchanged(tools, host, store, tools.update, 'run sudo /var/lib/ares/at login')
            self.assertNotIn('fixture-only', str(error) + json.dumps(host.trace))
            owner.AUTH.write_text('{"auths": {"ghcr.io": {}}}')
            self.unchanged(tools, host, store, tools.update, owner.LOGIN_REFUSAL)

    def test_active_updater_layout_trial_or_transaction_refuse(self):
        with route(pair()) as (tools, host, store):
            tools.processes = lambda: [dict(exe='/usr/bin/bootc', excluded_as_daemon=False)]
            self.unchanged(tools, host, store, tools.update, 'client active')
            tools.processes = lambda: []
            host.state['rpm']['transaction'] = ['upgrade', 'uupd', 'socket']
            self.unchanged(tools, host, store, tools.update, 'transaction active')
            host.state['rpm']['transaction'] = None
            tools.save('layout-pending', {})
            self.unchanged(tools, host, store, tools.update, 'Layout trial is unfinished')

    def test_stale_title_blocks_the_reboot_and_a_fresh_title_allows_it(self):
        with route(pair()) as (tools, host, store):
            tools.update()
            original = owner.resolved_bls.side_effect
            owner.resolved_bls.side_effect = lambda: [dict(e, title=e['title'] + ' changed') for e in original()]
            with self.assertRaisesRegex(owner.Stop, 'Title is stale'):
                tools.reboot()
            self.assertEqual(host.changes, ['bootc switch --retain ' + R21])
            owner.resolved_bls.side_effect = original
            tools.title()
            tools.reboot()
            self.assertEqual(host.changes[-1], ('systemctl', 'reboot'))

    def test_check_title_and_reboot_accept_each_update_shape(self):
        for state, known in ((staged_update(), H21), (updated(), H21), (queued_previous(), H21), (returned(), H21), (staged_later(), H30)):
            wheel = state['bootc']['status']['booted']['image']['imageDigest'] != R13.split('@')[1]
            with self.subTest(booted=state['bootc']['status']['booted']['ostree']['checksum'][:4]), route(state, known, wheel=wheel) as (tools, host, store):
                self.assertIn('Loaded y/z map, cmdline and all retained BLS maps passed', tools.check())
                tools.reboot()


class AccountRuleTest(unittest.TestCase):
    def test_each_release_requires_exactly_its_own_wheel_rule(self):
        for state, wheel, ok in ((updated(), True, True), (updated(), False, False),
                                 (returned(), False, True), (returned(), True, False),
                                 (pair(), False, True), (pair(), True, False)):
            booted = state['bootc']['status']['booted']['image']['imageDigest']
            with self.subTest(release=booted[:16], wheel=wheel), route(state, wheel=wheel) as (tools, host, store):
                if ok:
                    tools.check()
                else:
                    with self.assertRaisesRegex(owner.Stop, 'differs from this release record'):
                        tools.check()

    def test_current_tools_keep_r13_without_wheel(self):
        with route(pair(), H13, wheel=True) as (tools, host, store):
            with self.assertRaisesRegex(owner.Stop, 'differs from this release record'):
                tools.check()


class PreviousTest(unittest.TestCase):
    def test_previous_queues_the_older_release_and_keeps_every_deployment(self):
        with route(updated()) as (tools, host, store):
            lines = tools.previous()
            self.assertEqual(host.changes, ['bootc rollback'])
            self.assertEqual(host.state['rpm']['deployments'], queued_previous()['rpm']['deployments'])
            self.assertEqual(lines[0], 'Previous AresOS queued for the next start ' + R13)
            self.assertEqual(tools.load('title')['state'], host.state)
            tools.reboot()

    def test_previous_refuses_without_an_older_release_or_with_pending_work(self):
        for name, state, message in (('pair', pair(), 'nothing to return to'),
                                     ('other is newer', returned(), 'previous only returns from an update'),
                                     ('staged', staged_update(), 'Pending deployment'),
                                     ('already queued', queued_previous(), 'Pending deployment')):
            with self.subTest(name=name), route(state) as (tools, host, store):
                UpdateCommandTest.unchanged(self, tools, host, store, tools.previous, message)


class LoginTest(unittest.TestCase):
    def test_login_on_aresos_needs_a_newer_target_and_otherwise_keeps_the_stock_rules(self):
        with route(pair()) as (tools, host, store), patch.object(owner.sys.stdin, 'isatty', return_value=False):
            with self.assertRaisesRegex(owner.Stop, 'Login requires a real hidden terminal prompt'):
                tools.login()
        with route(pair(), H13) as (tools, host, store):
            with self.assertRaisesRegex(owner.Stop, 'already running; nothing to update'):
                tools.login()
        with route(staged_update()) as (tools, host, store):
            with self.assertRaisesRegex(owner.Stop, 'staged deployment already exists'):
                tools.login()


class OutcomeTest(unittest.TestCase):
    """check/title/records PASS only for the exact start that update/previous recorded."""

    def stopped(self, tools, host, store, method, message):
        return UpdateCommandTest.unchanged(self, tools, host, store, method, message)

    def test_update_is_confirmed_only_by_the_recorded_new_start(self):
        with route(pair()) as (tools, host, store):
            tools.update()
            self.assertIn('Update to ' + R21 + ' is not finished until the restart', tools.check())
            host.state, host.wheel, tools.boot[0] = updated(), True, 'boot-2'
            self.assertIn('Update to ' + R21 + ' confirmed after the restart', tools.check())
            self.assertFalse((store / (owner.OUTCOME + '.json')).exists())
            receipt, = store.glob('*-outcome-confirmed.json')
            self.assertEqual(json.loads(receipt.read_text())['confirmed_state'], host.state)
            self.assertNotIn('confirmed', ' '.join(tools.check()))

    def test_failed_finalization_stops_every_confirmation_until_help_retries_the_update(self):
        with route(pair()) as (tools, host, store):
            tools.update()
            # The staged update was lost at the restart: the old list is back.
            host.state, tools.boot[0] = pair(), 'boot-2'
            for name, method in (('check', tools.check), ('title', tools.title), ('reboot', tools.reboot),
                                 ('rollback', tools.recover), ('layout', lambda: tools.layout('begin', 'us')),
                                 ('previous', tools.previous)):
                with self.subTest(command=name):
                    self.stopped(tools, host, store, method, 'did not finish at the restart')
            # keep-stock needs booted stock and refuses earlier, also unchanged.
            self.stopped(tools, host, store, lambda: tools.recover(True), 'keep-stock requires booted saved stock')
            with self.assertRaisesRegex(owner.Stop, 'did not finish at the restart'):
                tools.records()
            # After Help, the same update may run once more from the unchanged list.
            tools.update()
            self.assertEqual(host.changes, ['bootc switch --retain ' + R21] * 2)
            self.assertEqual(len(list(store.glob('*-outcome-retried.json'))), 1)
            host.state, host.wheel, tools.boot[0] = updated(), True, 'boot-3'
            self.assertIn('Update to ' + R21 + ' confirmed after the restart', tools.check())

    def test_still_staged_after_the_restart_or_changed_before_it_stops(self):
        with route(pair()) as (tools, host, store):
            tools.update()
            host.state = pair()
            self.stopped(tools, host, store, tools.check, 'changed before the restart')
            self.stopped(tools, host, store, tools.reboot, 'changed before the restart')
            host.state, tools.boot[0] = staged_update(), 'boot-2'
            for method in (tools.check, tools.title, tools.update):
                self.stopped(tools, host, store, method, 'it is still pending')

    def test_an_unsuccessful_previous_stops_and_a_successful_one_is_confirmed(self):
        with route(updated(), wheel=True) as (tools, host, store):
            tools.previous()
            self.assertEqual(tools.load(owner.OUTCOME)['booted'], list(owner.key(release_row(R13))))
            host.state, tools.boot[0] = queued_previous(), 'boot-2'
            self.stopped(tools, host, store, tools.check, 'it is still pending')
            host.state = updated()
            for method in (tools.check, tools.title, tools.update):
                self.stopped(tools, host, store, method, 'return to ' + R13 + ' did not finish at the restart')
            tools.previous()
            self.assertEqual(host.changes, ['bootc rollback'] * 2)
            host.state, host.wheel, tools.boot[0] = returned(), False, 'boot-3'
            self.assertIn('Return to ' + R13 + ' confirmed after the restart', tools.check())


class IntentTest(unittest.TestCase):
    """update and previous journal their intent before any change (review 2)."""

    POINTS = ('before', 'after', 'observe', 'record')

    @contextlib.contextmanager
    def interrupted(self, kind, point):
        start = pair() if kind == 'update' else updated()
        with route(start, wheel=kind != 'update') as (tools, host, store):
            command = tools.update if kind == 'update' else tools.previous
            real_save = owner.Tools.save
            def save(obj, name, value):
                if point == 'record' and name == owner.OUTCOME and value.get('status') == 'recorded':
                    raise OSError('injected failure writing the record')
                return real_save(obj, name, value)
            if point != 'record':
                host.interrupt = (kind, point)
            with patch.object(owner.Tools, 'save', new=save), self.assertRaises((owner.Stop, OSError)):
                command()
            intent = tools.load(owner.OUTCOME)
            self.assertEqual((intent['status'], intent['kind'], intent['boot']), ('intent', kind, 'boot-1'))
            self.assertEqual(intent['before'], [list(owner.key(d)) for d in start['rpm']['deployments']])
            yield tools, host, store, command, start

    def test_the_intent_is_written_before_the_change(self):
        for kind in ('update', 'previous'):
            with self.subTest(kind=kind), route(pair() if kind == 'update' else updated()) as (tools, host, store):
                seen = []
                original = host.script
                def script(text, name, mutation=True):
                    if name == kind:
                        seen.append(tools.load(owner.OUTCOME)['status'])
                    return original(text, name, mutation)
                host.script = script
                (tools.update if kind == 'update' else tools.previous)()
                self.assertEqual(seen, ['intent'])
                self.assertEqual(tools.load(owner.OUTCOME)['status'], 'recorded')

    def test_every_interruption_leaves_an_unresolved_intent_that_check_title_records_refuse(self):
        for kind in ('update', 'previous'):
            for point in self.POINTS:
                with self.subTest(kind=kind, point=point), self.interrupted(kind, point) as (tools, host, store, command, start):
                    for method in (tools.check, tools.title, tools.reboot):
                        UpdateCommandTest.unchanged(self, tools, host, store, method, 'interrupted before its result was recorded')
                    # Stock rollback refuses too (on a staged/queued list with its own message).
                    UpdateCommandTest.unchanged(self, tools, host, store, tools.recover, '')
                    with self.assertRaisesRegex(owner.Stop, 'interrupted before its result was recorded'):
                        tools.records()
                    # Nothing passes on the old release after a restart either.
                    tools.boot[0] = 'boot-2'
                    host.state = copy.deepcopy(start)
                    UpdateCommandTest.unchanged(self, tools, host, store, tools.check, 'interrupted before its result was recorded')

    def test_the_same_command_redoes_an_unmade_change_or_records_a_made_one(self):
        for kind in ('update', 'previous'):
            for point in self.POINTS:
                with self.subTest(kind=kind, point=point), self.interrupted(kind, point) as (tools, host, store, command, start):
                    made = bool(host.changes)
                    self.assertEqual(made, point != 'before')
                    # A failed update step is undone before the STOP (review 1): its staging is removed.
                    undone = kind == 'update' and point == 'after'
                    if undone:
                        self.assertEqual(host.changes[-1], ('rpm-ostree', 'cleanup', '--pending'))
                        self.assertEqual(host.state, start)
                    lines = command()
                    if made and not undone:
                        self.assertEqual(len(host.changes), 1)
                        self.assertTrue(lines[0].startswith('Interrupted '))
                    else:
                        self.assertEqual(len(host.changes), 3 if undone else 1)
                        self.assertEqual(len(list(store.glob('*-outcome-retried.json'))), 1)
                    self.assertEqual(tools.load(owner.OUTCOME)['status'], 'recorded')
                    self.assertTrue(any('not finished until the restart' in line for line in tools.check()))
                    host.state = updated() if kind == 'update' else returned()
                    host.wheel, tools.boot[0] = kind == 'update', 'boot-2'
                    self.assertTrue(any(line.endswith('confirmed after the restart') for line in tools.check()))

    def test_after_a_restart_the_same_command_records_a_finished_change_or_redoes_a_lost_one(self):
        for kind in ('update', 'previous'):
            # A failed update step is undone at once (review 1); a lost read after it leaves the staging.
            point = 'observe' if kind == 'update' else 'after'
            with self.subTest(kind=kind, restart='finished'), self.interrupted(kind, point) as (tools, host, store, command, start):
                host.state = updated() if kind == 'update' else returned()
                host.wheel, tools.boot[0] = kind == 'update', 'boot-2'
                UpdateCommandTest.unchanged(self, tools, host, store, tools.check, 'interrupted before its result was recorded')
                lines = command()
                self.assertTrue(lines[0].startswith('Interrupted '))
                self.assertTrue(any(line.endswith('confirmed after the restart') for line in lines))
                self.assertEqual(len(host.changes), 1)
            with self.subTest(kind=kind, restart='lost'), self.interrupted(kind, point) as (tools, host, store, command, start):
                host.state, tools.boot[0] = copy.deepcopy(start), 'boot-2'
                command()
                self.assertEqual(len(host.changes), 2)
                self.assertEqual(tools.load(owner.OUTCOME)['status'], 'recorded')

    def test_other_commands_never_continue_an_intent_and_a_wrong_change_is_not_recorded(self):
        with self.interrupted('update', 'after') as (tools, host, store, command, start):
            UpdateCommandTest.unchanged(self, tools, host, store, tools.previous, 'interrupted before its result was recorded')
            # The target staged over a different running deployment is not the intended change.
            host.state = machine([release_row(R21, staged=True), release_row(R13, booted=True, checksum='d5' * 32), stock_row()])
            UpdateCommandTest.unchanged(self, tools, host, store, command, 'interrupted before its result was recorded')


class LockTest(unittest.TestCase):
    """One owner command at a time, and everything rechecked just before staging."""

    @contextlib.contextmanager
    def entry(self, state):
        """The real dispatcher over the modelled machine; the lock is a real flock."""
        with route(state) as (tools, host, store), contextlib.ExitStack() as stack:
            home = store.parent
            for name, value in (('HOME', home), ('STOP_RECORDS', home / 'diagnostics'), ('__file__', str(home / 'tools/owner.py')),
                                ('LOCK', home.parent / 'ares-owner.lock')):
                stack.enter_context(patch.object(owner, name, value))
            stack.enter_context(patch.object(owner.os, 'geteuid', return_value=0))
            stack.enter_context(patch.object(owner.os, 'umask'))
            stack.enter_context(patch.object(owner, 'private_tree'))
            stack.enter_context(patch.object(owner, 'Host', return_value=host))
            stack.enter_context(patch.object(owner.Tools, 'processes', lambda self: []))
            stack.enter_context(patch.object(owner.Tools, 'keyboard', lambda self: dict(DE)))
            real_stat = pathlib.Path.stat
            stack.enter_context(patch.object(pathlib.Path, 'stat', lambda p, *a, **kw:
                SimpleNamespace(st_uid=0, st_mode=0o40700) if p == home else real_stat(p, *a, **kw)))

            def run(*argv):
                out = io.StringIO()
                with patch.object(owner.sys, 'argv', ['at', *argv]), contextlib.redirect_stdout(out), common.kept_umask():
                    owner.main()
                return out.getvalue()
            yield tools, host, store, run

    def test_lock_admits_one_command_never_follows_a_link_and_is_released(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            root = pathlib.Path(temporary)
            with patch.object(owner, 'LOCK', root / 'ares-owner.lock'):
                first = owner.owner_lock()
                with self.assertRaisesRegex(owner.Stop, 'Another owner command is running'):
                    owner.owner_lock()
                os.close(first)
                os.close(owner.owner_lock())
            (root / 'elsewhere').write_text('')
            os.symlink(root / 'elsewhere', root / 'link.lock')
            with patch.object(owner, 'LOCK', root / 'link.lock'), self.assertRaises(OSError):
                owner.owner_lock()

    def test_a_layout_trial_during_update_verification_is_refused_and_the_update_completes(self):
        with self.entry(pair()) as (tools, host, store, run):
            refused = []

            def concurrent():
                with self.assertRaisesRegex(owner.Stop, 'Another owner command is running') as caught:
                    run('layout', 'begin', 'us')
                refused.append(str(caught.exception))
                self.assertFalse((store / 'layout-pending.json').exists())
            host.during_verify = concurrent
            output = run('update')
            self.assertEqual(len(refused), 1)
            self.assertIn('PASS update\n', output)
            self.assertEqual(host.changes, ['bootc switch --retain ' + R21])
            host.during_verify = None
            self.assertIn('PASS title\n', run('title'))

    def test_changes_during_verification_are_caught_immediately_before_staging(self):
        changes = {
            'layout trial': (lambda tools, host: tools.save('layout-pending', {}), 'Layout trial is unfinished'),
            'transaction': (lambda tools, host: host.state['rpm'].update(transaction=['upgrade', 'uupd', 'socket']), 'transaction active'),
            'staged elsewhere': (lambda tools, host: setattr(host, 'state', staged_update()), 'staged deployment already exists'),
            'queued rollback': (lambda tools, host: setattr(host, 'state', machine([stock_row(), release_row(R13, booted=True)])), 'rollback is queued'),
            'list changed': (lambda tools, host: setattr(host, 'state', machine([release_row(R13, booted=True, checksum='d4' * 32), stock_row()])),
                             'changed during verification'),
        }
        for name, (change, message) in changes.items():
            with self.subTest(change=name), route(pair()) as (tools, host, store):
                host.during_verify = lambda: change(tools, host)
                with self.assertRaisesRegex(owner.Stop, message):
                    tools.update()
                self.assertEqual(host.changes, [])
                self.assertFalse((store / (owner.OUTCOME + '.json')).exists())


class ToolsHost(FixtureHost):
    def __init__(self, tree, usb, state):
        super().__init__(tree, usb)
        self.state = state

    def json(self, *command):
        if command == ('rpm-ostree', 'status', '--json'):
            return copy.deepcopy(self.state['rpm'])
        if command == ('bootc', 'status', '--json'):
            return copy.deepcopy(self.state['bootc'])
        return super().json(*command)


class ToolsUpdateTest(unittest.TestCase):
    """The bootstrap's install entry over an existing installation."""

    def setUp(self):
        bytecode = patch.object(sys, 'dont_write_bytecode', True)
        bytecode.start()
        self.addCleanup(bytecode.stop)

    @contextlib.contextmanager
    def installation(self, installed=None, stick=None, state=None, legacy_owner=b'print("15f stand-in ran")\n', versioned=False):
        """installed/stick: (history or None for a history-less bundle, target, extra files).

        The installed tools live in tools/ (the first install, or the 15f
        stand-in) or, with versioned, in tools-<fingerprint>/ as after an update.
        """
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary, contextlib.ExitStack() as stack:
            root = pathlib.Path(temporary)
            home = root / 'home'
            home.mkdir(mode=0o700)
            (home / 'records').mkdir(mode=0o700)
            usb = root / 'usb'
            usb.mkdir()
            if stick is None:
                fingerprint = common.fixture_bundle(usb / 'ares-tools')
            else:
                fingerprint = write_bundle(usb / 'ares-tools', *stick)
            if installed is None:
                old = write_bundle(home / 'tools', drop=('history.json', 'release/update.sh', 'release/previous.sh'),
                                   extra={'owner.py': legacy_owner})
                stack.enter_context(patch.object(owner, 'LEGACY_TOOLS', (old,)))
            else:
                old = write_bundle(home / 'tools', *installed)
            toolset = 'tools-' + old if versioned else 'tools'
            if versioned:
                (home / 'tools').rename(home / toolset)
            for path in [home / toolset, *(home / toolset).rglob('*')]:
                path.chmod(0o700 if path.is_dir() or path.name == 'at' else 0o600)
            os.symlink(toolset + '/at', home / 'at')
            writer = object.__new__(owner.Tools)
            writer.store = home
            writer.save('install-intent', dict(schema='install1', manifest='1' * 64, disks=dict(target='TARGET', protected='KEEP'),
                identity={}, tools_volume_uuid='earlier', phase='complete'))
            writer.store = home / 'records'
            writer.save('disks', dict(target='TARGET', protected='KEEP'))
            writer.save('prepared', prepared())
            host = ToolsHost(fixture(), usb, state or pair())
            stack.enter_context(patch.object(owner, 'HOME', home))
            stack.enter_context(patch.object(owner.sys.stdin, 'isatty', return_value=True))
            stack.enter_context(patch.object(owner.Tools, 'processes', lambda self: []))
            self.private = stack.enter_context(patch.object(owner, 'private_tree'))
            run = lambda: owner.install(usb / 'ares-tools', host)
            yield home, run, fingerprint, old, host

    def snapshot(self, home):
        return {p.relative_to(home).as_posix(): (p.read_bytes() if p.is_file() and not p.is_symlink() else os.readlink(p) if p.is_symlink() else None)
                for p in home.rglob('*')}

    def updated(self, home, fingerprint, old):
        self.assertEqual(owner.checked_bundle(home / ('tools-' + fingerprint)), fingerprint)
        self.assertEqual(owner.checked_bundle(home / 'retired-tools' / old), old)
        self.assertEqual(os.readlink(home / 'at'), 'tools-' + fingerprint + '/at')
        for name in ('tools', 'tools-' + old, '.tools-held', '.update-tools', '.at.new'):
            self.assertFalse((home / name).exists() or (home / name).is_symlink(), name)
        intent = json.loads((home / 'tools-update-intent.json').read_text())
        self.assertEqual((intent['phase'], intent['previous'], intent['manifest']), ('complete', old, fingerprint))
        self.assertEqual(len(list((home / 'records').glob('*-tools-update.json'))), 1)

    NAMESPACE = ('mount -t tmpfs none /run && mount -t tmpfs none /var/lib && mkdir /var/lib/ares '
                 '&& mount --bind "$1" /var/lib/ares && echo pkg22-namespace-ready && exec bash "/var/lib/ares/$2" "${@:3}"')

    def entry_run(self, home, *args, path='at', timeout=60):
        """Run the real documented entry as root over this home: bash /var/lib/ares/at ...

        An unprivileged user and mount namespace makes the fixture owner uid 0,
        mounts the fixture home at /var/lib/ares and a tmpfs at /run for the
        owner lock. Nothing is patched: the tools run exactly as installed.
        """
        process = subprocess.Popen(['unshare', '-Urm', 'bash', '-c', self.NAMESPACE, 'entry', str(home), path, *args],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return SimpleNamespace(returncode=None, stdout=stdout, stderr=stderr, timed_out=True)
        if 'pkg22-namespace-ready' not in stdout:
            self.skipTest('no unprivileged user and mount namespace here: ' + stderr.strip())
        return SimpleNamespace(returncode=process.returncode, stdout=stdout, stderr=stderr, timed_out=False)

    def reached(self, result):
        """Which toolset the entry ran, by its explicit marker; a hung or silent entry is neither.

        '15f': the stand-in printed its marker; 'new': the new tools ran check
        and stopped at the fixture host's missing rpm-ostree. A timeout never
        counts, whatever was printed before it.
        """
        if result.timed_out:
            return None
        if '15f stand-in ran' in result.stdout:
            return '15f'
        if 'STOP: Required tool missing: rpm-ostree' in result.stdout:
            return 'new'
        return None

    def sleeper_entry_starts(self, home, old):
        """For the sleeping 15f stand-in, which can print no marker: the entry starts it from tools/."""
        self.assertEqual(os.readlink(home / 'at'), 'tools/at')
        self.assertEqual(owner.checked_bundle(home / 'tools'), old)
        process = subprocess.Popen(['bash', str(home / 'at'), 'check'], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while not any(r['pid'] == process.pid and str(home / 'tools/owner.py') in r.get('argv', [])
                          for r in owner.installed_commands(home)):
                self.assertLess(time.monotonic(), deadline, 'the sleeping stand-in did not start through the entry')
                self.assertIsNone(process.poll(), 'the sleeping stand-in ended early')
                time.sleep(.05)
        finally:
            process.kill()
            process.wait()

    def test_older_installed_tools_are_replaced_and_kept_and_records_survive(self):
        with self.installation() as (home, run, fingerprint, old, host):
            records = {p.name: p.read_bytes() for p in (home / 'records').iterdir()}
            lines = run()
            self.updated(home, fingerprint, old)
            self.assertEqual(lines[:2], ['Tools updated from version 1 to 2', 'manifest SHA256 ' + fingerprint])
            self.assertEqual({k: v for k, v in records.items()}, {p.name: p.read_bytes() for p in (home / 'records').iterdir()
                                                                if not p.name.endswith('-tools-update.json')})
            receipt = json.loads(next((home / 'records').glob('*-tools-update.json')).read_text())
            # The reviewed bundle over the 15f tools: the laptop's own update, release 13 then 27.
            self.assertEqual((receipt['previous_manifest'], receipt['manifest'], receipt['releases']),
                             (old, fingerprint, owner.lineage(PAYLOAD)['releases']))
            self.assertEqual([r['reference'] for r in receipt['releases']], [R13, PINNED['reference']])
            self.private.assert_any_call(home / 'tools')
            self.assertFalse(any(row.get('mutation') for row in host.trace))
            again = self.snapshot(home)
            self.assertEqual(run(), ['Tools already installed; nothing changed', 'manifest SHA256 ' + fingerprint])
            self.assertEqual(again, self.snapshot(home))

    def test_newer_bundle_over_history_tools_extends_the_installed_history(self):
        with self.installation(installed=(history(H13, 2), H13[-1]), stick=(history(H21, 3), H21[-1])) as (home, run, fingerprint, old, host):
            self.assertEqual(run()[:2], ['Tools updated from version 2 to 3', 'manifest SHA256 ' + fingerprint])
            self.updated(home, fingerprint, old)
            self.assertEqual(owner.lineage(home / ('tools-' + fingerprint))['releases'], H21)

    def test_downgrade_same_version_foreign_history_and_unknown_legacy_refuse_without_writes(self):
        cases = {
            'downgrade': dict(installed=(history(H21, 3), H21[-1])),
            'same version, other bytes': dict(installed=(history(H13, 2), H13[-1], (), {'media.py': b'# other\n'})),
            'history rewritten': dict(installed=(history(H13, 2), H13[-1]), stick=(history([record(R13, True), record(R21, True)], 3), H21[-1])),
            'history dropped a release': dict(installed=(history(H21, 2), H21[-1]), stick=(history([record(R13, False), record(R30, True)], 3), record(R30, True))),
        }
        cases['15f rule rewritten'] = dict(stick=(history([record(R13, True), record(R21, True)], 3), H21[-1]))
        messages = {'downgrade': 'refusing version 2', 'same version, other bytes': 'same version',
                    'history rewritten': 'does not extend', 'history dropped a release': 'does not extend',
                    '15f rule rewritten': 'does not extend'}
        for name, options in cases.items():
            with self.subTest(name=name), self.installation(**options) as (home, run, fingerprint, old, host):
                before = self.snapshot(home)
                with self.assertRaisesRegex(owner.Stop, messages[name]):
                    run()
                self.assertEqual(before, self.snapshot(home))
        with self.installation() as (home, run, fingerprint, old, host), patch.object(owner, 'LEGACY_TOOLS', ('0' * 64,)):
            before = self.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, 'not the known 15f tools'):
                run()
            self.assertEqual(before, self.snapshot(home))

    def test_state_the_new_tools_would_refuse_blocks_the_update_without_writes(self):
        for name, state, record_name in (('unknown staged image', machine([release_row(R99, staged=True), release_row(R13, booted=True), stock_row()]), None),
                                         ('layout trial', pair(), 'layout-pending'),
                                         ('unfinished prepare', pair(), 'prepare-intent')):
            with self.subTest(name=name), self.installation(state=state) as (home, run, fingerprint, old, host):
                if record_name:
                    writer = object.__new__(owner.Tools)
                    writer.store = home / 'records'
                    writer.save(record_name, dict(phase='pin'))
                before = self.snapshot(home)
                with self.assertRaises(owner.Stop):
                    run()
                self.assertEqual(before, self.snapshot(home))

    def test_interrupted_update_resumes_after_each_step(self):
        steps = []
        with self.installation() as (home, run, fingerprint, old, host):
            original = owner.Tools.save
            with patch.object(owner.Tools, 'save', new=lambda obj, name, value: (steps.append(name), original(obj, name, value))[1]):
                run()
        self.assertEqual(steps, ['tools-update-intent'] * 4 + [steps[4], 'tools-update-intent'])
        # Every file copy, every rename (six journal and record writes, the new
        # directory, the entry switch, the block and the retirement) and every record write.
        injections = [('copy', n) for n in range(1, len(common.bundle.PAYLOAD) + 3)] + \
                     [('replace', n) for n in range(1, 11)] + [('save', n) for n in range(1, 7)]
        for kind, stop in injections:
            with self.subTest(kind=kind, stop=stop), self.installation() as (home, run, fingerprint, old, host):
                seen = 0
                def hit():
                    nonlocal seen
                    seen += 1
                    if seen == stop:
                        raise OSError('injected after ' + kind)
                if kind == 'copy':
                    real = shutil.copy2
                    hook = patch('shutil.copy2', side_effect=lambda *a, **kw: (real(*a, **kw), hit())[0])
                elif kind == 'replace':
                    real = pathlib.Path.replace
                    hook = patch.object(pathlib.Path, 'replace', new=lambda p, t: (real(p, t), hit())[0])
                else:
                    real = owner.Tools.save
                    hook = patch.object(owner.Tools, 'save', new=lambda obj, name, value: (real(obj, name, value), hit())[0])
                with hook, self.assertRaises(OSError):
                    run()
                run()
                self.updated(home, fingerprint, old)

    # The complete STOP lines the tools print; a helper accepts nothing less than a whole line.
    BOUNCE = ('STOP: These tools are not the installed entry (the tools update was undone or superseded); '
              'run sudo /var/lib/ares/at check again')
    NOT_INSTALLED = 'STOP: Run the installed root-only tools'

    def refused(self, result, line):
        """The entry terminated by itself with exit status 1 and printed exactly this STOP line."""
        self.assertFalse(result.timed_out, 'the entry hung: ' + result.stdout + result.stderr)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(line, result.stdout.splitlines(), result.stdout + result.stderr)

    def works(self, home, old, fingerprint, timeout=20):
        """Invariant 1: the real entry reaches a complete, verified toolset, or the route to one.

        Before publication the entry may still point at the new tools after a
        cut; they settle the state and say to run the command again, and the
        second run reaches the previous tools. The rerun happens only after a
        run that terminated by itself with the complete bounce line; a hang
        fails, whatever it printed first.
        """
        result = self.entry_run(home, 'check', timeout=timeout)
        if not result.timed_out and result.returncode == 1 and self.BOUNCE in result.stdout.splitlines():
            result = self.entry_run(home, 'check', timeout=timeout)
        which = self.reached(result)
        self.assertIsNotNone(which, ('timed out' if result.timed_out else 'no marker') + ': ' + result.stdout + result.stderr)
        toolset = os.readlink(home / 'at').removesuffix('/at')
        self.assertEqual(owner.checked_bundle(home / toolset), old if which == '15f' else fingerprint)
        return which

    def test_a_hung_or_truncated_bounce_fails_every_helper(self):
        """An entry that prints the bounce or refusal text and then hangs, or prints part of it, is no pass."""
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            home = pathlib.Path(temporary) / 'home'
            (home / 'tools').mkdir(parents=True, mode=0o700)
            os.symlink('tools/at', home / 'at')
            cases = {
                'bounce then hang': 'echo "' + self.BOUNCE + '"; sleep 60\n',
                'refusal then hang': 'echo "' + self.NOT_INSTALLED + '"; sleep 60\n',
                'marker then hang': 'echo "15f stand-in ran"; sleep 60\n',
                'truncated bounce': 'echo "STOP: These tools are not the installed entry"; exit 1\n',
                'truncated refusal': 'echo "STOP: Run the installed"; exit 1\n',
            }
            for name, script in cases.items():
                with self.subTest(case=name):
                    (home / 'tools/at').write_text(script)
                    (home / 'tools/at').chmod(0o700)
                    result = self.entry_run(home, 'check', timeout=2)
                    self.assertEqual(result.timed_out, 'hang' in name)
                    self.assertIsNone(self.reached(result))
                    with self.assertRaises(AssertionError):
                        self.refused(result, self.BOUNCE)
                    with self.assertRaises(AssertionError):
                        self.refused(result, self.NOT_INSTALLED)
            # The complete lines, terminated, do pass refused(): the helper is strict, not broken.
            for name, line in (('bounce', self.BOUNCE), ('refusal', self.NOT_INSTALLED)):
                with self.subTest(case=name + ' complete'):
                    (home / 'tools/at').write_text('echo "' + line + '"; exit 1\n')
                    self.refused(self.entry_run(home, 'check', timeout=2), line)

    def test_works_reruns_only_after_a_complete_terminated_bounce(self):
        """A bad first run followed by a good one: works() must fail after exactly one invocation.

        Round 7's helper retried whenever the output mentioned the bounce, so a
        hang or a truncated line followed by a sound second run passed. Here
        the entry counts its invocations (in the home, outside the bundle) and
        answers differently the second time.
        """
        marker = 'echo "15f stand-in ran"; exit 0'
        bounce = 'echo "' + self.BOUNCE + '"; exit 1'
        cases = {
            'hang after the bounce, then success': ('echo "' + self.BOUNCE + '"; sleep 60', marker, False, 1),
            'truncated bounce, then success': ('echo "STOP: These tools are not the installed entry"; exit 1', marker, False, 1),
            'complete bounce, then success': (bounce, marker, True, 2),
            'complete bounce, then bounce again': (bounce, bounce, False, 2),
        }
        for name, (first, second, passes, invocations) in cases.items():
            with self.subTest(case=name), tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
                home = pathlib.Path(temporary) / 'home'
                home.mkdir(mode=0o700)
                script = ('#!/usr/bin/bash\ncount=/var/lib/ares/invocations\nn=$(cat "$count" 2>/dev/null || echo 0)\n'
                          'echo $((n + 1)) > "$count"\nif [ "$n" = 0 ]; then\n' + first + '\nfi\n' + second + '\n')
                old = write_bundle(home / 'tools', extra={'at': script.encode()})
                os.symlink('tools/at', home / 'at')
                if passes:
                    self.assertEqual(self.works(home, old, old, timeout=2), '15f')
                else:
                    with self.assertRaises(AssertionError):
                        self.works(home, old, old, timeout=2)
                self.assertEqual((home / 'invocations').read_text().strip(), str(invocations), name)

    @contextlib.contextmanager
    def power_cut_after(self, renames):
        """The machine stops right after the given rename: nothing later runs, no handler either."""
        real, count, dead = pathlib.Path.replace, [0], [False]
        def replace(path, target):
            if dead[0]:
                raise OSError('power is off')
            result = real(path, target)
            count[0] += 1
            if count[0] == renames:
                dead[0] = True
                raise OSError('power cut')
            return result
        with patch.object(pathlib.Path, 'replace', new=replace):
            yield

    @staticmethod
    def failing(target, attribute, error):
        """A refusal (change, undo) pair that makes a check raise while active."""
        patchers = []
        return (lambda home, host: patchers.append(patch.object(target, attribute, side_effect=error)) or patchers[-1].start(),
                lambda home, host: patchers.pop().stop())

    @staticmethod
    def record(home, name, value):
        """A private (0600) record, as the tools write them."""
        writer = object.__new__(owner.Tools)
        writer.store = home / 'records'
        writer.save(name, value)

    @staticmethod
    def journal_value(home, name, value):
        journal = home / 'tools-update-intent.json'
        if journal.exists():
            writer = object.__new__(owner.Tools)
            writer.store = home
            writer.save('tools-update-intent', dict(json.loads(journal.read_text()), **{name: value}))

    @staticmethod
    def staged_bytes(home, change):
        staged = home / '.update-tools/owner.py'
        if staged.exists():
            staged.write_bytes(change(staged.read_bytes()))

    def test_invariant_one_working_toolset_after_any_interruption_and_any_refusal(self):
        """After a cut at every rename, and a persistent refusal from any check, at always works.

        The refusals come from every kind of fallible check, not only the
        system preflight: the disk record, the resume identity, the staged
        bundle, an observation that fails, and an unexpected exception.
        """
        refusals = {
            'layout trial': (lambda home, host: self.record(home, 'layout-pending', dict(phase='pin')),
                             lambda home, host: (home / 'records/layout-pending.json').unlink(), owner.Stop),
            'transaction': (lambda home, host: host.state['rpm'].update(transaction=['upgrade', 'uupd', 'socket']),
                            lambda home, host: host.state['rpm'].update(transaction=None), owner.Stop),
            'disk record': (*self.failing(owner, 'disk_record', owner.Stop('Wrong or ambiguous target disk serial')), owner.Stop),
            'resume identity': (lambda home, host: self.journal_value(home, 'tools_volume_uuid', 'OTHER-STICK'),
                                lambda home, host: self.journal_value(home, 'tools_volume_uuid', 'CAFE-1234'), owner.Stop),
            'staged bundle': (lambda home, host: self.staged_bytes(home, lambda raw: raw + b'# changed\n'),
                              lambda home, host: self.staged_bytes(home, lambda raw: raw.removesuffix(b'# changed\n')), owner.Stop),
            'preflight error': (*self.failing(owner, 'observations', owner.Stop('Read failed: rpm-ostree status --json')), owner.Stop),
            'unexpected exception': (*self.failing(owner, 'installed_commands', RuntimeError('unexpected')), RuntimeError),
        }
        # A full run renames ten times: the journal to copy, the new directory,
        # the journal to publish, the entry switch, the block, the journal to
        # retire, the retirement, the journal to records, the receipt, complete.
        for cut in range(1, 11):
            for name, (change, undo, refusal) in refusals.items():
                with self.subTest(cut=cut, refusal=name), self.installation() as (home, run, fingerprint, old, host):
                    with self.power_cut_after(cut), self.assertRaises(OSError):
                        run()
                    change(home, host)
                    # Undo however the subtest ends: a patched check left active by a
                    # skip or a failure would break every later test (main, 2026-11-10).
                    try:
                        for attempt in range(2):  # a persistent failure refuses every time
                            try:
                                run()
                            except refusal:
                                pass
                            self.works(home, old, fingerprint)
                    finally:
                        undo(home, host)
                    run()
                    self.updated(home, fingerprint, old)
                    self.assertEqual(self.works(home, old, fingerprint), 'new')

    def test_the_real_entry_reaches_a_toolset_after_every_cut_and_every_bootstrap_failure(self):
        """No gap: bash /var/lib/ares/at always runs a complete toolset, or says which command to run again.

        The entry runs as root in its own namespace with nothing patched, right
        after a cut at every rename, and again after a bootstrap that fails to
        mount (it never runs), to copy (its private copy differs), to verify
        (the stick check refuses) or at the disk record.
        """
        real_check = owner.checked_bundle
        def corrupt_copy(usb):
            def checked_bundle(root):
                if pathlib.Path(root) == usb / 'ares-tools':
                    raise owner.Stop('Bundle hash mismatch: owner.py')
                return real_check(root)
            return patch.object(owner, 'checked_bundle', side_effect=checked_bundle)
        failures = {
            'mount': None,
            'copy': corrupt_copy,
            'verify': lambda usb: patch.object(owner, 'tools_stick', side_effect=owner.Stop('Private bootstrap copy differs from the tools USB')),
            'disk record': lambda usb: patch.object(owner, 'disk_record', side_effect=owner.Stop('Wrong or ambiguous target disk serial')),
        }
        for cut in range(1, 11):
            for name, failure in failures.items():
                with self.subTest(cut=cut, failure=name), self.installation() as (home, run, fingerprint, old, host):
                    with self.power_cut_after(cut), self.assertRaises(OSError):
                        run()
                    entry = os.readlink(home / 'at')
                    self.assertIn(entry, ('tools/at', 'tools-' + fingerprint + '/at'))
                    self.assertEqual(owner.checked_bundle(home / entry.removesuffix('/at')), old if entry == 'tools/at' else fingerprint)
                    first = self.works(home, old, fingerprint)  # right after the cut
                    if failure is not None:
                        with failure(home.parent / 'usb'), self.assertRaises(owner.Stop):
                            run()
                    second = self.works(home, old, fingerprint)  # after the failed bootstrap
                    # Before publication (journal at copy or publish) the previous tools answer; from retire on, the new ones.
                    phase = json.loads((home / 'tools-update-intent.json').read_text())['phase']
                    self.assertEqual({first, second}, {'15f' if phase in ('copy', 'publish') else 'new'}, (cut, phase))
                    run()
                    self.updated(home, fingerprint, old)

    def test_every_entry_settles_the_tools_before_any_check(self):
        """A cut at the entry switch, at the block and after publication: the first real entry run settles it."""
        for cut, expected in ((4, '15f'), (5, '15f'), (6, 'new')):
            with self.subTest(cut=cut), self.installation() as (home, run, fingerprint, old, host):
                with self.power_cut_after(cut), self.assertRaises(OSError):
                    run()
                self.assertEqual(os.readlink(home / 'at'), 'tools-' + fingerprint + '/at')
                self.assertEqual((home / 'tools').exists(), cut == 4)
                result = self.entry_run(home, 'check')
                if expected == '15f':
                    # The new tools settled the state (entry back, tools back) and bounced the command.
                    self.refused(result, self.BOUNCE)
                    self.assertEqual(os.readlink(home / 'at'), 'tools/at')
                    self.assertEqual(owner.checked_bundle(home / 'tools'), old)
                    self.assertFalse((home / '.tools-held').exists())
                    self.assertEqual(json.loads((home / 'tools-update-intent.json').read_text())['phase'], 'publish')
                    result = self.entry_run(home, 'check')
                else:
                    self.assertEqual(json.loads((home / 'tools-update-intent.json').read_text())['phase'], 'retire')
                    self.assertTrue((home / '.tools-held').exists())
                self.assertEqual(self.reached(result), expected, result.stdout + result.stderr)
                run()
                self.updated(home, fingerprint, old)

    def test_a_versioned_toolset_updates_by_the_entry_switch_alone_and_refuses_afterwards(self):
        """The second update: nothing is held aside, and the old versioned tools refuse once the entry moved on."""
        with self.installation(installed=(history(H13, 2), H13[-1]), stick=(history(H21, 3), H21[-1]), versioned=True) as (home, run, fingerprint, old, host):
            self.assertEqual(os.readlink(home / 'at'), 'tools-' + old + '/at')
            self.assertEqual(self.reached(self.entry_run(home, 'check')), 'new')
            renames = []
            real = pathlib.Path.replace
            record = lambda p, t: (renames.append((p.name, pathlib.Path(t).name)), real(p, t))[1]
            with patch.object(pathlib.Path, 'replace', new=record), self.power_cut_after(4), self.assertRaises(OSError):
                run()  # cut right after the entry switch, before publication
            self.assertEqual(os.readlink(home / 'at'), 'tools-' + fingerprint + '/at')
            # Run through their own directory, the old tools settle the state: before
            # publication they are current, so the entry is theirs again and they answer.
            self.assertEqual(self.reached(self.entry_run(home, 'check', path='tools-' + old + '/at')), 'new')
            self.assertEqual(os.readlink(home / 'at'), 'tools-' + old + '/at')
            self.assertEqual(json.loads((home / 'tools-update-intent.json').read_text())['phase'], 'publish')
            with patch.object(pathlib.Path, 'replace', new=record), self.power_cut_after(2), self.assertRaises(OSError):
                run()  # resumed: entry switch, checks, then the journal to retire: published
            self.assertEqual(json.loads((home / 'tools-update-intent.json').read_text())['phase'], 'retire')
            # Now the old tools refuse through their own directory: the entry moved on for good.
            result = self.entry_run(home, 'check', path='tools-' + old + '/at')
            self.refused(result, self.BOUNCE)
            self.assertEqual(os.readlink(home / 'at'), 'tools-' + fingerprint + '/at')
            self.assertEqual(self.reached(self.entry_run(home, 'check')), 'new')
            with patch.object(pathlib.Path, 'replace', new=record):
                run()
            self.assertNotIn('.tools-held', [name for pair in renames for name in pair])
            self.updated(home, fingerprint, old)
            self.assertEqual(self.reached(self.entry_run(home, 'check')), 'new')
            result = self.entry_run(home, 'check', path='retired-tools/' + old + '/at')
            self.refused(result, self.NOT_INSTALLED)

    def test_unexpected_states_stop_without_moving_anything(self):
        """Outside the journal's model the decision refuses; it never guesses."""
        with self.installation() as (home, run, fingerprint, old, host):
            with self.power_cut_after(5), self.assertRaises(OSError):
                run()
            held = home / '.tools-held'
            (held / 'owner.py').write_bytes(b'# tampered\n')
            before = self.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, 'No installed tools and no verified held copy: unverified .*hash mismatch: owner.py'):
                run()
            self.assertEqual(before, self.snapshot(home))
        with self.installation() as (home, run, fingerprint, old, host):
            with self.power_cut_after(3), self.assertRaises(OSError):
                run()
            self.journal_value(home, 'previous', 'a' * 64)
            before = self.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, 'match neither side of the tools update: ' + old):
                run()
            self.assertEqual(before, self.snapshot(home))
            self.works(home, old, fingerprint)

    def test_invariant_old_tools_retire_only_after_the_new_ones_are_published(self):
        with self.installation() as (home, run, fingerprint, old, host):
            order = []
            real = pathlib.Path.replace
            def rename(path, target):
                if path in (home / 'tools', home / '.update-tools', home / '.tools-held', home / '.at.new'):
                    order.append((path.name, pathlib.Path(target).relative_to(home).as_posix()))
                    if path == home / '.tools-held':
                        self.assertEqual(owner.checked_bundle(home / ('tools-' + fingerprint)), fingerprint)
                        self.assertEqual(os.readlink(home / 'at'), 'tools-' + fingerprint + '/at')
                        self.assertEqual(json.loads((home / 'tools-update-intent.json').read_text())['phase'], 'retire')
                return real(path, target)
            with patch.object(pathlib.Path, 'replace', new=rename):
                run()
            self.assertEqual(order, [('.update-tools', 'tools-' + fingerprint), ('.at.new', 'at'), ('tools', '.tools-held'),
                                     ('.tools-held', 'retired-tools/' + old)])
            self.updated(home, fingerprint, old)

    def legacy_command(self, path, home):
        """Start a command of the installed tools through a real entry path."""
        process = subprocess.Popen(['bash', str(path), 'layout', 'begin', 'us'], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: (process.kill(), process.wait()))
        # Wait until the real at wrapper has exec'd the python entry (same pid).
        deadline = time.monotonic() + 10
        while not any(r['pid'] == process.pid and r['argv'][1:3] == ['-I', '-B'] for r in owner.installed_commands(home)):
            self.assertLess(time.monotonic(), deadline, 'legacy command not found')
            self.assertIsNone(process.poll(), 'legacy command ended early')
            time.sleep(.05)
        return process

    def test_a_running_15f_command_through_the_real_entry_blocks_the_update(self):
        sleeper = b'import time\ntime.sleep(60)\n'
        with self.installation(legacy_owner=sleeper) as (home, run, fingerprint, old, host):
            self.assertEqual((home / 'tools/at').read_bytes(), (ROOT / 'os/owner-tools/at').read_bytes())
            process = self.legacy_command(home / 'at', home)
            found, = owner.installed_commands(home)
            # The real at wrapper has exec'd the 15f entry: python3 -I -B <tools>/owner.py.
            self.assertEqual(found['argv'][1:4], ['-I', '-B', str(home / 'tools/owner.py')])
            before = self.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, 'An owner command of the installed tools is running'):
                run()
            self.assertEqual(before, self.snapshot(home))
            process.kill()
            process.wait()
            run()
            self.updated(home, fingerprint, old)

    def legacy_attempts(self, home):
        """Try every way into the old tools; return each exit status (the entry's with its first STOP line)."""
        attempts = {
            'at': ['bash', str(home / 'at'), 'check'],
            'tools/at': ['bash', str(home / 'tools/at'), 'check'],
            'tools/owner.py': ['/usr/bin/python3', '-I', '-B', str(home / 'tools/owner.py'), 'check'],
        }
        codes = {}
        for name, argv in attempts.items():
            result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
            codes[name] = (result.returncode, result.stdout.splitlines()[0]) if name == 'at' else result.returncode
        return codes

    def test_every_legacy_path_is_unusable_at_the_final_scan_and_the_publication(self):
        """Blocked before scanning: at the deciding scan and at publication nothing old can start.

        The entry already reaches the new tools (here stopped by their root
        check, as this test is not root); the old directory is gone.
        """
        with self.installation() as (home, run, fingerprint, old, host):
            seen = []
            scan = owner.installed_commands
            def scanned(where):
                if (home / '.tools-held').is_dir():
                    seen.append(('scan', self.legacy_attempts(home)))
                return scan(where)
            real = owner.Tools.save
            def save(obj, name, value):
                if name == 'tools-update-intent' and value.get('phase') == 'retire':
                    seen.append(('publish', self.legacy_attempts(home)))
                return real(obj, name, value)
            with patch.object(owner, 'installed_commands', side_effect=scanned), patch.object(owner.Tools, 'save', new=save):
                run()
            self.assertEqual([where for where, _ in seen], ['scan', 'publish'])
            for where, codes in seen:
                # 127: bash cannot open the script; 2: python3 cannot open the file.
                self.assertEqual(codes, {'at': (1, 'STOP: Use sudo from the authenticated ares-recovery session'),
                                         'tools/at': 127, 'tools/owner.py': 2}, where)
            self.updated(home, fingerprint, old)

    def test_the_held_old_tools_cannot_run_outside_their_home(self):
        """The 15f main (git e062f4a2, the 3ef85c4a bundle) requires payload == HOME / 'tools'; so does this one for tools/."""
        source = (ROOT / 'os/owner-tools/owner.py').read_text()
        self.assertIn("require((payload == HOME / 'tools' or payload == HOME / ('tools-' + fingerprint)) and HOME.stat().st_uid == 0", source)
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            home = pathlib.Path(temporary)
            held = home / '.tools-held'
            common.fixture_bundle(held)
            with patch.object(owner, 'HOME', home), patch.object(owner, 'STOP_RECORDS', home / 'diagnostics'), \
                    patch.object(owner, '__file__', str(held / 'owner.py')), patch.object(owner, 'LOCK', home / 'ares-owner.lock'), \
                    patch.object(owner.os, 'geteuid', return_value=0), patch.object(owner.os, 'umask'), \
                    patch.object(owner.sys, 'argv', ['at', 'check']), contextlib.redirect_stdout(io.StringIO()), \
                    self.assertRaisesRegex(owner.Stop, 'Run the installed root-only tools'):
                owner.main()

    def test_a_legacy_command_that_ran_after_the_early_checks_leaves_no_stale_result(self):
        """It started and finished before the block; the checks after the block see it."""
        trial = (b'import pathlib\n(pathlib.Path(__file__).resolve().parent.parent / "records/layout-pending.json").write_text("{}")\n'
                 b'print("15f stand-in ran")\n')
        with self.installation(legacy_owner=trial) as (home, run, fingerprint, old, host):
            real = shutil.copy2
            ran = []
            def copy_file(*args, **kwargs):
                if not ran:
                    ran.append(subprocess.run(['bash', str(home / 'at'), 'layout', 'begin', 'us'], timeout=10).returncode)
                return real(*args, **kwargs)
            with patch('shutil.copy2', side_effect=copy_file), self.assertRaisesRegex(owner.Stop, 'Layout trial is unfinished'):
                run()
            self.assertEqual(ran, [0])
            self.assertEqual(owner.checked_bundle(home / 'tools'), old)
            self.assertEqual(os.readlink(home / 'at'), 'tools/at')
            self.assertFalse((home / '.tools-held').exists())
            self.assertEqual(json.loads((home / 'tools-update-intent.json').read_text())['phase'], 'publish')
            self.assertEqual(self.works(home, old, fingerprint), '15f')
            (home / 'records/layout-pending.json').unlink()
            run()
            self.updated(home, fingerprint, old)

    def test_a_legacy_command_still_running_at_the_block_is_refused_and_the_old_tools_return(self):
        sleeper = b'import time\ntime.sleep(60)\n'
        with self.installation(legacy_owner=sleeper) as (home, run, fingerprint, old, host):
            real = shutil.copy2
            started = []
            def copy_file(*args, **kwargs):
                if not started:
                    started.append(self.legacy_command(home / 'at', home))
                return real(*args, **kwargs)
            with patch('shutil.copy2', side_effect=copy_file), \
                    self.assertRaisesRegex(owner.Stop, 'An owner command of the installed tools is running'):
                run()
            self.assertEqual(owner.checked_bundle(home / 'tools'), old)
            self.assertFalse((home / '.tools-held').exists())
            self.sleeper_entry_starts(home, old)
            started[0].kill()
            started[0].wait()
            run()
            self.updated(home, fingerprint, old)

    def test_an_interruption_while_the_old_tools_are_blocked_recovers(self):
        with self.installation() as (home, run, fingerprint, old, host):
            # Rename 5 is the block (journal copy, the new directory, journal publish, the entry switch).
            with self.power_cut_after(5), self.assertRaises(OSError):
                run()
            self.assertFalse((home / 'tools').exists())
            self.assertEqual(owner.checked_bundle(home / '.tools-held'), old)
            self.assertEqual(self.legacy_attempts(home), {'at': (1, 'STOP: Use sudo from the authenticated ares-recovery session'),
                                                          'tools/at': 127, 'tools/owner.py': 2})
            self.assertEqual(self.works(home, old, fingerprint), '15f')
            run()
            self.updated(home, fingerprint, old)

    def test_invariant_broad_detection_refuses_every_kind_of_legacy_process(self):
        """Started during the copy, found by the deciding scan after the block."""
        sleeper = b'import time\ntime.sleep(60)\n'
        kinds = {
            'python3 -B, no -I': lambda home: (['/usr/bin/python3', '-B', str(home / 'tools/owner.py'), 'layout'], None, None),
            'relative script in tools': lambda home: (['/usr/bin/python3', '-B', 'owner.py', 'layout'], home / 'tools', None),
            'relative path from home': lambda home: (['/usr/bin/python3', 'tools/owner.py', 'layout'], home, None),
            'entry at': lambda home: (['bash', str(home / 'at'), 'layout', 'begin', 'us'], None, None),
            'entry tools/at': lambda home: (['bash', str(home / 'tools/at'), 'layout', 'begin', 'us'], None, None),
            'open file only': lambda home: (['/usr/bin/python3', '-c', 'import os,time\nf=open(os.environ["P"])\ntime.sleep(60)'],
                                            pathlib.Path('/'), dict(os.environ, P=str(home / 'tools/owner.py'))),
            'working directory only': lambda home: (['sleep', '60'], home / 'tools', None),
        }
        for name, kind in kinds.items():
            with self.subTest(kind=name), self.installation(legacy_owner=sleeper) as (home, run, fingerprint, old, host):
                started = []
                real = shutil.copy2
                def copy_file(*args, **kwargs):
                    if not started:
                        argv, cwd, env = kind(home)
                        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self.addCleanup(lambda: (process.kill(), process.wait()))
                        deadline = time.monotonic() + 10
                        while not any(r['pid'] == process.pid for r in owner.installed_commands(home)):
                            self.assertLess(time.monotonic(), deadline, name + ' not detected')
                            time.sleep(.05)
                        started.append(process)
                    return real(*args, **kwargs)
                with patch('shutil.copy2', side_effect=copy_file), \
                        self.assertRaisesRegex(owner.Stop, 'An owner command of the installed tools is running'):
                    run()
                self.assertEqual(owner.checked_bundle(home / 'tools'), old)
                self.sleeper_entry_starts(home, old)
                started[0].kill()
                started[0].wait()
                run()
                self.updated(home, fingerprint, old)
                self.assertEqual(self.works(home, old, fingerprint), 'new')

    @contextlib.contextmanager
    def unreadable(self, pid, where, error):
        """Make one /proc read of this process fail: its cwd, cmdline or a descriptor."""
        prefix = '/proc/' + str(pid) + '/'
        failing = {'cwd': prefix + 'cwd', 'cmdline': prefix + 'cmdline', 'descriptor': prefix + 'fd/'}[where]
        real_readlink, real_read = os.readlink, pathlib.Path.read_bytes
        def readlink(path, *args, **kwargs):
            if str(path).startswith(failing) and where != 'cmdline':
                raise error
            return real_readlink(path, *args, **kwargs)
        def read_bytes(path):
            if str(path) == failing:
                raise error
            return real_read(path)
        with patch.object(owner.os, 'readlink', readlink), patch.object(pathlib.Path, 'read_bytes', read_bytes):
            yield

    def test_unreadable_processes_count_as_in_use_and_refuse(self):
        """Any read error short of a confirmed disappearance is doubt, and doubt refuses."""
        errors = {'EACCES': PermissionError(13, 'Permission denied'), 'EIO': OSError(5, 'Input/output error')}
        for where in ('cwd', 'cmdline', 'descriptor'):
            for name, error in errors.items():
                with self.subTest(where=where, error=name), self.installation() as (home, run, fingerprint, old, host):
                    other = subprocess.Popen(['sleep', '60'], cwd='/')
                    self.addCleanup(lambda process=other: (process.kill(), process.wait()))
                    with self.unreadable(other.pid, where, error):
                        found = [r for r in owner.installed_commands(home) if r['pid'] == other.pid]
                        self.assertEqual(len(found), 1, found)
                        self.assertIn('unreadable', found[0]['reason'])
                        before = self.snapshot(home)
                        with self.assertRaisesRegex(owner.Stop, r'is running \(pid .*\b' + str(other.pid) + r'\b.*unreadable'):
                            run()  # the early scan: nothing written
                        self.assertEqual(before, self.snapshot(home))
                    self.assertEqual([r for r in owner.installed_commands(home) if r['pid'] == other.pid], [])
        # Appearing only after the block: the deciding scan refuses and the old tools come back.
        with self.installation() as (home, run, fingerprint, old, host):
            other = subprocess.Popen(['sleep', '60'], cwd='/')
            self.addCleanup(lambda: (other.kill(), other.wait()))
            doubt = contextlib.ExitStack()
            real = shutil.copy2
            def copy_file(*args, **kwargs):
                if not doubt._exit_callbacks:
                    doubt.enter_context(self.unreadable(other.pid, 'descriptor', errors['EIO']))
                return real(*args, **kwargs)
            with doubt, patch('shutil.copy2', side_effect=copy_file), \
                    self.assertRaisesRegex(owner.Stop, 'An owner command of the installed tools is running'):
                run()
            self.assertEqual(owner.checked_bundle(home / 'tools'), old)
            self.assertFalse((home / '.tools-held').exists())
            self.works(home, old, fingerprint)
            run()
            self.updated(home, fingerprint, old)

    def test_a_live_thread_beside_an_exited_leader_counts(self):
        """proc(5): cwd is unavailable once the main thread exited; the group may still hold the tools."""
        program = ('import ctypes, sys, threading, time\n'
                   'held = open(sys.argv[1])\n'
                   'threading.Thread(target=lambda: time.sleep(60)).start()\n'
                   'ctypes.CDLL(None).pthread_exit(None)\n')
        with self.installation() as (home, run, fingerprint, old, host):
            worker = subprocess.Popen(['/usr/bin/python3', '-c', program, str(home / 'tools/owner.py')], cwd='/')
            self.addCleanup(lambda: (worker.kill(), worker.wait()))
            deadline = time.monotonic() + 10
            while (pathlib.Path('/proc') / str(worker.pid) / 'stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z':
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.05)
            with self.assertRaises(FileNotFoundError):
                os.readlink('/proc/' + str(worker.pid) + '/cwd')
            found = [r for r in owner.installed_commands(home) if r['pid'] == worker.pid]
            self.assertEqual(len(found), 1, found)
            self.assertIn('unreadable', found[0]['reason'])
            self.assertFalse(owner.process_absent(pathlib.Path('/proc') / str(worker.pid)))
            before = self.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, r'is running \(pid .*\b' + str(worker.pid) + r'\b'):
                run()
            self.assertEqual(before, self.snapshot(home))
            worker.kill()
            worker.wait()
            run()
            self.updated(home, fingerprint, old)

    def test_a_worker_handoff_during_the_task_snapshot_still_counts(self):
        """Review 7's race: between the task/ enumeration and the per-thread reads, worker A starts B and exits."""
        program = ('import sys, threading, time, ctypes\n'
                   'held = open(sys.argv[1])\n'
                   'def worker_a():\n'
                   '    sys.stdin.readline()  # the test says when the scan has taken its snapshot\n'
                   '    threading.Thread(target=lambda: time.sleep(60)).start()  # worker B inherits the open file\n'
                   '    print("handed off", flush=True)\n'
                   'threading.Thread(target=worker_a).start()\n'
                   'ctypes.CDLL(None).pthread_exit(None)\n')
        with self.installation() as (home, run, fingerprint, old, host):
            child = subprocess.Popen(['/usr/bin/python3', '-c', program, str(home / 'tools/owner.py')], cwd='/',
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            self.addCleanup(lambda: (child.kill(), child.wait()))
            process = pathlib.Path('/proc') / str(child.pid)
            deadline = time.monotonic() + 10
            while (process / 'stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z' or len(list((process / 'task').iterdir())) != 2:
                self.assertLess(time.monotonic(), deadline)
                time.sleep(.05)
            snapshots = []
            real = pathlib.Path.iterdir
            def iterdir(path):
                entries = list(real(path))
                if path == process / 'task':
                    snapshots.append(sorted(p.name for p in entries))
                    if len(snapshots) == 1:
                        # The scan holds a snapshot of {leader, A}; now A starts B and exits.
                        child.stdin.write('go\n')
                        child.stdin.flush()
                        self.assertEqual(child.stdout.readline().strip(), 'handed off')
                        deadline = time.monotonic() + 10
                        while any(p.name == snapshots[0][1] for p in real(path)):
                            self.assertLess(time.monotonic(), deadline, 'worker A did not exit')
                            time.sleep(.05)
                return iter(entries)
            with patch.object(pathlib.Path, 'iterdir', iterdir):
                self.assertFalse(owner.process_absent(process))
            # The first snapshot lacked B; the confirming one listed it, so the group counted.
            self.assertEqual(len(snapshots), 2)
            self.assertNotEqual(snapshots[0], snapshots[1])
            self.assertEqual(len(snapshots[1]), 2)
            found = [r for r in owner.installed_commands(home) if r['pid'] == child.pid]
            self.assertEqual(len(found), 1, found)
            before = self.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, r'is running \(pid .*\b' + str(child.pid) + r'\b'):
                run()
            self.assertEqual(before, self.snapshot(home))

    def test_confirmed_absence_is_not_doubt(self):
        """What the kernel reports as absent (ENOENT) does not refuse: a zombie, a closed descriptor.

        A running user process always has a working directory, so ENOENT
        there means no filesystem context: a zombie (shown here), a task past
        exit, or a kernel thread, which root sees on every laptop; none of
        them can hold the tools.
        """
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            home = pathlib.Path(temporary) / 'home'
            (home / 'tools').mkdir(parents=True)
            zombie = subprocess.Popen(['sleep', '60'], cwd=home / 'tools')
            try:
                time.sleep(.2)
                self.assertTrue(any(r['pid'] == zombie.pid for r in owner.installed_commands(home)))
                zombie.kill()
                time.sleep(.2)  # exited, not yet waited for: /proc still lists it
                process = pathlib.Path('/proc') / str(zombie.pid)
                self.assertEqual((process / 'stat').read_text().rsplit(')', 1)[1].split()[0], 'Z')
                with self.assertRaises(FileNotFoundError):
                    os.readlink(str(process / 'cwd'))
                self.assertTrue(owner.process_absent(process))
                self.assertFalse(any(r['pid'] == zombie.pid for r in owner.installed_commands(home)))
            finally:
                zombie.kill()
                zombie.wait()
            self.assertFalse(any(r['pid'] == zombie.pid for r in owner.installed_commands(home)))
            # A closed descriptor reads as ENOENT; a process whose descriptor closes mid-scan is not counted.
            with self.assertRaises(FileNotFoundError):
                os.readlink('/proc/self/fd/4095')
            other = subprocess.Popen(['sleep', '60'], cwd='/')
            try:
                time.sleep(.2)
                with self.unreadable(other.pid, 'descriptor', FileNotFoundError(2, 'No such file or directory')):
                    self.assertFalse(any(r['pid'] == other.pid for r in owner.installed_commands(home)))
            finally:
                other.kill()
                other.wait()

    def test_invariant_broad_detection_ignores_unrelated_processes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            home = pathlib.Path(temporary) / 'home'
            (home / 'tools').mkdir(parents=True)
            other = subprocess.Popen(['sleep', '60'], cwd='/')
            try:
                time.sleep(.2)
                self.assertFalse(any(r['pid'] == other.pid for r in owner.installed_commands(home)))
            finally:
                other.kill()
                other.wait()

    def test_the_wrapper_stage_is_found_by_its_exact_path(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            home = pathlib.Path(temporary)
            (home / 'tools').mkdir()
            (home / 'tools/at').write_text('sleep 60\n')
            os.symlink('tools/at', home / 'at')
            for path in (home / 'at', home / 'tools/at'):
                with self.subTest(path=path.name):
                    process = subprocess.Popen(['bash', str(path)])
                    try:
                        deadline = time.monotonic() + 10
                        while not any(r['pid'] == process.pid for r in owner.installed_commands(home)):
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.05)
                    finally:
                        process.kill()
                        process.wait()
            other = subprocess.Popen(['bash', '-c', 'sleep 60', 'at'])
            try:
                time.sleep(.2)
                self.assertFalse(any(r['pid'] == other.pid for r in owner.installed_commands(home)))
            finally:
                other.kill()
                other.wait()

    def test_interrupted_update_resumes_only_with_the_same_bundle_and_stick(self):
        with self.installation() as (home, run, fingerprint, old, host):
            with patch('shutil.copytree', side_effect=OSError('interrupt')), self.assertRaises(OSError):
                run()
            intent = json.loads((home / 'tools-update-intent.json').read_text())
            writer = object.__new__(owner.Tools)
            writer.store = home
            writer.save('tools-update-intent', dict(intent, manifest='f' * 64))
            before = self.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, 'does not exactly match'):
                run()
            self.assertEqual(before, self.snapshot(home))

    def test_unchanged_first_install_route_refuses_an_updated_installation(self):
        """The 15f tools run this unchanged route: they cannot downgrade an update."""
        with self.installation() as (home, run, fingerprint, old, host):
            run()
            before = self.snapshot(home)
            intent = json.loads((home / 'install-intent.json').read_text())
            writer = object.__new__(owner.Tools)
            writer.store = home
            writer.save('install-intent', dict(intent, manifest=fingerprint, identity=owner.setup_identity(
                owner.disk_record(host, dict(target='TARGET', protected='KEEP'))), tools_volume_uuid='CAFE-1234'))
            before = self.snapshot(home)
            with patch.object(owner, 'installed_update', return_value=False), patch('builtins.input', side_effect=['TARGET', 'KEEP']), \
                    self.assertRaisesRegex(owner.Stop, 'Unexpected installation files'):
                run()
            self.assertEqual(before, self.snapshot(home))


# The fake bootc's staging, by mode. Every mode records its pid; a child records its own.
STOP_BOOTC = r'''#!/bin/bash
printf 'bootc %s\n' "$*" >> "$FIXTURE_CALLS"
case "$*" in
    'status --json') cat "$FIXTURE_ROOT/state.json" ;;
    'switch --retain '*)
        echo $$ > "$FIXTURE_ROOT/bootc.pid"; echo $PPID > "$FIXTURE_ROOT/step.pid"
        if [[ -e $FIXTURE_ROOT/weird-name ]]; then printf '\xff\xfe\xfdbootc' > /proc/$BASHPID/comm; fi
        target=${*: -1}
        case $(cat "$FIXTURE_ROOT/mode") in
            # Ignores TERM: only KILL ends it.
            hang) trap '' TERM; while :; do sleep 0.1; done ;;
            # Stages (another release if told), then is still running when the time limit hits.
            stage-then-run)
                if [[ -s $FIXTURE_ROOT/foreign ]]; then target=$(cat "$FIXTURE_ROOT/foreign"); fi
                echo "$target" > "$FIXTURE_ROOT/staged"; sleep 3600 ;;
            # Fails, leaving a TERM-proof child that closed the step's pipes.
            fail-with-child)
                ( trap '' TERM; exec > /dev/null 2>&1 < /dev/null
                  if [[ -e $FIXTURE_ROOT/weird-name ]]; then printf '\xc3' > /proc/$BASHPID/comm; fi
                  while :; do sleep 0.1; done ) &
                echo $! > "$FIXTURE_ROOT/child.pid"; exit 42 ;;
            stage-ok) echo "$target" > "$FIXTURE_ROOT/staged" ;;
        esac ;;
    *) echo UNEXPECTED_BOOTC_COMMAND >&2; exit 97 ;;
esac
'''


class StopRunner(Machine):
    """The update step through the real owner.Step: real bash, the real update.sh
    (fixture paths), a fake bootc and systemctl over a fixture /etc/systemd/system.
    Status reads, cleanup and the stop routine's systemctl calls go to the same model."""
    root = None
    failing_reads = 0
    broken_masks = False

    def start(self, text, name):
        if name != 'update':
            return super().start(text, name)
        for old, new in (('test -r /etc/ostree/auth.json', 'test -r "$FIXTURE_ROOT/auth.json"'),
                         ('policy=/usr/share/aresos/policy\n', 'policy="$FIXTURE_ROOT/policy"\n'),
                         ('units=/etc/systemd/system\n', 'units="$FIXTURE_ROOT/units"\n')):
            assert text.count(old) == 1, old
            text = text.replace(old, new)
        syntax(name, text)
        (self.root / 'state.json').write_text(json.dumps(self.state['bootc']))
        prefix = ('export FIXTURE_ROOT=' + shlex.quote(str(self.root)) + ' FIXTURE_CALLS='
                  + shlex.quote(str(self.root / 'calls')) + '\nPATH="$FIXTURE_ROOT/bin:$PATH"\n')
        return owner.Host.start(self, prefix + text, name)

    def sync(self):
        marker = self.root / 'staged'
        rows = self.state['rpm']['deployments']
        if marker.exists() and not any(r.get('staged') for r in rows):
            self.state = machine([release_row(marker.read_text().strip(), staged=True), *rows])

    def json(self, *command):
        if self.failing_reads and (self.root / 'bootc.pid').exists():
            self.failing_reads -= 1
            raise OSError('injected status read failure after the kill')
        self.sync()
        return super().json(*command)

    def mutate(self, *command, **unused):
        super().mutate(*command)
        if command == ('rpm-ostree', 'cleanup', '--pending'):
            (self.root / 'staged').unlink(missing_ok=True)

    def read(self, *command, **unused):
        if command[:2] == ('systemctl', 'is-enabled'):
            self.trace.append(dict(command=list(command), mutation=False))
            path = self.root / 'units' / command[2]
            masked = path.is_symlink() and os.readlink(path) == '/dev/null' and not self.broken_masks
            return 'masked\n' if masked else 'static\n'
        return super().read(*command)


class ToolKilled(BaseException):
    """Stands in for the default action of SIGTERM or SIGHUP: the tool dying where it stands."""


@unittest.skipIf(os.name == 'nt', 'needs a Linux bash, /proc and process groups')
class UpdateStopTest(unittest.TestCase):
    """Reviews 1 and 2: one stop routine for every unsuccessful end of the update step.

    The step runs in its own session through the real owner.Step. From its start to the
    end of the stop routine, SIGINT, SIGTERM and SIGHUP only note themselves. The routine
    ends every process of the step and proves none is left, removes only this update's
    own staged deployment, restores the finalizer masks in every case, and claims a
    clean stop only when every check passed.
    """
    MASKED = dict.fromkeys(owner.FINALIZERS, '/dev/null')

    spawned = []

    @classmethod
    def tearDownClass(cls):
        # Review 3: no test may leave a process behind; the survivor case kills its own after its checks.
        left = [(pid, start) for pid, start in cls.spawned if start is not None and cls.started(pid) == start]
        for pid, start in left:
            cls.kill(pid, start)
        assert not left, 'UpdateStopTest left processes behind: ' + repr(left)

    def run_stopped(self, mode, timeout=6, signals=(), foreign=None, failing_reads=0,
                    stdout=None, swallow_kill=False, weird_name=False, outsider=False, patches=(), broken_masks=False):
        import signal, threading
        import test_release27 as r27
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory, \
                route(pair(), host_class=StopRunner) as (tools, host, store), contextlib.ExitStack() as stack:
            root = pathlib.Path(directory)
            for name in ('units', 'policy', 'bin'):
                (root / name).mkdir()
            for name in ('masked-system-units.txt', 'masked-user-units.txt'):
                shutil.copyfile(ROOT / 'os/policy' / name, root / 'policy' / name)
            for name in ('auth.json', 'calls', 'system-unmasked', 'user-unmasked'):
                (root / name).write_text('{}\n' if name == 'auth.json' else '')
            (root / 'mode').write_text(mode)
            (root / 'foreign').write_text(foreign or '')
            for unit in owner.FINALIZERS:
                os.symlink('/dev/null', root / 'units' / unit)
            stubs = dict(systemctl=r27.UPDATE_STUBS['systemctl'], bootc=STOP_BOOTC,
                         python3='#!/bin/bash\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
            for name, source in stubs.items():
                (root / 'bin' / name).write_text(source)
                (root / 'bin' / name).chmod(0o755)
            host.root, host.failing_reads, host.broken_masks = root, failing_reads, broken_masks
            if weird_name:
                (root / 'weird-name').write_text('')
            if outsider:
                # A process outside the step whose /proc name is not UTF-8 (15 raw bytes may cut a character).
                other = subprocess.Popen([sys.executable, '-c', "open('/proc/self/comm', 'wb').write(b'\\xe2\\x82'); "
                                          "import time; time.sleep(120)"], start_new_session=True)
                self.addCleanup(other.wait, 5)
                self.addCleanup(other.kill)
                deadline = time.monotonic() + 10
                while pathlib.Path('/proc', str(other.pid), 'comm').read_bytes() != b'\xe2\x82\n':
                    self.assertLess(time.monotonic(), deadline, 'the outsider never took its name')
                    time.sleep(0.02)
            for target, replacement in patches:
                stack.enter_context(patch.object(owner.Step, target, replacement))
            # As at a terminal: Ctrl+C raises KeyboardInterrupt, and TERM or HUP would end the
            # tool where it stands (modelled by ToolKilled, so a failure cannot kill the test run).
            def killed(signum, frame):
                raise ToolKilled(signum)
            for signum, handler in ((signal.SIGINT, signal.default_int_handler), (signal.SIGTERM, killed),
                                    (signal.SIGHUP, killed)):
                self.addCleanup(signal.signal, signum, signal.signal(signum, handler))
            # Signals count from the fake bootc's start, so a slow (loaded) update.sh preamble cannot reorder them.
            cancelled = threading.Event()

            def send():
                started = time.monotonic() + 30
                while not (root / 'bootc.pid').exists() and not cancelled.is_set() and time.monotonic() < started:
                    time.sleep(0.02)
                begin = time.monotonic()
                for after, signum in sorted(signals):
                    if cancelled.wait(max(0, begin + after - time.monotonic())):
                        return
                    os.kill(os.getpid(), signum)
            timers = [threading.Thread(target=send, daemon=True)] if signals else []
            stack.enter_context(patch.object(owner, 'SCRIPT_TIMEOUT', timeout))
            stack.enter_context(patch.object(owner, 'STOP_GRACE', 1 if swallow_kill else 3))
            stack.enter_context(patch.object(owner, 'UNITS', root / 'units'))
            if swallow_kill:
                # A process that survives KILL: the routine's KILLs never arrive (TERM is ignored).
                real_kill, real_killpg = os.kill, os.killpg
                stack.enter_context(patch.object(owner.os, 'kill', side_effect=lambda pid, signum:
                    None if signum == signal.SIGKILL else real_kill(pid, signum)))
                stack.enter_context(patch.object(owner.os, 'killpg', side_effect=lambda pgid, signum:
                    None if signum == signal.SIGKILL else real_killpg(pgid, signum)))
            printed = io.StringIO() if stdout is None else stdout
            stack.enter_context(contextlib.redirect_stdout(printed))
            start = time.monotonic()
            for timer in timers:
                timer.start()
            try:
                tools.update()
                outcome = None
            except BaseException as error:
                outcome = error
            finally:
                cancelled.set()
                for timer in timers:
                    timer.join(5)
            elapsed = time.monotonic() - start
            # What the fake bootc really left, whether or not the tool looked again.
            host.sync()
            links = {path.name: os.readlink(path) if path.is_symlink() else None for path in (root / 'units').iterdir()}
            pids = [int((root / name).read_text()) for name in ('bootc.pid', 'child.pid') if (root / name).exists()]
            # Captured before the fixture directory goes (review 3: a path-based cleanup came too late);
            # the step's own shell too, for the case whose stop() is broken on purpose.
            shell = [int((root / 'step.pid').read_text())] if (root / 'step.pid').exists() else []
            for pid in pids + shell:
                # By start time too, so a reused PID is never killed.
                self.spawned.append((pid, self.started(pid)))
                self.addCleanup(self.kill, pid, self.started(pid))
            intent = tools.load(owner.OUTCOME)
            settled = None if host.state != pair() else tools.qualified(host.state, tools.load('prepared'), retry='update')
            return SimpleNamespace(outcome=outcome, links=links, pids=pids, host=host, intent=intent, settled=settled,
                                   elapsed=elapsed, printed=printed.getvalue() if stdout is None else '',
                                   calls=(root / 'calls').read_text().splitlines())

    @staticmethod
    def started(pid):
        """The live process's start time (stat field 22), or None once it is gone or a zombie."""
        try:
            raw = pathlib.Path('/proc', str(pid), 'stat').read_bytes()
        except (FileNotFoundError, ProcessLookupError):
            return None
        fields = raw.rsplit(b')', 1)[1].split() if raw else []
        return fields[19] if len(fields) > 19 and fields[0] != b'Z' else None

    @classmethod
    def kill(cls, pid, start):
        # Only a reverted fix (or the survivor case) leaves a fake process running; never leave it behind.
        import signal
        if start is not None and cls.started(pid) == start:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    @staticmethod
    def alive(pid):
        try:
            raw = pathlib.Path('/proc', str(pid), 'stat').read_bytes()
        except (FileNotFoundError, ProcessLookupError):
            return False
        return bool(raw) and raw.rsplit(b')', 1)[1].split()[0] != b'Z'

    def stopped_cleanly(self, run, words):
        # The named assertions (revert proofs): no staged deployment, the masks back, no
        # process of the step left, then the STOP that says so.
        self.assertEqual(run.host.state, pair(), 'a staged deployment remained after the stop')
        self.assertEqual(run.links, self.MASKED, 'the masks this run removed are not back')
        self.assertTrue(run.pids, 'the fake bootc never started staging')
        self.assertFalse([pid for pid in run.pids if self.alive(pid)], 'a process of the step outlived the tool')
        self.assertIsInstance(run.outcome, owner.Stop, 'the tool did not STOP through its routine')
        self.assertIn(words, str(run.outcome))
        self.assertIn('was stopped safely', str(run.outcome))
        self.assertIn('Nothing changes at the next start', str(run.outcome))
        # The running release, its rollback and the pinned stock are as before; the same command may retry.
        self.assertEqual((run.intent['status'], run.intent['before']),
                         ('intent', [list(owner.key(d)) for d in pair()['rpm']['deployments']]))
        self.assertEqual(run.settled, 'retry')

    def step(self, run):
        return [row for row in run.host.trace if row.get('script') == 'update' and row.get('stopped')][-1]

    def test_a_hung_staging_is_stopped_at_the_time_limit_and_undone(self):
        run = self.run_stopped('hang')
        self.stopped_cleanly(run, 'The update timed out')
        self.assertIn('bootc switch --retain ' + R21, run.calls)
        self.assertEqual((self.step(run)['stopped'], self.step(run)['group_gone']), ('timed out', True))
        self.assertIn('the staging finalizers are masked again', str(run.outcome))
        # The first line says what happens and for how long.
        self.assertIn('Stopping the update safely; this takes up to ', run.printed)
        self.assertLess(run.elapsed, 30)

    def test_staging_that_finished_before_the_time_limit_hits_the_still_running_step_is_removed(self):
        run = self.run_stopped('stage-then-run')
        self.stopped_cleanly(run, 'The update timed out')
        self.assertIn(('rpm-ostree', 'cleanup', '--pending'), run.host.changes)
        self.assertIn('its staged release was removed', str(run.outcome))

    def test_ctrl_c_stops_the_step_and_undoes_it(self):
        import signal
        run = self.run_stopped('hang', timeout=60, signals=[(1, signal.SIGINT)])
        self.stopped_cleanly(run, 'The update was interrupted (Ctrl+C)')
        self.assertLess(run.elapsed, 30)

    def test_a_second_and_third_ctrl_c_during_the_term_grace_cannot_cut_the_stop_short(self):
        import signal
        # The hung bootc ignores TERM, so the routine sits in its 3 s grace when the next two arrive.
        run = self.run_stopped('hang', timeout=60, signals=[(1, signal.SIGINT), (2, signal.SIGINT), (3, signal.SIGINT)])
        self.stopped_cleanly(run, 'The update was interrupted (Ctrl+C)')
        self.assertGreater(run.elapsed, 4)  # the TERM grace (3 s) ran after the first, around the others

    def test_a_closed_window_or_a_kill_starts_the_stop_routine(self):
        import signal

        class Closed(io.StringIO):
            def write(self, text):
                raise OSError(5, 'Input/output error')
        for signum, words in ((signal.SIGHUP, 'the window closing'), (signal.SIGTERM, 'a termination request')):
            with self.subTest(signal=signum):
                # A closed window also breaks the output; the routine still runs to its end.
                run = self.run_stopped('hang', timeout=60, signals=[(1, signum)],
                                       stdout=Closed() if signum == signal.SIGHUP else None)
                self.stopped_cleanly(run, 'The update was interrupted (' + words + ')')

    def test_a_failed_shell_with_a_surviving_child_is_stopped_before_anything_else(self):
        run = self.run_stopped('fail-with-child', timeout=60)
        self.assertEqual(len(run.pids), 2)
        self.stopped_cleanly(run, 'The update failed')
        # update.sh's own trap passes bootc's status on; the routine still had a child to stop.
        self.assertEqual(self.step(run)['returncode'], 42)
        self.assertLess(run.elapsed, 30)

    def test_a_status_read_that_fails_after_the_kill_still_restores_the_masks(self):
        run = self.run_stopped('stage-then-run', failing_reads=1)
        self.assertEqual(run.links, self.MASKED, 'the masks this run removed are not back')
        self.assertFalse([pid for pid in run.pids if self.alive(pid)], 'a process of the step outlived the tool')
        self.assertNotIn(('rpm-ostree', 'cleanup', '--pending'), run.host.changes)
        self.assertIsInstance(run.outcome, owner.Stop)
        self.assertIn('stopping it did not finish: deployments: injected status read failure', str(run.outcome))
        self.assertIn('Do not reboot', str(run.outcome))
        self.assertNotIn('stopped safely', str(run.outcome))

    def test_a_foreign_staged_deployment_is_never_deleted(self):
        run = self.run_stopped('stage-then-run', foreign=R30)
        self.assertNotIn(('rpm-ostree', 'cleanup', '--pending'), run.host.changes, 'a foreign staged deployment was deleted')
        self.assertEqual([r['container-image-reference-digest'] for r in run.host.state['rpm']['deployments'] if r.get('staged')],
                         [R30.split('@')[1]])
        self.assertEqual(run.links, self.MASKED, 'the masks this run removed are not back')
        self.assertIn('a staged deployment this update did not make is present; nothing was deleted', str(run.outcome))
        self.assertIn('Do not reboot', str(run.outcome))

    def test_a_process_that_survives_kill_is_reported_and_nothing_is_deleted_behind_it(self):
        run = self.run_stopped('hang', swallow_kill=True)
        self.assertTrue(run.pids and self.alive(run.pids[0]), 'the survivor is a real, live process')
        self.kill(run.pids[0], self.started(run.pids[0]))
        self.assertEqual(self.step(run)['group_gone'], False, 'a survivor was not reported')
        self.assertIn('survived TERM and KILL, so nothing was deleted', str(run.outcome), 'a survivor was not reported')
        self.assertNotIn(('rpm-ostree', 'cleanup', '--pending'), run.host.changes)
        self.assertEqual(run.links, self.MASKED, 'the masks this run removed are not back')
        self.assertIn('Do not reboot', str(run.outcome))

    def test_names_that_are_not_utf8_inside_and_outside_the_step_do_not_stop_the_stop(self):
        import signal
        # Review 3: one such name anywhere made the scan raise before the first signal.
        for name, options, words in (
                ('time limit', dict(mode='hang'), 'The update timed out'),
                ('Ctrl+C', dict(mode='hang', timeout=60, signals=[(1, signal.SIGINT)]), 'The update was interrupted (Ctrl+C)'),
                ('failed shell', dict(mode='fail-with-child', timeout=60), 'The update failed')):
            with self.subTest(name):
                run = self.run_stopped(weird_name=True, outsider=True, **options)
                self.stopped_cleanly(run, words)

    def test_an_exception_in_the_scan_deletes_nothing_and_still_restores_the_masks(self):
        def broken(step):
            raise RuntimeError('injected scan failure')
        run = self.run_stopped('stage-then-run', patches=[('members', broken)])
        self.assertNotIn(('rpm-ostree', 'cleanup', '--pending'), run.host.changes, 'something was deleted behind an unproved stop')
        self.assertEqual([r['container-image-reference-digest'] for r in run.host.state['rpm']['deployments'] if r.get('staged')],
                         [R21.split('@')[1]])
        self.assertEqual(run.links, self.MASKED, 'the masks this run removed are not back')
        self.assertIsInstance(run.outcome, owner.Stop)
        self.assertIn('stopping the update step failed (RuntimeError: injected scan failure), so nothing was deleted',
                      str(run.outcome))
        self.assertIn('Do not reboot', str(run.outcome))
        self.assertNotIn('stopped safely', str(run.outcome))

    def test_an_exception_in_stop_and_a_failed_mask_check_are_both_reported(self):
        def broken(step):
            raise RuntimeError('injected stop failure')
        run = self.run_stopped('stage-then-run', patches=[('stop', broken)], broken_masks=True)
        self.assertNotIn(('rpm-ostree', 'cleanup', '--pending'), run.host.changes, 'something was deleted behind an unproved stop')
        self.assertEqual(run.links, self.MASKED, 'the masks this run removed are not back')
        self.assertIn('stopping the update step failed (RuntimeError: injected stop failure), so nothing was deleted',
                      str(run.outcome))
        self.assertIn('finalizer masks: The mask of ', str(run.outcome))
        self.assertIn('Do not reboot', str(run.outcome))

    def test_a_successful_step_through_the_real_runner_stages_and_keeps_the_finalizers_unmasked(self):
        run = self.run_stopped('stage-ok', timeout=60)
        self.assertIsNone(run.outcome)
        self.assertEqual(run.links, {})
        self.assertEqual([r['container-image-reference-digest'] for r in run.host.state['rpm']['deployments'] if r.get('staged')],
                         [R21.split('@')[1]])
        self.assertNotIn('Stopping the update', run.printed)
        self.assertEqual(run.intent['status'], 'recorded')

if __name__ == '__main__':
    unittest.main()
