"""Check the retained Linux receiver records; never starts a browser or imports runtime code."""
import collections
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit


def read(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def case(row):
    return parse_qs(urlsplit(row['url']).query).get('case', [''])[0]


def audit(pair):
    run, mode = pair.split(':')
    assert run.isdigit() and mode in {'external', 'policy'}
    root = Path(__file__).parent / 'records' / f'integrate-{run}-{mode}'
    matrix = read(root / 'matrices.json')
    assert len(matrix) == 61 and len({row['name'] for row in matrix}) == 61
    assert all(row['passed'] is True for row in matrix)
    qualification = read(root / 'qualification-result.json')
    assert qualification['groups']['12'] is False
    assert all(value is True for group, value in qualification['groups'].items() if group != '12')
    assert all(value is True for value in qualification['core'].values())
    assert all(value is True for value in qualification['adapters'].values())
    raw = lines(root / 'receiver.jsonl')
    counts = collections.Counter(case(row) for row in raw)
    expected = {
        'loaded-popup-clean': 2, 'loaded-popup-dirty': 2,
        'popup-clean': 1, 'popup-dirty': 1,
        'flow-popup-clean': 1, 'flow-popup-dirty': 1,
        'loaded-popup-stop': 1, 'popup-stop': 0,
        'loaded-popup-opener-release': 1, 'popup-opener-release': 0,
        'loaded-popup-opener-close': 1, 'popup-opener-close': 0,
        'popup-post': 1, 'loaded-popup-outside': 1, 'popup-outside': 0,
    }
    for name, count in expected.items():
        assert counts[name] == count, (pair, name, counts[name], count)
    post = [row for row in raw if case(row) == 'popup-post']
    assert post[0]['method'] == 'POST'
    probes = [json.loads(row['body']) for row in raw if case(row) == 'state-popup-stop']
    assert len(probes) == 2 and probes[0] == probes[1]
    assert probes[0]['document'] and probes[0]['opener'] is True
    assert probes[0]['openerClosed'] is False and probes[0]['draft'] == 'Saved'
    observations = lines(root / 'popup-controls.jsonl')
    stopped = None
    for before, after in zip(observations, observations[1:]):
        if len(before['popups']) == 1 and 'id=popup-stop&' in before['popups'][0]['url'] and not after['popups']:
            stopped = before, after
            break
    assert stopped, (pair, 'missing native Stop transition')
    before, after = stopped
    assert before['windows'] == after['windows']
    child = before['popups'][0]['tab']
    old_child = next(row for row in before['tabs'] if row['tab'] == child)
    new_child = next(row for row in after['tabs'] if row['tab'] == child)
    assert old_child['opener'] == new_child['opener']
    parent = old_child['opener']
    assert next(row for row in before['tabs'] if row['tab'] == parent)['badge'] == 'POP'
    assert next(row for row in after['tabs'] if row['tab'] == parent)['badge'] == 'ON'
    assert new_child['badge'] == ''
    snapshots = lines(root / 'adapters-receiver.jsonl')
    approvals = collections.defaultdict(dict)
    free_dialogs = set()
    for row in snapshots:
        assert row['count'] == len(row['arrivals'])
        assert all(arrival in raw for arrival in row['arrivals'])
        if row['phase'] in {'before approval', 'after approval', 'after repeat'}:
            assert row['phase'] not in approvals[row['id']]
            approvals[row['id']][row['phase']] = row['count']
        if row['phase'] == 'independent free dialog':
            assert row['count'] == counts[row['id']] == 1
            free_dialogs.add(row['id'])
    assert len(approvals) == 135
    for name, phases in approvals.items():
        assert phases == {'before approval': 0, 'after approval': 1, 'after repeat': 1}, (pair, name, phases)
        assert counts[name] == 1
    assert len(free_dialogs) == 20
    return {'run': run, 'mode': mode, 'passed_named_cases': len(matrix),
            'adapter_approval_sequences_0_1_1': len(approvals),
            'independent_free_dialog_sequences': len(free_dialogs),
            'same_popup_document_and_native_windows_after_stop': True,
            'post_popup_requests': len(post), 'group12': False,
            'view': read(root / 'view-measurements.json')}


if __name__ == '__main__':
    print(json.dumps([audit(pair) for pair in sys.argv[1:]], indent=2))
