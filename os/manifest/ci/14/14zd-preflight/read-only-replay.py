import pathlib,subprocess,os
root=pathlib.Path.cwd();os.environ['GITHUB_REPOSITORY']='Ares-Empire/AresOS'
for name,args in [('release',['python','-X','utf8','os/ci/verify_release.py','40154642447']),('zero-cost',['python','-X','utf8','reviews/14-owner-tools/verify-zero-cost.py','--14b','--listing','.work/14/squashfs-files.txt'])]:
 p=subprocess.run(args,capture_output=True,text=True,encoding='utf-8');(root/'.work/14'/('14zd-'+name+'-replay.log')).write_text(p.stdout+p.stderr,encoding='utf-8',newline='\n');assert p.returncode==0,(name,p.returncode)
 print('PASS actual read-only',name,'replay')
