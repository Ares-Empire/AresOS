"""Replay old full captures with the documented deterministic caller fixture input.

Only that input changes; comparisons still use literal, complete public paths.
This converter is never used by the expectation model or the strict checker.
"""
import argparse
import copy
import gzip
import json
from pathlib import Path
import re
from .gaps import full_pack, unpack
from .identity import caller_name
from .records import canonical


def stabilize(entries):
    result, folders, changed = dict(entries), {}, 0
    for key, detail in entries.items():
        parts = key.split('/')
        if len(parts) < 6 or parts[0] not in {'attachment_export', 'testapp_export', 'export_rollback'}:
            continue
        flow, mode, point, cleanup, read_phase = parts[:5]
        phase = 'crash' if read_phase.startswith('crash-') else 'live'
        name = caller_name(flow, int(point), mode, int(cleanup), phase)
        replacements = []
        for index, failure in enumerate(detail['delta']['failures']):
            for side in ('missing', 'extra'):
                for number, fact in enumerate(failure[side]):
                    if fact[1] not in {'mail_attachment_save', 'mail_file_save', 'testapp_file_save'} or '/control/test-work/tmp' not in fact[3]:
                        continue
                    entry = json.loads(fact[3])
                    content = entry.get('untrusted_content', {})
                    container, field = (content, 'folder') if fact[1] == 'mail_attachment_save' else (content.get('save', {}), 'path')
                    value = container.get(field, '')
                    match = re.fullmatch(r'(.*/control/test-work/)(tmp[^/]{8})(/Downloads(?:/export\.bin)?)', value)
                    leaf = '/Downloads' if field == 'folder' else '/Downloads/export.bin'
                    if not match or entry.get('action') != fact[1] or match[3] != leaf:
                        raise ValueError(('Unknown caller input', key, value))
                    script = (flow, mode, point, cleanup, phase)
                    folder = match[1] + match[2]
                    if script in folders and folders[script] != folder:
                        raise ValueError(('Two different targets in one script; cannot convert', key))
                    folders[script] = folder
                    container[field] = match[1] + name + leaf
                    encoded = canonical(entry)
                    if encoded != fact[3]:
                        replacements.append((index, side, number, encoded))
        if replacements:
            value = copy.deepcopy(detail)
            for index, side, number, encoded in replacements:
                value['delta']['failures'][index][side][number][3] = encoded
            result[key] = value
            changed += 1
    return result, changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+')
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    root = Path(args.output_dir)
    if '.work' not in root.parts:
        parser.error('Full captures must stay under .work/')
    total = 0
    for name in args.inputs:
        path = Path(name)
        opener = gzip.open if path.suffix == '.gz' else open
        with opener(path, 'rt') as stream:
            entries, changed = stabilize(unpack(json.load(stream)))
        output = root / path.parent.name / path.name
        output.parent.mkdir(parents=True, exist_ok=True)
        with (gzip.open(output, 'wt') if output.suffix == '.gz' else output.open('w')) as stream:
            json.dump(full_pack(entries), stream, sort_keys=True)
        print(path.name, 'exact keys', len(entries), 'scripted-folder changes', changed)
        total += changed
    print('Total scripted-folder assertion changes:', total)


if __name__ == '__main__':
    main()
