"""Package 22c: take a VM run's captures out of its evidence artifact and into the repository.

Usage (from the repository root, with the run's `two-disk-evidence` artifact downloaded):
  python3 reviews/22c-ways-back-after-update/collect.py <artifact>/two-disk <run id>

Writes reviews/22c-ways-back-after-update/runs/<kind>-<run id>/ with, for every stage of the
result file, the captures the brief names (P5): the raw `rpm-ostree status --json` and
`bootc status --json` with every boot entry (`-deployments.json`), the layout capture, the facts
by role, and for every move the command's output and ostree's journal lines. The protected-disk
audits are summarized in audits.json (one row per boot; the raw audit files stay in the artifact).

Before anything is written, every file is checked for tokens, password hashes and the run's
passwords' known shape, and the run stops on a hit. A JSON capture is checked as it is stored and
as it reads: json writes `ü` as an escape, which would hide the harness password's start from a
search of the stored text alone. Two kinds of VM-only identifiers are
replaced by fixed words, the same word for the same value everywhere, so that equality between
captures survives: the VM disk's filesystem UUIDs (`root=UUID=`) and the boot ids. The public
repository holds no GUIDs, also not a throwaway VM's. rpm-ostree's and bootc's JSON hold neither.
Prints the stage table for the report.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
UUID = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
# A token, a credential header, a crypt hash, or the harness password: its fixed start with the
# first of its random hex digits. The start alone is the public typing text (`yz-/!ü`), which the
# tools print in every check ("Also prove yz-/!ü by physical typing ...") and which the rehearsal's
# transcript therefore holds.
FORBIDDEN = (r'gh[pousr]_[A-Za-z0-9]{20,}', r'github_pat_', r'x-access-token', r'[Aa]uthorization: ', r'"auth"\s*:',
             r'\$(?:6|5|y|gy|2[aby])\$', r'yz-/!ü[0-9a-f]{4}', r'BEGIN [A-Z ]*PRIVATE KEY')
PER_STAGE = ('-deployments.json', '-layout.json', '-observed.json')
PER_MOVE = ('-set-default.json', '-journal-before.json', '-journal-after.json', '-swap.json')
MENU = ('menu-bls-entries.json', 'menu-recorded-stock-entry.json', 'b-grub-menu-ocr-proof.json', 'b-grub-selection.json')
# Stage 2's rehearsal (ways-back): one set of menu files per boot-menu choice, the cut's proof, the stock's updaters,
# and the installed toolset's folder as the harness read it before each layout proof (stage 2, step 2).
REHEARSAL = ('*-menu-bls-entries.json', '*-menu-recorded-stock-entry.json', '*-grub-menu-ocr-proof.json', '*-grub-selection.json',
             'cut-rollback-proof.json', 'cut-rollback-watcher.json', '*-stock-updaters.json', '*-toolset.json')


def searched(name, text):
    """The text the forbidden patterns are searched in: the stored bytes and, for JSON, what they say."""
    return text + '\n' + json.dumps(json.loads(text), ensure_ascii=False) if name.endswith('.json') else text


def main():
    evidence, run = pathlib.Path(sys.argv[1]), sys.argv[2]
    assert run.isdigit() and evidence.is_dir()
    results = sorted(evidence.glob('*-result.json'))
    result_file, = [path for path in results if path.name in ('reorder-probe-result.json', 'ways-back-rehearsal-result.json')]
    result = json.loads(result_file.read_text())
    kind = result_file.name.removesuffix('-result.json')
    names = [result_file.name]
    for row in result['stages']:
        names += [row['stage'] + suffix for suffix in PER_STAGE]
        if row.get('bootconfig_swap') is not None or (evidence / (row['stage'] + '-swap.json')).exists():
            # A reorder by the owner tools has no output of its own: the tools keep it in their private record.
            names += [row['stage'] + suffix for suffix in PER_MOVE
                      if suffix != '-set-default.json' or (evidence / (row['stage'] + suffix)).exists()]
    names += [name for name in MENU if (evidence / name).exists()]
    if kind == 'ways-back-rehearsal':
        names += sorted({path.name for pattern in REHEARSAL for path in evidence.glob(pattern)} - set(names))
    frames = [((result.get('menu') or {}).get('choice') or {}).get('frame')]
    frames += [(row.get('choice') or {}).get('frame') for row in result.get('menus', [])]
    names += [frame + '-ocr.txt' for frame in frames if frame]
    missing = [name for name in names if not (evidence / name).is_file()]
    assert not missing, 'The artifact lacks captures: ' + ', '.join(missing)
    texts = {name: (evidence / name).read_text(encoding='utf-8') for name in names}

    # 1. Nothing secret, before anything is written.
    hits = sorted({(name, pattern) for name, text in texts.items() for pattern in FORBIDDEN if re.search(pattern, searched(name, text))})
    assert not hits, 'STOP: a capture holds a token, credential or password hash: ' + repr(hits)

    # 2. VM-only identifiers become fixed words.
    roots, boots = [], []
    for text in texts.values():
        for value in re.findall(r'root=UUID=(' + UUID + ')', text):
            if value not in roots:
                roots.append(value)
    for row in result['stages']:
        observed = json.loads(texts[row['stage'] + '-observed.json'])
        if observed['boot_id'] not in boots:
            boots.append(observed['boot_id'])
    words = {value: 'VM-ROOT-FILESYSTEM' + (str(n) if n else '') for n, value in enumerate(roots)}
    words.update({value: f'vm-boot-{n}' for n, value in enumerate(boots, 1)})
    words.update({value.replace('-', ''): word for value, word in list(words.items())})  # journal fields print ids without dashes
    for name, text in texts.items():
        for value, word in words.items():
            text = text.replace(value, word)
        texts[name] = text
    left = {name: sorted(set(re.findall(UUID, text))) for name, text in texts.items() if re.search(UUID, text)}
    assert not left, 'STOP: an identifier of another kind is left; decide about it first: ' + repr(left)

    # 3. The audits, one row per boot, in boot order.
    baseline = json.loads((evidence / 'protected-baseline.json').read_text())['sha256']
    audits = []
    for path in evidence.glob('*-protected.json'):
        stage = path.name.removesuffix('-protected.json')
        boot = json.loads((evidence / (stage + '-bootnext-audit.json')).read_text())['boot']
        audits.append(dict(boot=boot, stage=stage, protected_disk_equals_baseline=json.loads(path.read_text())['sha256'] == baseline))
    audits.sort(key=lambda row: row['boot'])
    assert audits and [row['boot'] for row in audits] == list(range(1, len(audits) + 1)), 'STOP: a boot without its audit'
    assert all(row['protected_disk_equals_baseline'] for row in audits), 'STOP: a protected-disk audit differs from the baseline'

    folder = ROOT / 'reviews/22c-ways-back-after-update/runs' / f'{kind}-{run}'
    folder.mkdir(parents=True, exist_ok=False)
    for name, text in texts.items():
        (folder / name).write_text(text, encoding='utf-8', newline='\n')
    index = dict(run='https://github.com/Ares-Empire/AresOS/actions/runs/' + run, kind=kind, commit=result.get('commit'),
                 status=result['status'], files=sorted(names),
                 replaced=dict(vm_root_filesystem_uuids=len(roots), boot_ids=len(boots),
                               rule='the same fixed word for the same value in every file; nothing else was changed'),
                 checked_for=list(FORBIDDEN), protected_disk_baseline_sha256=baseline, audits=audits)
    (folder / 'index.json').write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f'wrote {len(names) + 1} files to {folder.relative_to(ROOT)}; {len(audits)} audits equal the baseline\n')
    print('| Stage | Reached by | Order | Runs | bootc booted / rollback | rollbackQueued | Pinned (origin file) | Titles top to bottom | Swap |')
    print('|---|---|---|---|---|---|---|---|---|')
    for row in result['stages']:
        titles = '; '.join(f"{t['title'].split('(')[-1].rstrip(')')} {t['role']}" for t in row['titles'])
        pins = ', '.join(row['pinned']) + ' (' + ', '.join(role for role, pinned in sorted(row['origin_pins'].items()) if pinned) + ')'
        print(f"| `{row['stage']}` | {row['reached']} | {' '.join(row['order'])} | {row['running']} | "
              f"{row['bootc_booted']} / {row['bootc_rollback']} | {str(row['rollback_queued']).lower()} | {pins} | {titles} | "
              f"{row['bootconfig_swap'] or ''} |")


if __name__ == '__main__':
    main()
