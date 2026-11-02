"""Read-only replay of the failed host-source gate using Git checkout filters."""
import hashlib,json,pathlib,re,subprocess,sys
r=pathlib.Path.cwd();w=r/'.work/14';run=41363231606;head='dda72ed8a5bdb038d953f950f76c66fc37297115'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
rows=read(r/'os/manifest/ci/14/host-walk/result.json')['sources'];mismatches=[]
for row in rows:
 p=row['path'];blob=subprocess.check_output(['git','show',head+':'+p])
 assert sha(blob)==row['sha256'],('Unexpected Git-blob binding',p)
 filtered=subprocess.check_output(['git','cat-file','--filters','--path='+p,head+':'+p])
 if sha(filtered)!=row['sha256']:
  mismatches.append(dict(bound_sha256=row['sha256'],checkout_sha256=sha(filtered),path=p,
    blob_bytes=len(blob),checkout_bytes=len(filtered),blob_crlf=blob.count(b'\r\n'),
    checkout_crlf=filtered.count(b'\r\n'),lf_to_crlf_only=filtered==blob.replace(b'\n',b'\r\n'),
    attributes=subprocess.check_output(['git','check-attr','text','eol','--',p],text=True).splitlines()))
assert len(mismatches)==1 and mismatches[0]['path']=='os/tests/owner-tools.Tests.ps1'
assert mismatches[0]['lf_to_crlf_only']
base=w/('run-'+str(run));native=(base/'native.log').read_text(encoding='utf-8')
assert re.search(r'Ran 627 tests in 163\.918s',native) and re.search(r'Z OK\s*$',native,re.M)
assert not re.search(r'^.*Z (?:FAIL:|ERROR:|FAILED \()',native,re.M)
full=w/'14zzd'/('basic-'+str(run))/'full-logs/1_Pinned live ISO inspection and two-disk rehearsal.txt'
t=full.read_text(encoding='utf-8');assert 'AssertionError: Host walk is stale' in t
assert not (base/'evidence/two-disk').exists()
v=dict(status='proven checkout-filter mismatch; native failing row not named in its assertion',run=run,head=head,
 native_tests=627,native_seconds=163.918,native_skips=0,native_errors=0,native_failures=0,
 gate='owner_vm.main host-walk source byte hashes, before Media.create and Guest boot',
 sources=len(rows),git_blob_bindings_passed=len(rows),checkout_filter_mismatches=mismatches,
 provenance='git show HEAD:path then git cat-file --filters --path=path HEAD:path; exact pushed-tree attributes',
 proven='The only checkout-filter mismatch is the PowerShell test: its committed manifest binds LF bytes, while eol=crlf expands checkout bytes. The native guard reads checkout bytes.',
 inference='This exactly reproduces the stale-source condition on the pushed tree. The native assertion does not export the failing row, so its individual runtime hash was not retained.',
 actions_rerun=False,qualification_dispatched=False,pushed_tree_changed=False,
 native_log=dict(sha256=sha((base/'native.log').read_bytes()),path=(base/'native.log').relative_to(r).as_posix()),
 full_log=dict(sha256=sha(full.read_bytes()),path=full.relative_to(r).as_posix()))
(w/'14zzd/stop-diagnosis.json').write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
(w/'14zzd/STOP-reason.txt').write_text('probe 33 passed all 627 native tests, then owner_vm.main refused Host walk is stale before guest boot. Read-only Git checkout-filter replay proves the PowerShell test source binding is LF while its declared checkout is CRLF. Qualification 21 was not dispatched',encoding='utf-8',newline='\n')
print(json.dumps(dict(status=v['status'],sources=len(rows),mismatches=mismatches,native_tests=627,native_seconds=163.918),indent=2))
