import pathlib,subprocess
r=pathlib.Path.cwd();d=r/'.work/14/14zzd/linux-filter';assert not d.exists()
for name in ('.gitattributes','os/tests/owner-tools.Tests.ps1'):
 p=d/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes(subprocess.check_output(['git','show','dda72ed8a5bdb038d953f950f76c66fc37297115:'+name]))
