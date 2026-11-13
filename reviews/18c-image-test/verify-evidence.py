"""Independently cross-check a downloaded control-boundary evidence artifact."""
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
terminal = root / 'terminal'
interactive = terminal / 'interactive'
summary = json.loads((interactive / 'summary.json').read_text())
assert (root/'interactive-console.txt').read_text().splitlines()[0] == 'INTERACTIVE_VERSION 2.1.319 (Claude Code)'
assert len(summary) == 17 and len({r['case'] for r in summary}) == 17
receiver = (terminal / 'stub.txt').read_text()
for row in summary:
    case = row['case']
    assert receiver.count('POST /precedence/send/' + case + ' HTTP/1.1') == row['send_arrivals']
    if '-permission-' not in case:
        assert all(row['prompt_shown'])
        assert row['send_arrivals'] == int(case in ('normal-yes', 'normal-daa', 'skip-daa'))
    if case.endswith('-daa'):
        assert row['prompt_shown'] == [True, True] and row['new_session']['prompt_shown'] == [True]
        local = '/home/assistant/work/.claude/settings.local.json'
        first = json.loads((interactive/case/'session-1/settings-after-turn-1.json').read_text())
        third = json.loads((interactive/case/'session-3/settings-before.json').read_text())
        assert 'mcp__testapp__send' in first[local]['permissions']['allow']
        assert third[local] == first[local]
    if '-permission-' in case or case.endswith('pre-allow'):
        events = [json.loads(s) for s in (interactive/case/'hook-events.jsonl').read_text().splitlines()]
        assert len(events) == row['hook_calls'] == 1
        assert events[0]['tool_name'] == 'mcp__testapp__send'
    for actions in (interactive/case).glob('session-*/actions.jsonl'):
        for line in actions.read_text().splitlines():
            action = json.loads(line)
            screen = (actions.parent/action['screen']).read_text()
            assert action['option'] in screen
            if action['key'] is not None:
                assert action['key'] + '. ' + action['option'] in screen
            if action['option'] in ('Yes', 'No') or action['option'].startswith("Yes, and don't ask again"):
                assert screen.index('question:') < screen.index('operation_id:') < screen.index('description:')
assert sum(r['send_arrivals'] for r in summary) == 7
expected = json.loads(Path('control/boundary/interactive-permission-request-expected.json').read_text())
observed = json.loads((interactive/'permission-request.json').read_text())
assert {case: {key: row[key] for key in ('send_arrivals', 'hook_calls', 'owner_answers')}
        for case, row in observed.items()} == expected
size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
assert size < 180_000_000
assert sum(len(json.loads(p.read_text())) for p in interactive.glob('*/session-*/results.json')) == 21
print('EVIDENCE_CHECK_PASS cases=17 arrivals=7 hooks=6 bytes=' + str(size))
