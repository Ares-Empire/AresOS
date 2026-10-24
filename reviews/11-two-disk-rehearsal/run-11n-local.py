"""Run all native discovery under existing WSL without local elevation."""
import json
import pathlib
import subprocess

root = pathlib.Path.cwd()
work = root / '.work/11n'
for name in ('tmp', 'no-admin'):
    (work / name).mkdir(parents=True, exist_ok=True)
(work / 'no-admin/sudo').write_text('#!/bin/bash\necho "LOCAL_UNAVAILABLE: local elevation forbidden; this test requires disposable CI" >&2\nexit 126\n', encoding='utf-8', newline='\n')
(work / 'run-local.sh').write_text('''#!/bin/bash
set -euo pipefail
export TMPDIR="$PWD/.work/11n/tmp"
chmod +x .work/11n/no-admin/sudo
export PATH="$PWD/.work/11n/no-admin:$PATH"
exec python3 -m unittest discover -s os/tests -v
''', encoding='utf-8', newline='\n')
logs = root / 'reviews/11-two-disk-rehearsal/logs/11n'
logs.mkdir(parents=True, exist_ok=True)
command = ['wsl', '-d', 'Ubuntu', '--cd', '/mnt/c/Users/pab/AresOS-11-two-disk-rehearsal', '--exec',
           '/bin/bash', '--noprofile', '--norc', '.work/11n/run-local.sh']
with (logs / 'local-native-tests.txt').open('wb') as output:
    result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
print('Complete WSL native discovery exit:', result.returncode)
(work / 'local-result.json').write_text(json.dumps(dict(command=command, returncode=result.returncode, local_admin_blocked=True), indent=2) + '\n')
