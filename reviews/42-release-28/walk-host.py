"""Run package 42's zero-cost host walk and bind it to its sources.

The rehearsal's route (briefs/42-release-28.md, B; os/ci/release28_walk.py): package 27's route up to release 27
with tools version 2, tools version 4 and then the announced tools (version 5) from the desktop's password window,
the console's update to release 28, previous and forward. The walk drives the real owner_vm, tools_local and
release28_walk control flow with synthetic guest answers and a stand-in record for release 28. No VM, privilege,
hardware query or token is used; this is a prerequisite for the hosted run (owner_vm.main refuses a stale walk),
never VM evidence. Package 22d's receipt stays as its own; this one is package 42's.

Run on Linux, from the repository root, after the last change to a file it binds:
python3 reviews/42-release-28/walk-host.py
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/tests'))
import test_owner_walk
import release28_walk

# Read by this package's walk and harness in addition to package 22d's set.
ADDED = {'os/ci/control/release_checks.py', 'os/ci/release28_walk.py', 'os/tests/test_release28_rehearsal.py', 'reviews/42-release-28/walk-host.py',
         'os/manifest/releases/27.json', 'os/config/usr/libexec/aresos-desktop'}
ROUTES = ('release-28',)


def main():
    walks = {route: test_owner_walk.walk(route=route, control=release28_walk.CONTROL_RIDES) for route in ROUTES}
    previous = json.loads((ROOT / 'os/manifest/ci/22d/host-walk.json').read_text())
    inherited = {row['path'] for row in previous['sources']}
    # A file package 22d bound that no longer exists is named, never silently dropped.
    gone = sorted(path for path in inherited if not (ROOT / path).is_file())
    paths = (inherited - set(gone)) | ADDED
    sources = [dict(sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), path=path) for path in sorted(paths)]
    result = dict(status='passed', control_rides=release28_walk.CONTROL_RIDES,
        kind="local synthetic owner host walk (package 42's route); not VM or physical qualification",
        stick_across_reboot=False,
        stages={route: walk['stages'] for route, walk in walks.items()},
        checks={route: len(walk['checks']) for route, walk in walks.items()},
        markers={route: walk['markers'] for route, walk in walks.items()},
        command_count={route: len(walk['commands']) for route, walk in walks.items()},
        typed_count={route: len(walk['typed']) for route, walk in walks.items()},
        inherited_from='os/manifest/ci/22d/host-walk.json', no_longer_bound=gone,
        sources=sources)
    folder = ROOT / 'os/manifest/ci/42'
    folder.mkdir(exist_ok=True)
    with open(folder / 'host-walk.json', 'w', newline='\n', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(f'PASS package 42 host walk ({", ".join(ROUTES)}): {len(sources)} sources; no VM started')


if __name__ == '__main__':
    main()
