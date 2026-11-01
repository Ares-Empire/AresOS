"""Scan every completed job log, accepting only the pinned 14zzb checksum class."""
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import zipfile

r=pathlib.Path.cwd()
w=r/'.work/14'
run=sys.argv[1]
assert run.isdigit()
basic=w/'14zzb'/('basic-'+run)
receipt=json.loads((basic/'receipt.json').read_text())
head=json.loads((w/'14zzb-one-push-scan.json').read_text())['checked_commit']
assert receipt['head']==head
folder=basic/'full-logs'
if not folder.exists():
    folder.mkdir()
    with zipfile.ZipFile(basic/'logs.zip') as archive:
        for member in archive.infolist():
            p=pathlib.PurePosixPath(member.filename)
            assert not p.is_absolute() and '..' not in p.parts and '\\' not in member.filename and ':' not in member.filename
            if member.is_dir():continue
            target=folder/member.filename
            assert target.resolve().is_relative_to(folder.resolve())
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive.read(member))
scanner=w/'gitleaks/gitleaks.exe'
assert hashlib.sha256(scanner.read_bytes()).hexdigest()=='671591bd75e11fcd4a25732852afbbf0c3892b368181164ba19aa72e7513af8e'
scan=w/'gitleaks'/('14zzb-'+run+'-full-logs.json')
result=subprocess.run([str(scanner),'dir',str(folder),'--config',str(r/'.gitleaks.toml'),
    '--redact=100','--no-banner','--log-level=error','--report-format=json','--report-path',str(scan)])
assert result.returncode in (0,1), 'STOP: full-log scanner failed'
spec=importlib.util.spec_from_file_location('review',w/'14zzb-classify.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
value=review.classify_logs(run,scan,folder,json.loads((basic/'jobs.json').read_text()),head)
(basic/'log-privacy.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('PASS all job logs;',value['findings'],'findings in exact pinned-action class; no rule/ignore changes')
