"""Regression for the real compressed-PNG false positive; no real secrets used."""
import ast
import base64
import pathlib
import re
import zipfile

root=pathlib.Path.cwd()
source=root/'reviews/11-two-disk-rehearsal/verify-11i-evidence.py'
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.Assign)
          and any(isinstance(t,ast.Name) and t.id=='credential' for t in n.targets))
pattern=re.compile(ast.literal_eval(node.value.args[0]))
for prefix in (b'$6$salt$',b'$6$rounds=10000$salt$',b'$y$j9T$salt$'):
    assert pattern.search(prefix+b'A'*86), 'A valid crypt specimen was missed'
for token in (b'ghp_'+b'A'*36,b'github_pat_'+b'A'*40):
    assert pattern.search(token)
    assert pattern.search(base64.b64decode(base64.b64encode(token)))
with zipfile.ZipFile(root/'reviews/11-two-disk-rehearsal/artifacts/11f-probe-1-two-disk-evidence.zip') as z:
    raw=z.read('two-disk/protected-second/configuration-00-answered.png')
    assert re.search(rb'\$6\$[^\s\x27\x22<>]{15,}',raw), 'The historical false-positive fixture changed'
    assert not pattern.search(raw)
print('ASCII SHA512/rounds/yescrypt hashes and raw/decoded token fixtures detected; real compressed PNG has no credential match.')
