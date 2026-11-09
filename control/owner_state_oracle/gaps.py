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
            if key.startswith('notice:') and value['id'] not in self.aliases:
                self.aliases[value['id']] = 'occurrence:#' + str(len(self.aliases))

    def facts(self, values):
        result = []
        for f in sorted(values):
            if f.source not in self.aliases:
                self.aliases[f.source] = (f.source.rsplit(':', 1)[0] if not f.source.startswith('op:') else 'op') + ':#' + str(len(self.aliases))
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
        def check(view, expected, actual):
            key = case + '/' + view
            # Bind common values before differences so random UUID sorting
            # cannot make a recorded failure non-reproducible.
            self.facts(expected)
            self.facts(actual)
            delta = {'missing': self.facts(expected - actual), 'extra': self.facts(actual - expected)}
            if key in self.entries:
                self.seen.add(key)
                assert expected != actual, ('Unexpected pass; remove this known gap', key)
                assert self.entries[key]['delta'] == delta, ('Known gap changed; possible regression', key, self.entries[key], delta)
            elif expected != actual:
                if not self.recording:
                    raise AssertionError(('Unlisted owner-state gap', key, delta))
                kinds = {f.kind for f in expected ^ actual}
                row = 'M06' if 'recovery' in kinds else 'M07' if 'sent_copies' in kinds else 'M14'
                self.entries[key] = {'row': row, 'stage': 3, 'delta': delta}
        return check

    def save(self):
        PATH.write_text(json.dumps({'format': 1, 'assertions': self.entries}, sort_keys=True, indent=2) + '\n')
