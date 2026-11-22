"""Generate the package 331 local receipt and selective fixture diagnostics.

Run from the repository root with TMPDIR inside the worktree:
python3 reviews/331-release-29/walk-host.py
"""

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/tests'))

from test_owner_walk import walk as historical_walk
from test_release29_rehearsal import CONTROL_FAILURES, TERMINAL_FAILURES, CandidateRouteTest
from release29_walk import HOST_WALK_RECEIPT, baseline_inputs, probes, r28
import checkout_sources


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def guest_paths(model, value):
    # Mapped paths, including those in error messages, should name the guest files.
    return json.loads(json.dumps(value).replace(str(model.session.root), ''))


def diagnostics():
    CandidateRouteTest.setUpClass()
    try:
        test = CandidateRouteTest()
        with test.model('masked-ordering') as model:
            model.run_route()
            successful = {name: guest_paths(model, value) for name, value in model.saved.items() if name.endswith((
                '-control', '-control-login', '-session', '-terminal', '-terminal-path', '-package21-rules',
                '-polkit-sweep', '-sites-stage', '-sites-placeholder', '-sites-hash', '-game-scope',
                '-chrome-first-use', '-deployment-walk'))}
            candidate = dict(stages=[stage for stage, event in model.events if event == 'F12 Bazzite'],
                             audits=[stage for stage, event in model.events if event == 'audit'],
                             checks=[stage for stage, event in model.events if event == 'check'],
                             probe_count=sum(event == 'probe' for _, event in model.events),
                             result=model.saved['release-29-deployment-walk']['status'])
        negative = {}
        cases = {fault: (message, 'release-28-terminal') for fault, (message, _) in TERMINAL_FAILURES.items()}
        cases.update({fault: (message, name) for fault, (message, _, name) in CONTROL_FAILURES.items()})
        for fault, (message, name) in cases.items():
            with test.model(fault) as model:
                try:
                    model.run_route()
                except AssertionError as error:
                    assert re.search(message, str(error)), (fault, str(error))
                else:
                    raise AssertionError('The fixture accepted ' + fault)
                negative[fault] = guest_paths(model, model.saved[name])
        with test.model('late-monitor') as model:
            model.run_route()
            successful['late-monitor-terminal'] = guest_paths(model, model.saved['release-28-terminal'])
    finally:
        CandidateRouteTest.doClassCleanups()
    return candidate, dict(evidence='synthetic guest fixture', passed=successful, refused=negative)


def main():
    historical = historical_walk(route='release-29')
    historical['session'].close()
    candidate, evidence = diagnostics()
    parent = 'os/manifest/ci/42/host-walk.json'
    inherited = {row['path'] for row in json.loads((ROOT / parent).read_bytes())['sources']}
    gone = sorted(path for path in inherited if not (ROOT / path).is_file())
    tracked_chrome = r28.git('ls-files', '-z', '--', 'control/chrome/extension', 'control/chrome/packaging')
    paths = (inherited - set(gone)) | {row['path'] for row in baseline_inputs()} | {
        parent, probes.CONTROL_CHECKER, probes.CHROME_FIRST_USE, probes.POLKIT_REVIEW,
        'os/config/usr/share/aresos/apps/browser.json', 'os/config/usr/share/aresos/apps/terminal.json',
        'os/tests/test_release29_rehearsal.py', 'reviews/331-release-29/walk-host.py',
        *tracked_chrome.decode().split('\0')[:-1],
    }
    paths.discard(HOST_WALK_RECEIPT)
    result = dict(status='passed', kind='local synthetic R29 host walk', stick_across_reboot=False,
                  probe_settings=probes.receipt_settings(),
                  baseline=dict(stages=historical['stages'], markers=historical['markers'],
                                checks=len(historical['checks']), command_count=len(historical['commands']),
                                typed_count=len(historical['typed']), result=historical['result']['status']),
                  candidate=candidate, inherited_from=parent, no_longer_bound=gone,
                  sources=checkout_sources.records(ROOT, sorted(paths)))
    probes.check_receipt(result)
    save(ROOT / HOST_WALK_RECEIPT, result)
    save(ROOT / 'reviews/331-release-29/diagnostics/step4-probes.json', evidence)
    print(f'PASS package 331 synthetic baseline and candidate host walk with {len(paths)} sources')


if __name__ == '__main__':
    main()
