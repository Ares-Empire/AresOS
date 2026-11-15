"""Real Sigstore verifier and durable-delivery fixtures; no browser access."""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
from unittest.mock import Mock
import urllib.error
import urllib.request
import urllib.response

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from aresos_control.chrome.qualification import Qualification, REPOSITORY, VERIFIER_CACHE_RESERVE, verify
from aresos_control.common import Refused
from aresos_control.storage import Store
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qualify


# gh's own wording for each refusal (cli/cli pkg/cmd/attestation): a source-ref
# mismatch names the expected and the attested ref; a signature or
# certificate-identity (signer workflow) policy failure, and a subject whose
# digest no bundle names (an altered record), are reported as "verifying with
# issuer"; a missing bundle file as "could not load content".
# A refusal counts only as gh's failed verification naming its own reason, so
# a timeout or a verifier that could not start never passes as one.
SOURCE_REF = 'expected SourceRepositoryRef to be '
POLICY = 'verifying with issuer "sigstore.dev"'
MISSING = 'could not load content from file path'
# The append-only check's own refusal: authentic signatures never authorize
# a rollback of held history or of the shipped baseline.
ROLLBACK = 'qualification_rollback'
# The attestation API's answer for a digest it lists no attestation for.
NOT_FOUND = b'{"message":"Not Found","documentation_url":"https://docs.github.com/rest/repos/attestations#list-attestations","status":"404"}'


def expected_refusal(action, reason):
    """action must refuse for exactly reason: gh's failed verification naming it, or Refused with that code (ROLLBACK).

    gh failing for another reason fails the case; any other exception,
    a Refused with another code included, propagates and fails the job.
    """
    try:
        action()
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.decode('utf-8', 'replace') if isinstance(error.stderr, bytes) else error.stderr or ''
        if reason not in stderr:
            raise AssertionError('gh refused for another reason than ' + repr(reason) + ': ' + stderr.strip()[-400:]) from error
    except Refused as error:
        if error.code != reason:
            raise
    else:
        raise AssertionError('accepted')


def refused(qualification, path, check, reason, held):
    expected_refusal(lambda: qualification.accept(path, check), reason)
    assert qualification.record() == held, 'a refusal changed the held record'


def altered_subject(qualification, path, check, held):
    """An altered record no longer matches its bundle's subject digest: gh's named policy refusal."""
    original = path.read_bytes()
    try:
        path.write_bytes(original + b' ')
        refused(qualification, path, check, POLICY, held)
    finally:
        path.write_bytes(original)


def listed(recording):
    """The attestations a recorded API response lists; none for a 404 body, an empty list or no JSON."""
    try:
        data = json.loads(recording or b'null')
    except ValueError:
        return []
    attestations = data.get('attestations') if isinstance(data, dict) else None
    return attestations if isinstance(attestations, list) else []


def attestation_url(path):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return f'https://api.github.com/repos/{REPOSITORY}/attestations/sha256:{digest}?per_page=100'


class RecordedAttestationAPI(urllib.request.BaseHandler):
    """CI-only: answers exactly one recorded URL offline and refuses every other.

    The recording is made by the workflow step with gh api and the job's
    token; the product's anonymous verify() runs unchanged through it and
    never sees a token or a header. This class ships in no installed file.
    """

    def __init__(self, url, payload, status=200, headers=None):
        self.url, self.payload, self.status, self.headers = url, payload, status, headers or {}
        self.requests = []

    def https_open(self, request):
        self.requests.append(request)
        if request.full_url != self.url:
            raise urllib.error.URLError('Recording refuses an unrecorded URL: ' + request.full_url)
        if 'Authorization' in request.headers:
            raise urllib.error.URLError('The anonymous path must not send credentials')
        headers = {'Content-Type': 'application/json', **self.headers}
        if self.status != 200:
            raise urllib.error.HTTPError(self.url, self.status, 'recorded status', headers, io.BytesIO(self.payload))
        return urllib.response.addinfourl(io.BytesIO(self.payload), headers, self.url, self.status)

    def http_open(self, request):
        raise urllib.error.URLError('Recording refuses plain HTTP: ' + request.full_url)


def recorded(url, payload, status=200, headers=None):
    handler = RecordedAttestationAPI(url, payload, status, headers)
    opener = urllib.request.OpenerDirector()
    opener.add_handler(handler)
    return opener, handler


def with_recording(url, payload, action, status=200, headers=None):
    opener, handler = recorded(url, payload, status, headers)
    urllib.request.install_opener(opener)
    try:
        return action(), handler
    finally:
        urllib.request.install_opener(None)


def minimal_environment(action):
    # Exercise the runtime default: no personal authentication, no inherited
    # token, gh --bundle with the same source policy.
    environment = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update({'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
        try:
            return action()
        except subprocess.CalledProcessError as error:
            raise AssertionError('Minimal-environment verifier failed: ' + error.stderr.decode(errors='replace')[:4000]) from error
    finally:
        os.environ.clear()
        os.environ.update(environment)


def exercise(path, bundle, ref, response):
    candidate = json.loads(path.read_text())
    baseline = {'format': 1, 'entries': candidate['entries'][:1]}
    recording = Path(response).read_bytes()
    attestations = listed(recording)
    assert attestations, 'The recorded API response lists no attestation for this record (the API answers 404 or an empty list while none is listed)'
    url = attestation_url(path)
    with tempfile.TemporaryDirectory(dir=path.parent) as directory:
        root = Path(directory)
        store = Store(root/'state', root/'evidence')
        qualification = Qualification(store, candidate['entries'][0]['build'], baseline)
        verifier = lambda subject: verify(subject, ref=ref, bundle=bundle)
        qualification.accept(path, verifier)
        assert qualification.record() == candidate
        print('QUALIFICATION DELIVERY newer valid attested record used PASS', flush=True)
        # The product's anonymous lookup, offline: its urlopen reaches only the
        # recorded response for exactly its own URL, then the real gh verify.
        _, handler = with_recording(url, recording, lambda: minimal_environment(lambda: verify(path, ref=ref)))
        assert [request.full_url for request in handler.requests] == [url]
        assert all('Authorization' not in request.headers for request in handler.requests)
        cache = path.parent/'qualification-verifier-cache'
        cache_bytes = sum(file.stat().st_size for file in cache.rglob('*') if file.is_file())
        assert cache_bytes <= VERIFIER_CACHE_RESERVE, 'Verifier cache exceeds admitted reserve'
        print(f'QUALIFICATION DELIVERY anonymous bundle lookup in launch-equivalent environment PASS; {len(attestations)} recorded attestation(s), cache {cache_bytes} bytes', flush=True)
        # Transport failures of the anonymous path refuse without a verdict.
        # The API answers 404 for a digest it lists nothing for; an empty
        # list is the same condition in another shape.
        for name, status, payload, expected in [
            ('empty attestation list', 200, b'{"attestations":[]}', Refused),
            ('nothing listed 404', 404, NOT_FOUND, urllib.error.HTTPError),
            ('rate limit 403', 403, b'{"message":"API rate limit exceeded"}', urllib.error.HTTPError),
            ('secondary rate limit 429', 429, b'{"message":"too many requests"}', urllib.error.HTTPError),
            ('server error 500', 500, b'', urllib.error.HTTPError)]:
            try:
                with_recording(url, payload, lambda: verify(path, ref=ref), status, {'Retry-After': '60'} if status == 429 else None)
            except expected as error:
                assert status == 200 or error.code == status
            else:
                raise AssertionError(name + ' was accepted')
            print('QUALIFICATION DELIVERY anonymous lookup ' + name + ' refused PASS', flush=True)
        try:
            with_recording(url, recording, lambda: urllib.request.urlopen('https://api.github.com/rate_limit', timeout=5))
        except urllib.error.URLError:
            print('QUALIFICATION DELIVERY recording opener refuses an unrecorded URL PASS', flush=True)
        else:
            raise AssertionError('The recording opener answered an unrecorded URL')
        original = path.read_bytes()
        altered = copy.deepcopy(json.loads(bundle.read_text()))
        signature = altered['dsseEnvelope']['signatures'][0]['sig']
        altered['dsseEnvelope']['signatures'][0]['sig'] = ('A' if signature[0] != 'A' else 'B') + signature[1:]
        broken = root/'altered-bundle.json'
        broken.write_text(json.dumps(altered))
        # The genuine bundle passed above with the right policy, so the wrong
        # workflow, branch and main cases fail on identity or source ref alone.
        cases = [
            ('missing attestation', lambda subject: verify(subject, ref=ref, bundle=root/'missing.json'), MISSING),
            ('altered attestation', lambda subject: verify(subject, ref=ref, bundle=broken), POLICY),
            ('wrong workflow', lambda subject: verify(subject, ref=ref, bundle=bundle, workflow='.github/workflows/untrusted-fixture.yml'), POLICY),
            ('wrong branch', lambda subject: verify(subject, branch='untrusted-fixture-branch', bundle=bundle), SOURCE_REF + 'refs/heads/untrusted-fixture-branch'),
        ]
        if ref != 'refs/heads/main':
            # The installed service's main policy must refuse a bundle attested
            # on this branch or pull request ref, however genuine.
            cases.append(('production main rejects a bundle attested on ' + ref, lambda subject: verify(subject, bundle=bundle), SOURCE_REF + 'refs/heads/main'))
        for name, check, reason in cases:
            try:
                refused(qualification, path, check, reason, candidate)
            except AssertionError as error:
                raise AssertionError(name + ': ' + str(error)) from error
            print('QUALIFICATION DELIVERY ' + name + ' refused (' + reason + '); held retained PASS', flush=True)
        try:
            altered_subject(qualification, path, verifier, candidate)
        except AssertionError as error:
            raise AssertionError('altered subject: ' + str(error)) from error
        print('QUALIFICATION DELIVERY altered subject refused (' + POLICY + '); held retained PASS', flush=True)
        rollback_cases(qualification, store, path, verifier, candidate)
        store.close()
        publisher_cases(root/'publication', original, baseline, candidate, verifier)


def rollback_cases(qualification, store, path, verifier, candidate):
    """Authentic signatures do not authorize rollback of local history: only the append-only refusal counts."""
    for name, held in [('dropped held entry', {'format': 1, 'entries': candidate['entries'] + [{**candidate['entries'][-1], 'version': '999.0.1.0'}]}),
                       ('changed held entry', copy.deepcopy(candidate))]:
        if name == 'changed held entry':
            held['entries'][-1]['core']['binding'] = not held['entries'][-1]['core']['binding']
        # Each starts from its own previously held record, then verifies the
        # genuine candidate. The append-only check must still refuse it.
        store.write({'chrome:qualification': held}, 'chrome_fixture', 'Synthetic held qualification history')
        try:
            refused(qualification, path, verifier, ROLLBACK, held)
        except AssertionError as error:
            raise AssertionError(name + ': ' + str(error)) from error
        print('QUALIFICATION DELIVERY ' + name + ' refused (' + ROLLBACK + ') after real verification PASS', flush=True)


def publisher_cases(publication, original, baseline, candidate, verifier):
    """The publisher verifies the genuine held record, then signs nothing forward, each case for its own reason.

    An inserted entry changes the signed bytes, so gh's named policy failure
    refuses it. The non-append-only baseline keeps the genuine bytes, which
    verify, so only the append-only check can refuse it.
    """
    subject = publication/qualify.RECORD
    subject.parent.mkdir(parents=True)
    subject.write_bytes(original)
    result = qualify.prepare(publication, [], baseline, verifier)
    assert result == candidate
    print('QUALIFICATION PUBLISHER real held attestation and baseline verified PASS', flush=True)
    inserted = {'format': 1, 'entries': candidate['entries'] + [{**candidate['entries'][-1], 'version': '999.0.1.0'}]}
    for name, contents, trusted_baseline, reason in [
        ('unsigned inserted entry', json.dumps(inserted).encode(), baseline, POLICY),
        ('non-append-only shipped baseline', original, {'format': 1, 'entries': [dict(candidate['entries'][0], run='changed-fixture-baseline')]}, ROLLBACK)
    ]:
        subject.write_bytes(contents)
        notifications = Mock(return_value=Mock(stdout='[]'))
        try:
            expected_refusal(lambda: qualify.prepare(publication, [], trusted_baseline, verifier), reason)
        except AssertionError as error:
            raise AssertionError(name + ': ' + str(error)) from error
        qualify.notify(None, False, notifications)
        assert subject.read_bytes() == contents
        # One open-issue lookup, then the refusal issue; never a pull request.
        assert [call.args[0][1:3] for call in notifications.call_args_list] == [['issue', 'list'], ['issue', 'create']]
        print('QUALIFICATION PUBLISHER ' + name + ' refused (' + reason + '); no write, issue stubbed PASS', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('record', type=Path)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('response', type=Path, help='the attestation API response recorded by gh api for this record')
    parser.add_argument('--ref', default=os.environ.get('GITHUB_REF'), help='the full ref the bundle was attested on')
    arguments = parser.parse_args()
    if not arguments.ref or not arguments.ref.startswith('refs/'):
        raise SystemExit('--ref (or GITHUB_REF) must be a full ref such as refs/heads/main or refs/pull/N/merge')
    exercise(arguments.record, arguments.bundle, arguments.ref, arguments.response)
