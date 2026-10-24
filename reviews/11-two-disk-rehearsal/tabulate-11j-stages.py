import json
from pathlib import Path

root = Path('os/manifest/ci/11j')
rows = ['| Run / order / stage | Protected bytes / final writes | Firmware and Linux position events |',
        '|---|---|---|']
for run in sorted(p for p in root.iterdir() if p.is_dir() and (p / 'run.json').exists()):
    for baseline in sorted(run.rglob('protected-baseline.json')):
        folder = baseline.parent
        original = json.loads(baseline.read_text(encoding='utf-8'))
        captures = list(folder.glob('*-protected.json'))
        def sequence(path):
            devices = path.with_name(path.name.removesuffix('-protected.json') + '-devices.json')
            return json.loads(devices.read_text())['boot'] if devices.exists() else -1
        for path in sorted(captures, key=sequence):
            stage = path.name.removesuffix('-protected.json')
            matches = json.loads(path.read_text()) == original
            alias = stage.removeprefix('switch-sequence-')
            if alias.endswith('-pre-login-reset'):
                alias = 'pre-login-reset'
            if stage == 'b-recovered-stock' and not (folder / (alias + '-blockstats.json')).exists():
                alias = 'b-promote-recorded-stock'
            if stage == 'b-menu-preparation' and (folder / 'b-unresolved-menu-blockstats.json').exists():
                alias = 'b-unresolved-menu'
            stats = folder / (alias + '-blockstats.json')
            writes = 'missing counter'
            if stats.exists():
                protected, = [item['stats'] for item in json.loads(stats.read_text()) if item.get('device') == 'protected']
                writes = f"{protected['wr_bytes']} bytes / {protected['wr_operations']} operations"
            failure = folder / (alias + '-failure-counter.json')
            if failure.exists():
                proof = json.loads(failure.read_text())
                writes += '; failure path ' + proof['status']
            diff = folder / (stage + '-nvram-diff.json')
            changes = 'Baseline ownership' if stage == 'baseline-firmware' else 'No accepted NVRAM diff'
            if diff.exists():
                data = json.loads(diff.read_text())
                events = []
                for e in data['firmware_changes']:
                    events.append(f"{e['device']}: {e['before_option'] or 'absent'} → {e['after_option'] or 'absent'}"
                                  + ('; relabel' if e['relabeled'] else ''))
                for e in data['linux_position_changes']:
                    events.append(f"Linux {e['option']}: index {e['old_index']} → {e['new_index']}")
                changes = '<br>'.join(events) or 'None'
            order = 'reverse' if folder.name == 'protected-second' else 'first'
            rows.append(f"| {run.name} / {order} / {stage} | {'MATCH' if matches else 'FAIL'}; {writes} | {changes} |")
Path('os/manifest/ci/11j/stage-table.md').write_text('\n'.join(rows) + '\n', encoding='utf-8', newline='\n')
print('Stage rows:', len(rows) - 2)
