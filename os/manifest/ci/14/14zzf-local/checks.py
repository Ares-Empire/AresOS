"""Local-only 14zzf receipts. No network, push or dispatch."""
import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import unittest

r = pathlib.Path.cwd()
w = r / '.work/14/14zzf'
out = r / 'os/manifest/ci/14/14zzf-local'
out.mkdir(exist_ok=True)
pin = '3e2c78ebedf7789b0616e7a4f21ad791d76784667344e76e97a1fbd95115a6fd'
sys.path[:0] = [str(r/'os/tests'), str(r/'os/ci')]
import test_owner_export as tests
import test_owner_tools as common
git = '/mnt/c/Program Files/Git/cmd/git.exe' if sys.platform == 'linux' else 'git'

assert common.bundle.check(r/'os/owner-tools/payload') == pin, 'STOP: frozen payload differs'
for prefix in ['os/owner-tools', 'os/release', 'os/ci', '.github', '.gitattributes', '.gitleaksignore', '.gitleaks.toml', 'docs']:
    subprocess.run([git, 'diff', '--exit-code', '04d4051', '--', prefix], check=True)

if sys.argv[1:] == ['negative']:
    old = subprocess.check_output([git,'rev-parse','bd85527'],text=True).strip()
    archive = w/'pre-14zzc-exact'
    assert not archive.is_symlink()
    raw = subprocess.check_output([git,'show',old+':os/owner-tools/payload/SHA256.json'])
    rows = json.loads(raw)
    archive.mkdir(exist_ok=True)
    for name in [row['path'] for row in rows] + ['SHA256.json']:
        p = archive/name
        p.parent.mkdir(parents=True,exist_ok=True)
        expected = subprocess.check_output([git,'show',old+':os/owner-tools/payload/'+name])
        if p.exists():
            assert p.read_bytes() == expected
        else:
            p.write_bytes(expected)
    assert b"STOP_RECORDS = pathlib.Path('/run/ares-owner-diagnostics')" in (archive/'owner.py').read_bytes()
    tests.ExportSurvivalTest.bundle_source = archive
    def historical_bundle(destination, source):
        # This format predates SHA256SUMS and its checker rejects that extra
        # file. Copy only the exact historical JSON manifest and its entries;
        # no production bytes, path constants or checks are substituted.
        destination.mkdir(parents=True)
        for row in rows:
            assert pathlib.PurePosixPath(row['path']).as_posix() == row['path'] and '..' not in row['path'].split('/')
            origin, target = source/row['path'], destination/row['path']
            assert hashlib.sha256(origin.read_bytes()).hexdigest() == row['sha256']
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(origin,target)
        shutil.copyfile(source/'SHA256.json',destination/'SHA256.json')
    tests.ExportSurvivalTest.copy_bundle = staticmethod(historical_bundle)
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(tests.ExportSurvivalTest))
    text = log.getvalue()
    assert result.testsRun == 1 and len(result.failures) == 1 and not result.errors and not result.skipped
    assert 'STOP diagnostic missing from persistent /var/lib/ares/diagnostics' in text
    assert '1 != 1' not in text
    text = text.replace(str(r), '<worktree>')
    (out/'pre-14zzc-negative.txt').write_text(text,encoding='utf-8',newline='\n')
    receipt = dict(status='expected failure at persistent-path assertion', source_commit=old,
        payload_fingerprint=hashlib.sha256(raw).hexdigest(),historical_manifest_format='SHA256.json only; exact manifest entries',
        tests=1,failures=1,errors=0,skips=0,production_code_rewritten=False,
        failure='STOP diagnostic missing from persistent /var/lib/ares/diagnostics',
        log=dict(sha256=hashlib.sha256((out/'pre-14zzc-negative.txt').read_bytes()).hexdigest(),path='pre-14zzc-negative.txt'))
    (out/'negative-control.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('EXPECTED_PRE_14ZZC_FAILURE',old,'persistent diagnostic absent',flush=True)
else:
    assert sys.argv[1:] in (['normal'],['no-bytecode'])
    mode = sys.argv[1]
    modules = ['test_owner_export','test_owner_diagnostics','test_owner_entry','test_owner_tools']
    command = [sys.executable, *(['-B'] if mode == 'no-bytecode' else []), '-m','unittest','-v',*modules]
    environment = dict(os.environ, PYTHONPATH=str(r/'os/tests')+os.pathsep+str(r/'os/ci'))
    environment.pop('PYTHONDONTWRITEBYTECODE',None)
    start = time.monotonic()
    with (out/(mode+'.txt')).open('w',encoding='utf-8',newline='\n') as log:
        result = subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT)
    text = (out/(mode+'.txt')).read_text()
    assert result.returncode == 0 and '\nOK\n' in text and 'skipped' not in text, text[-5000:]
    assert common.bundle.check(r/'os/owner-tools/payload') == pin
    receipt = dict(status='passed',mode=mode,command=['python3',*command[1:]],modules=modules,
        seconds=round(time.monotonic()-start,3),bytecode_environment='PYTHONDONTWRITEBYTECODE unset',
        payload_fingerprint=pin,log=dict(sha256=hashlib.sha256((out/(mode+'.txt')).read_bytes()).hexdigest(),path=mode+'.txt'))
    (out/(mode+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('AFFECTED_PASSED',mode,receipt['seconds'],text[text.rfind('Ran '):].strip(),flush=True)
