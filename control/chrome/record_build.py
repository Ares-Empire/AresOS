"""Record shipped Chrome builds in builds.json, and check the release manifests against it.

    python3 control/chrome/record_build.py add --commit <40 hex> --shipped-at <YYYY-MM-DDTHH:MM:SSZ> [--expect <64 hex>]
    python3 control/chrome/record_build.py check

`add` hashes the commit's control/ with that commit's own build.py (git archive into a
temporary folder, never the working tree), adds the row and keeps the newest three by
shipped_at, as qualify.py's planner reads them. `check` requires os/manifest/release.json's
`control` object to have its row, and a row for any manifest under os/manifest/releases/ to
be equal. Brief 18c-b, item 4. This file is not one of build.py's inputs.
"""
import argparse
from datetime import datetime
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = 'control/chrome/builds.json'
RELEASE = 'os/manifest/release.json'
RELEASES = 'os/manifest/releases'
RELEASE_28_SOURCE = '7d5fbbf2c7f7c5b4d41dd707a9407e6401a4d062'
KEEP = 3
COMMIT = re.compile(r'[0-9a-f]{40}')
BUILD = re.compile(r'[0-9a-f]{64}')
SHIPPED_AT = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z')


class Refused(Exception):
    pass


def shipped_time(value):
    if type(value) is not str or not SHIPPED_AT.fullmatch(value):
        raise Refused('shipped_at must be a UTC time like 2026-11-15T12:00:00Z: ' + repr(value))
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        raise Refused('shipped_at is not a real time: ' + value) from None


def validate(registry):
    """The planner's rules (qualify.plan) plus unique commits and the strict Z time this tool writes."""
    if type(registry) is not dict or set(registry) != {'format', 'builds'} or type(registry['format']) is not int \
            or registry['format'] != 1 or type(registry['builds']) is not list:
        raise Refused('builds.json is not {"format":1,"builds":[...]}')
    commits, builds = set(), set()
    for row in registry['builds']:
        if type(row) is not dict or set(row) != {'commit', 'build', 'shipped_at'}:
            raise Refused('a builds.json row needs exactly commit, build and shipped_at: ' + json.dumps(row))
        if type(row['commit']) is not str or not COMMIT.fullmatch(row['commit']) \
                or type(row['build']) is not str or not BUILD.fullmatch(row['build']):
            raise Refused('a builds.json row needs a 40-hex commit and a 64-hex build: ' + json.dumps(row))
        shipped_time(row['shipped_at'])
        if row['commit'] in commits or row['build'] in builds:
            raise Refused('builds.json names a commit or a build twice: ' + json.dumps(row))
        commits.add(row['commit'])
        builds.add(row['build'])
    return registry


def load(path):
    try:
        text = Path(path).read_text(encoding='utf-8')
    except OSError as error:
        raise Refused('cannot read ' + str(path) + ': ' + error.strerror) from None
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise Refused(str(path) + ' is not JSON: ' + str(error)) from None


def newest(rows):
    return sorted(rows, key=lambda row: (shipped_time(row['shipped_at']), row['commit']), reverse=True)


def render(registry):
    # One row per line, so the pull request that pins a release shows its row as one added line.
    order = ['commit', 'build', 'shipped_at']
    rows = [json.dumps({key: row[key] for key in order}, separators=(',', ':')) for row in registry['builds']]
    if not rows:
        return '{"format":1,"builds":[]}\n'
    return '{"format":1,"builds":[\n' + ',\n'.join(rows) + '\n]}\n'


def write(path, registry):
    path = Path(path)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, prefix='.builds-', delete=False) as handle:
        handle.write(render(registry))
    try:
        os.chmod(handle.name, mode)
        os.replace(handle.name, path)
    except BaseException:
        os.unlink(handle.name)
        raise


def git(repo, *args):
    done = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, timeout=300)
    if done.returncode != 0:
        raise Refused('git ' + ' '.join(args[:2]) + ' failed: ' + done.stderr.decode(errors='replace').strip())
    return done.stdout


def commit_hash(repo, commit):
    """build.py's output for that commit, computed by that commit's own build.py over its archived control/."""
    if type(commit) is not str or not COMMIT.fullmatch(commit):
        raise Refused('--commit must be a full 40-hex commit: ' + repr(commit))
    try:
        resolved = git(repo, 'rev-parse', '--verify', '--quiet', commit + '^{commit}').decode().strip()
    except Refused:
        resolved = None
    if resolved != commit:
        raise Refused('not a commit of this repository: ' + commit)
    # build.py hashes only paths under control/ (ROOT/control); the whole tree is about a gigabyte.
    archive = git(repo, 'archive', '--format=tar', commit, '--', 'control')
    with tempfile.TemporaryDirectory(prefix='aresos-record-build-') as folder:
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(folder, filter='data')
        script = Path(folder) / 'control/chrome/build.py'
        if not script.is_file():
            raise Refused('commit ' + commit + ' has no control/chrome/build.py')
        done = subprocess.run([sys.executable, '-I', '-B', str(script)], cwd=folder, capture_output=True, timeout=300)
    output = done.stdout.decode(errors='replace').strip()
    if done.returncode != 0 or not BUILD.fullmatch(output):
        raise Refused('build.py of ' + commit + ' failed: ' + (done.stderr.decode(errors='replace').strip() or output))
    return output


def add(commit, shipped_at, expect=None, registry_path=None, repo=ROOT):
    registry_path = Path(registry_path or Path(repo) / REGISTRY)
    candidate_time = shipped_time(shipped_at)
    if expect is not None and not BUILD.fullmatch(expect):
        raise Refused('--expect must be a 64-hex build hash: ' + repr(expect))
    registry = validate(load(registry_path))
    build = commit_hash(repo, commit)
    if expect is not None and build != expect:
        raise Refused(f'commit {commit} hashes to {build}, not the expected {expect}')
    row = {'commit': commit, 'build': build, 'shipped_at': shipped_at}
    for held in registry['builds']:
        if held['commit'] == commit:
            if held['build'] != build:
                raise Refused(f'builds.json records {commit} as {held["build"]}, but it hashes to {build}')
            return held, 'already recorded; builds.json unchanged'
    # The planner refuses a build named twice. Only a more recent shipment with
    # the same runtime inputs may take over the row for that build.
    rows = registry['builds']
    previous = next((held for held in rows if held['build'] == build), None)
    if previous is not None and shipped_time(previous['shipped_at']) >= candidate_time:
        return previous, 'same build already has an equally recent or newer shipment; builds.json unchanged'
    kept = newest([held for held in rows if held is not previous] + [row])[:KEEP]
    if row not in kept:
        raise Refused(f'{shipped_at} is older than the {KEEP} newest recorded builds; it would be pruned at once')
    write(registry_path, {'format': 1, 'builds': kept})
    return row, 'recorded' + (', replacing the row of an earlier commit with the same build' if previous else '')


def check(root=ROOT):
    """Return (failures, notes) for the release manifests against builds.json."""
    root = Path(root)
    failures, notes = [], []
    try:
        rows = {row['commit']: row for row in validate(load(root / REGISTRY))['builds']}
    except Refused as error:
        return [str(error)], notes
    manifests = [root / RELEASE] + sorted((root / RELEASES).rglob('*.json'))
    for path in manifests:
        name = str(path.relative_to(root))
        try:
            manifest = load(path)
        except Refused as error:
            failures.append(str(error))
            continue
        if type(manifest) is not dict:
            failures.append(name + ': not a JSON object')
            continue
        if 'control' not in manifest:
            notes.append(name + ': no control object; nothing to check')
            continue
        control = manifest['control']
        # Release 28 shipped the Control service before the browser integration.
        if (name in (RELEASE, f'{RELEASES}/28.json')
                and manifest.get('tag') == f'28-{RELEASE_28_SOURCE}'
                and manifest.get('source_commit') == RELEASE_28_SOURCE
                and control == {'source_revision': RELEASE_28_SOURCE}):
            notes.append(name + ': release 28 predates Chrome build records')
            continue
        if type(control) is not dict or set(control) != {'source_revision', 'chrome_build'} \
                or type(control['source_revision']) is not str or not COMMIT.fullmatch(control['source_revision']) \
                or type(control['chrome_build']) is not str or not BUILD.fullmatch(control['chrome_build']):
            failures.append(name + ': control must be exactly {"source_revision": <40 hex>, "chrome_build": <64 hex>}')
            continue
        commit, build = control['source_revision'], control['chrome_build']
        if manifest.get('source_commit') != commit:
            failures.append(f'{name}: control.source_revision {commit} is not the manifest\'s source_commit '
                            f'{manifest.get("source_commit")!r}')
            continue
        row = rows.get(commit)
        if row is None:
            if path == root / RELEASE:
                failures.append(f'{name}: builds.json has no row for {commit}; run record_build.py add')
            else:
                notes.append(f'{name}: no row for {commit} (only the newest {KEEP} are kept)')
        elif row['build'] != build:
            failures.append(f'{name}: chrome_build {build} but builds.json records {commit} as {row["build"]}')
        else:
            notes.append(f'{name}: {commit} {build} matches builds.json')
    return failures, notes


def main(argv=None):
    parser = argparse.ArgumentParser(description='Record shipped Chrome builds and check release manifests.')
    commands = parser.add_subparsers(dest='command', required=True)
    adding = commands.add_parser('add', help='record a shipped commit in builds.json')
    adding.add_argument('--commit', required=True)
    adding.add_argument('--shipped-at', required=True)
    adding.add_argument('--expect')
    adding.add_argument('--registry', help='builds.json to change (default: the repository\'s)')
    adding.add_argument('--repo', default=str(ROOT), help='git repository holding the commit')
    checking = commands.add_parser('check', help='check the release manifests against builds.json')
    checking.add_argument('--root', default=str(ROOT), help='checkout to read')
    args = parser.parse_args(argv)
    if args.command == 'add':
        try:
            row, outcome = add(args.commit, args.shipped_at, args.expect, args.registry, args.repo)
        except Refused as error:
            print('record_build: refused: ' + str(error), file=sys.stderr)
            return 1
        print(json.dumps(row, separators=(',', ':')))
        print('record_build: ' + outcome)
        return 0
    failures, notes = check(args.root)
    for note in notes:
        print('info: ' + note)
    for failure in failures:
        print('FAIL: ' + failure)
    if failures:
        return 1
    print('record_build check passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
