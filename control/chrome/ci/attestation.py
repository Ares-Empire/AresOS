"""Real GitHub verifier fixture. Pure Python; no browser or profile access."""
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from aresos_control.chrome.qualification import verify

path=Path(sys.argv[1])
branch=os.environ.get('GITHUB_HEAD_REF') or os.environ['GITHUB_REF_NAME']
verify(path,branch=branch)
original=path.read_bytes()
try:
    path.write_bytes(original+b' ')
    try:verify(path,branch=branch)
    except Exception:pass
    else:raise AssertionError('Altered attestation subject was accepted')
finally:path.write_bytes(original)
try:verify(path,branch='untrusted-fixture-branch')
except Exception:pass
else:raise AssertionError('A different source branch was accepted')
print('QUALIFICATION DELIVERY real attestation / altered bytes / wrong branch PASS')
