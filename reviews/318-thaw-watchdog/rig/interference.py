"""Read-only host watch. Publish process classes/counts, never command lines or personal paths."""
import json
import os
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent))
from host import context


def external_work():
    found=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit(): continue
        try:
            comm=(proc/'comm').read_text().strip()
            if comm not in ('java','javaw','javac'): continue
            group=(proc/'cgroup').read_text()
            if 'pkg318-rig-' in group or 'pkg318-game-' in group: continue
            args=(proc/'cmdline').read_bytes().replace(b'\0',b' ').lower()
            kind='gradle' if any(token in args for token in (b'gradledaemon',b'gradlewrappermain',b'org.gradle')) else 'game' if any(token in args for token in (b'devlaunchinjector',b'net.minecraft',b'knotclient',b'lunar')) else 'other-java'
            found.append({'pid':int(proc.name),'kind':kind})
        except (OSError, ProcessLookupError): pass
    return found


if __name__=='__main__':
    with Path(sys.argv[1]).open('a') as output:
        while True:
            output.write(json.dumps({**context(),'external_java':external_work()})+'\n')
            output.flush()
            time.sleep(2)
