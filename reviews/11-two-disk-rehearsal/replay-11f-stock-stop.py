"""Replay the real pending-stock refusal without running guest commands."""
import ast
import contextlib
import hashlib
import io
import json
import pathlib
import re
import subprocess
from unittest.mock import patch

root=pathlib.Path.cwd()
folder=root/'os/manifest/ci/11f/full-2/two-disk'
text=(folder/'pin-stock.txt').read_text(encoding='utf-8')
text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
status=ast.literal_eval(text.split('AssertionError:',1)[1].splitlines()[0].strip())
script=root/'os/release/pin-stock.sh'
source=script.read_text().split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
with patch.object(subprocess,'check_output',return_value=json.dumps(status).encode()), patch.object(subprocess,'run') as command, contextlib.redirect_stdout(io.StringIO()):
    try:
        exec(compile(source,str(script),'exec'),{})
    except AssertionError:
        refused=True
    else:
        refused=False
    assert refused
    command.assert_not_called()
fields=('checksum','booted','staged','serial','pinned','version','container-image-reference','container-image-reference-digest')
deployments=[{k:d.get(k) for k in fields} for d in status['deployments']]
bootc=json.loads((folder/'stock-status.json').read_text())['status']
assert bootc['booted']['image']['imageDigest']=='sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151'
assert bootc['staged']['image']['imageDigest']=='sha256:d0e5e105ebf43c7ddbe3c4a5dfecac1628b0e0dcf152bbd2aee0eda3e4b4cdd4'
assert any(d['staged'] for d in deployments)
assert not (folder/'switch-inspection.json').exists()
assert not (folder/'verify-published-signature.txt').exists()
paths=[script,root/'os/ci/switch_vm.py',folder/'pin-stock.txt',folder/'stock-status.json',folder/'stock-initialization-0-boot-console.txt',folder/'stock-boot-console.txt']
def input_digest(path):
    raw=path.read_bytes()
    if path.suffix == '.txt':
        # Display captures are normalized before Git stores them with LF.
        raw=('\n'.join(line.rstrip() for line in raw.decode('utf-8').splitlines()).rstrip()+'\n').encode()
    return hashlib.sha256(raw).hexdigest()

record=dict(status='stopped',qualified=False,run=40054116223,source='1b00581df4b9871c9880db67e3f54ed2b82fb487',
    failure='pin-stock exit 1: pending staged upstream deployment; unchanged no-staged guard refused before pin or AresOS switch',
    command_replay='passed: same real rpm-ostree status triggers AssertionError; no ostree pin command executed',
    bootc=bootc, rpm_ostree_deployments=deployments,
    updater_started_in_boot_console='uupd.service' in (folder/'stock-initialization-0-boot-console.txt').read_text(),
    updater_causation='Inferred from uupd startup plus newer staged stock; no updater journal was collected',
    final_stock_zero_write_proof=False,reason='Host-terminated failure-close session has no stock-blockstats.json',
    aresos_switch_started=False,part_a='not qualified',part_b='untested',
    input_format='LF-normalized display text as committed; other input bytes exact; original ZIP receipts unchanged',
    inputs={p.relative_to(root).as_posix():input_digest(p) for p in paths})
(root/'os/manifest/ci/11f/full-stop-analysis.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(record['command_replay'])
print('Pinned stock booted; newer upstream stock staged; no AresOS switch or installed signature read reached.')
