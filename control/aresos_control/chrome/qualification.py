"""Signed, append-only qualification and per-build/per-major switches."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.request

from ..common import Refused, canonical
from .policy import CORE_GROUPS, HOSTS

REPOSITORY = 'Ares-Empire/AresOS'
WORKFLOW = '.github/workflows/control-chrome.yml'
NOTICE = "This Chrome version is not qualified for this installed tool build; adapters and don't-ask-again are off and activating inputs ask."


def version(text):
    if not isinstance(text, str) or not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', text):
        raise Refused('invalid_input', 'Chrome must report its full four-part version.')
    return tuple(int(part) for part in text.split('.'))


def validate_record(record):
    if type(record) is not dict or set(record) != {'format', 'entries'} or record['format'] != 1 or type(record['entries']) is not list:
        raise Refused('qualification_invalid', 'Invalid Chrome qualification record; held record retained.')
    keys = set()
    for entry in record['entries']:
        if set(entry) != {'build', 'version', 'channel', 'run', 'core', 'adapters'}:
            raise Refused('qualification_invalid', 'Invalid qualification entry.')
        version(entry['version'])
        if (not re.fullmatch(r'[0-9a-f]{64}', entry['build']) or entry['channel'] not in {'stable', 'beta'} or
                type(entry['run']) is not str or not entry['run'] or
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
    # A beta qualification is evidence for its major before the first stable.
    if not applicable:
        applicable = [entry for entry in entries if entry['channel'] == 'beta']
    if not applicable:
        return {'conservative': True, 'notice': NOTICE, 'core': {key: True for key in CORE_GROUPS}, 'adapters': {key: False for key in HOSTS}}
    chosen = max(applicable, key=lambda item: (version(item['version']), item['channel'] == 'stable'))
    return {'conservative': False, 'notice': '', 'core': chosen['core'], 'adapters': chosen['adapters']}


def verify(path, *, branch='main', bundle=None):
    # Require the fixed gh verifier's security corrections; no hand-written crypto.
    output = subprocess.run(['gh', '--version'], check=True, capture_output=True, text=True, timeout=10).stdout
    match = re.search(r'gh version (\d+)\.(\d+)\.(\d+)', output)
    if not match or tuple(map(int, match.groups())) < (2, 102, 0):
        raise Refused('qualification_invalid', 'Qualification verification requires GitHub CLI 2.102.0 or newer.')
    command = ['gh', 'attestation', 'verify', str(path), '--repo', REPOSITORY,
               '--signer-workflow', REPOSITORY + '/' + WORKFLOW,
               '--source-ref', 'refs/heads/' + branch, '--deny-self-hosted-runners']
    if bundle:
        command += ['--bundle', str(bundle)]
    subprocess.run(command, check=True, capture_output=True, timeout=30)


class Qualification:
    def __init__(self, store, build, shipped):
        self.store, self.build, self.shipped = store, build, validate_record(shipped)

    def record(self):
        return append_only(self.shipped, self.store.get('chrome:qualification', self.shipped))

    def accept(self, path, verifier=verify):
        verifier(path)
        candidate = append_only(self.record(), json.loads(Path(path).read_text()))
        self.store.write({'chrome:qualification': candidate}, 'chrome_qualification', 'Verified append-only Chrome qualification update')
        return candidate

    def refresh(self, *, now=None, verifier=verify):
        now = time.time() if now is None else now
        previous = self.store.get('chrome:qualification_fetch', {})
        if now - previous.get('time', 0) < 86400:
            return
        url = f'https://raw.githubusercontent.com/{REPOSITORY}/refs/heads/chrome-qualification/control/chrome/qualification.json'
        try:
            with urllib.request.urlopen(url, timeout=10) as stream:
                data = stream.read(4 * 1024 * 1024 + 1)
            if len(data) > 4 * 1024 * 1024:
                raise ValueError('Qualification exceeds delivery bound')
            with tempfile.NamedTemporaryFile(dir=self.store.state_dir, suffix='.json') as temporary:
                temporary.write(data)
                temporary.flush()
                self.accept(temporary.name, verifier)
            result = 'Verified record accepted.'
        except Exception:
            result = 'Qualification refresh unavailable or verification failed; held record retained.'
        self.store.write({'chrome:qualification_fetch': {'time': now, 'result': result}}, 'chrome_qualification', result)
