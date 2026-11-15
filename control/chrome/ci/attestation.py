"""Real Sigstore verifier and durable-delivery fixtures; no browser access."""
import copy
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from aresos_control.chrome.qualification import Qualification, VERIFIER_CACHE_RESERVE, verify
from aresos_control.storage import Store
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qualify


def exercise(path, bundle, branch):
    candidate = json.loads(path.read_text())
    baseline = {'format': 1, 'entries': candidate['entries'][:1]}
    with tempfile.TemporaryDirectory(dir=path.parent) as directory:
        root = Path(directory)
        store = Store(root/'state', root/'evidence')
        qualification = Qualification(store, candidate['entries'][0]['build'], baseline)
        verifier = lambda subject: verify(subject, branch=branch, bundle=bundle)
        qualification.accept(path, verifier)
        assert qualification.record() == candidate
        print('QUALIFICATION DELIVERY newer valid attested record used PASS', flush=True)
        environment = dict(os.environ)
        try:
            # Exercise the runtime default: public HTTPS lookup, no personal
            # authentication, gh --bundle with the same source policy.
            os.environ.clear()
            os.environ.update({'PATH':'/usr/bin:/bin', 'LANG':'C.UTF-8'})
            try:
                verify(path, branch=branch)
            except subprocess.CalledProcessError as error:
                raise AssertionError('Minimal-environment verifier failed: '+error.stderr.decode(errors='replace')[:4000]) from error
        finally:
            os.environ.clear()
            os.environ.update(environment)
        cache = path.parent/'qualification-verifier-cache'
        cache_bytes = sum(file.stat().st_size for file in cache.rglob('*') if file.is_file())
        assert cache_bytes <= VERIFIER_CACHE_RESERVE, 'Verifier cache exceeds admitted reserve'
        print(f'QUALIFICATION DELIVERY anonymous bundle lookup in launch-equivalent environment PASS; cache {cache_bytes} bytes', flush=True)
        original = path.read_bytes()
        altered = copy.deepcopy(json.loads(bundle.read_text()))
        signature = altered['dsseEnvelope']['signatures'][0]['sig']
        altered['dsseEnvelope']['signatures'][0]['sig'] = ('A' if signature[0] != 'A' else 'B') + signature[1:]
        broken = root/'altered-bundle.json'
        broken.write_text(json.dumps(altered))
        cases = [
            ('missing attestation', lambda subject: verify(subject, branch=branch, bundle=root/'missing.json')),
            ('altered attestation', lambda subject: verify(subject, branch=branch, bundle=broken)),
            ('wrong workflow', lambda subject: verify(subject, branch=branch, bundle=bundle, workflow='.github/workflows/untrusted-fixture.yml')),
            ('wrong branch', lambda subject: verify(subject, branch='untrusted-fixture-branch', bundle=bundle)),
            ('production main rejects branch fixture', lambda subject: verify(subject, bundle=bundle))
        ]
        if branch == 'main':
            cases.pop()
        for name, check in cases:
            try:
                qualification.accept(path, check)
            except Exception:
                assert qualification.record() == candidate
            else:
                raise AssertionError(name + ' was accepted')
            print('QUALIFICATION DELIVERY ' + name + ' refused; held retained PASS', flush=True)
        try:
            path.write_bytes(original + b' ')
            try:
                qualification.accept(path, verifier)
            except Exception:
                assert qualification.record() == candidate
            else:
                raise AssertionError('Altered subject accepted')
            print('QUALIFICATION DELIVERY altered subject refused; held retained PASS', flush=True)
        finally:
            path.write_bytes(original)
        # Authentic signatures do not authorize rollback of local history.
        for name, held in [('dropped held entry', {'format': 1, 'entries': candidate['entries'] + [{**candidate['entries'][-1], 'version': '999.0.1.0'}]}),
                           ('changed held entry', copy.deepcopy(candidate))]:
            if name == 'changed held entry':
                held['entries'][-1]['core']['binding'] = not held['entries'][-1]['core']['binding']
            # Each starts from its own previously held record, then verifies the
            # genuine candidate. The append-only check must still refuse it.
            store.write({'chrome:qualification': held}, 'chrome_fixture', 'Synthetic held qualification history')
            try:
                qualification.accept(path, verifier)
            except Exception:
                assert qualification.record() == held
            else:
                raise AssertionError(name + ' accepted')
            print('QUALIFICATION DELIVERY ' + name + ' refused after real verification PASS', flush=True)
        store.close()
        publication = root/'publication'
        subject = publication/qualify.RECORD
        subject.parent.mkdir(parents=True)
        subject.write_bytes(original)
        result = qualify.prepare(publication, [], baseline, verifier)
        assert result == candidate
        print('QUALIFICATION PUBLISHER real held attestation and baseline verified PASS', flush=True)
        for name, contents, trusted_baseline in [
            ('unsigned inserted entry', {'format':1, 'entries':candidate['entries'] + [{**candidate['entries'][-1], 'version':'999.0.1.0'}]}, baseline),
            ('non-append-only shipped baseline', candidate, {'format':1, 'entries':[dict(candidate['entries'][0], run='changed-fixture-baseline')]})
        ]:
            subject.write_text(json.dumps(contents))
            notifications = Mock(return_value=Mock(stdout='[]'))
            try:
                qualify.prepare(publication, [], trusted_baseline, verifier)
            except Exception:
                qualify.notify(None, False, notifications)
            else:
                raise AssertionError(name+' was signed forward')
            assert json.loads(subject.read_text()) == contents
            assert notifications.call_count == 1 and 'issue' in notifications.call_args.args[0]
            print('QUALIFICATION PUBLISHER '+name+' refused; no write, issue stubbed PASS', flush=True)


if __name__ == '__main__':
    exercise(Path(sys.argv[1]), Path(sys.argv[2]), os.environ.get('GITHUB_HEAD_REF') or os.environ['GITHUB_REF_NAME'])
