"""Exact assertion deltas. No skips, wildcard matches or exception swallowing."""
import json
import hashlib
import gzip
import os
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / 'reviews/19b-owner-state/KNOWN-GAPS.json'


def unpack(value):
    if value['format'] == 1:
        return value['assertions']
    if value['format'] != 2:
        raise ValueError('Unknown known-gap ledger format')
    entries = {}
    for group in value['groups']:
        detail = {key: group[key] for key in ('row', 'stage', 'delta')}
        for case in group['cases']:
            if case in entries:
                raise ValueError('Duplicate known-gap assertion')
            entries[case] = detail
    return entries


def full_pack(entries):
    # Duplicate deltas share storage; every case name remains explicit.
    groups = {}
    for case, detail in sorted(entries.items()):
        key = json.dumps(detail, sort_keys=True)
        groups.setdefault(key, {**detail, 'cases': []})['cases'].append(case)
    return {'format': 2, 'groups': list(groups.values())}


BUCKETS = 12  # Four CI shards, three isolated workers per shard.


def owner(key):
    parts = key.split('/')
    if len(parts) > 2 and parts[1] in {'single', 'persistent'} and parts[2].isdigit():
        point = int(parts[2])
        return 'shared' if not point else str(int.from_bytes(hashlib.sha256(f'{parts[0]}/{point}'.encode()).digest()[:8]) % BUCKETS)
    return 'suite'


def pack(entries):
    groups = {}
    for key, detail in sorted(entries.items()):
        identity = [key.split('/')[0], owner(key), detail['row'], detail['stage']]
        group_id = json.dumps(identity, separators=(',', ':'))
        delta = detail['delta']
        assert detail['stage'] in (2, 3) and detail['row'] and delta['calls'] > 0 and delta['failures'], ('Malformed known gap', group_id, key)
        seen_pages = set()
        for failure in delta['failures']:
            assert failure['missing'] or failure['extra'], ('Empty gap delta', group_id, key)
            for page in failure['pages']:
                assert page in range(delta['calls']) and page not in seen_pages, ('Invalid gap page', group_id, key, page)
                seen_pages.add(page)
        group = groups.setdefault(group_id, {'id': group_id, 'suite': identity[0], 'owner': identity[1],
            'row': detail['row'], 'stage': detail['stage'], 'keys': []})
        group['keys'].append([key, detail])
    result = []
    for group in groups.values():
        keys = group.pop('keys')
        # Newline-delimited canonical [key,{row,stage,delta}] records. The row,
        # stage, calls and exact missing/extra facts/pages all enter the digest.
        digest = hashlib.sha256()
        for value in keys:
            digest.update((json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n').encode())
        result.append({**group, 'count': len(keys), 'sha256': digest.hexdigest(), 'samples': [value[0] for value in keys[:3]]})
    return {'format': 3, 'buckets': BUCKETS, 'groups': sorted(result, key=lambda g: g['id'])}


def owned(group, shard=0, shards=1, worker=0, workers=1):
    if group['owner'] in {'suite', 'shared'}:
        return True
    assert BUCKETS % (shards * workers) == 0, 'Ledger ownership requires a divisor of twelve workers'
    bucket = int(group['owner'])
    return bucket % shards == shard and (bucket // shards) % workers == worker


class Gaps:
    def __init__(self, recording=False):
        self.recording = recording
        self.groups = {} if recording else {g['id']: g for g in json.loads(PATH.read_text())['groups']}
        self.entries = {}
        self.executed = set()
        self.seen = set()
        self.aliases = {}
        self._indexed_entries = None
        self.by_case = {}

    def bind(self, record):
        for key, value in record.rows.items():
            if key.startswith(('op:', 'mail:filing:', 'mail:rename:', 'intent:', 'export:', 'mail:account:')) and key not in self.aliases:
                self.aliases[key] = (key.rsplit(':', 1)[0] if not key.startswith('op:') else 'op') + ':#' + str(len(self.aliases))
            if key.startswith('op:'):
                self.aliases['cancel:' + value['id']] = 'cancel(' + self.aliases[key] + ')'
                self.aliases['settle:' + value['id']] = 'settle(' + self.aliases[key] + ')'
            if key.startswith('notice:') and value['id'] not in self.aliases:
                self.aliases[value['id']] = 'occurrence:#' + str(len(self.aliases))

    def facts(self, values):
        result = []
        for f in sorted(values):
            if f.source not in self.aliases:
                self.aliases[f.source] = (f.source.rsplit(':', 1)[0] if not f.source.startswith(('op:', 'cancel:', 'settle:', 'unbound:')) else f.source.split(':', 1)[0]) + ':#' + str(len(self.aliases))
            # Occurrence aliases are separate: two warnings about the same
            # operation cannot collapse into one just because counts agree.
            identity = f.occurrence
            if identity:
                if identity not in self.aliases:
                    self.aliases[identity] = 'occurrence:#' + str(len(self.aliases))
                identity = self.aliases[identity]
            result.append([self.aliases[f.source], f.kind, identity, f.detail])
        return sorted(result)

    def checker(self, case):
        if self._indexed_entries is not self.entries:
            self.by_case = {}
            for key in self.entries:
                self.by_case.setdefault(key.rsplit('/', 1)[0], set()).add(key)
            self._indexed_entries = self.entries
        calls, failures, kinds_seen, sources_seen = {}, {}, {}, {}
        def check(view, expected, actual):
            self.facts(expected)
            self.facts(actual)
            number = calls.get(view, 0)
            calls[view] = number + 1
            if expected != actual:
                delta = {'missing': self.facts(expected - actual), 'extra': self.facts(actual - expected)}
                group = next((value for value in failures.setdefault(view, []) if value['missing'] == delta['missing'] and value['extra'] == delta['extra']), None)
                if group is None:
                    group = {'pages': [], **delta}
                    failures[view].append(group)
                group['pages'].append(number)
                kinds_seen.setdefault(view, set()).update(f.kind for f in expected ^ actual)
                sources_seen.setdefault(view, set()).update(f.source for f in expected ^ actual)
        def finish():
            self.executed.add(case)
            expected_keys = self.by_case.get(case, set())
            actual_keys = {case + '/' + view for view in calls}
            assert expected_keys <= actual_keys, ('Known-gap assertion not executed', sorted(expected_keys - actual_keys))
            for view, count in calls.items():
                key = case + '/' + view
                delta = {'calls': count, 'failures': failures.get(view, [])}
                if key in self.entries:
                    self.seen.add(key)
                    assert delta['failures'], ('Unexpected pass; remove this known gap', key)
                    assert self.entries[key]['delta'] == delta, ('Known gap changed; possible regression', key, self.entries[key], delta)
                elif delta['failures']:
                    if not self.recording and not self.groups:
                        raise AssertionError(('Unlisted owner-state gap', key, delta))
                    kinds = kinds_seen.get(view, set())
                    r2 = any(k.startswith('R2.') for k in kinds)
                    if case.startswith('G22-rename') or case.startswith('G22-evidence'):
                        row = 'M03/C03'
                    elif case.startswith('G22-latch'):
                        row = 'M08/M10/M13'
                    elif r2:
                        mapping = {'R2.DATA': 'M04', 'R2.APPEND': 'M04/M05/M12', 'R2.MOVE': 'M02/C02', 'R2.COPY': 'M02/C02',
                                   'R2.RENAME': 'M03/C03', 'R2.CREATE': 'M05/M12', 'R2.DELETE': 'M04/M12',
                                   'R2.STORE': 'M04/M05', 'R2.EXPUNGE': 'M04', 'R2.POST': 'M04', 'R2.RECEIVE': 'M04',
                                   'R2.CONFIGURE': 'M05', 'R2.LOCAL_DELETE': 'M04', 'R2.LOCAL_CHANGE': 'M05/M12'}
                        row = ','.join(sorted({mapping[k] for k in kinds if k in mapping}))
                    elif view.startswith('qualification'):
                        row = 'M12/C05'
                    elif 'background-storage' in kinds:
                        row = 'M08'
                    elif view.startswith('restore'):
                        row = 'M09'
                    elif 'holds' in view:
                        row = 'M10/M11'
                    elif 'publication' in view:
                        row = 'M11'
                    elif any(source.startswith('mail:rename:') for source in sources_seen.get(view, set())):
                        row = 'M03/C03/M14'
                    elif any(source.startswith('mail:filing:') for source in sources_seen.get(view, set())):
                        row = 'M02/C02/C04/M14'
                    elif any(source.startswith('mail:account:') for source in sources_seen.get(view, set())):
                        row = 'M12/C05/M14'
                    elif kinds & {'missing-committed-history', 'changed-observed-commit', 'unjustified-restore-transition',
                                  'narrowed-obligation', 'missing-obligation-source'}:
                        row = 'M06/M09/M14'
                    elif 'locations' in view:
                        row = 'M02/C04'
                    else:
                        row = 'M06' if 'recovery' in kinds else 'M07/C01' if 'sent_copies' in kinds else 'M03/C03' if 'rename' in kinds else 'M02/C02' if 'filing' in kinds else 'M14'
                    self.entries[key] = {'row': row, 'stage': 2 if r2 else 3, 'delta': delta}
                    self.seen.add(key)
                    self.by_case.setdefault(case, set()).add(key)
        check.finish = finish
        return check


    def verify(self, suites, shard=0, shards=1, worker=0, workers=1, artifact=True):
        actual = {g['id']: g for g in pack(self.entries)['groups'] if g['suite'] in suites}
        expected = {k: g for k, g in self.groups.items() if g['suite'] in suites and owned(g, shard, shards, worker, workers)}
        # Emit actual full lists even on strict failure. Only test data enters
        # these files; no credentials, fixture keys or production modules.
        if artifact:
            root = PATH.parents[1].parent / '.work' / ('control-ci' if suites == {'channel'} else 'mail-ci')
            root.mkdir(parents=True, exist_ok=True)
            name = '-'.join(sorted(suites)) if len(suites) < 4 else 'sweep'
            with gzip.open(root / f'owner-gaps-{name}-{shard}-{worker}.json.gz', 'wt') as stream:
                json.dump(full_pack(self.entries), stream, sort_keys=True)
        if self.recording:
            return
        errors = []
        for key in sorted(expected.keys() | actual.keys()):
            old, new = expected.get(key), actual.get(key)
            if old == new:
                continue
            if old is None:
                reason = 'Unlisted gap'
            elif new is None:
                reason = 'Unexpected pass or owned group not executed'
            elif new['count'] < old['count']:
                reason = 'Unexpected pass or removed key; known gap changed'
            elif new['count'] > old['count']:
                reason = 'Unlisted gap or added key; known gap changed'
            else:
                reason = 'Known gap changed'
            errors.append((reason, key, old, new))
        assert not errors, errors

    def save(self):
        PATH.write_text(json.dumps(pack(self.entries), sort_keys=True, indent=2) + '\n')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Convert/diff a full .work ledger or merge CI actual lists; never writes full lists in reviews.')
    parser.add_argument('inputs', nargs='+')
    parser.add_argument('--output', required=True)
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    entries = {}
    for name in args.inputs:
        opener = gzip.open if name.endswith('.gz') else open
        with opener(name, 'rt') as stream:
            for key, detail in unpack(json.load(stream)).items():
                if key in entries and entries[key] != detail:
                    raise ValueError(('Conflicting shared capture', key))
                entries[key] = detail
    output = Path(args.output)
    if args.full and '.work' not in output.parts:
        parser.error('Full lists must stay under .work/')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(full_pack(entries) if args.full else pack(entries), sort_keys=True, indent=2) + '\n')
    print(json.dumps({'assertions': len(entries), 'groups': len(pack(entries)['groups']),
        'stages': {stage: sum(v['stage'] == stage for v in entries.values()) for stage in (2, 3)}, 'bytes': output.stat().st_size}))


if __name__ == '__main__':
    main()
