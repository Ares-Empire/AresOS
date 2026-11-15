"""Browser-free qualification, delivery, and workflow contracts."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome import qualification as q
from aresos_control.common import Refused
from aresos_control.storage import Store
from test_policy import entry

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT/'.work/20-chrome'
WORK.mkdir(parents=True, exist_ok=True)


def record(*entries):
    return {'format': 1, 'entries': list(entries)}


class Records(unittest.TestCase):
    def test_strict_schema_rejects_malformed_entries_and_non_boolean_passes(self):
        invalid = [None, [], {'format': True, 'entries': []}, {'format': 1, 'entries': [None]}]
        for key, values in {'build': [None, 'a', [], 1], 'version': [None, '158', '158.1.2.3-extra'],
                            'channel': [[], None, 'dev'], 'run': ['', None, 1],
                            'core': [None, [], {}, {'binding': True}], 'adapters': [None, [], {}]}.items():
            invalid += [record(entry(**{key: value})) for value in values]
        for category, key in [('core', 'binding'), ('adapters', 'gmail')]:
            for value in [1, 'true', None, []]:
                changed = entry(); changed[category][key] = value; invalid.append(record(changed))
        invalid.append(record(entry(), entry()))
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(Refused):
                q.validate_record(candidate)

    def test_append_only_rejects_removed_changed_reordered_and_duplicate_history(self):
        held = record(entry(), entry(version='158.0.1.0', channel='beta'))
        candidates = [record(), record(*held['entries'][::-1]), record(*held['entries'], entry())]
        changed = copy.deepcopy(held); changed['entries'][0]['core']['binding'] = False; candidates.append(changed)
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaises(Refused):
                q.append_only(held, candidate)
        self.assertEqual(q.append_only(held, record(*held['entries'], entry(version='159.0.1.0')) )['entries'][:2], held['entries'])

    def test_beta_stable_failure_and_later_passing_patch_sequence(self):
        beta = entry(version='158.0.20.0', channel='beta')
        held = record(beta)
        self.assertFalse(q.switches(held, 'a'*64, '158.0.10.0')['conservative'])
        self.assertTrue(q.switches(held, 'a'*64, '158.0.10.0')['core']['binding'])
        stable = entry(version='158.0.10.0'); stable['core']['binding'] = False; stable['adapters']['gmail'] = False
        held['entries'].append(stable)
        for version in ['158.0.10.0', '158.0.11.0', '158.0.21.0']:
            mode = q.switches(held, 'a'*64, version)
            self.assertFalse(mode['conservative']); self.assertFalse(mode['core']['binding']); self.assertFalse(mode['adapters']['gmail'])
        held['entries'].append(entry(version='158.0.22.0'))
        self.assertTrue(q.switches(held, 'a'*64, '158.0.23.0')['core']['binding'])
        self.assertFalse(q.switches(held, 'a'*64, '158.0.21.0')['core']['binding'])

    def test_failed_beta_then_stable_and_future_recorded_failure_never_conservative(self):
        for channel in ['stable', 'beta']:
            failed = entry(version='158.0.20.0', channel=channel)
            failed['core']['page_script'] = False
            failed['adapters']['gmail'] = False
            for version in ['158.0.10.0', '158.0.20.0', '158.0.21.0']:
                mode = q.switches(record(failed), 'a'*64, version)
                self.assertFalse(mode['conservative']); self.assertFalse(mode['core']['page_script'])
                self.assertFalse(mode['adapters']['gmail'])
        passed = entry(version='158.0.20.0')
        self.assertFalse(q.switches(record(failed, passed), 'a'*64, '158.0.21.0')['core']['page_script'])

    def test_newer_beta_failure_is_not_hidden_by_older_stable_pass(self):
        stable = entry(version='158.0.10.0')
        beta = entry(version='158.0.20.0', channel='beta')
        beta['core']['binding'] = False; beta['adapters']['gmail'] = False
        held = record(stable, beta)
        self.assertTrue(q.switches(held, 'a'*64, '158.0.19.0')['core']['binding'])
        for chrome_version in ['158.0.20.0', '158.0.21.0']:
            mode = q.switches(held, 'a'*64, chrome_version)
            self.assertFalse(mode['conservative']); self.assertFalse(mode['core']['binding']); self.assertFalse(mode['adapters']['gmail'])
        held['entries'].append(entry(version='158.0.22.0'))
        self.assertTrue(q.switches(held, 'a'*64, '158.0.23.0')['core']['binding'])

    def test_only_own_build_and_major_count_and_later_qualified_patch_is_normal(self):
        held = record(entry(build='b'*64, version='158.0.1.0'), entry())
        for build, version in [('a'*64, '158.0.2.0'), ('c'*64, '157.0.2.0')]:
            mode = q.switches(held, build, version)
            self.assertTrue(mode['conservative']); self.assertTrue(mode['notice']); self.assertFalse(any(mode['adapters'].values()))
        mode = q.switches(held, 'a'*64, '157.0.100.0')
        self.assertFalse(mode['conservative']); self.assertTrue(all(mode['adapters'].values()))

    def test_gh_verifier_is_fixed_to_repository_workflow_main_and_hosted_runners(self):
        runner = Mock(side_effect=[Mock(stdout='gh version 2.102.0'), Mock()])
        with patch.object(q.subprocess, 'run', runner):
            q.verify('record.json', bundle='bundle.json')
        command = runner.call_args.args[0]
        for required in ['--repo', q.REPOSITORY, '--signer-workflow', q.REPOSITORY+'/'+q.WORKFLOW,
                         '--source-ref', 'refs/heads/main', '--deny-self-hosted-runners', '--bundle', 'bundle.json']:
            self.assertIn(required, command)
        # CI verifies the bundle it attested on its own full ref; the default stays main.
        runner = Mock(side_effect=[Mock(stdout='gh version 2.102.0'), Mock()])
        with patch.object(q.subprocess, 'run', runner):
            q.verify('record.json', bundle='bundle.json', ref='refs/pull/7/merge')
        command = runner.call_args.args[0]
        self.assertEqual(command[command.index('--source-ref')+1], 'refs/pull/7/merge')
        self.assertNotIn('refs/heads/main', command)
        with patch.object(q.subprocess, 'run', return_value=Mock(stdout='gh version 2.94.0')) as runner:
            with self.assertRaises(Refused): q.verify('record.json')
            self.assertEqual(runner.call_count, 1)

    def test_runtime_verifier_uses_bounded_anonymous_bundle_lookup(self):
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            path = Path(directory)/'record.json'; path.write_text('{}')
            payload = json.dumps({'attestations':[{'bundle':{'fixture':'untrusted bundle'}}]}).encode()
            def runner(command, **kwargs):
                if command[1] == '--version': return Mock(stdout='gh version 2.102.0')
                bundle = Path(command[command.index('--bundle')+1])
                self.assertEqual(bundle.suffix, '.jsonl')
                self.assertLessEqual(bundle.stat().st_size, q.DELIVERY_LIMIT)
                self.assertEqual(json.loads(bundle.read_text()), {'fixture':'untrusted bundle'})
                self.assertEqual(kwargs['env']['XDG_CACHE_HOME'], str(path.parent/'qualification-verifier-cache'))
                return Mock()
            with patch.object(q.subprocess, 'run', side_effect=runner), patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(payload)) as transport:
                q.verify(path)
            request = transport.call_args.args[0]
            self.assertTrue(request.full_url.startswith('https://api.github.com/'))
            self.assertNotIn('Authorization', request.headers)
            self.assertEqual(list(path.parent.glob('.qualification-bundle-*')), [])
            for data in [b'{"attestations":[]}', b'x'*(4*1024*1024+1)]:
                with patch.object(q.subprocess, 'run', return_value=Mock(stdout='gh version 2.102.0')), patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(data)), self.assertRaises(Refused):
                    q.verify(path)

    def test_non_ascii_attestations_cannot_expand_past_admitted_bundle_bytes(self):
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            path = Path(directory)/'record.json'; path.write_text('{}')
            payload = json.dumps({'attestations':[{'bundle':{'fixture':'\u0800'*1_000_000}}]}, ensure_ascii=False).encode()
            self.assertLess(len(payload), q.DELIVERY_LIMIT)
            def runner(command, **kwargs):
                if command[1] == '--version': return Mock(stdout='gh version 2.102.0')
                bundle = Path(command[command.index('--bundle')+1])
                self.assertLessEqual(bundle.stat().st_size, q.DELIVERY_LIMIT)
                return Mock()
            with patch.object(q.subprocess, 'run', side_effect=runner), patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(payload)):
                q.verify(path)


class RecordingOpener(unittest.TestCase):
    """Main fix H2: CI replays a token-fetched API response through the product's anonymous path."""
    FIXTURE = ROOT/'control/chrome_tests/fixtures/qualification/42687597384'

    def setUp(self):
        spec = importlib.util.spec_from_file_location('chrome_ci_attestation', ROOT/'control/chrome/ci/attestation.py')
        self.attestation = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.attestation)
        self.addCleanup(urllib.request.install_opener, None)

    def test_recording_serves_exactly_one_url_offline_and_refuses_every_other(self):
        url = 'https://api.github.com/repos/'+q.REPOSITORY+'/attestations/sha256:'+'0'*64+'?per_page=100'
        payload = json.dumps({'attestations':[{'bundle':{'fixture':'recorded'}}]}).encode()
        opener, handler = self.attestation.recorded(url, payload)
        with opener.open(url, timeout=1) as response:
            self.assertEqual(response.read(q.DELIVERY_LIMIT+1), payload)
        for other in [url.replace('per_page=100', 'per_page=1'), 'https://api.github.com/rate_limit', url.replace('https://', 'http://'),
                      'https://raw.githubusercontent.com/'+q.REPOSITORY+'/refs/heads/chrome-qualification/control/chrome/qualification.json']:
            with self.subTest(url=other), self.assertRaises(urllib.error.URLError):
                opener.open(other, timeout=1)
        with self.assertRaises(urllib.error.URLError):
            opener.open(urllib.request.Request(url, headers={'Authorization':'token private'}), timeout=1)
        for status in [403, 429, 500]:
            opener, _ = self.attestation.recorded(url, b'{"message":"private"}', status)
            with self.subTest(status=status), self.assertRaises(urllib.error.HTTPError) as caught:
                opener.open(url, timeout=1)
            self.assertEqual(caught.exception.code, status); caught.exception.close()
        # Installed, the product's verify() reaches it through urlopen and
        # serializes the recorded bundles for gh exactly as it would online.
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            path = Path(directory)/'record.json'; path.write_bytes((self.FIXTURE/'record.json').read_bytes())
            recording = (self.FIXTURE/'api-response.json').read_bytes()
            expected = ''.join(json.dumps(item['bundle'], ensure_ascii=False, separators=(',',':'))+'\n' for item in json.loads(recording)['attestations']).encode()
            self.assertEqual(json.loads(recording)['attestations'][0]['bundle']['dsseEnvelope']['signatures'][0]['sig'],
                             json.loads((self.FIXTURE/'bundle.json').read_text())['dsseEnvelope']['signatures'][0]['sig'])
            seen = {}
            def runner(command, **kwargs):
                if command[1] == '--version': return Mock(stdout='gh version 2.102.0')
                seen['bundle'] = Path(command[command.index('--bundle')+1]).read_bytes(); seen['ref'] = command[command.index('--source-ref')+1]
                return Mock()
            with patch.object(q.subprocess, 'run', side_effect=runner):
                _, handler = self.attestation.with_recording(self.attestation.attestation_url(path), recording, lambda: q.verify(path, ref='refs/heads/pkg/20-chrome-qual'))
            self.assertEqual(seen, {'bundle': expected, 'ref': 'refs/heads/pkg/20-chrome-qual'})
            self.assertEqual([request.full_url for request in handler.requests], [self.attestation.attestation_url(path)])
            self.assertIsNone(urllib.request._opener)
            with patch.object(q.subprocess, 'run', side_effect=runner), self.assertRaises(urllib.error.HTTPError):
                self.attestation.with_recording(self.attestation.attestation_url(path), b'{}', lambda: q.verify(path, ref='refs/heads/pkg/20-chrome-qual'), 403)

    def test_the_recording_opener_never_ships(self):
        # Like the CI stand-in polkit rule: the opener and anything that
        # installs one live only in control/chrome/ci at run time.
        sys.path.insert(0, str(ROOT/'control/chrome'))
        from build import inputs
        installed = list(inputs(ROOT))
        markers = ['install_opener', 'RecordedAttestationAPI', 'OpenerDirector', 'api-response.json']
        self.assertEqual([path for path in installed if any(marker in path.read_text(errors='replace') for marker in markers)], [])
        self.assertNotIn(ROOT/'control/chrome/ci/attestation.py', installed)
        self.assertIn('Authorization', (ROOT/'control/chrome/ci/attestation.py').read_text())
        product = (ROOT/'control/aresos_control/chrome/qualification.py').read_text()
        for forbidden in ['Authorization', 'GH_TOKEN', 'GITHUB_TOKEN', 'install_opener']:
            self.assertNotIn(forbidden, product)


class Delivery(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temporary.name)
        self.store = Store(self.root/'state', self.root/'evidence')
        self.held = record(entry())
        self.newer = record(entry(), entry(version='158.0.1.0', channel='beta'))
        self.qualification = q.Qualification(self.store, 'a'*64, self.held)
        self.path = self.root/'candidate.json'; self.path.write_text(json.dumps(self.newer))

    def tearDown(self):
        self.store.close(); self.temporary.cleanup()

    def test_valid_update_is_used_after_service_restart(self):
        verifier = Mock()
        self.qualification.accept(self.path, verifier)
        verifier.assert_called_once_with(self.path)
        self.store.close(); self.store = Store(self.root/'state', self.root/'evidence')
        restarted = q.Qualification(self.store, 'a'*64, self.held)
        self.assertEqual(restarted.record(), self.newer)
        self.assertFalse(q.switches(restarted.record(), restarted.build, '158.0.2.0')['conservative'])

    def test_image_upgrade_reconciles_older_held_history_and_can_fetch_again(self):
        self.qualification.accept(self.path, Mock())
        upgraded_baseline = record(*self.newer['entries'], entry(version='159.0.1.0'))
        upgraded = q.Qualification(self.store, 'b'*64, upgraded_baseline)
        self.assertEqual(upgraded.record(), upgraded_baseline)
        next_record = record(*upgraded_baseline['entries'], entry(version='160.0.1.0'))
        self.path.write_text(json.dumps(next_record)); upgraded.accept(self.path, Mock())
        self.assertEqual(upgraded.record(), next_record)
        divergent = copy.deepcopy(upgraded_baseline); divergent['entries'][0]['run'] = 'divergent'
        with self.assertRaises(Refused): q.Qualification(self.store, 'b'*64, divergent).record()

    def test_failed_verification_and_dropped_or_changed_history_leave_held_unchanged(self):
        for name in ['missing', 'altered', 'wrong_workflow', 'wrong_branch']:
            with self.subTest(name=name), self.assertRaises(Refused):
                self.qualification.accept(self.path, Mock(side_effect=Refused('qualification_invalid', name)))
            self.assertEqual(self.qualification.record(), self.held)
        for candidate in [record(), record(entry(run='changed'))]:
            self.path.write_text(json.dumps(candidate))
            with self.assertRaises(Refused): self.qualification.accept(self.path, Mock())
            self.assertEqual(self.qualification.record(), self.held)

    def test_daily_https_fetch_and_forced_unknown_version_refresh(self):
        transport = Mock(side_effect=lambda *args, **kw: io.BytesIO(json.dumps(self.newer).encode()))
        verifier = Mock()
        with patch.object(q.urllib.request, 'urlopen', transport):
            self.qualification.refresh(now=0, verifier=verifier)
            self.qualification.refresh(now=86399, verifier=verifier)
            self.assertEqual(transport.call_count, 1)
            self.qualification.refresh(now=86400, verifier=verifier)
            self.qualification.refresh(now=86401, verifier=verifier, force=True)
        self.assertEqual(transport.call_count, 3); self.assertEqual(verifier.call_count, 3)
        self.assertTrue(transport.call_args.args[0].startswith('https://'))
        self.assertEqual(self.qualification.record(), self.newer)
        self.assertEqual(list(self.store.state_dir.glob('.qualification-*')), [])

    def test_offline_keeps_held_logs_reason_and_obeys_retry_interval(self):
        with patch.object(q.urllib.request, 'urlopen', side_effect=OSError('private transport detail')) as transport:
            self.qualification.refresh(now=10)
            self.qualification.refresh(now=11)
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(self.qualification.record(), self.held)
        result = self.store.get('chrome:qualification_fetch')['result']
        self.assertIn('OSError', result); self.assertIn('held record retained', result)
        self.assertNotIn('private transport detail', result)

    def test_rate_limits_timeouts_and_server_errors_keep_held_and_wait_a_day(self):
        # Main fix H2: the daily fetch on the laptop meets GitHub's quota, a
        # slow network or a 5xx. The held record stays, nothing private is
        # logged, and the next attempt comes about 24 h later, never sooner.
        url = 'https://api.github.com/repos/'+q.REPOSITORY+'/attestations/sha256:'+'0'*64
        def http(code, headers=None):
            return urllib.error.HTTPError(url, code, 'private reason', headers or {}, io.BytesIO(b'{"message":"private body"}'))
        download = lambda *args, **kw: io.BytesIO(json.dumps(self.newer).encode())
        cases = [('HTTPError', 403, download, Mock(side_effect=http(403))),
                 ('HTTPError', 429, download, Mock(side_effect=http(429, {'Retry-After': '60'}))),
                 ('HTTPError', 500, download, Mock(side_effect=http(500))),
                 ('URLError', 'connect timeout', Mock(side_effect=urllib.error.URLError(TimeoutError('private host'))), Mock()),
                 ('TimeoutError', 'read timeout', Mock(side_effect=TimeoutError('private host')), Mock()),
                 ('HTTPError', 503, Mock(side_effect=http(503)), Mock())]
        now = 1_000_000
        for name, detail, transport, verifier in cases:
            with self.subTest(name=name, detail=detail):
                now += 2*86400  # past the previous case's own daily gate
                with patch.object(q.urllib.request, 'urlopen', side_effect=transport) as opened:
                    self.qualification.refresh(now=now, verifier=verifier)
                    self.assertEqual(opened.call_count, 1)
                    self.qualification.refresh(now=now+1, verifier=verifier)
                    self.qualification.refresh(now=now+86399, verifier=verifier)
                    self.assertEqual(opened.call_count, 1, 'A failed fetch must not be retried before the daily interval')
                self.assertEqual(self.qualification.record(), self.held)
                fetch = self.store.get('chrome:qualification_fetch')
                self.assertEqual(fetch['time'], now)
                self.assertIn(name, fetch['result']); self.assertIn('held record retained', fetch['result'])
                for private in ['private', 'api.github.com', 'Retry-After', str(detail)]:
                    self.assertNotIn(private, fetch['result'])
                self.assertEqual(list(self.store.state_dir.glob('.qualification-*')), [])
                with patch.object(q.urllib.request, 'urlopen', side_effect=transport) as opened:
                    self.qualification.refresh(now=now+86400, verifier=verifier)
                    self.assertEqual(opened.call_count, 1)
                self.assertEqual(self.qualification.record(), self.held)
        # The service keeps serving: a later good fetch is accepted normally.
        with patch.object(q.urllib.request, 'urlopen', side_effect=download):
            self.qualification.refresh(now=now+2*86400, verifier=Mock())
        self.assertEqual(self.qualification.record(), self.newer)

    def test_bad_signature_rollback_malformed_and_oversized_downloads_keep_held(self):
        for data, verifier, reason in [
            (json.dumps(self.newer).encode(), Mock(side_effect=Refused('qualification_invalid', 'fixture')), 'qualification_invalid'),
            (json.dumps(record()).encode(), Mock(), 'qualification_rollback'),
            (b'not json', Mock(), 'JSONDecodeError'),
            (b'x'*(4*1024*1024+1), Mock(), 'ValueError')]:
            with self.subTest(reason=reason), patch.object(q.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                self.qualification.refresh(now=100, verifier=verifier, force=True)
            self.assertEqual(self.qualification.record(), self.held)
            self.assertIn(reason, self.store.get('chrome:qualification_fetch')['result'])
            self.assertEqual(list(self.store.state_dir.glob('.qualification-*')), [])


MAIN_ONLY = "github.ref == 'refs/heads/main' && github.event_name != 'pull_request'"
PULL_REQUEST_MODE = "github.ref != 'refs/heads/main' || github.event_name == 'pull_request'"
# The only steps that may run on main alone: the writes that reach GitHub.
MAIN_ONLY_WRITES = {'Verify the new attestation then push only the data branch',
                    'Publish failure details and propose shipped-copy update'}
PULL_REQUEST_COUNTERPARTS = {'Verify the new attestation then publish to a local bare remote (pull-request mode)'}


def workflow_conditions(source):
    """(job, step name or None, condition) for every if: in a workflow, by indentation."""
    rows, job, step = [], None, None
    for line in source.split('\njobs:\n', 1)[1].splitlines():
        if re.match(r'^  \S', line):
            job, step = line.strip().rstrip(':'), None
        elif re.match(r'^      - ', line):
            step = {'name': None}
        found = re.match(r'^(?:      - |        )name: (.*)$', line)
        if found and step is not None:
            step['name'] = found[1].strip()
        found = re.match(r'^( +)if: (.*)$', line)
        if found:
            rows.append((job, None if len(found[1]) == 4 else step, found[2].strip()))
    for job, step, condition in rows:
        if step is not None and step['name'] is None:
            step['name'] = '<unnamed>'
    return [(job, step and step['name'], condition) for job, step, condition in rows]


class Workflow(unittest.TestCase):
    QUALIFICATION = ROOT/'.github/workflows/control-chrome-qualification.yml'
    CHROME = ROOT/'.github/workflows/control-chrome.yml'

    def test_main_only_mutations_serialized_publication_and_daily_stable_beta_pairs(self):
        source = self.QUALIFICATION.read_text()
        self.assertIn("cron: '19 4 * * *'", source)
        self.assertIn('branches: [pkg/20-chrome-qual, main]', source)
        plan = source.split('  qualification-plan:')[1].split('  qualification-pairs:')[0]
        publisher = source.split('  qualification-publish:')[1].split('  delivery-attestation:')[0]
        self.assertIn("QUALIFICATION_CHANNELS: ${{ github.ref == 'refs/heads/main' && 'stable,beta' || 'stable' }}", plan)
        self.assertIn('plan --channels "$QUALIFICATION_CHANNELS"', plan)
        self.assertIn('group: chrome-qualification-publisher\n      cancel-in-progress: false', publisher)
        for permission in ['contents: write', 'id-token: write', 'attestations: write', 'issues: write', 'pull-requests: write']:
            self.assertIn(permission, publisher)
        self.assertLess(publisher.index('qualify.py prepare'), publisher.index('actions/attest-build-provenance'))
        self.assertLess(publisher.index('actions/attest-build-provenance'), publisher.index('qualify.py publish'))
        self.assertIn('--plan .work/qualification-plan.json', publisher)
        # Main fix H3: the fresh attestation is verified from the attest step's bundle.
        self.assertIn('id: attest', publisher)
        self.assertIn('BUNDLE: ${{ steps.attest.outputs.bundle-path }}', publisher)
        self.assertIn('qualify.py publish --bundle "$BUNDLE"\n', publisher)
        self.assertIn('qualify.py publish --bundle "$BUNDLE" --remote .work/publish-remote.git --ref "$GITHUB_REF"', publisher)
        self.assertNotIn('publish --bundle "$BUNDLE" --ref', publisher)
        self.assertIn('path: qualification-plan.json', source)
        self.assertIn('--runtime-root runtime', source)
        self.assertIn('QUALIFICATION_OUTCOME: ${{ steps.suite.outcome }}', source)
        attestation = source.split('  delivery-attestation:')[1]
        # Main fix H2: the API response is recorded with the job token; the
        # product's anonymous path replays it; the PR-made bundle is checked
        # on the run's own full ref, and the retained fixture offline.
        self.assertIn('gh api "repos/$GITHUB_REPOSITORY/attestations/sha256:$DIGEST?per_page=100" > .work/attestation/api-response.json', attestation)
        self.assertIn('.work/attestation/api-response.json --ref "$GITHUB_REF"', attestation)
        self.assertIn('42687597384/api-response.json --ref refs/heads/pkg/20-chrome-qual', attestation)
        self.assertNotIn('GITHUB_HEAD_REF', attestation)
        self.assertIn("entry(run=run)", attestation)
        self.assertNotIn("github.event_name == 'push'", attestation)
        # Runner-only browser harness remains in the original fixtures job.
        self.assertNotIn('delivery-attestation:', self.CHROME.read_text())

    def test_no_job_is_main_only_and_only_allow_listed_write_steps_are(self):
        # Main fix H4: every job of both workflows runs on pull requests, so a
        # path cannot reach main unexercised (run 43647781498). Main-only
        # conditions exist only on the allow-listed write steps, and each of
        # those steps has one.
        markers = ['refs/heads/main', 'pull_request', 'github.ref', 'event_name', 'github.base_ref', 'head_ref']
        for workflow in [self.QUALIFICATION, self.CHROME]:
            rows = workflow_conditions(workflow.read_text())
            self.assertTrue(rows)
            for job, step, condition in rows:
                with self.subTest(workflow=workflow.name, job=job, step=step):
                    if step is None:
                        self.assertFalse(any(marker in condition for marker in markers), 'Job-level main-only condition: '+condition)
                    elif condition in {MAIN_ONLY, 'always() && '+MAIN_ONLY}:
                        self.assertIn(step, MAIN_ONLY_WRITES)
                    elif condition == PULL_REQUEST_MODE:
                        self.assertIn(step, PULL_REQUEST_COUNTERPARTS)
                    else:
                        self.assertFalse(any(marker in condition for marker in markers), 'Unlisted ref condition: '+condition)
        rows = workflow_conditions(self.QUALIFICATION.read_text())
        self.assertEqual({step for _, step, condition in rows if condition in {MAIN_ONLY, 'always() && '+MAIN_ONLY}}, MAIN_ONLY_WRITES)
        self.assertEqual({step for _, step, condition in rows if condition == PULL_REQUEST_MODE}, PULL_REQUEST_COUNTERPARTS)
        jobs = set(re.findall(r'^  (\S+):', self.QUALIFICATION.read_text().split('\njobs:\n', 1)[1], re.M))
        self.assertEqual(jobs, {'qualification-tests', 'qualification-plan', 'qualification-pairs', 'qualification-combine', 'qualification-publish', 'delivery-attestation'})
        # The product's own guard, not only the workflow, keeps the real writes on main.
        qualify = (ROOT/'control/chrome/qualify.py').read_text()
        self.assertIn("if not on_main:raise SystemExit('Qualification publication to origin is restricted to main')", qualify)
        self.assertIn("if not on_main:raise SystemExit('Qualification notifications are restricted to main')", qualify)

    def test_path_triggers_cover_every_input_of_the_jobs(self):
        # The jobs copy or archive these beside control/**; a change to any of
        # them must start the workflow on the pull request.
        expected = {self.QUALIFICATION: ['control/**', 'docs/control/TOOLS.md', 'reviews/20-chrome/QUALIFICATION*', 'reviews/20-chrome/audit-review-evidence.mjs',
                                         '.github/workflows/control-chrome-qualification.yml', '.github/workflows/control-chrome.yml'],
                    self.CHROME: ['control/**', 'docs/control/TOOLS.md', 'reviews/20-chrome/**', '.github/workflows/control-chrome.yml', '.github/workflows/control-chrome-qualification.yml']}
        for workflow, paths in expected.items():
            source = workflow.read_text().split('\njobs:\n')[0]
            for event in ['push', 'pull_request']:
                section = re.search(r'^  '+event+r':\n((?:    .*\n)+)', source, re.M)[1]
                for path in paths:
                    with self.subTest(workflow=workflow.name, event=event, path=path):
                        self.assertIn("'"+path+"'", section)
            self.assertIn('pull_request:', source)
