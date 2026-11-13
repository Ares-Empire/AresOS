"""Package 27's binding records, and the waiting list for later packages.

pending "<note>": list every bound file that differs from the active bindings
  (checkout.active_tables: package 27's since its rehearsal) with its exact
  checkout bytes in os/manifest/ci/16/pending-rebind.json, and add the note to
  the changes waiting there. Run it after the last change to a bound file.
record <27-bound-sources.json> <run id>: package 27's one-time step after its
  rehearsal passed: write os/manifest/ci/27/source-bindings.json exactly as the
  run recorded it, check every row against this checkout, and empty the pending
  list. Its result is the first entry of the list's "rebound" history.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import checkout_sources as checkout

PENDING = ROOT / 'os/manifest/ci/16/pending-rebind.json'


def write(path, value):
    with open(path, 'w', newline='\n', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def changed():
    """Every bound file whose checkout bytes differ from the active bindings, with its current bytes."""
    union = checkout.merge(checkout.active_tables(ROOT))
    current = checkout.records(ROOT, [row['path'] for row in union])
    return [now for old, now in zip(union, current) if old != now]


def pending(note):
    rows = changed()
    record = json.loads(PENDING.read_text())
    if note not in record['changes']:
        record['changes'].append(note)
    record['files'] = rows
    write(PENDING, record)
    print(f'pending: {len(rows)} bound files differ from the active bindings')


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
        pending(sys.argv[2])
    else:
        record(sys.argv[2], sys.argv[3])
