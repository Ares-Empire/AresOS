"""14s/14v artifact review only; never changes scanner rules or ignores."""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
KERNEL = re.compile(r"\[[ \t]*[0-9]+\.[0-9]+\] Loaded X\.509 cert '(?P<label>[^'\r\n]+): (?P<fingerprint>[0-9a-fA-F]{40})'")


def kernel_line(line):
    match = KERNEL.fullmatch(line)
    assert match is not None, 'STOP: finding is not a complete kernel X.509 certificate boot message'
    return dict(sha256=hashlib.sha256(line.encode()).hexdigest(),
        certificate_label=match['label'], fingerprint_hex_length=40)


def classify(run, scan):
    base = ROOT/'.work/14'/('run-'+str(run))
    rows = json.loads(pathlib.Path(scan).read_text())
    assert isinstance(rows, list)
    listing, captured = base/'evidence/installer/squashfs-files.txt', base/'evidence/two-disk'
    certificates, iso = [], []
    for row in rows:
        assert row['RuleID'] == 'generic-api-key', 'STOP: unclassified artifact finding rule'
        path = (ROOT/row['File'].replace('\\', '/')).resolve()
        assert path.is_relative_to(base.resolve()), 'STOP: finding path outside current run'
        if path == listing.resolve():
            iso.append(row)
            continue
        assert path.parent == captured.resolve() and re.fullmatch(r'[a-z0-9-]+-boot-console\.txt', path.name), 'STOP: finding outside captured boot console'
        number = row['StartLine']
        assert type(number) is int and number == row['EndLine'], 'STOP: multiline or malformed finding'
        # Gitleaks counts LF-delimited source lines. Do not treat arbitrary
        # control characters as line breaks or strip them into a valid message.
        lines = path.read_bytes().split(b'\n')
        assert 1 <= number <= len(lines)
        line = lines[number-1].removesuffix(b'\r').decode('utf-8')
        proof = kernel_line(line)
        assert re.fullmatch(r"key: REDACTED'", row['Match']), 'STOP: unexpected redacted finding match'
        certificates.append(dict(**proof, path=path.relative_to(base).as_posix(), line=number,
            rule=row['RuleID'], classification='14v public kernel X.509 certificate fingerprint'))
    assert len(iso) == 507, 'STOP: public ISO listing count differs from reviewed 507'
    return dict(status='passed', run=int(run), head=json.loads((base/'receipt.json').read_text())['head'],
        scan=dict(sha256=hashlib.sha256(pathlib.Path(scan).read_bytes()).hexdigest(),
            path=pathlib.Path(scan).resolve().relative_to(ROOT).as_posix()),
        findings=len(rows), iso_listing_findings=len(iso), kernel_certificate_findings=certificates,
        policy='briefs/14s-loop-node-race.md and briefs/14v-efibootmgr-format.md; exact whole source line in captured boot console only',
        ignore_changes=False, workflow_changes=False, raw_consoles_committed=False)


if __name__ == '__main__':
    result = classify(sys.argv[1], sys.argv[2])
    target = pathlib.Path(sys.argv[3])
    target.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('PASS', result['findings'], 'classified artifact findings;', len(result['kernel_certificate_findings']), 'exact kernel lines; no ignore/rule changes')
