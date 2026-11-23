"""Read the owned game scope's final counters before cleanup removes it. No attach or cgroup writes."""
import json
from pathlib import Path
import subprocess
import sys
import time

pid,unit,rig=sys.argv[1:]
assert unit.startswith('pkg318-game-') and unit.endswith('.scope')
record={'monotonic_ns':time.monotonic_ns(),'unit':unit}
group=subprocess.run(['systemctl','--user','show','-P','ControlGroup',unit],capture_output=True,text=True,timeout=2).stdout.strip()
if group and Path(group).name==unit:
    base=Path('/sys/fs/cgroup')/group.lstrip('/')
    for file in ('memory.events','memory.peak','memory.swap.current'):
        try:record[file]=(base/file).read_text().strip()
        except FileNotFoundError:record[file]=None
for file in ('game.txt','gradle.txt'):
    path=Path(rig)/file
    if path.exists() and 'OutOfMemoryError' in path.read_text(errors='replace'):record['out_of_memory']=True
(Path(rig)/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
