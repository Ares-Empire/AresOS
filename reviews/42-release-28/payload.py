"""Package 42: release 28's record (step 5) and, after the rehearsal, the payload commit's files.

Usage:
  python3 -B reviews/42-release-28/payload.py record <evidence/release.json> <run id> <owner review line>
  python3 -B reviews/42-release-28/payload.py announce

record (step 5, right after the publish) writes only os/manifest/releases/28.json: the evidence's record, which
release28_record.py completed in the job, plus daily_wheel true and the owner's review line. The rehearsal (step 6)
reads it and generates its stand-in announced commit from it (the lead's decision 2 of 2026-11-17, PROGRESS.md).

announce (after the rehearsal passed) writes, from the committed record's bytes, exactly the files of
os/ci/release28_walk.announced(): both history.json copies (release 28's row, tools_version 5), the payload's
release.json, SHA256.json and SHA256SUMS, commands.json, os/manifest/release.json and lines 1 and 3 of
docs/OWNER-TOOLS.md. announced() is the reference (the real payload commit must be byte-identical to the walk's
stand-in), so nothing here is computed a second way; `bundle.py --refresh` must then change nothing. The guides,
INSTALL-STATUS and the tests that pin release 27 or version 4 move in the same pin step (PROGRESS.md lists them).
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import release28_walk  # noqa: E402

RECORD = 'os/manifest/releases/28.json'


def record_of(evidence, run, review):
    release = json.loads(pathlib.Path(evidence).read_text())
    assert re.fullmatch(r'ghcr\.io/ares-empire/aresos@sha256:[0-9a-f]{64}', release['reference']), 'not an org digest'
    assert release['signature'] == dict(method='cosign keyless', identity=release28_walk.IDENTITY,
                                        issuer='https://token.actions.githubusercontent.com'), 'signature identity differs'
    assert release['visibility'] == 'private', 'not private'
    assert release['run'] == 'https://github.com/Ares-Empire/AresOS/actions/runs/' + run, 'run differs'
    assert release['tag'] == '28-' + release['source_commit'], 'tag differs from the source commit'
    assert release['image_diff']['status'] == 'passed' and not release['image_diff']['unexplained'], 'image diff not passed'
    assert release['job_token_read']['status'] == 'passed' and not release['job_token_read']['owner_token_used']
    assert release['control'] == dict(source_revision=release['source_commit']), 'Control revision differs'
    assert 'daily_wheel' not in release and 'owner_review' not in release
    for row in release['source_trees']:
        tree = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD:' + row['path']], text=True).strip()
        assert tree == row['tree'], 'image source changed since the publish: ' + row['path']
    assert review.strip() == review and review, 'owner review line'
    return (json.dumps(dict(release, daily_wheel=True, owner_review=review), indent=2) + '\n').encode()


def record(evidence, run, review):
    data = record_of(evidence, run, review)
    assert not (ROOT / RECORD).exists(), RECORD + ' exists already'
    (ROOT / RECORD).write_bytes(data)
    print('PASS release 28 record ' + json.loads(data)['reference'])


def announce():
    data = (ROOT / RECORD).read_bytes()
    committed = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:' + RECORD])
    assert data == committed, RECORD + ' differs from the committed record'
    result = release28_walk.announced(data, source=str(ROOT))
    for path, content in sorted(result['files'].items()):
        (ROOT / path).write_bytes(content)
    output = subprocess.check_output([sys.executable, '-B', str(ROOT / 'os/owner-tools/bundle.py'), '--refresh'],
                                     cwd=ROOT, text=True)
    assert output == 'PASS bundle manifest SHA256 ' + result['fingerprint'] + '\n', output
    changed = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=all'],
                                      text=True).split('\n')
    paths = sorted(line[3:] for line in changed if line)
    assert paths == sorted(result['files']), 'changed paths differ from the announced files: ' + repr(paths)
    print('PASS announced files written; tools version ' + str(result['version']) + ' fingerprint ' + result['fingerprint'])


if __name__ == '__main__':
    if sys.argv[1:2] == ['record'] and len(sys.argv) == 5:
        record(*sys.argv[2:])
    elif sys.argv[1:] == ['announce']:
        announce()
    else:
        sys.exit(__doc__)
