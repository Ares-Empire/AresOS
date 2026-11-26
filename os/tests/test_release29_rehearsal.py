"""Fixture checks for the historical preflight and R29 route, with no live guest."""
import contextlib
import configparser
import copy
import errno
import json
import os
import pathlib
import shlex
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))

import owner_media
import owner_capabilities
import owner_counter_kernel
import owner_devices
import owner_vm as vm
import registry_auth as auth
import release29_walk as walk
from release29_walk import probes
from test_owner_walk import Release28Local, Release28Session, laptop_rows


ENV = dict(GITHUB_ACTIONS='true', GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='Ares-Empire/AresOS',
           GITHUB_REF_NAME=auth.BASELINE_BRANCH, GITHUB_REF='refs/heads/' + auth.BASELINE_BRANCH,
           REHEARSAL_PACKAGE='331', REHEARSAL_MODE='release-29-baseline', GITHUB_SHA='ab' * 20, GITHUB_RUN_ID='331',
           GITHUB_RUN_ATTEMPT='1', GITHUB_ACTOR='fixture-runner', GH_TOKEN='fixture-job-token')

TERMINAL_FAILURES = {
    'display': ('no Wayland display', 0),
    'cwd': ('did not start in the daily home', 1),
    'vt': ('requires tty1', 0),
    'replacement-pid': ('did not survive', 1),
    'no-monitor': ('could not find a monitor in five attempts', 5),
}
CONTROL_FAILURES = {
    'rewrite-sites': ('sites hash or metadata changed', 'previous-28', 'previous-28-sites-hash'),
    'restored-placeholder': ('sites hash or metadata changed', 'final-29', 'final-29-control'),
    'missing-sites': ('sites hash failed', 'previous-28', 'previous-28-sites-hash'),
    'missing-check': ('Control checks missing or failed', 'release-29', 'release-29-control'),
    'gh-version': ('shipped gh version differs', 'release-29', 'release-29-control'),
    'gate-reached-page': ('first-use gate failed', 'release-29', 'release-29-chrome-first-use'),
    'masked-requirement': ('requires masked', 'release-28', 'r29-starting-28-control-login'),
    'masked-control': ('Control service delays login', 'release-28', 'r29-starting-28-control-login'),
    'wanted-control': ('Control service delays login', 'release-28', 'r29-starting-28-control-login'),
}


def save(path, value):
    path.write_text(json.dumps(value))


def registry_fixture():
    rows = [dict(auth.historical_row(version, json.loads(raw)), signature_sha256='ab' * 32)
            for version, raw in auth.historical_records().items()]
    return dict(status='passed', **auth.baseline_run(), visibility='private',
                auth_kind='job-token', owner_token_used=False, targets=rows)


def prepare_fixture(root, stack):
    registry = root / 'historical-registry.json'
    stack.enter_context(patch.object(auth, 'BASELINE_REGISTRY', registry))
    stack.enter_context(patch.object(walk, 'BASELINE_RECEIPT', root / 'evidence' / 'baseline.json'))
    download = walk.installer_download
    stack.enter_context(patch.object(walk, 'installer_download', side_effect=lambda live: download(live, root)))
    save(registry, registry_fixture())
    live = vm.td.LIVE
    save(root / 'iso-download.json', dict(status='passed', filename=live['filename'], url=live['url'],
         downloaded_sha256=live['sha256'], official_sha256=live['sha256'], bytes=live['bytes']))
    prefix = 'http://127.0.0.1:18080/cockpit/@localhost/anaconda-webui/index.js'
    hashes = walk.ui_hashes()
    save(root / 'completion-selector-source.json', dict(sources=[
        dict(url=prefix, sha256=hashes['bundle_sha256']), dict(url=prefix + '.map', sha256=hashes['source_map_sha256'])]))
    return walk.prepare(vm)


class RegistryTest(unittest.TestCase):
    def test_r29_native_runner_tools_require_the_exact_hosted_walk(self):
        for mode in auth.R29_WALK_MODES:
            with self.subTest(mode=mode), patch.dict(os.environ, ENV | {'REHEARSAL_MODE': mode}, clear=True), \
                    patch('builtins.print'), \
                    patch.object(owner_capabilities.shutil, 'which', return_value=None), \
                    patch.object(owner_devices.os, 'geteuid', return_value=0), \
                    patch.object(owner_devices, 'Observations'), patch.object(owner_devices, 'prove') as devices, \
                    patch.object(pathlib.Path, 'exists', return_value=False), patch.object(pathlib.Path, 'write_text'):
                owner_media.require_runner()
                with self.assertRaisesRegex(AssertionError, 'missing host capability tool'):
                    owner_capabilities.main()
                owner_devices.main()
                devices.assert_called_once()
                owner_counter_kernel.native()
        package14 = dict(REHEARSAL_PACKAGE='14', GITHUB_REF_NAME='pkg/14-owner-tools',
                         GITHUB_REF='refs/heads/pkg/14-owner-tools')
        for changed in ({'GITHUB_REF': 'refs/tags/' + auth.BASELINE_BRANCH}, {'REHEARSAL_MODE': 'publish-29'},
                        *(package14 | {'REHEARSAL_MODE': mode} for mode in auth.R29_WALK_MODES)):
            with self.subTest(changed=changed), patch.dict(os.environ, ENV | changed, clear=True), \
                    patch.object(owner_devices, 'Observations'), patch.object(owner_devices, 'prove') as devices, \
                    patch.object(owner_capabilities.shutil, 'which') as tool, patch.object(owner_counter_kernel, 'prove') as counter, \
                    patch.object(pathlib.Path, 'exists', return_value=False) as exists, patch.object(pathlib.Path, 'write_text'):
                for script in (owner_media.require_runner, owner_capabilities.main, owner_devices.main, owner_counter_kernel.native):
                    with self.subTest(script=script.__module__), self.assertRaisesRegex(AssertionError, 'R29 dispatch'):
                        script()
                tool.assert_not_called()
                devices.assert_not_called()
                counter.assert_not_called()
                exists.assert_not_called()

    def test_vm_refuses_a_receipt_from_another_run_or_walk_before_host_access(self):
        dispatch = dict(mode=ENV['REHEARSAL_MODE'], commit=ENV['GITHUB_SHA'],
                        run_id=ENV['GITHUB_RUN_ID'], attempt=ENV['GITHUB_RUN_ATTEMPT'])
        checks = dict(status='passed', sha=ENV['GITHUB_SHA'], run=13)
        for changed in ({'dispatch': dispatch | {'run_id': '442'}},
                        {'dispatch': dispatch | {'mode': 'release-29'}},
                        {'model': checks | {'run': 14}}):
            receipt = dict(allowance='331', native=checks, model=checks, dispatch=dispatch) | changed
            with self.subTest(changed=changed), patch.dict(os.environ, ENV, clear=True), \
                    patch.object(sys, 'argv', ['owner_vm.py', 'release-29']), \
                    patch.object(pathlib.Path, 'read_text', return_value=json.dumps(receipt)) as read, \
                    patch.object(vm, 'Media') as media, self.assertRaisesRegex(AssertionError, 'R29 .*receipt'):
                vm.main()
            read.assert_called_once()
            media.assert_not_called()

    def test_installed_guest_audits_a_login_stall_after_closing(self):
        guest = object.__new__(vm.Guest)
        guest.mode = 'installed'
        guest.webui_server = guest.webui_socket = None
        guest.audit = Mock()
        order = Mock()
        order.attach_mock(guest.audit.check, 'audit')
        with patch.dict(os.environ, REHEARSAL_PACKAGE='331'), patch.object(vm.td, 'save'), \
                patch.object(vm.td.Guest, 'close', order.close):
            try:
                raise TimeoutError('fixture live console stall')
            except TimeoutError:
                guest.close('release-29')
        self.assertEqual(order.mock_calls, [call.close('release-29'), call.audit('release-29', guest)])

    def test_owner_marker_guest_starts_after_preflight_removes_host_auth(self):
        firmware = ROOT / 'os/manifest/ci/11k/full-5/two-disk/protected-second/pre-firmware-vars.fd'
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as tmp, contextlib.ExitStack() as stack:
            root = pathlib.Path(tmp)
            (root / 'vars.fd').write_bytes(firmware.read_bytes())
            for name in ('target.raw', 'protected.raw'):
                (root / name).touch()
            stack.enter_context(patch.dict(os.environ, ENV, clear=True))
            for module in (vm.td, vm.sw):
                stack.enter_context(patch.multiple(module, WORK=root, EVIDENCE=root))
            stack.enter_context(patch.multiple(vm.Guest, mode='marker-baseline', order='protected-second',
                                               boot_purpose='baseline-firmware', network_up=False))
            stack.enter_context(patch.object(vm.td.Guest, 'boot_count', 0))
            legacy = stack.enter_context(patch.object(vm.td, 'auth_file', wraps=auth.auth_file))
            monitor = stack.enter_context(patch.object(vm.sw, 'QMP')).return_value
            stack.enter_context(patch.object(vm.Guest, 'connect'))
            stack.enter_context(patch.object(vm.Guest, 'device_inventory', return_value={}))

            def launch(argv, *, stdout, stderr):
                stdout.close()
                return Mock()

            qemu = stack.enter_context(patch.object(vm.sw.subprocess, 'Popen', side_effect=launch))
            guest = vm.Guest(root / 'target.raw', '', [])
            legacy.assert_not_called()
            qemu.assert_called_once()
            argv = qemu.call_args.args[0]
            self.assertEqual(argv[0], 'qemu-system-x86_64')
            self.assertNotIn('-fsdev', argv)
            self.assertFalse(guest.bootnext_authorization['written'])
            self.assertEqual(monitor.command.call_args_list, [call('qmp_capabilities'),
                call('set_link', {'name': 'owner-net', 'up': False}), call('cont')])

    def test_branch_allowlist_rejects_other_ref_types_and_modes(self):
        for mode in auth.R29_WALK_MODES:
            with patch.dict(os.environ, ENV | {'REHEARSAL_MODE': mode}, clear=True):
                auth.require_baseline_dispatch()
                owner_media.require_runner()
        for key, value in [('GITHUB_ACTIONS', 'false'), ('GITHUB_EVENT_NAME', 'push'),
                           ('GITHUB_REF_NAME', 'main'), ('GITHUB_REF', 'refs/tags/' + auth.BASELINE_BRANCH),
                           ('GITHUB_REPOSITORY', 'fork/AresOS'), ('REHEARSAL_PACKAGE', '42'),
                           ('GITHUB_REF', 'refs/heads/pkg/331-Release-29'),
                           ('REHEARSAL_MODE', 'release-28'), ('REHEARSAL_MODE', 'publish-29'),
                           ('GHCR_READ_TOKEN', 'fixture')]:
            with self.subTest(key=key), patch.dict(os.environ, ENV | {key: value}, clear=True), \
                    patch.object(auth, 'write_auth') as create, self.assertRaises(AssertionError):
                auth.baseline_preflight('/unused')
            create.assert_not_called()

    def test_preflight_reads_and_checks_the_exact_three_signatures_with_job_credentials(self):
        records = {version: json.loads(raw) for version, raw in auth.historical_records().items()}
        references = {record['reference']: record for record in records.values()}
        for fail in (None, 'token', 'read', 'signature', 'empty-signature'):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as tmp, contextlib.ExitStack() as stack:
                root = pathlib.Path(tmp)
                temporary = root / 'runner'
                temporary.mkdir()
                env = ENV | dict(RUNNER_TEMP=str(temporary), GITHUB_WORKSPACE=str(root / 'checkout'))
                if fail == 'token':
                    env['GH_TOKEN'] = ''
                stack.enter_context(patch.dict(os.environ, env, clear=True))
                stack.enter_context(patch.object(auth, 'BASELINE_REGISTRY', root / 'result.json'))
                stack.enter_context(patch.object(auth, 'CANDIDATE_REGISTRY', root / 'candidate.json'))
                candidate = stack.enter_context(patch.object(auth, 'r29_candidate', side_effect=AssertionError('baseline must never read R29')))
                auth.BASELINE_REGISTRY.write_text('stale proof')
                tool = root / 'cosign'
                tool.touch(mode=0o700)
                reads, signatures = [], []

                def run(argv, **kwargs):
                    if argv[0] == 'gh':
                        return subprocess.CompletedProcess(argv, 0, stdout='{"visibility":"private"}')
                    if argv[0] == 'skopeo':
                        self.assertEqual(argv[1:6], ['inspect', '--authfile', str(auth.directory() / 'auth.json'), '--format', '{{.Digest}}'])
                        reference = argv[-1].removeprefix('docker://')
                        self.assertIn(reference, references)
                        reads.append(reference)
                        digest = reference.split('@')[1] if not (fail == 'read' and len(reads) == 2) else 'wrong'
                        return subprocess.CompletedProcess(argv, 0, stdout=digest)
                    self.assertEqual(argv[:2], [str(tool), 'verify'])
                    record = references[argv[-1]]
                    self.assertEqual(argv[2:-1], ['--certificate-identity', record['signature']['identity'],
                                                 '--certificate-oidc-issuer', record['signature']['issuer']])
                    self.assertEqual(kwargs['env']['DOCKER_CONFIG'], str(auth.directory()))
                    self.assertEqual((auth.directory() / 'config.json').readlink(), pathlib.Path('auth.json'))
                    signatures.append(argv[-1])
                    return subprocess.CompletedProcess(argv, int(fail == 'signature' and len(signatures) == 2),
                        stdout=b'' if fail == 'empty-signature' else b'fixture signature', stderr=b'fixture-job-token')

                stack.enter_context(patch.object(auth.subprocess, 'run', side_effect=run))
                stack.enter_context(patch.object(auth, 'job_auth_file', return_value=auth.directory() / 'auth.json'))
                if fail:
                    with self.assertRaises(AssertionError):
                        auth.baseline_preflight(str(tool))
                    self.assertFalse(auth.BASELINE_REGISTRY.exists())
                    self.assertLess(len(signatures), 3)
                else:
                    auth.baseline_preflight(str(tool))
                    proof = walk.read_json(auth.BASELINE_REGISTRY)
                    auth.check_baseline_registry(proof, auth.historical_records(), auth.baseline_run())
                    self.assertEqual(reads, list(references))
                    self.assertEqual(signatures, reads)
                    self.assertNotIn(ENV['GH_TOKEN'], auth.BASELINE_REGISTRY.read_text())
                self.assertFalse(auth.directory().exists())
                candidate.assert_not_called()
                self.assertFalse(auth.CANDIDATE_REGISTRY.exists())

    def test_candidate_registry_proof_binds_the_exact_reference_and_current_run(self):
        release = dict(reference='ghcr.io/ares-empire/aresos@sha256:' + '29' * 32, source_commit='bc' * 20,
                       signature=dict(identity=walk.IDENTITY, issuer='https://token.actions.githubusercontent.com'))
        with patch.dict(os.environ, ENV, clear=True):
            run = auth.baseline_run()
        proof = dict(status='passed', **run, visibility='private', auth_kind='job-token', owner_token_used=False,
                     **auth.candidate_row(release), signature_sha256='ab' * 32)
        auth.check_candidate_registry(proof, release, run)
        for field in ('reference', 'identity', 'issuer', 'source_commit', 'attempt', 'run_id', 'commit', 'signature_sha256'):
            with self.subTest(field=field), self.assertRaisesRegex(AssertionError, 'same-run R29'):
                auth.check_candidate_registry(proof | {field: 'wrong'}, release, run)

    def test_all_records_are_bound_and_live_installer_uses_historical_r13(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as tmp, contextlib.ExitStack() as stack:
            root = pathlib.Path(tmp)
            stack.enter_context(patch.dict(os.environ, ENV, clear=True))
            stack.enter_context(patch.object(vm.td, 'EVIDENCE', root))
            prepared = prepare_fixture(root, stack)
            guest = Mock()
            with patch.object(vm.td, 'substitute_stock', side_effect=RuntimeError('stock rewind reached')):
                with self.assertRaisesRegex(RuntimeError, 'stock rewind reached'):
                    vm.td.live_inventory(guest, 'baseline-install')
                proof = walk.read_json(root / 'baseline-install-release-signature-proof.json')
                self.assertEqual(proof['reference'], json.loads(prepared.records['13'])['reference'])
                guest.command.assert_not_called()
                stale = copy.deepcopy(prepared.registry)
                stale['targets'].pop()
                save(auth.BASELINE_REGISTRY, stale)
                with self.assertRaisesRegex(AssertionError, 'incomplete historical registry'):
                    vm.td.live_inventory(guest, 'baseline-install')
            for version in prepared.records:
                original = pathlib.Path.read_bytes

                def changed(path):
                    raw = original(path)
                    return raw + b' ' if path == pathlib.Path(f'os/manifest/releases/{version}.json') else raw

                with self.subTest(version=version), patch.object(pathlib.Path, 'read_bytes', changed), \
                        self.assertRaisesRegex(AssertionError, f'immutable R{version}'):
                    auth.historical_records()
            for field, value in [('attempt', '2'), ('auth_kind', 'owner-token'), ('commit', 'cd' * 20)]:
                wrong = prepared.registry | {field: value}
                with self.subTest(field=field), self.assertRaises(AssertionError):
                    auth.check_baseline_registry(wrong, prepared.records, auth.baseline_run())


class InputTest(unittest.TestCase):
    def test_historical_tools_records_and_images_are_read_at_pinned_sources(self):
        records = auth.historical_records()
        tools, commands = walk.historical_tools(vm, records)
        self.assertEqual(list(tools), [1, 2, 4, 5])
        self.assertIn(vm.LAPTOP_TOOLS, commands[1]['install'])
        self.assertIn(vm.TOOLS_V2, commands[2]['install'])
        self.assertIn(walk.TOOLS_V5, commands[5]['tools-routine'])
        original = vm.git_blob

        def other_bytes(commit, path):
            if commit == vm.TOOLS_V2_COMMIT and path == walk.PAYLOAD + '/release.json':
                return records['13']
            return original(commit, path)

        with patch.object(vm, 'git_blob', other_bytes), self.assertRaisesRegex(AssertionError, 'tools v2 release record differs'):
            walk.historical_tools(vm, records)
        wrong = json.loads(records['28'])
        wrong['source_commit'] = vm.TOOLS_V2_COMMIT
        with self.assertRaisesRegex(AssertionError, 'R28 image source differs'):
            walk.historical_tools(vm, dict(records, **{'28': json.dumps(wrong).encode()}))

    def test_bad_installer_hashes_and_incomplete_transfers_do_not_qualify(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as tmp, contextlib.ExitStack() as stack:
            root = pathlib.Path(tmp)
            stack.enter_context(patch.dict(os.environ, ENV, clear=True))
            prepared = prepare_fixture(root, stack)
            self.assertEqual(walk.served_webui(root), walk.ui_hashes())
            self.assertEqual(prepared.iso['sha256'], vm.td.LIVE['sha256'])
            download = root / 'iso-download.json'
            value = walk.read_json(download)
            for key, bad in [('official_sha256', '00' * 32), ('downloaded_sha256', '00' * 32), ('bytes', 1)]:
                save(download, value | {key: bad})
                with self.subTest(key=key), self.assertRaises((AssertionError, IOError)):
                    walk.prepare(vm)
            source = root / 'completion-selector-source.json'
            value = walk.read_json(source)
            for index in range(2):
                broken = copy.deepcopy(value)
                broken['sources'][index]['sha256'] = '00' * 32
                save(source, broken)
                with self.assertRaisesRegex(AssertionError, 'served Web UI hashes differ'):
                    walk.served_webui(root)
            save(source, dict(sources=[*value['sources'], value['sources'][1]]))
            with self.assertRaisesRegex(AssertionError, 'ambiguous served Web UI'):
                walk.served_webui(root)

    def test_browser_checks_served_bytes_before_reporting_qualified_assets(self):
        fixtures = ROOT / 'os/manifest/ci/11b/inspect-8/installer/webui-source'
        names = ['components/installation/InstallationProgress.jsx', 'components/Error.jsx',
                 'components/AnacondaWizardFooter.jsx']
        mapping = json.dumps(dict(sources=[f'webpack:///src/{name}' for name in names],
                                  sourcesContent=[(fixtures / name).read_text() for name in names])).encode()
        bundle = b'fixture installer bundle'
        url = 'http://127.0.0.1:18080/cockpit/@localhost/anaconda-webui/index.js'
        webui = walk.installer_webui
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as tmp, \
                patch.multiple(webui, UI_BUNDLE_SHA256=walk.sha256(bundle), UI_SOURCE_MAP_SHA256=walk.sha256(mapping)):
            pages = object.__new__(webui.Pages)
            pages.evidence = pathlib.Path(tmp)
            pages.frame = Mock()
            pages.frame.locator.return_value.evaluate_all.return_value = [url]
            pages.page = Mock()
            response = {url: bundle, url + '.map': mapping}

            def get(key):
                return Mock(ok=True, **{'body.return_value': response[key]})

            pages.page.request.get.side_effect = get
            pages.completion_source()
            self.assertEqual(walk.served_webui(pages.evidence), walk.ui_hashes())
            for asset, error in [(url, 'Served installer bundle changed'), (url + '.map', 'Served UI source map changed')]:
                with self.subTest(asset=asset), patch.dict(response, {asset: response[asset] + b' '}), \
                        self.assertRaisesRegex(AssertionError, error):
                    pages.completion_source()

    def test_input_binding_requires_a_rerun_when_baseline_inputs_change(self):
        inputs = walk.baseline_inputs()
        original = pathlib.Path.read_bytes

        def changed(path):
            raw = original(path)
            return raw + b' ' if path == pathlib.Path(changed_path) else raw

        with patch.object(pathlib.Path, 'read_bytes', changed):
            for changed_path in ('os/manifest/installer-isos.json', 'os/ci/installer_webui.py',
                                 'os/manifest/releases/28.json', 'os/ci/release28_walk.py',
                                 'os/ci/install-tools.sh', 'os/ci/toolchain.json', 'os/ci/firmware_contract.py'):
                with self.subTest(path=changed_path), self.assertRaisesRegex(AssertionError, 'rerun the historical'):
                    walk.check_receipt(vm, dict(status='passed', inputs=inputs))
            for changed_path in ('os/manifest/release.json', 'os/owner-tools/payload/SHA256SUMS'):
                self.assertEqual(walk.baseline_inputs(), inputs)

    def test_baseline_receipt_binds_the_host_walk_when_it_lands(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as tmp:
            path = pathlib.Path(tmp).relative_to(ROOT) / 'host-walk.json'
            with patch.object(walk, 'HOST_WALK_RECEIPT', str(path)):
                without_host = walk.baseline_inputs()
                path.write_bytes(b'{"status":"passed"}\n')
                with_host = walk.baseline_inputs()
                self.assertIn(dict(sha256=walk.sha256(path.read_bytes()), path=str(path)), with_host)
                with self.assertRaisesRegex(AssertionError, 'rerun the historical'):
                    walk.check_receipt(vm, dict(status='passed', inputs=without_host))
                path.write_bytes(b'{"status":"passed","sources":[]}\n')
                with self.assertRaisesRegex(AssertionError, 'rerun the historical'):
                    walk.check_receipt(vm, dict(status='passed', inputs=with_host))


def candidate_fixture(root):
    records = auth.historical_records()
    row = json.loads(records['28'])
    row.update(reference=auth.BASELINE_IMAGE + '@sha256:' + '29' * 32,
               signature=dict(row['signature'], identity=walk.IDENTITY))
    raw = (json.dumps(row, indent=2) + '\n').encode()
    historical = walk.r28.standin_origin(root / 'stand-in-28', records['28'])
    candidate = walk.candidate_origin(root / 'stand-in-29', historical, raw, 6)
    repo = candidate['repository']
    git = lambda *args, **kw: walk.r28.git(*args, source=repo, **kw).decode().strip()
    tree = git('rev-parse', candidate['commits']['announced'] + '^{tree}')
    head = git('commit-tree', tree, '-m', 'Real candidate fixture', env=walk.tools_local.STANDIN_ENV)
    equality = walk.candidate_equality(head, candidate, repo)
    return SimpleNamespace(candidate=candidate, historical=historical, equality=equality), records, git


class CandidateEqualityTest(unittest.TestCase):
    def test_exact_candidate_and_only_unchanged_v5_can_defer(self):
        with tempfile.TemporaryDirectory() as tmp:
            qualified, records, git = candidate_fixture(pathlib.Path(tmp))
            candidate = qualified.candidate
            repo, head = candidate['repository'], qualified.equality['head']
            self.assertTrue(qualified.equality['equal'])
            self.assertNotEqual(head, candidate['commits']['announced'])
            self.assertEqual(git('bundle', 'list-heads', str(candidate['bundle'])), candidate['commits']['announced'] + ' refs/heads/main')
            self.assertTrue(walk.candidate_equality(walk.TOOLS_V5_COMMIT, candidate, allow_deferred=True)['deferred'])
            with self.assertRaisesRegex(AssertionError, 'candidate equality before the walk'):
                walk.candidate_equality(walk.TOOLS_V5_COMMIT, candidate)
            for path in (*walk.r28.BOUND[1:], walk.r28.GUIDE, walk.PAYLOAD + '/SHA256SUMS', 'os/owner-tools/commands.json'):
                with self.subTest(path=path):
                    blob = git('show', head + ':' + path).encode() + b'\nchange\n'
                    tree, _ = walk.r28.tree_with(repo, head, {path: blob})
                    changed = git('commit-tree', tree, '-m', 'Candidate drift', env=walk.tools_local.STANDIN_ENV)
                    with self.assertRaisesRegex(AssertionError, 'differs from the rehearsed bundle or guide'):
                        walk.candidate_equality(changed, candidate, repo, allow_deferred=True)
            raw = candidate['files']['os/manifest/release.json']
            with self.assertRaisesRegex(AssertionError, 'guide fingerprint'):
                walk.announced(raw, 6, guide=b'wrong\n\nwrong\n')
            with self.assertRaisesRegex(AssertionError, 'historical digest'):
                reused = dict(json.loads(records['28']), signature=json.loads(raw)['signature'])
                walk.announced((json.dumps(reused) + '\n').encode(), 6)


class Release29Session(Release28Session):
    """Run submitted probe Python against disposable paths and explicit guest stand-ins."""

    def __init__(self, bundle, fault):
        super().__init__(True, faults={
            'display': ('supervisor_without_display',),
            'late-monitor': ('late_monitor',),
            'masked-ordering': ('masked_login_unit',),
            'masked-requirement': ('masked_login_requirement',),
            'masked-control': ('masked_unit_after_control',),
        }.get(fault, ()))
        self.bundle, self.fault, self.release = bundle, fault, '28'
        self.wants_target = 'aresos-toold.service' if fault == 'wanted-control' else None
        self.control_fixture()
        self.Path('/run/user/1001').mkdir(exist_ok=True)
        labwc = self.Path('/proc/42/environ')
        labwc.write_text(labwc.read_text() + 'PATH=' + vm.SYSTEM_PATH + '\0')
        supervisor = self.Path('/proc/43/environ')
        supervisor.write_text(supervisor.read_text() + 'XDG_CURRENT_DESKTOP=AresOS\0')
        self.write('/usr/libexec/aresos-shell', 'fixture')
        for app in ('terminal', 'browser'):
            rel = f'usr/share/aresos/apps/{app}.json'
            self.write('/' + rel, (ROOT / 'os/config' / rel).read_text())
        self.tee_calls = 0
        self.now = 0
        self.owners[str(self.Path(probes.STAGED_SITES))] = (0, 0)
        self.passwordless = {'org.aresos.rehearsal.unreviewed'} if fault == 'polkit' else set()
        self.actions = sorted(self.passwordless | {'org.aresos.rehearsal.authentication'})

    def start(self, release, stage):
        self.release = release
        self.foot, self.vt = 1, 'tty3'
        self.write('/usr/share/aresos/labwc/rc.xml', f'<labwc_config><theme><name>{probes.THEMES[release]}</name></theme></labwc_config>')
        if release == '29':
            for rel in ('usr/share/aresos/labwc/rc.xml', 'usr/share/themes/AresOS/labwc/themerc',
                        'usr/share/applications/aresos-mimeapps.list', 'usr/share/applications/' + probes.PRISM_DESKTOP):
                self.write('/' + rel, (ROOT / 'os/config' / rel).read_text())
            live = self.Path(probes.SITES)
            if not live.exists():
                self.write(probes.SITES, probes.PLACEHOLDER.decode())
                self.owners[str(live)] = (0, 250)
                live.chmod(0o640)
            self.chrome_files()
        if stage == 'previous-28' and self.fault in ('rewrite-sites', 'missing-sites'):
            if self.fault == 'rewrite-sites':
                self.write(probes.SITES, '{"format":1,"hosts":["changed.invalid"]}\n')
            else:
                self.Path(probes.SITES).unlink()
        if stage == 'final-29' and self.fault == 'restored-placeholder':
            self.write(probes.SITES, probes.PLACEHOLDER.decode())

    def chrome_files(self):
        files, extension = self.bundle
        record_path = self.Path('/usr/share/aresos/manifest/control.json')
        record = json.loads(record_path.read_bytes())
        record['chrome_extension'] = extension
        folder = '/usr/share/aresos/chrome/'
        for name, data in files.items():
            path = self.Path(folder + name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for rel, file in (('policies/managed/aresos.json', 'policy.json'),
                          ('native-messaging-hosts/org.aresos.chrome.json', 'native-host.json')):
            for top in ('/etc/opt/chrome/', '/usr/etc/opt/chrome/'):
                link = self.Path(top + rel)
                link.parent.mkdir(parents=True, exist_ok=True)
                if not link.is_symlink():
                    link.symlink_to(self.Path(folder + file))
        action = '/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy'
        self.write(action, '<policyconfig/>\n')
        record['files'][action] = dict(mode='0644', sha256=walk.sha256(self.Path(action).read_bytes()))
        self.write('/usr/bin/gh', 'fixture gh')
        binary = walk.sha256(b'fixture gh')
        version = '2.0.0' if self.fault == 'gh-version' else probes.gh_version()
        record['gh'] = dict(version=version, binary_sha256=binary)
        self.write('/usr/share/aresos/manifest/gh.lock.json',
                   json.dumps(dict(nevra=f'gh-{version}-1.x86_64', binary_sha256=binary)))
        record_path.write_text(json.dumps(record))

    def probe_modules(self, modules, allowed):
        def readlink(path):
            if path == '/proc/50/cwd':
                return '/var/home/recovery' if self.fault == 'cwd' else '/var/home/ares'
            return self.readlink(path)

        def get_group(name):
            if name == 'wheel':
                return SimpleNamespace(gr_mem=[] if self.fault == 'wheel' else ['ares'])
            assert name == 'aresos-tools'
            return SimpleNamespace(gr_gid=250)

        def chown(path, uid, gid, *, follow_symlinks=True):
            path = self.Path(path)
            assert path.is_relative_to(self.root)
            self.owners[str(path)] = uid, gid

        def mkdtemp(*, prefix, dir):
            return tempfile.mkdtemp(prefix=prefix, dir=self.Path(dir))

        modules['os'].readlink = readlink
        modules['os'].fchmod = os.fchmod
        modules['os'].chown = chown
        modules['os'].chdir = lambda path: self.expect(path == '/')
        modules['grp'].getgrnam = get_group
        modules['time'].monotonic = lambda: self.now
        modules['time'].sleep = lambda seconds: setattr(self, 'now', self.now + seconds)
        modules['tempfile'] = SimpleNamespace(mkdtemp=mkdtemp, TemporaryDirectory=lambda **kw:
                                              tempfile.TemporaryDirectory(dir=self.root, **kw))
        allowed.update(('http.server', 'urllib.request', 'shutil', 'struct', 'threading'))

    @staticmethod
    def expect(condition):
        assert condition, 'Unexpected probe command or data'

    def run(self, argv, **kw):
        command = list(argv)
        words = command[4:] if command[:4] == ['runuser', '-u', 'ares', '--'] else command
        if words[:1] in (['env'], ['/usr/bin/env']):
            words = words[2:] if words[1] == '-i' else words[1:]
        while '=' in words[0]:
            words = words[1:]
        status, stdout, stderr = 0, '', ''
        if words[:3] == ['/usr/bin/python3', '-I', '-']:
            self.expect(kw['input'] == (ROOT / probes.CONTROL_CHECKER).read_text())
            self.expect(tuple(words[3:]) == (probes.SERVICE_CHECKS if self.release == '28'
                                           else probes.SERVICE_CHECKS + probes.CHROME_CHECKS))
            status, stdout = self.execute(kw['input'], argv=words[3:], allow_exit=True)
            if self.fault == 'missing-check' and self.release == '29':
                first, *lines = stdout.splitlines()
                checks = json.loads(first)
                del checks['chrome_polkit']
                stdout = '\n'.join([json.dumps(checks), *lines]) + '\n'
        elif words[0] == '/usr/bin/fc-match':
            stdout = '/wrong/font' if self.fault == 'fontconfig' else probes.FONTS_29[words[-1]]
        elif words == ['/usr/bin/xdg-mime', 'query', 'default', probes.PRISM_MIME]:
            self.expect(self.release == '29' and command[:4] == ['runuser', '-u', 'ares', '--']
                        and 'XDG_CURRENT_DESKTOP=AresOS' in command)
            apps = self.Path('/usr/share/applications')
            mime = configparser.ConfigParser(interpolation=None)
            mime.read(apps / 'aresos-mimeapps.list')
            handler = mime['Default Applications'][probes.PRISM_MIME].rstrip(';')
            desktop = configparser.ConfigParser(interpolation=None)
            desktop.read(apps / handler)
            self.expect('prism' in desktop['Desktop Entry']['MimeType'])
            stdout = ('old-handler.desktop' if self.fault == 'prism-default' else handler) + '\n'
        elif words == ['/usr/bin/sha256sum']:
            stdout = walk.sha256(kw['stdin'].read()) + '  -\n'
        elif words[0] == '/usr/bin/tee':
            self.expect(words[1:] == [str(self.Path(probes.SITES))] and kw['input'] == probes.SYNTHETIC_SITES)
            self.Path(words[1]).write_bytes(kw['input'])
            self.tee_calls += 1
        elif words[:2] == ['/usr/bin/aresos', 'chrome']:
            self.expect(command[:4] == ['runuser', '-u', 'ares', '--'] and kw['cwd'] == '/var/home/ares')
            if self.Path(probes.SITES).read_bytes() == probes.PLACEHOLDER:
                self.expect(words[2] in ('tabs', 'read', 'open', 'take'))
                code = 'chrome_settings_unavailable'
                if self.fault == 'gate-reached-page' and words[2] == 'open':
                    import urllib.request
                    direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                    with direct.open(json.loads(words[-1])['url'], timeout=5):
                        pass
                if words[2] == 'tabs' and getattr(self, 'waiting_for_chrome', True):
                    code = 'chrome_unavailable'
                    self.waiting_for_chrome = False
                status, stdout = 1, json.dumps(dict(ok=False, error=dict(code=code)))
            else:
                self.expect(words[2] == 'tabs')
                stdout = '{"ok":true,"data":{"seen":"fixture","total":0,"untrusted_content":{"list":""}}}'
        elif words[:3] == ['/usr/bin/systemctl', '--user', 'stop']:
            self.expect(words[3:] == ['app-aresos-browser-r29-probe.scope'])
        elif pathlib.Path(words[0]) == self.Path('/usr/bin/openssl'):
            self.expect(words[1:6] == ['dgst', '-sha256', '-keyform', 'DER', '-verify'])
            self.expect(all(pathlib.Path(words[i]).is_relative_to(self.root) for i in (6, 8)))
            return subprocess.run(['/usr/bin/openssl', *words[1:]], **kw)
        elif pathlib.Path(words[0]) == self.Path('/usr/bin/gh'):
            self.expect(words[1:] == ['--version'])
            version = '2.0.0' if self.fault == 'gh-version' else probes.gh_version()
            stdout = f'gh version {version}\n'
        elif words[:2] == ['sudo', '-l']:
            stdout = 'Defaults timestamp_timeout=0\n    (ALL) ALL\n'
        elif words[-3:] == ['sudo', '-n', 'true']:
            status, stderr = 1, 'sudo: a password is required'
        elif words[:2] == ['getent', 'shadow']:
            stdout = 'fixture:$fixture:1::::::\n'
        elif words[0] == 'timeout':
            stdout = 'ARESOS_CHROME_STARTED'
        elif words == ['/usr/bin/google-chrome', '--version']:
            stdout = 'Chrome fixture'
        elif words == ['/usr/libexec/aresos-shell', '--list']:
            stdout = json.dumps(dict(apps=[dict(id=id, available=True) for id in ('browser', 'notepad', 'terminal')]))
        elif words[0] == 'setsid' and self.fault == 'no-monitor':
            self.expect(words[1:] == ['-f', *vm.HUB_TERMINAL])
            self.launches += 1
            kw['stdout'].write(b'err: no monitors available\n')
        else:
            done = super().run(argv, **kw)
            if self.wants_target and words[:2] == ['systemctl', 'show'] \
                    and words[-1] == 'greetd.service' and 'Wants' in words[2:-1]:
                done.stdout += 'Wants=' + self.wants_target + '\n'
            if words[0] == 'setsid':
                self.write('/proc/50/cwd', '')
            if words[0] == 'pgrep' and words[-1] == 'foot' and done.stdout and self.launches and self.fault == 'replacement-pid':
                self.foot_reads = getattr(self, 'foot_reads', 0) + 1
                if self.foot_reads >= 2:
                    done.stdout = '51\n'
            return done
        done = subprocess.CompletedProcess(argv, status, stdout, stderr)
        if kw.get('check'):
            done.check_returncode()
        return done

    def popen(self, argv, **kw):
        if '/usr/bin/systemd-run' in argv:
            self.expect(argv[:4] == ['runuser', '-u', 'ares', '--'] and kw['cwd'] == '/var/home/ares')
            self.expect('/usr/bin/google-chrome' in argv and '--slice=app.slice' in argv)
            kw['stdout'].write(b'fixture Chrome started\n')
            def wait(**_kw):
                browser.returncode = 0

            browser = SimpleNamespace(returncode=None, poll=lambda: browser.returncode, wait=wait)
            return browser
        return super().popen(argv, **kw)


class RouteModel:
    def __init__(self, prepared, qualified, session, fault=None):
        self.session, self.fault, self.events, self.saved = session, fault, [], {}
        self.q = qualified
        self.r27, self.r28 = (json.loads(prepared.records[v])['reference'] for v in ('27', '28'))
        self.r29 = qualified.candidate['reference']
        base = walk.stock_image.base()
        def row(reference, checksum, **flags):
            return dict(checksum=checksum * 32, serial=0, osname='default', booted=False, pinned=False, staged=False,
                        **{'container-image-reference': 'ostree-unverified-registry:' + reference,
                           'container-image-reference-digest': reference.split('@')[1]}) | flags

        stock = row(base['reference'], 'ba', pinned=True)
        old = row(json.loads(prepared.records['13'])['reference'], '13', booted=True)
        self.rows = {27: row(self.r27, '27'), 28: row(self.r28, '28'), 29: row(self.r29, '29'), 'stock': stock}
        *_, self.machine = laptop_rows(dict(rpm=dict(transaction=None, deployments=[old, stock]), bootc={'status': {}}), self.r27)
        self.order, self.running, self.staged, self.pending = [28, 27, 'stock'], 28, False, 'Update'
        self.route = dict(old=old['container-image-reference'].split(':', 1)[1], new=self.r27,
                          new_digest=self.r27.split('@')[1], stock=stock, stock_digest=base['digest'])
        self.audit = SimpleNamespace(windows_default=True, check=self.audit_boot)
        self.td = SimpleNamespace(start_installed=self.boot, marker=self.marker, save=self.save, EVIDENCE=session.root)
        self.vm = SimpleNamespace(td=self.td, kb=SimpleNamespace(deployment_snapshot=self.snapshot), sw=vm.sw,
                                  deployment_shape=vm.deployment_shape, keyboard=Mock(), Console=self.console, finish=vm.finish,
                                  result_lines=vm.result_lines, ACTIVE_DESKTOP=vm.ACTIVE_DESKTOP, HUB_TERMINAL=vm.HUB_TERMINAL,
                                  diagnostic_reader=Mock(), git_blob=vm.git_blob, release_rules=vm.release_rules,
                                  terminal_path=vm.terminal_path, polkit_sweep=vm.polkit_sweep)
        self.local = Release28Local([], None, 'fixture-password', session.root)
        candidate = qualified.candidate
        for fingerprint, version in candidate['variants'].values():
            self.local.known(fingerprint, version)
        self.local.machine = dict(tools=walk.TOOLS_V5, entry='tools-' + walk.TOOLS_V5 + '/at', journal=None,
                                  records=[], folder=None, toolsets=[])
        self.local.lines = self.folder_lines
        self.guests = []
        self.place_tools(walk.TOOLS_V5, walk.TOOLS_V5_COMMIT, ROOT)

    def place_tools(self, fingerprint, commit, repo):
        directory = '/var/lib/ares/tools-' + fingerprint
        entry = self.session.Path('/var/lib/ares/at')
        entry.unlink(missing_ok=True)
        item = walk.r28.git('ls-tree', '-r', '--name-only', commit, walk.PAYLOAD, source=repo)
        for path in item.decode().splitlines():
            target = self.session.Path(directory) / path.removeprefix(walk.PAYLOAD + '/')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(walk.r28.git('show', commit + ':' + path, source=repo))
        entry.symlink_to('tools-' + fingerprint + '/at')

    def folder_lines(self, stage):
        commit = self.local.callers[stage]['commit']
        raw = walk.r28.git('show', commit + ':os/owner-tools/commands.json', source=self.q.candidate['repository'])
        commands = json.loads(raw)
        return dict(folder=commands['tools-folder'], routine=commands['tools-routine'])

    def caller(self, driver, stage, steps, commit, *, entries):
        self.events.append((stage, 'caller'))
        self.local.callers[stage] = dict(steps=steps, commit=commit, entries=entries)
        self.local.windows[stage] = dict(typed=len(self.local.typed), helper='fixture')
        return stage

    def window(self, driver, stage, out, fingerprint, action, answer):
        self.assert_route(out == stage and answer == 'password' and driver.bootstrap.label(fingerprint, action).startswith(
            'AresOS owner tools ' + fingerprint[:8]))
        self.local.typed.append((self.local.ares_password + '\n', 'de'))

    def result(self, driver, stage, out):
        before = self.local.machine['tools']
        done = self.local.run(stage)
        fingerprint = self.local.machine['tools']
        if done['routine']['status'] == 0 and fingerprint != before:
            done['routine']['stdout'] += 'manifest SHA256 ' + fingerprint + '\n'
            self.place_tools(fingerprint, driver.standin['commits']['announced'], driver.standin['repository'])
        if self.fault == 'cached-ticket' and stage == 'r29-tools':
            done['no_ticket']['status'] = 0
        return done

    def capture(self, driver, name, source):
        if name == 'r29-tools-receipt':
            return dict(self.local.installs[-1], status='passed', source='folder', finished_from='folder',
                        caller=dict(login_uid=1001, terminal=False))
        if name.endswith('-keyrings'):
            return []
        value = copy.deepcopy(self.local.machine)
        if name == 'r29-tools-mismatch-rechecked-state' and self.fault == 'tools-drift':
            value['journal']['phase'] = 'publish'
        return value

    @staticmethod
    def assert_route(condition):
        assert condition, 'Model route was out of order'

    def historical_stage(self, *_args, **_kwargs):
        ids = {row['container-image-reference-digest']: vm.ke.key(row) for row in self.rows.values()}
        return self.route, ids, None, None

    def snapshot(self, guest, stage):
        rows = [self.rows[key] | dict(booted=key == self.running, staged=self.staged and i == 0)
                for i, key in enumerate(self.order)]
        value = self.machine(*rows)
        if self.fault == 'wrong-staged-slot' and stage == 'r29-update-staged':
            value['bootc']['status']['staged']['ostree']['deploySerial'] = 1
        if self.fault == 'unpinned-stock' and stage == 'previous-28':
            value['rpm']['deployments'][-1]['pinned'] = False
        if self.fault == 'update-stop-unpinned' and stage == 'r29-update-refused':
            value['rpm']['deployments'][-1]['pinned'] = False
        return value

    def boot(self, password, hashed, stage):
        self.events.append((stage, 'F12 Bazzite'))
        if stage != 'release-28':
            self.assert_route(self.guests[-1].process.poll() == 0)
        self.running = self.order[0]
        if stage == 'release-29' and self.fault in ('recovery', 'open-on-recovery', 'not-applied', 'retry-still-r28'):
            self.running = 28
        if stage == 'release-29-retry' and self.fault == 'retry-still-r28':
            self.running = 28
        self.session.start(str(self.running), stage)
        guest = Mock(stage=stage, stopped_events_verified=False, failed_command=False)
        guest.process.poll.return_value = None
        guest.capture_json.side_effect = lambda name, script: self.probe(guest, name, script)
        guest.command.side_effect = lambda name, script: self.command(name, script)
        guest.keys.side_effect = lambda keys: self.keys(keys)
        guest.poweroff.side_effect = lambda name: guest.process.poll.configure_mock(return_value=0)
        self.guests.append(guest)
        return guest

    def keys(self, keys):
        if keys == ['ctrl', 'alt', 'f1'] and self.fault != 'vt':
            self.session.vt = 'tty1'
        if keys == ['ctrl', 'alt', 'f3']:
            self.session.vt = 'tty3'

    def command(self, name, script):
        if name.endswith('-path-prepare'):
            import base64
            words = shlex.split(script)
            self.session.write('/run/aresos-path.py', base64.b64decode(words[words.index('printf')+2]).decode())
        if name.endswith('-path-session') or name.endswith('-path-foot'):
            self.assert_route(self.session.vt == 'tty1' and self.session.foot == 1)

    def type_text(self, guest, text, layout):
        self.assert_route(text == 'python3 /run/aresos-path.py\n' and layout == 'de')
        self.session.execute(self.session.Path('/run/aresos-path.py').read_text(), uid=1001)

    def probe(self, guest, name, framed):
        self.events.append((name, 'probe'))
        self.session.write('/sys/class/tty/tty0/active', self.session.vt + '\n')
        if name.endswith('-home') and guest.stage == 'final-29':
            if self.fault == 'corrupt-world':
                self.session.Path(walk.r28.INSTANCE + '/minecraft/saves/' + walk.r28.WORLD + '/level.dat').write_bytes(b'corrupt')
            if self.fault == 'missing-image-targets':
                self.session.share.rename(self.session.absent_share)
        if '-path-' in name:
            script = framed.split("python3 - <<'PY'\n", 1)[1].split('\nPY', 1)[0]
        else:
            words = shlex.split(framed)
            script = words[words.index('python3') + 2]
        state = dict(state='SETUP', reason='setup', ready=False, jvm_pid=None)
        if name.endswith('-save-gate') and self.fault in ('open-on-update', 'open-on-recovery', 'open-on-forward',
                                                           'missing-close-message', 'normal-close'):
            wanted = {'open-on-update': 'r29-update', 'open-on-recovery': 'release-29-recovery',
                      'open-on-forward': 'r29-forward', 'missing-close-message': 'r29-update', 'normal-close': 'r29-update'}[self.fault]
            if name.startswith(wanted + '-reboot'):
                if self.fault in ('missing-close-message', 'normal-close'):
                    state.update(state='RECOVERY', reason='quit')
                else:
                    state.update(state='IN_WORLD', ready=True)

        def run(argv, **kw):
            if name.endswith('-save-gate') and argv[:-1] == [*walk.r28.AS_ARES, '/usr/libexec/aresos-desktop']:
                message = 'Minecraft was closed. Nothing is wrong.\n' if self.fault == 'normal-close' else 'Other message\n'
                output = json.dumps(state) if argv[-1] == 'status' else message
                return subprocess.CompletedProcess(argv, 0, output, '')
            return process(argv, **kw)

        process = self.session.run
        with patch.object(self.session, 'run', side_effect=run):
            return json.loads(self.session.execute(script))

    def console(self, guest, *, commands):
        console = Mock(commands=commands)
        console.run.side_effect = lambda word, stage, **kw: self.run(guest, console, word, stage, **kw)
        console.select.side_effect = lambda: self.keys(['ctrl', 'alt', 'f3'])
        return console

    def run(self, guest, console, word, stage, *, expect_stop=False, allow_stop=False):
        self.events.append((stage, word))
        console.select()
        self.assert_route(console.commands[word].endswith('/at ' + word))
        result = []
        if word == 'check':
            if expect_stop:
                self.assert_route(self.session.foot == 0)
                return dict(status='stopped', error=walk.r28.FOOT_STOP, trace=[])
            self.assert_route(self.session.foot > 0)
            if self.running == 28 and self.pending == 'Update' and guest.stage != 'release-28':
                outcome = ' is in place and has not started yet' if self.order[0] == 29 else \
                    ' was not applied: the deployments are as before it, and nothing is waiting'
                result = ['Update to ' + self.r29 + outcome, 'this start was not the default']
            elif self.pending:
                reference = self.r28 if self.running == 28 else self.r29
                if self.fault != 'wrong-confirmation' or self.running != 29:
                    result = [self.pending + ' to ' + reference + ' confirmed after the restart']
                self.pending = None
        if word == 'update':
            if self.fault in ('update-stop', 'update-stop-unpinned'):
                self.assert_route(allow_stop)
                return dict(status='stopped', error='model update failed safely')
            self.order.insert(0, 29)
            self.staged, self.pending = True, 'Update'
            result = ['Signed exact release staged ' + self.r29, 'Running release stays as rollback ' + self.r28,
                      'Older AresOS ' + self.r27 + ' is removed when the update finishes at shutdown', 'pin yes; transaction idle']
        if word == 'title':
            order = [29, 28, 'stock'] if self.staged else self.order
            label = 'Boot menu after the update finishes at shutdown (expected):' if self.staged else 'Boot menu at the next start:'
            if self.fault == 'stale-title' and self.staged:
                order = [28, 27, 'stock']
            result = ['pin yes; transaction idle', 'Previous title INVALID; use this record until the next reorder',
                      label + ' ' + '; '.join(self.rows[k]['container-image-reference-digest'].split(':')[1][:12] for k in order)]
        if word == 'export' and self.fault != 'wrong-export':
            result = ['Tools stick absent: records copied to /run/ares-records with SHA256 readback']
        if word in ('previous', 'forward'):
            self.order = [28, 29, 'stock'] if word == 'previous' else [29, 28, 'stock']
            self.pending = 'Return' if word == 'previous' else 'Forward'
            result = ['Previous AresOS queued for the next start ' + self.r28 if word == 'previous' else
                      'Newest installed AresOS starts next ' + self.r29]
        if word == 'reboot':
            if self.running == 28:
                self.assert_route(self.events[-2] == (stage + '-save-gate', 'probe'))
            if self.staged:
                self.staged = False
                self.order = [28, 27, 'stock'] if self.fault == 'not-applied' else [29, 28, 'stock']
            guest.stopped_events_verified = True
            guest.process.poll.return_value = 0
        return dict(status='passed', result=result)

    def save(self, name, value):
        self.saved[name] = value

    def audit_boot(self, stage, guest):
        guest.close.assert_called_once_with(stage)
        self.events.append((guest.stage, 'audit'))

    def marker(self, audit, stage, **_kw):
        self.assert_route(audit.windows_default is True)
        self.events.append((stage, 'Windows marker'))


class CandidateRouteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.qualified, cls.records, _ = candidate_fixture(pathlib.Path(cls.folder.name))
        import importlib.util
        path = ROOT / 'control/chrome/packaging/pack.py'
        spec = importlib.util.spec_from_file_location('release29_pack_fixture', path)
        pack = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pack)
        cls.bundle = pack.pack(ROOT / 'control/chrome/extension')

    @contextlib.contextmanager
    def model(self, fault=None):
        with contextlib.ExitStack() as stack:
            session = Release29Session(self.bundle, fault)
            stack.callback(session.close)
            prepared = SimpleNamespace(records=self.records, commands={5: json.loads(vm.git_blob(walk.TOOLS_V5_COMMIT, 'os/owner-tools/commands.json'))},
                                       inputs=walk.baseline_inputs())
            model = RouteModel(prepared, self.qualified, session, fault)
            stack.enter_context(patch.object(vm.time, 'sleep'))
            stack.enter_context(patch.object(vm.td, 'save', side_effect=model.save))
            stack.enter_context(patch.object(vm, 'type_text', side_effect=model.type_text))
            stack.enter_context(patch.object(walk.r28, 'stage_update', side_effect=model.historical_stage))
            stack.enter_context(patch.object(walk, 'served_webui', return_value=walk.ui_hashes()))
            stack.enter_context(patch.object(vm.owner_xhci, 'checkpoint'))
            for name in ('caller', 'window', 'result', 'capture'):
                stack.enter_context(patch.object(walk.CandidateWalk, name, autospec=True, side_effect=getattr(model, name)))
            model.run_route = lambda: walk.rehearsal(model.vm, model.audit, None, 'recovery', 'hash', 'daily', None,
                                                     prepared, qualifying=self.qualified)
            yield model

    def test_full_route_preserves_home_and_audits_every_start(self):
        with self.model('normal-close') as model:
            model.run_route()
            result = model.saved['release-29-deployment-walk']
            self.assertEqual(result['status'], 'passed')
            self.assertEqual(result['retired'], model.route['new_digest'])
            self.assertEqual(result['first_booted'], result['staged'])
            self.assertEqual(result['first_booted'], result['booted'])
            self.assertEqual(result['confirmations'], ['Update to ' + model.r29 + ' confirmed after the restart',
                'Return to ' + model.r28 + ' confirmed after the restart', 'Forward to ' + model.r29 + ' confirmed after the restart'])
            self.assertEqual([stage for stage, event in model.events if event == 'audit'],
                             ['release-28', 'release-29', 'previous-28', 'final-29'])
            self.assertEqual(model.session.launches, 4)
            homes = [model.saved[stage + '-home'] for stage in ('r29-starting-28', 'release-29', 'previous-28', 'final-29')]
            self.assertTrue(all(home['accessible']['saves_writable'] is True for home in homes))
            saves = model.session.Path(walk.r28.INSTANCE_LINKS['minecraft/saves'])
            self.assertFalse((saves / walk.r28.WORLD / '.aresos-rehearsal-write-probe').exists())
            self.assertEqual(len(model.local.installs), 1)
            self.assertEqual(set(model.local.ran), {'r29-tools', 'r29-tools-identical', 'r29-tools-mismatch', 'r29-tools-v5'})
            ordered = [('r29-update', 'update'), ('r29-update-title', 'title'), ('r29-update-export', 'export'),
                       ('r29-update-reboot-save-gate', 'probe'), ('r29-update-reboot', 'reboot'), ('release-29', 'F12 Bazzite'),
                       ('release-29-no-foot-check', 'check'), ('release-29-terminal', 'probe'), ('release-29-check', 'check')]
            self.assertEqual([event for event in model.events if event in ordered], ordered)

    def test_submitted_probes_follow_the_chrome_gate_and_game_order(self):
        with self.model('masked-ordering') as model:
            model.session.wants_target = 'wanted.service'
            model.run_route()
            saved = model.saved
            staged = saved['r29-starting-28-sites-stage']
            self.assertEqual(staged['sha256'], walk.sha256(probes.SYNTHETIC_SITES))
            self.assertEqual(saved['previous-28-sites-hash']['sha256'], staged['sha256'])
            self.assertEqual(saved['release-29-sites-placeholder']['sha256'], walk.sha256(probes.PLACEHOLDER))
            refusals = dict.fromkeys(('tabs', 'read', 'open', 'take'), 'chrome_settings_unavailable')
            self.assertEqual(saved['release-29-chrome-first-use']['refusals'], refusals)
            self.assertEqual(set(saved['release-29-chrome-first-use']['calls']), set(refusals))
            self.assertEqual(saved['release-29-deployment-walk']['chrome_first_use'],
                             dict(refusals=refusals, page_server_hits=0))
            self.assertTrue(saved['release-29-chrome-first-use']['opened'])
            self.assertEqual(saved['release-29-chrome-first-use']['page_server_hits'], 0)
            self.assertEqual(model.session.tee_calls, 1)
            self.assertFalse(model.session.Path(probes.STAGED_SITES).exists())
            self.assertEqual(model.session.Path(probes.SITES).read_bytes(), probes.SYNTHETIC_SITES)
            for stage, release in (('r29-starting-28', '28'), ('release-29', '29'),
                                   ('previous-28', '28'), ('final-29', '29')):
                with self.subTest(stage=stage):
                    lines = saved[stage + '-control']['stdout'].splitlines()
                    checks = json.loads(lines[0])
                    self.assertEqual(set(checks), set(probes.receipt_settings()['control_checks'][release]))
                    self.assertEqual(lines[1:-1], ['CONTROL_CHROME_SITES_SHA256 ' + staged['sha256']] if release == '29' else [])
                    graph = saved[stage + '-control-login']['graph']
                    self.assertIn('masked.service', graph)
                    self.assertIn('wanted.service', graph)
                    self.assertEqual(saved[stage + '-session']['theme'], probes.THEMES[release])
                    if release == '29':
                        self.assertEqual(saved[stage + '-prism-handler']['handler'], probes.PRISM_DESKTOP)
                        self.assertEqual(checks['gh']['value']['version'], probes.gh_version())
                    else:
                        self.assertNotIn(stage + '-prism-handler', saved)
                    self.assertEqual(saved[stage + '-terminal-path']['path'], vm.DAILY_PATH)
                    self.assertEqual(saved[stage + '-polkit-sweep']['session_active'], 'yes')
                    self.assertTrue(saved[stage + '-package21-rules']['sudo_n_refused'])
            game = saved['final-29-game-scope']
            self.assertEqual(game['memory_high'], '2684354560')
            self.assertTrue(game['in_scope'])
            order = list(saved)
            self.assertLess(order.index('release-29-sites-placeholder'), order.index('release-29-chrome-first-use'))
            self.assertLess(order.index('release-29-chrome-first-use'), order.index('release-29-control'))
            self.assertLess(order.index('final-29-control'), order.index('final-29-control-login'))
            self.assertLess(order.index('final-29-control-login'), order.index('final-29-game-scope'))
            self.assertNotIn('release-29-game-scope', saved)

    def test_historical_r28_control_guard_does_not_follow_wants(self):
        with self.model('wanted-control') as model:
            guest = SimpleNamespace(capture_json=model.session.capture)
            result = walk.r28.control(guest, 'release-28', model.vm)
            graph = result['login']['graph']
            self.assertNotIn('Wants', graph['greetd.service']['properties'])
            self.assertNotIn('aresos-toold.service', graph)

    def test_terminal_uses_same_pid_and_retries_only_for_a_missing_monitor(self):
        with self.model('late-monitor') as model:
            model.run_route()
            terminal = model.saved['release-28-terminal']
            first, second = terminal['attempts']
            self.assertIn('no monitors available', first['log'])
            self.assertEqual(first['survived'], [])
            self.assertEqual(second['started'], second['survived'])
            self.assertEqual(terminal['pid'], int(second['survived'][0]))
        for fault, (message, launches) in TERMINAL_FAILURES.items():
            with self.subTest(fault=fault), self.model(fault) as model:
                with self.assertRaisesRegex(AssertionError, message):
                    model.run_route()
                self.assertEqual(model.session.launches, launches)
                self.assertEqual(len(model.saved['release-28-terminal']['attempts']), launches)
                self.assertEqual(model.events[-1], ('release-28', 'audit'))

    def test_control_stops_on_bad_state_and_saves_its_actual_results(self):
        for fault, (error, stage, diagnostic) in CONTROL_FAILURES.items():
            with self.subTest(fault=fault), self.model(fault) as model:
                with self.assertRaisesRegex(AssertionError, error):
                    model.run_route()
                self.assertIn(diagnostic, model.saved)
                self.assertEqual(model.events[-1], (stage, 'audit'))
                if fault == 'missing-check':
                    self.assertNotIn(stage + '-control-login', model.saved)
                if fault == 'gate-reached-page':
                    self.assertEqual(model.saved[diagnostic]['page_server_hits'], 1)
                    self.assertEqual(model.session.tee_calls, 0)

    def test_theme_font_privilege_and_game_failures_are_retained(self):
        cases = [('theme', 'labwc theme differs', 'r29-starting-28-session'),
                 ('fontconfig', 'fontconfig differs', 'r29-starting-28-session'),
                 ('prism-default', 'Prism callback handler differs', 'release-29-prism-handler'),
                 ('wheel', 'ares_in_wheel', 'r29-starting-28-package21-rules'),
                 ('polkit', 'beyond the reviewed list', 'r29-starting-28-polkit-sweep')]
        for fault, error, diagnostic in cases:
            with self.subTest(fault=fault), self.model(fault) as model, self.assertRaisesRegex(AssertionError, error):
                try:
                    if fault == 'theme':
                        start = model.session.start

                        def bad_theme(release, stage):
                            start(release, stage)
                            model.session.write('/usr/share/aresos/labwc/rc.xml',
                                                '<labwc_config><theme><name>AresOS</name></theme></labwc_config>')

                        model.session.start = bad_theme
                    model.run_route()
                finally:
                    self.assertIn(diagnostic, model.saved)
        for bad_value in ('max', '2684354559'):
            with self.subTest(memory_high=bad_value), self.model() as model:
                group = '/user.slice/user-1001.slice/user@1001.service/aresos.slice/aresos-game-fixture.scope'
                model.session.write('/sys/fs/cgroup' + group + '/memory.high', bad_value)
                with self.assertRaisesRegex(AssertionError, 'memory.high'):
                    model.run_route()
                self.assertEqual(model.saved['final-29-game-scope']['memory_high'], bad_value)
        with self.model() as model:
            model.session.write('/proc/4242/cgroup', '0::/user.slice/app.slice/fixture.scope\n')
            model.session.write('/sys/fs/cgroup/user.slice/app.slice/fixture.scope/memory.high', '2684354560')
            with self.assertRaisesRegex(AssertionError, 'JVM is not in its game scope'):
                model.run_route()
            self.assertFalse(model.saved['final-29-game-scope']['in_scope'])

    def test_host_receipt_rejects_changed_settings_or_each_omitted_source(self):
        receipt = walk.read_json(ROOT / walk.HOST_WALK_RECEIPT)
        walk.check_host_receipt(receipt)
        self.assertIn('os/ci/release29_walk.py', {row['path'] for row in receipt['sources']})
        for index, row in enumerate(receipt['sources']):
            with self.subTest(path=row['path']), self.assertRaisesRegex(AssertionError, 'missing sources: ' + row['path']):
                walk.check_host_receipt(dict(receipt, sources=receipt['sources'][:index] + receipt['sources'][index + 1:]))
        wrong = dict(receipt['probe_settings'], control_checks={'28': list(probes.SERVICE_CHECKS)})
        with self.assertRaisesRegex(AssertionError, 'probe settings differ'):
            walk.check_host_receipt(dict(receipt, probe_settings=wrong))

    def test_failed_start_may_retry_once_after_the_r28_save_gate(self):
        with self.model('recovery') as model:
            with self.assertRaisesRegex(AssertionError, 'did not boot on the first unattended start'):
                model.run_route()
            result = model.saved['release-29-deployment-walk']
            self.assertEqual(result['status'], 'not-qualifying')
            self.assertEqual(result['first_booted'], model.r28.split('@')[1])
            self.assertEqual(result['booted'], model.r29.split('@')[1])
            stages = [stage for stage, event in model.events if event in ('reboot', 'audit', 'F12 Bazzite')]
            self.assertIn('release-29-recovery-reboot', stages)
            self.assertEqual(stages[stages.index('release-29-recovery-reboot') + 1:][:2], ['release-29', 'release-29-retry'])
        with self.model('not-applied') as model, self.assertRaisesRegex(AssertionError, 'was not applied'):
            try:
                model.run_route()
            finally:
                self.assertNotIn(('r29-previous', 'previous'), model.events)
                self.assertNotIn(('release-29-recovery-reboot', 'reboot'), model.events)
                self.assertIn(('release-29', 'audit'), model.events)
                self.assertEqual(model.saved['release-29-deployment-walk']['status'], 'not-qualifying')

    def test_second_r28_start_audits_and_stops_without_retrying_again(self):
        with self.model('retry-still-r28') as model:
            with self.assertRaisesRegex(AssertionError, 'did not start after the recovery restart'):
                model.run_route()
            self.assertEqual(model.saved['release-29-deployment-walk']['status'], 'not-qualifying')
            self.assertEqual([stage for stage, event in model.events if event == 'reboot'],
                             ['r29-update-reboot', 'release-29-recovery-reboot'])
            self.assertEqual(model.events[-1], ('release-29-retry', 'audit'))

    def test_read_only_saves_fail_on_either_release(self):
        for stage in ('release-28', 'release-29'):
            with self.subTest(stage=stage), self.model() as model:
                saves = model.session.Path(walk.r28.INSTANCE_LINKS['minecraft/saves'])
                world = saves / walk.r28.WORLD
                path_open = model.session.Path.open
                writes = []

                def open_file(path, mode='r', *args, **kwargs):
                    if path.is_relative_to(saves) and mode == 'xb' and model.guests[-1].stage == stage:
                        writes.append(path)
                        raise OSError(errno.EROFS, os.strerror(errno.EROFS))
                    return path_open(path, mode, *args, **kwargs)

                with patch.object(model.session.Path, 'open', open_file), \
                        self.assertRaisesRegex(AssertionError, 'Read-only file system'):
                    model.run_route()
                self.assertEqual(writes, [world / '.aresos-rehearsal-write-probe'])
                self.assertEqual((world / 'level.dat').read_bytes(), bytes.fromhex(walk.r28.WORLD_FILES['level.dat']))
                self.assertEqual(model.events[-1], (stage, 'audit'))
                self.assertNotIn('release-29-deployment-walk', model.saved)

    def test_route_stops_and_audits_on_each_failure(self):
        cases = [('cached-ticket', 'kept a ticket', 'release-28'), ('tools-drift', 'changed installed tools', 'release-28'),
                 ('update-stop', 'update was refused', 'release-28'), ('update-stop-unpinned', 'pin lost', 'release-28'),
                 ('wrong-staged-slot', 'staged deployment', 'release-28'),
                 ('stale-title', 'wrong boot order', 'release-28'), ('wrong-export', 'no-stick export', 'release-28'),
                 ('open-on-update', 'Minecraft close', 'release-28'), ('missing-close-message', 'Minecraft close', 'release-28'),
                 ('open-on-recovery', 'Minecraft close', 'release-29'), ('wrong-confirmation', 'was not confirmed', 'release-29'),
                 ('unpinned-stock', 'pin lost', 'previous-28'), ('open-on-forward', 'Minecraft close', 'previous-28'),
                 ('corrupt-world', 'world contents', 'final-29'), ('missing-image-targets', 'inaccessible', 'final-29')]
        for fault, error, stage in cases:
            with self.subTest(fault=fault), self.model(fault) as model, self.assertRaisesRegex(AssertionError, error):
                try:
                    model.run_route()
                finally:
                    self.assertEqual(model.events[-1], (stage, 'audit'))
                    if fault == 'open-on-recovery':
                        self.assertEqual(model.saved['release-29-deployment-walk']['status'], 'not-qualifying')
                    else:
                        self.assertNotIn('release-29-deployment-walk', model.saved)
                    model.guests[-1].poweroff.assert_not_called()

    def test_console_returns_a_recorded_stop_only_when_the_route_accepts_it(self):
        console = object.__new__(vm.Console)
        console.guest = Mock(owner_layout='de')
        stopped = dict(status='stopped', error='fixture refusal')
        console.guest.capture_json.return_value = stopped
        console.commands = {'update': 'sudo /var/lib/ares/at update'}
        console.select = console.prompt = console.visible = Mock()
        console.records = Mock(return_value=[])
        with patch.object(vm.owner_xhci, 'checkpoint'), patch.object(vm.owner_xhci, 'context'), \
                patch.object(vm.owner_xhci, 'guard', return_value='pass'), patch.object(vm.td, 'save') as evidence:
            with self.assertRaisesRegex(AssertionError, 'Owner command failed'):
                console.run('update', 'fixture')
            self.assertEqual(console.run('update', 'fixture', allow_stop=True), stopped)
        self.assertIn(call('fixture-owner-diagnostics', stopped), evidence.call_args_list)
        console.guest.screenshot.assert_not_called()


if __name__ == '__main__':
    unittest.main()
