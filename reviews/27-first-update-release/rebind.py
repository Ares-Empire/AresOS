"""Package 27's binding records.

pending: before the rehearsal, list every bound file that differs from package
  16's bindings with its exact checkout bytes (os/manifest/ci/16/pending-rebind.json).
  The local walk now types update and previous, so no command stays unwalked.
record <27-bound-sources.json> <run id>: after the rehearsal passed, write
  os/manifest/ci/27/source-bindings.json exactly as the run recorded it, check
  every row against this checkout, and empty the pending list.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import checkout_sources as checkout

PENDING = ROOT / 'os/manifest/ci/16/pending-rebind.json'
SIXTEEN = ROOT / 'os/manifest/ci/16/source-bindings.json'


def write(path, value):
    with open(path, 'w', newline='\n', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def pending():
    tables = [(t['name'], t['sources']) for t in json.loads(SIXTEEN.read_text())['tables']]
    union = checkout.merge(tables)
    current = checkout.records(ROOT, [row['path'] for row in union])
    changed = [now for old, now in zip(union, current) if old != now]
    record = json.loads(PENDING.read_text())
    note = ('Package 27 (first update release): release 27 pinned in release.json and the tools bundle, the update '
            'rehearsal harness (laptop tools, step 8 route, passwd and sudo proofs), package 27 dispatch wiring')
    if note not in record['changes']:
        record['changes'].append(note)
    record['files'] = changed
    record['unwalked_commands'] = []
    record['unwalked_rule'] = ('Commands added by package 22 are typed by the local walk of package 27\'s update '
                               'rehearsal (os/tests/test_owner_walk.py, route update); none is waiting.')
    write(PENDING, record)
    print(f'pending: {len(changed)} bound files differ from package 16; unwalked commands: none')


def record(evidence, run):
    value = json.loads(pathlib.Path(evidence).read_text())
    assert value['package'] == '27' and value['tables'][0]['name'] == 'package27 host walk'
    walk = json.loads((ROOT / 'os/manifest/ci/27/host-walk.json').read_text())
    assert walk['sources'] == value['tables'][0]['sources'], 'The run walked other sources than the host walk'
    tables = [(t['name'], t['sources']) for t in value['tables']]
    union = checkout.merge(tables)
    assert checkout.verify(ROOT, union) == len(union)
    out = dict(package='27', encoding='Git checkout-index bytes; core.autocrlf=false; repository attributes',
               run='https://github.com/Ares-Empire/AresOS/actions/runs/' + run, commit=value['commit'],
               tables=value['tables'])
    write(ROOT / 'os/manifest/ci/27/source-bindings.json', out)
    previous = json.loads(PENDING.read_text())
    previous.update(status='rebound by package 27\'s update rehearsal',
                    walk='os/manifest/ci/27/source-bindings.json',
                    rebound_by='https://github.com/Ares-Empire/AresOS/actions/runs/' + run, files=[])
    write(PENDING, previous)
    print(f'recorded {len(value["tables"])} tables, {len(union)} unique sources; pending list empty')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'pending':
        pending()
    else:
        record(sys.argv[2], sys.argv[3])
