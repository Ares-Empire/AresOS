import pathlib,json,hashlib,re,sys,importlib.util
r=pathlib.Path.cwd();b=r/'.work/14/run-40844950597';scan=r/'.work/14/gitleaks/14zq-qualification-artifact.json'
spec=importlib.util.spec_from_file_location('classify',r/'reviews/14-owner-tools/classify-artifacts.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
iso=[];kernel=[];unknown=[]
for row in json.loads(scan.read_text()):
    path=(r/row['File'].replace('\\','/')).resolve();assert path.is_relative_to(b.resolve())
    if path==b/'evidence/installer/squashfs-files.txt':iso.append(row);continue
    lines=path.read_bytes().split(b'\n');line=lines[row['StartLine']-1].removesuffix(b'\r');whole=c.KERNEL.fullmatch(line.decode('utf-8'))
    metadata=dict(sha256=hashlib.sha256(line).hexdigest(),path=path.relative_to(b).as_posix(),line=row['StartLine'],end_line=row['EndLine'],rule=row['RuleID'],match=row['Match'])
    permitted=path.parent==(b/'evidence/two-disk') and re.fullmatch('[a-z0-9-]+-boot-console\\.txt',path.name) and row['StartLine']==row['EndLine'] and whole and row['RuleID']=='generic-api-key' and re.fullmatch(r"key: REDACTED'",row['Match'])
    if permitted:
        metadata.update(c.kernel_line(line.decode('utf-8')));kernel.append(metadata)
    else:
        metadata.update(exact_whole_kernel_message=bool(whole),policy='unclassified; outside current14s/14v exception; STOP')
        unknown.append(metadata)
assert len(iso)==507
value=dict(status='STOP unclassified artifact findings; no rule/ignore changes',run=40844950597,head=json.loads((b/'receipt.json').read_text())['head'],findings=len(iso)+len(kernel)+len(unknown),iso_listing_findings=507,kernel_certificate_findings=kernel,unclassified=unknown,raw_lines_or_secrets_saved=False)
(b/'14zq-privacy-stop.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
print('PRIVACY_STOP',len(iso),'reviewed ISO;',len(kernel),'allowed exact kernel;',len(unknown),'unclassified')
for v in unknown:print(json.dumps(v))
diag=json.loads((b/'evidence/two-disk/layout-us-begin-owner-diagnostics.json').read_text())
login=[{k:t[k] for k in ('command','stdout','stderr','returncode') if k in t} for t in diag['trace'] if t.get('command',[None])[0]=='loginctl']
(b/'14zq-layout-session.json').write_text(json.dumps(dict(sha256=hashlib.sha256((b/'evidence/two-disk/layout-us-begin-owner-diagnostics.json').read_bytes()).hexdigest(),path='evidence/two-disk/layout-us-begin-owner-diagnostics.json',error=diag['error'],mutation_calls=sum(t.get('mutation') is True for t in diag['trace']),loginctl=login,expected_audit_value_not_retained=True),indent=2)+'\n',newline='\n')
print('SESSION_READS',json.dumps(login))
