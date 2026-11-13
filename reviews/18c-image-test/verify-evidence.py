"""Independently cross-check a downloaded control-boundary evidence artifact."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'control/boundary'))
from interactive_suite import check_case_evidence

root = Path(sys.argv[1])
terminal = root / 'terminal'
interactive = terminal / 'interactive'
summary = json.loads((interactive / 'summary.json').read_text())
assert (root/'interactive-console.txt').read_text().splitlines()[0] == 'INTERACTIVE_VERSION 2.1.319 (Claude Code)'
assert len(summary) == 17 and len({r['case'] for r in summary}) == 17
receiver = (terminal / 'stub.txt').read_text()
expected = json.loads((Path(__file__).resolve().parents[2] /
                       'control/boundary/interactive-permission-request-expected.json').read_text())
for row in summary:
    case = row['case']
    check_case_evidence(interactive / case, row, expected)
    assert receiver.count('POST /precedence/send/' + case + ' HTTP/1.1') == row['send_arrivals']
    if '-permission-' not in case:
        assert all(row['prompt_shown'])
        assert row['send_arrivals'] == int(case in ('normal-yes', 'normal-daa', 'skip-daa'))
assert sum(r['send_arrivals'] for r in summary) == 7
observed = json.loads((interactive/'permission-request.json').read_text())
assert {case: {key: row[key] for key in ('send_arrivals', 'hook_calls', 'owner_answers')}
        for case, row in observed.items()} == expected
size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
assert size < 180_000_000
assert sum(len(json.loads(p.read_text())) for p in interactive.glob('*/session-*/results.json')) == 21
print('EVIDENCE_CHECK_PASS cases=17 arrivals=7 hooks=6 bytes=' + str(size))
