"""Run package 22d's zero-cost host walk and bind it to its sources.

The rehearsal's route (briefs/22d-tools-without-stick.md, "The walk"): package 27's route up to
release 27 with tools version 2, then the owner tools from the desktop's password window
(os/ci/tools_local.py). The walk drives the real owner_vm and tools_local control flow with
synthetic guest answers. No VM, privilege, hardware query or token is used; this is a
prerequisite for the hosted run (owner_vm.main refuses a stale walk), never VM evidence.
Package 22c's receipt stays frozen (its record step ran); this one is 22d's own (review 1).

Run on Linux, from the repository root, after the last change to a file it binds:
python3 reviews/22d-tools-without-stick/walk-host.py
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/tests'))
import test_owner_walk

# Read by this package's walk and harness in addition to package 22c's set.
ADDED = {'os/ci/tools_local.py', 'os/tests/test_tools_local_wiring.py', 'reviews/22d-tools-without-stick/walk-host.py'}
ROUTES = ('tools-local',)


def main():
    walks = {route: test_owner_walk.walk(route=route) for route in ROUTES}
    previous = json.loads((ROOT / 'os/manifest/ci/22c/host-walk.json').read_text())
    inherited = {row['path'] for row in previous['sources']}
    # A file package 22c bound that no longer exists is named, never silently dropped.
    gone = sorted(path for path in inherited if not (ROOT / path).is_file())
    paths = (inherited - set(gone)) | ADDED
    sources = [dict(sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), path=path) for path in sorted(paths)]
    result = dict(status='passed',
        kind="local synthetic owner host walk (package 22d's route); not VM or physical qualification",
        stick_across_reboot=False,
        stages={route: walk['stages'] for route, walk in walks.items()},
        checks={route: len(walk['checks']) for route, walk in walks.items()},
        markers={route: walk['markers'] for route, walk in walks.items()},
        command_count={route: len(walk['commands']) for route, walk in walks.items()},
        typed_count={route: len(walk['typed']) for route, walk in walks.items()},
        inherited_from='os/manifest/ci/22c/host-walk.json', no_longer_bound=gone,
        sources=sources)
    folder = ROOT / 'os/manifest/ci/22d'
    folder.mkdir(exist_ok=True)
    with open(folder / 'host-walk.json', 'w', newline='\n', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(f'PASS package 22d host walk ({", ".join(ROUTES)}): {len(sources)} sources; no VM started')


if __name__ == '__main__':
    main()
