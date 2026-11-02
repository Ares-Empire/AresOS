"""Verify the checkout-byte diagnosis using existing Linux Git, without checkout."""
import hashlib,json,pathlib,subprocess
r=pathlib.Path.cwd();head='dda72ed8a5bdb038d953f950f76c66fc37297115'
fixture=r/'.work/14/14zzd/linux-filter';assert fixture.is_dir() and not (fixture/'.git').exists()
subprocess.run(['git','init','-q',str(fixture)],check=True)
p='os/tests/owner-tools.Tests.ps1'
subprocess.run(['git','-C',str(fixture),'add','--','.gitattributes',p],check=True)
b=subprocess.check_output(['git','-C',str(fixture),'cat-file','--filters','--path='+p,':'+p]);h=hashlib.sha256(b).hexdigest()
bad=[dict(sha256=h,path=p,bytes=len(b),crlf=b.count(b'\r\n'))]
assert bad==[dict(sha256='62a1fd816586ffae3fb1f2f35072d1e2da9373fb9359930eb323684103772948',path='os/tests/owner-tools.Tests.ps1',bytes=4961,crlf=72)]
v=dict(status='same PowerShell checkout-filter mismatch under Linux Git',git=subprocess.check_output(['git','--version'],text=True).strip(),head=head,
 fixture='isolated two-file Git fixture within .work; exact pushed .gitattributes and PowerShell test blobs; original worktree metadata untouched',
 mismatches=bad,tracked_working_tree_mutations=False,
 initial_direct_linux_attempt='Windows absolute gitdir in .git is not a Linux pathname; no metadata modification attempted')
(r/'.work/14/14zzd/linux-checkout-proof.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v))
