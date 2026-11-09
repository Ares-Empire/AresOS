"""Signed, append-only qualification and per-build/per-major switches."""
import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.request

from ..common import Refused, canonical, cleanup, storage_stream
from .policy import CORE_GROUPS, HOSTS

REPOSITORY = 'Ares-Empire/AresOS'
WORKFLOW = '.github/workflows/control-chrome-qualification.yml'
NOTICE = "This Chrome version is not qualified for this installed tool build; adapters and don't-ask-again are off and activating inputs ask."
DELIVERY_LIMIT = 4*1024*1024
VERIFIER_CACHE_RESERVE = 8*1024*1024


def version(text):
    if not isinstance(text, str) or not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', text):
        raise Refused('invalid_input', 'Chrome must report its full four-part version.')
    return tuple(int(part) for part in text.split('.'))


def validate_record(record):
    if type(record) is not dict or set(record) != {'format', 'entries'} or type(record['format']) is not int or record['format'] != 1 or type(record['entries']) is not list:
        raise Refused('qualification_invalid', 'Invalid Chrome qualification record; held record retained.')
    keys = set()
    for entry in record['entries']:
        if type(entry) is not dict or set(entry) != {'build', 'version', 'channel', 'run', 'core', 'adapters'}:
            raise Refused('qualification_invalid', 'Invalid qualification entry.')
        version(entry['version'])
        if (type(entry['build']) is not str or not re.fullmatch(r'[0-9a-f]{64}', entry['build']) or
                type(entry['channel']) is not str or entry['channel'] not in {'stable', 'beta'} or
                type(entry['run']) is not str or not entry['run'] or
                type(entry['core']) is not dict or type(entry['adapters']) is not dict or
                set(entry['core']) != set(CORE_GROUPS) or set(entry['adapters']) != set(HOSTS) or
                any(type(value) is not bool for value in [*entry['core'].values(), *entry['adapters'].values()])):
            raise Refused('qualification_invalid', 'Incomplete qualification result.')
        key = entry['build'], entry['version'], entry['channel']
        if key in keys:
            raise Refused('qualification_invalid', 'Repeated qualification key.')
        keys.add(key)
    return record


def append_only(held, candidate):
    validate_record(held)
    validate_record(candidate)
    # Order and complete entry bytes are immutable too.
    if candidate['entries'][:len(held['entries'])] != held['entries']:
        raise Refused('qualification_rollback', 'Fetched qualification changed or removed held history; held record retained.')
    return candidate


def switches(record, build, chrome_version):
    current = version(chrome_version)
    entries = [entry for entry in validate_record(record)['entries'] if entry['build'] == build and version(entry['version'])[0] == current[0]]
    if not entries:
        return {'conservative': True, 'notice': NOTICE, 'core': {key: True for key in CORE_GROUPS}, 'adapters': {key: False for key in HOSTS}}
    applicable = [entry for entry in entries if version(entry['version']) <= current]
    # Advance beta evidence covers the first stable of a major even if its full
    # version is lower. A recorded major never re-enters conservative mode.
    evidence = applicable or [entry for entry in entries if entry['channel'] == 'beta'] or entries

    def passed(category, key):
        for index, failed in enumerate(evidence):
            if failed[category][key]:
                continue
            # Both publication order and patch order matter: an earlier beta
            # pass cannot undo a subsequently discovered stable failure, and a
            # newer beta failure cannot be hidden by an older stable pass.
            if not any(later[category][key] and version(later['version']) > version(failed['version'])
                       for later in evidence[index + 1:]):
                return False
        return True

    return {'conservative': False, 'notice': '',
            'core': {key: passed('core', key) for key in CORE_GROUPS},
            'adapters': {key: passed('adapters', key) for key in HOSTS}}


def verify(path, *, branch='main', bundle=None, workflow=WORKFLOW):
    # Require the fixed gh verifier's security corrections; no hand-written crypto.
    output = subprocess.run(['gh', '--version'], check=True, capture_output=True, text=True, timeout=10).stdout
    match = re.search(r'gh version (\d+)\.(\d+)\.(\d+)', output)
    if not match or tuple(map(int, match.groups())) < (2, 102, 0):
        raise Refused('qualification_invalid', 'Qualification verification requires GitHub CLI 2.102.0 or newer.')
    command = ['gh', 'attestation', 'verify', str(path), '--repo', REPOSITORY,
               '--signer-workflow', REPOSITORY + '/' + workflow,
               '--source-ref', 'refs/heads/' + branch, '--deny-self-hosted-runners']
    cache = Path(path).resolve().parent/'qualification-verifier-cache'
    environment = {**os.environ, 'XDG_CACHE_HOME': str(cache), 'XDG_CONFIG_HOME': str(cache/'config')}
    if bundle is not None:
        subprocess.run([*command, '--bundle', str(bundle)], check=True, capture_output=True, timeout=30, env=environment)
        return
    # Public repository delivery must work without the owner's GitHub login.
    # Fetch untrusted bundles anonymously, then let gh verify their signatures
    # and identity offline. An API response is never itself trusted evidence.
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    request = urllib.request.Request(f'https://api.github.com/repos/{REPOSITORY}/attestations/sha256:{digest}?per_page=100',
                                     headers={'Accept':'application/vnd.github+json', 'X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(request, timeout=10) as response:
        data = response.read(DELIVERY_LIMIT+1)
    if len(data) > DELIVERY_LIMIT:
        raise Refused('qualification_invalid', 'Qualification attestation exceeds the delivery bound.')
    attestations = json.loads(data).get('attestations')
    if not isinstance(attestations, list) or not attestations:
        raise Refused('qualification_invalid', 'Qualification attestation is missing; held record retained.')
    serialized = ''.join(json.dumps(attestation['bundle'], ensure_ascii=False, separators=(',',':'))+'\n'
                         for attestation in attestations).encode('utf-8')
    if len(serialized) > DELIVERY_LIMIT:
        raise Refused('qualification_invalid', 'Serialized qualification attestations exceed the delivery bound.')
    with storage_stream(tempfile.NamedTemporaryFile(dir=Path(path).parent, prefix='.qualification-bundle-', suffix='.jsonl', mode='wb')) as temporary:
        temporary.write(serialized)
        temporary.flush()
        subprocess.run([*command, '--bundle', temporary.name], check=True, capture_output=True, timeout=30, env=environment)


class Qualification:
    def __init__(self, store, build, shipped):
        self.store, self.build, self.shipped = store, build, validate_record(shipped)

    def record(self):
        held = validate_record(self.store.get('chrome:qualification', self.shipped))
        # Image updates can advance the trusted shipped baseline beyond a
        # previously fetched record. Neither trusted history may be rewritten.
        if len(held['entries']) <= len(self.shipped['entries']):
            return append_only(held, self.shipped)
        return append_only(self.shipped, held)

    def accept(self, path, verifier=verify):
        verifier(path)
        candidate = append_only(self.record(), json.loads(Path(path).read_text()))
        self.store.write({'chrome:qualification': candidate}, 'chrome_qualification', 'Verified append-only Chrome qualification update')
        return candidate

    def refresh(self, *, now=None, verifier=verify, force=False):
        now = time.time() if now is None else now
        previous = self.store.get('chrome:qualification_fetch', {})
        if not force and 'time' in previous and now - previous['time'] < 86400:
            return
        url = f'https://raw.githubusercontent.com/{REPOSITORY}/refs/heads/chrome-qualification/control/chrome/qualification.json'
        try:
            for obsolete in self.store.state_dir.glob('.qualification-*'):
                obsolete.unlink()
            with urllib.request.urlopen(url, timeout=10) as stream:
                data = stream.read(DELIVERY_LIMIT + 1)
            if len(data) > DELIVERY_LIMIT:
                raise ValueError('Qualification exceeds delivery bound')
            self.store.ledger.admit(len(data)+DELIVERY_LIMIT+VERIFIER_CACHE_RESERVE+8192)
            fd,temporary=tempfile.mkstemp(dir=self.store.state_dir,prefix='.qualification-',suffix='.json')
            try:
                with storage_stream(os.fdopen(fd,'wb')) as stream:
                    stream.write(data);stream.flush()
                self.accept(temporary,verifier)
            finally:
                with cleanup('Qualification temporary unlink'):
                    os.unlink(temporary)
            result = 'Verified record accepted.'
        except Exception as exc:
            # Do not copy transport output or remote content into owner logs.
            reason = exc.code if isinstance(exc, Refused) else type(exc).__name__
            result = f'Qualification refresh refused ({reason}); held record retained.'
        self.store.write({'chrome:qualification_fetch': {'time': now, 'result': result}}, 'chrome_qualification', result)
