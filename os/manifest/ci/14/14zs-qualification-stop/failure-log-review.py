import pathlib,json,zipfile,subprocess,hashlib
r=pathlib.Path.cwd();b=r/'.work/14/run-40897501964'
scanner=r/'.work/14/gitleaks/gitleaks.exe'
assert hashlib.sha256(scanner.read_bytes()).hexdigest()=='671591bd75e11fcd4a25732852afbbf0c3892b368181164ba19aa72e7513af8e'
with zipfile.ZipFile(b/'logs.zip') as archive:
    names=[name for name in archive.namelist() if 'Prepare disposable file disks' in name and name.endswith('.txt')]
    assert len(names)==1
    data=archive.read(names[0]);assert len(data)<10_000_000
(b/'failure.log').write_bytes(data)
p=r/'.work/14/gitleaks/14zs-qualification-failure-log.json'
result=subprocess.run([str(scanner),'stdin','--redact=100','--no-banner','--log-level=warn','--report-format=json','--report-path='+str(p)],input=data,capture_output=True)
assert result.returncode==0 and json.loads(p.read_text())==[],'STOP: failure log privacy finding'
text=data.decode('utf-8');start=text.rfind('Traceback (most recent call last)')
assert start>=0
print('PASS failure log privacy:0')
print(text[start:][-7000:])
