"""Fixture checks for the historical R29 preflight. No registry, VM or host tools."""
import contextlib
import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, call, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))

import owner_media
import owner_vm as vm
import registry_auth as auth
import release29_walk as walk


ENV = dict(GITHUB_ACTIONS='true', GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='Ares-Empire/AresOS',
           GITHUB_REF_NAME=auth.BASELINE_BRANCH, GITHUB_REF='refs/heads/' + auth.BASELINE_BRANCH,
           REHEARSAL_PACKAGE='331', REHEARSAL_MODE='release-29', GITHUB_SHA='ab' * 20, GITHUB_RUN_ID='331',
           GITHUB_RUN_ATTEMPT='1', GITHUB_ACTOR='fixture-runner', GH_TOKEN='fixture-job-token')


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
    stack.enter_context(patch.object(walk, 'BASELINE_RECEIPT', root / 'baseline.json'))
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
        with patch.dict(os.environ, ENV, clear=True):
            auth.require_baseline_dispatch()
            owner_media.require_runner()
        for key, value in [('GITHUB_ACTIONS', 'false'), ('GITHUB_EVENT_NAME', 'push'),
                           ('GITHUB_REF_NAME', 'main'), ('GITHUB_REF', 'refs/tags/' + auth.BASELINE_BRANCH),
                           ('GITHUB_REPOSITORY', 'fork/AresOS'), ('REHEARSAL_PACKAGE', '42'),
                           ('REHEARSAL_MODE', 'release-28')]:
            with self.subTest(key=key), patch.dict(os.environ, ENV | {key: value}, clear=True), \
                    patch.object(auth, 'write_auth') as create, self.assertRaisesRegex(AssertionError, 'unauthorized'):
                auth.baseline_preflight('/unused')
            create.assert_not_called()

    def test_preflight_reads_and_checks_the_exact_three_signatures_with_job_credentials(self):
        records = {version: json.loads(raw) for version, raw in auth.historical_records().items()}
        references = {record['reference']: record for record in records.values()}
        for fail in (None, 'token', 'read', 'signature'):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as tmp, contextlib.ExitStack() as stack:
                root = pathlib.Path(tmp)
                temporary = root / 'runner'
                temporary.mkdir()
                env = ENV | dict(RUNNER_TEMP=str(temporary), GITHUB_WORKSPACE=str(root / 'checkout'))
                if fail == 'token':
                    env['GH_TOKEN'] = ''
                stack.enter_context(patch.dict(os.environ, env, clear=True))
                stack.enter_context(patch.object(auth, 'BASELINE_REGISTRY', root / 'result.json'))
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
                                                       stdout=b'fixture signature', stderr=b'fixture-job-token')

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


if __name__ == '__main__':
    unittest.main()
