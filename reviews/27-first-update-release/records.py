"""Package 27: write the release records from the publish run's evidence.

Usage: python reviews/27-first-update-release/records.py <evidence/release.json> <run id>

Writes os/manifest/releases/27.json and os/manifest/release.json (the tools
bundle carries release.json, and package 22's rule makes the bundle's newest
history record equal it), appends the release to os/owner-tools/history.json
with daily_wheel true, regenerates the payload and pins its fingerprint in
every owner page, commands.json and the guide's step 6 digest.
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
IDENTITY = 'https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/27-first-update-release'


def write(path, text):
    with open(ROOT / path, 'w', newline='\n', encoding='utf-8') as stream:
        stream.write(text)


def main():
    evidence, run = sys.argv[1], sys.argv[2]
    release = json.loads(pathlib.Path(evidence).read_text())
    assert re.fullmatch(r'ghcr\.io/ares-empire/aresos@sha256:[0-9a-f]{64}', release['reference'])
    assert release['signature'] == dict(method='cosign keyless', identity=IDENTITY, issuer='https://token.actions.githubusercontent.com')
    assert release['visibility'] == 'private' and release['run'].endswith('/actions/runs/' + run)
    assert release['image_diff']['status'] == 'passed' and release['job_token_read']['status'] == 'passed'
    paths = ['os/Containerfile', 'os/.containerignore', 'os/build.sh', 'os/packages.lock.json', 'os/google-chrome.lock.json',
             'os/config', 'os/policy', 'os/manifest/base.json', 'os/keys', 'os/tests/audit.py']
    trees = {path: subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', release['source_commit'] + ':' + path],
                                           text=True).strip() for path in paths}
    record = dict(release, source_trees=trees, daily_wheel=True, rehearsal='pending',
                  owner_review='owner OK 2026-11-09 to publish and pin once the rehearsal passes')
    text = json.dumps(record, indent=2) + '\n'
    write('os/manifest/releases/27.json', text)
    write('os/manifest/release.json', text)

    history = json.loads((ROOT / 'os/owner-tools/history.json').read_text())
    # A rerun replaces this package's own record (a placeholder or an earlier candidate).
    rows = [r for r in history['releases'] if r['identity'] != IDENTITY]
    rows.append(dict(reference=release['reference'], identity=IDENTITY, daily_wheel=True))
    history['releases'] = rows
    write('os/owner-tools/history.json', json.dumps(history, indent=2) + '\n')

    old = re.search(r'PASS tools manifest SHA256 ([0-9a-f]{64})', (ROOT / 'docs/INSTALL.md').read_text())[1]
    output = subprocess.check_output([sys.executable, str(ROOT / 'os/owner-tools/bundle.py'), '--refresh'], text=True)
    new = re.fullmatch(r'PASS bundle manifest SHA256 ([0-9a-f]{64})\n', output)[1]
    previous = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:os/manifest/release.json']))['reference']
    for path in ('docs/INSTALL.md', 'docs/INSTALL-STATUS.md', 'os/owner-tools/commands.json',
                 'reviews/27-first-update-release/REPORT.md'):
        text = (ROOT / path).read_text(encoding='utf-8')
        if old != new:
            text = text.replace(old, new)
        release13 = json.loads((ROOT / 'os/manifest/releases/13.json').read_text())['reference']
        if path == 'docs/INSTALL.md' and previous != release['reference']:
            # Step 6's exact release/signature line: a fresh install switches to this release.
            text = text.replace('`' + previous + '`.', '`' + release['reference'] + '`.')
        elif previous not in (release['reference'], release13):
            # Rerun over a placeholder or earlier candidate of this release.
            text = text.replace(previous, release['reference'])
        write(path, text)
    print('records written; tools manifest SHA256 ' + new)


if __name__ == '__main__':
    main()
