"""Browser-free qualification, delivery, and workflow contracts."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

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


class Workflow(unittest.TestCase):
    def test_main_only_mutations_serialized_publication_and_daily_stable_beta_pairs(self):
        source = (ROOT/'.github/workflows/control-chrome-qualification.yml').read_text()
        self.assertIn("cron: '19 4 * * *'", source)
        self.assertIn('branches: [pkg/20-chrome-qual, main]', source)
        plan = source.split('  qualification-plan:')[1].split('  qualification-pairs:')[0]
        publisher = source.split('  qualification-publish:')[1].split('  delivery-attestation:')[0]
        self.assertIn("github.ref == 'refs/heads/main'", plan)
        self.assertIn("github.ref == 'refs/heads/main'", publisher)
        self.assertIn("github.event_name != 'pull_request'", publisher)
        self.assertIn('group: chrome-qualification-publisher\n      cancel-in-progress: false', publisher)
        for permission in ['contents: write', 'id-token: write', 'attestations: write', 'issues: write', 'pull-requests: write']:
            self.assertIn(permission, publisher)
        self.assertLess(publisher.index('qualify.py prepare'), publisher.index('actions/attest-build-provenance'))
        self.assertLess(publisher.index('actions/attest-build-provenance'), publisher.index('qualify.py publish'))
        self.assertIn('--plan .work/qualification-plan.json', publisher)
        self.assertIn('path: qualification-plan.json', source)
        self.assertIn('--runtime-root runtime', source)
        self.assertIn('QUALIFICATION_OUTCOME: ${{ steps.suite.outcome }}', source)
        attestation = source.split('  delivery-attestation:')[1]
        self.assertIn("github.event_name != 'pull_request'", attestation)
        self.assertNotIn("github.event_name == 'push'", attestation)
        # Runner-only browser harness remains in the original fixtures job.
        self.assertNotIn('delivery-attestation:', (ROOT/'.github/workflows/control-chrome.yml').read_text())
