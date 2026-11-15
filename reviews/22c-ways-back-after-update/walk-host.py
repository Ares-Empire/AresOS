"""Run package 22c's zero-cost host walks and bind them to their sources.

Stage 0: the reorder probe's route (package 27's route up to release 27
confirmed, then the six orders with plain `ostree admin set-default`, one
boot-menu choice). Stage 2: the rehearsal's route (brief 22c, E: the same
history, tools version 3 from the stick, the layout trials, every way between
the three systems, two boot-menu rows and one cut), where the owner tools
themselves answer each way-back command over a modelled machine. The walks
drive the real owner_vm control flow with synthetic guest answers and a
modelled disk. No VM, privilege, hardware query or token is used; this is a
prerequisite for the hosted run (owner_vm.main refuses a stale walk), never VM
evidence. Package 27's generator and receipt stay as they are.

Run on Linux, from the repository root, after the last change to a file it
binds: python3 reviews/22c-ways-back-after-update/walk-host.py
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/tests'))
import test_owner_walk

# Read by this package's walks and harness in addition to package 27's set.
ADDED = {'os/ci/reorder_probe.py', 'os/ci/grub_bls.py', 'os/ci/keyboard_entries.py', 'os/ci/greeter.py', 'os/ci/greeter_probe.py',
         'os/tests/test_ways_back_probe.py', 'reviews/22c-ways-back-after-update/walk-host.py',
         # The rehearsal's route: the tools' own reorder step and the modelled machine its answers run on.
         'os/release/start-next.sh', 'os/owner-tools/payload/release/start-next.sh', 'os/tests/test_ways_back.py',
         'os/tests/test_owner_update.py', 'os/tests/ways_back_keyboard.py'}
ROUTES = ('reorder-probe', 'ways-back')


def main():
    walks = {route: test_owner_walk.walk(route=route) for route in ROUTES}
    previous = json.loads((ROOT / 'os/manifest/ci/27/host-walk.json').read_text())
    inherited = {row['path'] for row in previous['sources']}
    # A file package 27 bound that no longer exists is named, never silently dropped.
    gone = sorted(path for path in inherited if not (ROOT / path).is_file())
    paths = (inherited - set(gone)) | ADDED
    sources = [dict(sha256=hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), path=path) for path in sorted(paths)]
    result = dict(status='passed',
        kind="local synthetic owner host walks (package 22c's routes); not VM or physical qualification",
        stick_across_reboot=False,
        stages={route: walk['stages'] for route, walk in walks.items()},
        checks={route: len(walk['checks']) for route, walk in walks.items()},
        markers={route: walk['markers'] for route, walk in walks.items()},
        command_count={route: len(walk['commands']) for route, walk in walks.items()},
        typed_count={route: len(walk['typed']) for route, walk in walks.items()},
        set_default_indexes={route: walk['disk'].sets for route, walk in walks.items()},
        inherited_from='os/manifest/ci/27/host-walk.json', no_longer_bound=gone,
        sources=sources)
    folder = ROOT / 'os/manifest/ci/22c'
    folder.mkdir(exist_ok=True)
    with open(folder / 'host-walk.json', 'w', newline='\n', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(f'PASS package 22c host walks ({", ".join(ROUTES)}): {len(sources)} sources; no VM started')


if __name__ == '__main__':
    main()
