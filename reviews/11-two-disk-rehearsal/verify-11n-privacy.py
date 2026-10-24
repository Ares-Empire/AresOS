"""Bind original privacy logs to all three successful checks, including raw scans."""
import ast
import base64
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import zipfile

proof_path, prefix, destination = sys.argv[1:]
proofs = json.loads(pathlib.Path(proof_path).read_text())
assert len(proofs) == 2
tree = ast.parse(pathlib.Path('reviews/11-two-disk-rehearsal/verify-11n-evidence.py').read_text())
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'check_archive' or
         isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'credential' for t in n.targets)]
assert len(nodes) == 2
scope = dict(re=re, base64=base64, zipfile=zipfile)
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<owned archive verifier>', 'exec'), scope)
results = []
for proof in proofs:
    assert proof['status'] == 'passed' and proof['personal_terms_skip_warning'] is False
    assert proof['steps_metadata_available']
    assert proof['checks'] == {name: 'success' for name in ('No secrets (gitleaks)', 'Only private commit emails', 'No personal terms')}
    path = pathlib.Path(prefix + str(proof['run']) + '-logs.zip')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == proof['logs_zip_sha256']
    scanned = scope['check_archive'](path)
    with zipfile.ZipFile(path) as archive:
        text = archive.read('0_scan.txt').decode('utf-8-sig')
    groups = re.findall(r'##\[group\]Run ([^\n]+)', text)
    assert sum(g.startswith('docker run --rm') and 'gitleaks:v8.21.2' in g for g in groups) == 1
    assert sum(g.startswith('bad=$(git log --all') for g in groups) == 1
    assert sum(g.startswith('if [ -z "$PRIVATE_TERMS" ]') for g in groups) == 1
    assert '##[error]' not in text and '##[warning]PRIVATE_TERMS secret is not set' not in text
    workflow = subprocess.check_output(['git', 'show', proof['head'] + ':.github/workflows/privacy-check.yml'])
    assert hashlib.sha256(workflow).hexdigest() == proof['workflow_sha256']
    assert b'continue-on-error' not in workflow
    results.append(dict(run=proof['run'], head=proof['head'], status='passed', all_three_checks=True,
                        personal_terms_enabled=True, archive_records_scanned=scanned, zip_sha256=digest))
pathlib.Path(destination).write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8', newline='\n')
print('Both privacy archives independently verified: all3 checks, no personal-term skip, original hashes and raw/base64 credential scans passed.')
