"""Exact assertion deltas. No skips, wildcard matches or exception swallowing."""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / 'reviews/19b-owner-state/KNOWN-GAPS.json'


class Gaps:
    def __init__(self, recording=False):
        self.recording = recording
        self.entries = {} if recording else json.loads(PATH.read_text())['assertions']
        self.seen = set()
        self.aliases = {}

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
            expected_keys = {key for key in self.entries if key.startswith(case + '/')}
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
                    if not self.recording:
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
                                   'R2.STORE': 'M04/M05', 'R2.EXPUNGE': 'M04', 'R2.RECEIVE': 'M04'}
                        row = ','.join(sorted({mapping[k] for k in kinds if k in mapping}))
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
                    elif 'locations' in view:
                        row = 'M02/C04'
                    else:
                        row = 'M06' if 'recovery' in kinds else 'M07/C01' if 'sent_copies' in kinds else 'M03/C03' if 'rename' in kinds else 'M02/C02' if 'filing' in kinds else 'M14'
                    self.entries[key] = {'row': row, 'stage': 2 if r2 else 3, 'delta': delta}
        check.finish = finish
        return check

    def save(self):
        PATH.write_text(json.dumps({'format': 1, 'assertions': self.entries}, sort_keys=True, indent=2) + '\n')
