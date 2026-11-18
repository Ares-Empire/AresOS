"""22d: the two sources of a tools bundle, the stick block and the folder block.

Importing test_owner_update is library use only: nothing here starts the real
entry, a namespace, sudo or a host tool. The tools of versions 2 and 3 are read
from their commits with git show (like test_ways_back_compatibility): exactly
the code that was, or could have been, installed before the current tools.
"""
import contextlib
import functools
import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import test_owner_update as base
from test_owner_devices import FixtureHost, fixture
from ways_back_keyboard import PowerCut

ROOT, owner, common = base.ROOT, base.owner, base.common
# The merge commits whose payload is tools version 2 (on the laptop) and version 3 (on main, never installed there).
OLD = {2: ('41b06513', '851eb742bfe20bd4b47370b9f2558494edf4b74056d7023cc0d412e32fee6f33'),
       3: ('58738e5e', '2084c786c29d691a0d8c6ca450c59ef524751e5f6c475de0491f200a80765a3a')}
# What tools before version 4 wrote into the tools update journal.
JOURNAL_FIELDS = {'schema', 'previous', 'previous_directory', 'manifest', 'previous_version', 'tools_version',
                  'tools_volume_uuid', 'phase'}
STICK_ONLY = 'Interrupted tools update began from the tools USB; finish it from that stick at the recovery console'


@functools.lru_cache(maxsize=None)
def blob(version, path):
    return subprocess.check_output(['git', 'show', OLD[version][0] + ':os/owner-tools/payload/' + path], cwd=ROOT)


@functools.lru_cache(maxsize=None)
def old_tools(version):
    module = types.ModuleType('owner_v' + str(version) + '_' + OLD[version][0])
    module.__file__ = str(ROOT / 'os/owner-tools/payload/owner.py')
    exec(compile(blob(version, 'owner.py'), OLD[version][0] + ':owner.py', 'exec'), module.__dict__)
    return module


@functools.lru_cache(maxsize=None)
def old_files(version):
    rows = json.loads(blob(version, 'SHA256.json'))
    files = {row['path']: blob(version, row['path']) for row in rows}
    assert all(hashlib.sha256(files[row['path']]).hexdigest() == row['sha256'] for row in rows)
    return files


def journal(home):
    return json.loads((home / (owner.TOOLS_JOURNAL + '.json')).read_text())


def receipt(home):
    path, = (home / 'records').glob('*-tools-update.json')
    return json.loads(path.read_text())


@contextlib.contextmanager
def installation(version=None, versioned=False, source='stick'):
    """This checkout's bundle arriving over the 15f stand-in (version None) or over the exact tools of version 2 or 3.

    versioned is the laptop's shape: the old tools in tools-<fingerprint>/ after an earlier
    update from the stick, whose completed journal names no source.
    """
    harness = base.ToolsUpdateTest()
    installed = None
    if version is not None:
        current = {row['path'] for row in json.loads((base.PAYLOAD / 'SHA256.json').read_text())}
        installed = (None, None, tuple(current - set(old_files(version))), old_files(version))
    with patch.object(sys, 'dont_write_bytecode', True), contextlib.ExitStack() as stack:
        home, run, fingerprint, previous, host = stack.enter_context(
            harness.installation(installed=installed, versioned=versioned, source=source))
        if version is not None:
            assert previous == OLD[version][1]
            stack.enter_context(patch.object(old_tools(version), 'HOME', home))
        if versioned:
            writer = object.__new__(owner.Tools)
            writer.store = home
            writer.save(owner.TOOLS_JOURNAL, dict(schema='tools-update1', previous=owner.LEGACY_TOOLS[0], previous_directory='tools',
                manifest=previous, previous_version=1, tools_version=2, tools_volume_uuid='CAFE-1234', phase='complete',
                receipt='20261113T120000.000000Z-tools-update'))
        login = home.parent / 'loginuid'
        login.write_text('1001\n')
        stack.enter_context(patch.object(owner, 'LOGIN_UID', login))
        yield harness, home, run, fingerprint, previous, host


@contextlib.contextmanager
def events(home, stop=None):
    """Every file copy, rename and record write of an update with the journal phase after it; stop cuts the power there."""
    seen = []
    copy2, replace, save = owner.shutil.copy2, pathlib.Path.replace, owner.Tools.save

    def after(kind, call, *args, **options):
        result = call(*args, **options)
        path = home / (owner.TOOLS_JOURNAL + '.json')
        seen.append((kind, json.loads(path.read_text())['phase'] if path.exists() else None))
        if stop == len(seen):
            raise PowerCut('event ' + str(stop))
        return result
    with patch.object(owner.shutil, 'copy2', side_effect=lambda *a, **k: after('copy', copy2, *a, **k)), \
            patch.object(pathlib.Path, 'replace', lambda path, target: after('replace', replace, path, target)), \
            patch.object(owner.Tools, 'save', lambda obj, name, value: after('save', save, obj, name, value)):
        yield seen


def cut(run, home, stop):
    """Run the update until the power goes at one event: nothing of the tools runs after it.

    install settles the tools on every exception; a power cut leaves no time
    for that, so its handler finds the recovery switched off once the event came.
    """
    settle = owner.settle_tools
    with events(home, stop) as seen, patch.object(owner, 'settle_tools', lambda: settle() if len(seen) < stop else None):
        try:
            run()
        except PowerCut:
            return True
    return False


class RouteTest(unittest.TestCase):
    def test_the_block_that_ran_decides_the_route_whatever_is_plugged_in(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            root = pathlib.Path(temporary)
            for name, marker, expected in (('folder', None, 'folder'), ('stick', 'directory', 'stick'), ('doubt', 'link', 'stick')):
                private = root / name
                fingerprint = common.fixture_bundle(private / 'ares-tools')
                if marker == 'directory':
                    (private / 'm').mkdir()
                elif marker == 'link':
                    (private / 'm').symlink_to(root / 'nowhere')
                with self.subTest(block=name):
                    self.assertEqual(owner.bundle_source(private / 'ares-tools'), expected)
                    # The real main, up to the install it starts: the route is the block's, read from the private copy.
                    output = io.StringIO()
                    with patch.object(owner.os, 'geteuid', return_value=0), patch.object(owner, 'LOCK', root / (name + '.lock')), \
                            patch.object(owner, 'HOME', root / 'no-installation'), \
                            patch.object(owner, '__file__', str(private / 'ares-tools/owner.py')), \
                            patch.object(sys, 'argv', ['owner.py', 'install']), \
                            patch.object(owner, 'install', return_value=['installed']) as install, contextlib.redirect_stdout(output):
                        owner.main()
                    (payload, host, source), options = install.call_args
                    self.assertEqual((payload, source, options), (private / 'ares-tools', expected, {}))
                    self.assertIn('PASS install\ninstalled\n', output.getvalue())
            # The installed entry has no mount beside its toolset: install through it follows the folder rules.
            home = root / 'var/lib/ares'
            (home / ('tools-' + fingerprint)).mkdir(parents=True)
            self.assertEqual(owner.bundle_source(home / ('tools-' + fingerprint)), 'folder')
            self.assertEqual(owner.bundle_source(home / 'tools'), 'folder')
        self.assertEqual(owner.SOURCES, ('stick', 'folder'))
        self.assertEqual(tuple(common.module('bootstrap').SOURCES), owner.SOURCES)

    def test_the_caller_is_the_login_uid_and_whether_stdin_is_a_terminal(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            login = pathlib.Path(temporary) / 'loginuid'
            for text, expected in (('1001\n', 1001), ('1000', 1000), ('0\n', 0), ('4294967295\n', None), ('', None), ('ares', None)):
                login.write_text(text)
                for terminal in (False, True):
                    with self.subTest(text=text, terminal=terminal), patch.object(owner, 'LOGIN_UID', login), \
                            patch.object(owner.sys.stdin, 'isatty', return_value=terminal):
                        self.assertEqual(owner.caller(), dict(login_uid=expected, terminal=terminal))
            with patch.object(owner, 'LOGIN_UID', login / 'missing'), patch.object(owner.sys.stdin, 'isatty', return_value=False):
                self.assertEqual(owner.caller(), dict(login_uid=None, terminal=False))
            # Review 2, N3: with stdin closed (not /dev/null) Python has no sys.stdin; no terminal, no error.
            login.write_text('1001\n')
            with patch.object(owner, 'LOGIN_UID', login), patch.object(owner.sys, 'stdin', None):
                self.assertEqual(owner.caller(), dict(login_uid=1001, terminal=False))
        self.assertEqual(owner.LOGIN_UID, pathlib.Path('/proc/self/loginuid'))

    def test_the_folder_block_installs_without_a_terminal_and_never_looks_at_an_attached_stick(self):
        """The fixture's stick is plugged in and mounted; run() fails the test if the folder route asks for it."""
        with installation(source='folder') as (harness, home, run, fingerprint, previous, host):
            records = {p.name: p.read_bytes() for p in (home / 'records').iterdir()}
            self.assertIsNotNone(common.module('media').find(host, owner.require), 'the fixture stick is attached')
            host.trace.clear()
            lines = run()
            self.assertEqual(lines[:2], ['Tools updated from version 1 to 6', 'manifest SHA256 ' + fingerprint])
            harness.updated(home, fingerprint, previous)
            self.assertFalse(any('LABEL' in ' '.join(row['command']) for row in host.trace))
            self.assertFalse(any(row.get('mutation') for row in host.trace))
            value = journal(home)
            self.assertEqual(set(value), JOURNAL_FIELDS | {'source', 'receipt'})
            self.assertEqual((value['source'], value['tools_volume_uuid']), ('folder', None))
            written = receipt(home)
            self.assertEqual((written['source'], written['finished_from'], written['tools_volume_uuid'], written['caller']),
                             ('folder', 'folder', None, dict(login_uid=1001, terminal=False)))
            self.assertEqual({p.name: p.read_bytes() for p in (home / 'records').iterdir() if not p.name.endswith('-tools-update.json')}, records)
            again = harness.snapshot(home)
            self.assertEqual(run(), ['Tools already installed; nothing changed', 'manifest SHA256 ' + fingerprint])
            self.assertEqual(run('stick'), ['Tools already installed; nothing changed', 'manifest SHA256 ' + fingerprint])
            self.assertEqual(again, harness.snapshot(home))

    def test_the_stick_block_keeps_every_rule_and_its_record_names_the_stick(self):
        with installation(source='stick') as (harness, home, run, fingerprint, previous, host):
            before = harness.snapshot(home)
            for refusal, message in ((patch.object(owner.sys.stdin, 'isatty', return_value=False), 'Tools update runs only from the physical recovery console'),
                                     (patch.object(host, 'usb_root', home.parent / 'other-mount'), 'Bundle is not on the labelled removable tools USB')):
                with self.subTest(message=message), refusal, self.assertRaisesRegex(owner.Stop, '^' + message + '$'):
                    run()
                self.assertEqual(before, harness.snapshot(home))
            tree = fixture()
            for disk in tree['blockdevices']:
                disk['children'] = [row for row in disk.get('children', []) if row.get('label') != 'ARESTOOLS']
            with patch.object(host, 'tree', tree), self.assertRaisesRegex(owner.Stop, '^Tools USB label not found$'):
                run()
            self.assertEqual(before, harness.snapshot(home))
            self.assertEqual(run()[0], 'Tools updated from version 1 to 6')
            harness.updated(home, fingerprint, previous)
            value, written = journal(home), receipt(home)
            self.assertEqual(set(value), JOURNAL_FIELDS | {'source', 'receipt'})
            self.assertEqual((value['source'], value['tools_volume_uuid']), ('stick', 'CAFE-1234'))
            self.assertEqual((written['source'], written['finished_from'], written['tools_volume_uuid'], written['caller']),
                             ('stick', 'stick', 'CAFE-1234', dict(login_uid=1001, terminal=True)))
        with self.assertRaisesRegex(owner.Stop, '^Unknown bundle source$'), installation() as (harness, home, run, fingerprint, previous, host):
            run('network')

    def test_the_first_installation_refuses_on_the_folder_route_whatever_the_terminal(self):
        message = '^The first installation runs only from the tools USB at the recovery console; nothing changed$'
        for terminal in (False, True):
            with self.subTest(terminal=terminal), tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
                root = pathlib.Path(temporary)
                usb = root / 'usb'
                usb.mkdir()
                fingerprint = common.fixture_bundle(usb / 'ares-tools')
                home, host = root / 'home', FixtureHost(fixture(), usb)
                asked = AssertionError('The folder route asked for a serial')
                with patch.object(owner, 'HOME', home), patch.object(owner.sys.stdin, 'isatty', return_value=terminal), \
                        patch.object(sys, 'dont_write_bytecode', True), \
                        patch('builtins.input', side_effect=asked), common.private_metadata(home):
                    with self.assertRaisesRegex(owner.Stop, message):
                        owner.install(usb / 'ares-tools', host, 'folder')
                    self.assertFalse(home.exists())
                    self.assertEqual(host.trace, [])
                    # The same bundle from the stick block at a terminal: the first installation as before.
                    with patch('builtins.input', side_effect=['TARGET', 'KEEP']), patch.object(owner.sys.stdin, 'isatty', return_value=True):
                        self.assertIn('manifest SHA256 ' + fingerprint, owner.install(usb / 'ares-tools', host, 'stick'))
                    # Its rerun, and install through the installed entry, are that route too: the folder refuses them.
                    before = base.ToolsUpdateTest().snapshot(home)
                    for payload in (usb / 'ares-tools', home / 'tools'):
                        with self.assertRaisesRegex(owner.Stop, message):
                            owner.install(payload, host, 'folder')
                    self.assertEqual(before, base.ToolsUpdateTest().snapshot(home))


class LayoutTrialTest(unittest.TestCase):
    def test_the_tools_updates_readiness_check_names_abandon_for_a_trial_from_an_earlier_boot(self):
        """Review 3 of 22d, nit 3: system_ready with a trial record from another boot refuses with the
        wording that names layout abandon; one from this boot keeps the first wording. Nothing changes."""
        for source in owner.SOURCES:
            for began, message in (('an-earlier-boot', owner.LAYOUT_TRIAL_RESTARTED), ('this-boot', owner.LAYOUT_TRIAL)):
                with self.subTest(source=source, began=began), installation(source=source) as (harness, home, run, fingerprint, previous, host), \
                        patch.object(owner, 'boot_id', return_value='this-boot'):
                    base.ToolsUpdateTest.record(home, 'layout-pending', dict(phase='pin', administrator=dict(boot=began)))
                    before = harness.snapshot(home)
                    host.trace.clear()
                    with self.assertRaises(owner.Stop) as caught:
                        run()
                    self.assertEqual(str(caught.exception), message)
                    self.assertEqual(harness.snapshot(home), before)
                    self.assertFalse(any(row.get('mutation') for row in host.trace))
        self.assertTrue(owner.LAYOUT_TRIAL_RESTARTED.startswith('Layout trial is unfinished and began before the last restart: '))
        # Review 3, nit 2: in the trial's own boot the first wording names abandon too, for a closed console.
        self.assertEqual(owner.LAYOUT_TRIAL, 'Layout trial is unfinished; prove it or revert first; if the console that began '
                         'it is closed, from a fresh physical administrator login run sudo /var/lib/ares/at layout abandon')


class ResumeTest(unittest.TestCase):
    def test_a_folder_update_resumes_from_either_block_and_a_stick_update_only_from_its_stick(self):
        with installation(source='folder') as (harness, home, run, fingerprint, previous, host), events(home) as seen:
            run()
        total = len(seen)
        self.assertEqual([phase for kind, phase in seen if kind == 'save'][-1], 'complete')
        for began, resumed in (('folder', 'folder'), ('folder', 'stick'), ('stick', 'stick'), ('stick', 'folder')):
            for stop in range(1, total):
                with self.subTest(began=began, resumed=resumed, stop=stop), installation(source=began) as (
                        harness, home, run, fingerprint, previous, host):
                    self.assertTrue(cut(run, home, stop))
                    started = journal(home)
                    self.assertEqual((started['source'], started['tools_volume_uuid']),
                                     (began, 'CAFE-1234' if began == 'stick' else None))
                    # The journal is complete once its last rename landed: nothing is left to resume then.
                    done = started['phase'] == 'complete'
                    # The receipt names the run that wrote it, which a cut after its rename leaves to the first run.
                    wrote = began if list((home / 'records').glob('*-tools-update.json')) else resumed
                    if (began, resumed) == ('stick', 'folder') and not done:
                        owner.settle_tools()  # what the next entry does first
                        before = harness.snapshot(home)
                        for attempt in range(2):
                            with self.assertRaisesRegex(owner.Stop, '^' + STICK_ONLY + '$'):
                                run(resumed)
                            self.assertEqual(before, harness.snapshot(home))
                        resumed = wrote = 'stick' if wrote == 'folder' else wrote
                    self.assertEqual(run(resumed)[0], 'Tools already installed; nothing changed' if done
                                     else 'Tools updated from version 1 to 6')
                    harness.updated(home, fingerprint, previous)
                    written = receipt(home)
                    self.assertEqual((journal(home)['source'], written['source'], written['finished_from']), (began, began, wrote))
                    self.assertEqual(written['caller'], dict(login_uid=1001, terminal=wrote == 'stick'))
                    self.assertEqual(written['tools_volume_uuid'], 'CAFE-1234' if began == 'stick' else None)

    def test_another_stick_another_bundle_and_an_unknown_source_never_resume(self):
        for began in owner.SOURCES:
            changes = dict(manifest='f' * 64, source='network')
            if began == 'stick':
                changes['tools_volume_uuid'] = 'OTHER-STICK'
            for name, value in changes.items():
                with self.subTest(began=began, changed=name), installation(source=began) as (harness, home, run, fingerprint, previous, host):
                    with patch('shutil.copytree', side_effect=OSError('interrupt')), self.assertRaises(OSError):
                        run()
                    harness.journal_value(home, name, value)
                    before = harness.snapshot(home)
                    for route in owner.SOURCES:
                        with self.assertRaisesRegex(owner.Stop, '^Interrupted tools update does not exactly match this bundle/stick; get help$'
                                                    if (name, began, route) != ('tools_volume_uuid', 'stick', 'folder') else '^' + STICK_ONLY + '$'):
                            run(route)
                        self.assertEqual(before, harness.snapshot(home))

    def test_a_journal_of_older_tools_names_no_source_and_counts_as_begun_from_the_stick(self):
        with installation(source='stick') as (harness, home, run, fingerprint, previous, host):
            self.assertTrue(cut(run, home, 3))
            value = journal(home)
            del value['source']
            writer = object.__new__(owner.Tools)
            writer.store = home
            writer.save(owner.TOOLS_JOURNAL, value)
            owner.settle_tools()
            before = harness.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, '^' + STICK_ONLY + '$'):
                run('folder')
            self.assertEqual(before, harness.snapshot(home))
            run()
            harness.updated(home, fingerprint, previous)
            self.assertEqual(receipt(home)['source'], 'stick')


class OlderToolsTest(unittest.TestCase):
    """Until publication the installed tools stay current: after a cut their recovery code reads the current tools' journal."""

    def test_the_exact_older_bundles_and_their_recovery_check(self):
        for version, (commit, fingerprint) in OLD.items():
            with self.subTest(version=version):
                self.assertEqual(hashlib.sha256(blob(version, 'SHA256SUMS')).hexdigest(), fingerprint)
                self.assertEqual(json.loads(blob(version, 'history.json'))['tools_version'], version)
                self.assertEqual(blob(version, 'owner.py'), subprocess.check_output(
                    ['git', 'show', commit + ':os/owner-tools/owner.py'], cwd=ROOT))
                self.assertEqual(old_tools(version).settle_tools.__code__.co_filename, commit + ':owner.py')
                self.assertNotIn('source', blob(version, 'owner.py').decode().split('def settle_tools():')[1].split('\ndef ')[0])
        self.assertEqual(owner.lineage(base.PAYLOAD)['tools_version'], 6)

    def test_version_6_installs_over_versions_2_and_3_from_both_blocks_in_both_shapes(self):
        for version in OLD:
            for versioned in (True, False):
                for source in owner.SOURCES:
                    with self.subTest(version=version, versioned=versioned, source=source), installation(version, versioned, source) as (
                            harness, home, run, fingerprint, previous, host):
                        if versioned:
                            self.assertNotIn('source', journal(home))
                        lines = run()
                        self.assertEqual(lines[:2], ['Tools updated from version ' + str(version) + ' to 6', 'manifest SHA256 ' + fingerprint])
                        harness.updated(home, fingerprint, previous)
                        self.assertEqual(owner.checked_bundle(home / 'retired-tools' / previous), OLD[version][1])
                        written = receipt(home)
                        self.assertEqual((written['previous_version'], written['tools_version'], written['source'], written['caller']['terminal']),
                                         (version, 6, source, source == 'stick'))
                        self.assertFalse(any(row.get('mutation') for row in host.trace))
                        # The old bundle is now incoming, not installed data: its missing numbers
                        # refuse even before the downgrade check. The installed copy was accepted above.
                        before = harness.snapshot(home)
                        with self.assertRaisesRegex(owner.Stop, '^Invalid release record fields$'):
                            owner.install(home / 'retired-tools' / previous, host, 'folder')
                        self.assertEqual(before, harness.snapshot(home))

    def test_older_recovery_code_settles_every_cut_before_publication_and_version_6_resumes(self):
        """Brief 22d, decision 7 and review F8: schema and fields as before, one new key, nothing else new on disk."""
        for version in OLD:
            old = old_tools(version)
            for versioned in (True, False):
                for source in owner.SOURCES:
                    with installation(version, versioned, source) as (harness, home, run, fingerprint, previous, host), events(home) as seen:
                        run()
                    cuts = [index for index, (kind, phase) in enumerate(seen, 1) if phase in ('copy', 'publish')]
                    self.assertTrue({'copy', 'publish'} <= {seen[index - 1][1] for index in cuts})
                    self.assertTrue({'copy', 'replace', 'save'} <= {seen[index - 1][0] for index in cuts})
                    for stop in cuts:
                        with self.subTest(version=version, versioned=versioned, source=source, stop=stop), \
                                installation(version, versioned, source) as (harness, home, run, fingerprint, previous, host):
                            old_name = 'tools-' + previous if versioned else 'tools'
                            records = {p.name: p.read_bytes() for p in (home / 'records').iterdir()}
                            self.assertTrue(cut(run, home, stop))
                            raw = journal(home)
                            self.assertEqual(set(raw), JOURNAL_FIELDS | {'source'})
                            self.assertEqual((raw['schema'], raw['previous'], raw['previous_directory'], raw['manifest'],
                                              raw['previous_version'], raw['tools_version'], raw['source']),
                                             ('tools-update1', previous, old_name, fingerprint, version, 6, source))
                            self.assertEqual(raw['tools_volume_uuid'], 'CAFE-1234' if source == 'stick' else None)
                            self.assertIn(raw['phase'], ('copy', 'publish'))
                            # Nothing new under the installation but the journal's key: the names the old update
                            # code accepts, and the records exactly as they were.
                            self.assertTrue(all(p.name in old.UPDATE_NAMES or old.re.fullmatch(old.TOOLSET, p.name)
                                                or p.name.startswith('.' + old.TOOLS_JOURNAL + '.') and p.name.endswith('.new')
                                                for p in home.iterdir()), sorted(p.name for p in home.iterdir()))
                            self.assertEqual({p.name: p.read_bytes() for p in (home / 'records').iterdir()}, records)
                            self.assertFalse((home / 'retired-tools' / previous).exists())
                            # The old tools' own recovery: it accepts the journal and leaves the old tools current.
                            self.assertEqual(old.settle_tools(), raw)
                            self.assertEqual(old.entry_toolset(), old_name)
                            self.assertEqual(old.checked_bundle(home / old_name), previous)
                            self.assertFalse((home / '.tools-held').exists())
                            self.assertEqual(old.settle_tools(), raw)  # every later command of the old tools too
                            self.assertEqual(run()[0], 'Tools updated from version ' + str(version) + ' to 6')
                            harness.updated(home, fingerprint, previous)
                    print('22d: version', version, 'settle_tools read the version 6 journal at', len(cuts),
                          'cuts before publication; versioned=', versioned, 'source=', source)


class ExportTest(unittest.TestCase):
    """Decision 6: which stick export accepts and who may read the copy that stays on the laptop
    (media.export's own behaviour: test_owner_export)."""

    def test_export_accepts_the_installed_bundle_and_each_verified_one_this_laptop_installed_before(self):
        with installation(2, versioned=True, source='folder') as (harness, home, run, fingerprint, previous, host):
            run()
            tools = owner.Tools(home / ('tools-' + fingerprint), host, home / 'records')
            calls = []
            stub = types.SimpleNamespace(export=lambda *args: calls.append(args) or ['exported'])

            def asked():
                calls.clear()
                with patch.object(owner, 'media_module', return_value=stub) as loaded:
                    self.assertEqual(tools.export(), ['exported'])
                loaded.assert_called_once_with(home / ('tools-' + fingerprint))
                (called, store, accepted, check, require, reader), = calls
                self.assertEqual((called, store, check, require), (host, home / 'records', owner.checked_bundle, owner.require))
                return accepted, reader

            retired = home / 'retired-tools'
            # The installed bundle first, then version 2: what the stick in the drawer holds after this update.
            self.assertEqual(asked(), ([fingerprint, previous], 1001))
            # A name is a claim, the bytes are the proof: other entries add nothing.
            common.fixture_bundle(retired / ('a' * 64))
            (retired / 'notes').mkdir()
            (retired / ('b' * 64)).write_text('not a folder')
            self.assertEqual(asked(), ([fingerprint, previous], 1001))
            with (retired / previous / 'owner.py').open('a') as stream:
                stream.write('# changed\n')
            self.assertEqual(asked(), ([fingerprint], 1001))
            aside = home.parent / 'aside'
            retired.rename(aside)
            self.assertEqual(asked(), ([fingerprint], 1001))
            retired.symlink_to(aside)
            self.assertEqual(asked(), ([fingerprint], 1001))
            (home.parent / 'loginuid').write_text('4294967295\n')
            self.assertEqual(asked(), ([fingerprint], None))


if __name__ == '__main__':
    unittest.main()
