"""Run package 27's zero-cost host walks and bind them to their sources.

Both local walks (package 14's qualification and package 27's update route)
drive the real owner_vm control flow with synthetic guest answers. No VM,
privilege, hardware query or token is used; this is a prerequisite for the
hosted rehearsal (owner_vm.main refuses a stale walk), never VM evidence.
Run on Linux: python3 reviews/27-first-update-release/walk-host.py
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/tests'))
import test_owner_walk


def main():
    qualification = test_owner_walk.walk()
    update = test_owner_walk.walk(route='update')
    previous = json.loads((ROOT / 'os/manifest/ci/16/host-walk.json').read_text())
    paths = {row['path'] for row in previous['sources']}
    # Read by the update walk and its harness in addition to package 16's set.
    paths.update({'os/ci/polkit-review.json', 'os/manifest/release.json', 'os/manifest/releases/13.json', 'os/owner-tools/history.json',
                  'os/owner-tools/payload/history.json', 'os/tests/owner_console_shim.py',
                  'reviews/27-first-update-release/walk-host.py'})
    sources = [dict(sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), path=path) for path in sorted(paths)]
    result = dict(status='passed', kind='local synthetic owner host walks (qualification and update route); not VM or physical qualification',
        stick_across_reboot=False,
        stages=dict(qualification=qualification['stages'], update=update['stages']),
        checks=dict(qualification=len(qualification['checks']), update=len(update['checks'])),
        markers=dict(qualification=qualification['markers'], update=update['markers']),
        command_count=dict(qualification=len(qualification['commands']), update=len(update['commands'])),
        typed_count=dict(qualification=len(qualification['typed']), update=len(update['typed'])),
        sources=sources)
    folder = ROOT / 'os/manifest/ci/27'
    folder.mkdir(exist_ok=True)
    with open(folder / 'host-walk.json', 'w', newline='\n', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(f'PASS package 27 host walks: {len(sources)} sources; no VM started')


if __name__ == '__main__':
    main()
