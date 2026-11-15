"""Package 27's binding records, and the waiting list for later packages.

pending "<note>": list every bound file that differs from the active bindings
  (checkout.active_tables: package 27's since its rehearsal) with its exact
  checkout bytes in os/manifest/ci/16/pending-rebind.json, every bound file
  that no longer exists under "removed" (22c took three scripts out of the
  owner payload), and add the note to the changes waiting there. Run it after
  the last change to a bound file.
record <27-bound-sources.json> <run id>: package 27's one-time step after its
  rehearsal passed: write os/manifest/ci/27/source-bindings.json exactly as the
  run recorded it, check every row against this checkout, and empty the pending
  list. Its result is the first entry of the list's "rebound" history.
rebind <package> <NN-bound-sources.json> <run id>: the same step for every
  later rehearsal, with the package key (22c is the first): write
  os/manifest/ci/<package>/source-bindings.json exactly as the run recorded
  it, check every row against this checkout, move what waited (changes, files,
  removed paths) into a new entry of the "rebound" history and empty the list.
  checkout.active_tables returns the new bindings from then on, so `pending`
  goes on working for the next package.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import checkout_sources as checkout

PENDING = ROOT / 'os/manifest/ci/16/pending-rebind.json'


def write(path, value):
    with open(path, 'w', newline='\n', encoding='utf-8') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def removed(root=ROOT):
    """Every bound path that is no longer a file in the checkout (it cannot have checkout bytes)."""
    union = checkout.merge(checkout.active_tables(root))
    return [row['path'] for row in union if not (root / row['path']).is_file()]


def changed(root=ROOT):
    """Every remaining bound file whose checkout bytes differ from the active bindings, with its current bytes."""
    gone = set(removed(root))
    union = [row for row in checkout.merge(checkout.active_tables(root)) if row['path'] not in gone]
    current = checkout.records(root, [row['path'] for row in union])
    return [now for old, now in zip(union, current) if old != now]


def pending(note):
    rows = changed()
    record = json.loads(PENDING.read_text())
    if note not in record['changes']:
        record['changes'].append(note)
    record['files'] = rows
    record['removed'] = removed()
    write(PENDING, record)
    print(f'pending: {len(rows)} bound files differ from the active bindings, {len(record["removed"])} removed')


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


def rebind(package, evidence, run, root=ROOT):
    """A later rehearsal's record step (brief 22c, D): the run's bound sources become the active tables."""
    root = pathlib.Path(root)
    folder, list_path = root / 'os/manifest/ci' / package, root / 'os/manifest/ci/16/pending-rebind.json'
    target = folder / 'source-bindings.json'
    assert re.fullmatch('[0-9]+[a-z]?', package) and run.isdigit(), 'Invalid package key or run id'
    assert not target.exists(), 'Package ' + package + ' has recorded its bindings already'
    value = json.loads(pathlib.Path(evidence).read_text())
    assert value['package'] == package and value['tables'][0]['name'] == 'package' + package + ' host walk'
    walk = json.loads((folder / 'host-walk.json').read_text())
    assert walk['sources'] == value['tables'][0]['sources'], 'The run walked other sources than the host walk'
    waiting = json.loads(list_path.read_text())
    active = checkout.merge(checkout.active_tables(root))  # still the rehearsal before this one
    union = checkout.merge([(table['name'], table['sources']) for table in value['tables']])
    assert checkout.verify(root, union) == len(union)
    # No bound file leaves the tables silently: each earlier path is rebound, or listed as removed and gone.
    left, listed = {row['path'] for row in active} - {row['path'] for row in union}, set(waiting.get('removed', []))
    assert left == listed, ('Bound files left the tables without being listed as removed, or a listed one is still bound: '
                            + ', '.join(sorted(left ^ listed)))
    assert not any((root / path).exists() for path in left), 'A removed path still exists'
    link = 'https://github.com/Ares-Empire/AresOS/actions/runs/' + run
    write(target, dict(package=package, encoding='Git checkout-index bytes; core.autocrlf=false; repository attributes',
                       run=link, commit=value['commit'], tables=value['tables']))
    entry = dict(status='rebound by package ' + package + "'s rehearsal", waited_for=waiting['walk'],
                 walk=target.relative_to(root).as_posix(), changes=waiting['changes'],
                 files=[row['path'] for row in waiting['files']], removed=waiting.get('removed', []), rebound_by=link)
    waiting['rebound'] = [*waiting.get('rebound', []), entry]
    waiting.update(status=entry['status'], walk=entry['walk'], changes=[], files=[], removed=[])
    write(list_path, waiting)
    assert changed(root) == [] and removed(root) == [], 'The new bindings do not hold this checkout'
    print(f'recorded {len(value["tables"])} tables, {len(union)} unique sources for package {package}; '
          f'{len(entry["files"])} waiting files and {len(entry["removed"])} removed paths moved to the history; pending list empty')


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'pending':
        pending(sys.argv[2])
    elif mode == 'rebind':
        rebind(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        record(sys.argv[2], sys.argv[3])
