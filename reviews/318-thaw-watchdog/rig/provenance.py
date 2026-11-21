"""Capture only explicitly allowed runtime facts from this run's owned JVM."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

pid=int(sys.argv[1]);rig=Path(sys.argv[2]);root=Path(__file__).resolve().parents[3]
args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
environ=dict(v.split(b'=',1) for v in (Path('/proc')/str(pid)/'environ').read_bytes().split(b'\0') if b'=' in v)
allowed=('MALLOC_ARENA_MAX','GLIBC_TUNABLES','JE_MALLOC_CONF','__NV_PRIME_RENDER_OFFLOAD','__GLX_VENDOR_LIBRARY_NAME','__VK_LAYER_NV_optimus','ALSOFT_DRIVERS','DISPLAY','WAYLAND_DISPLAY')
flags=[a.decode() for a in args if a.startswith((b'-Xms',b'-Xmx',b'-XX:',b'-Dorg.lwjgl'))]
files=list((root/'mod/build/libs').glob('*.jar'))+[rig.parents[1]/'pkg41-frames.jar']
facts={'pid':pid,'flags':flags,'environment':{k:environ.get(k.encode(),b'').decode() for k in allowed},'cgroup':(Path('/proc')/str(pid)/'cgroup').read_text().strip(),'executable_sha256':hashlib.sha256((Path('/proc')/str(pid)/'exe').resolve().read_bytes()).hexdigest(),'jars_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.exists()},'git_objects':dict(zip(('revision','mod_tree','helper_blob','labwc_blob'),subprocess.check_output(['git','rev-parse','HEAD','HEAD:mod','HEAD:os/config/usr/libexec/aresos-shell','HEAD:os/config/usr/share/aresos/labwc/rc.xml'],cwd=root,text=True).splitlines()))}
(rig/'provenance.json').write_text(json.dumps(facts,indent=2)+'\n')
