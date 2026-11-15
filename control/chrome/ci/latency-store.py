"""Where the latency pair's store lived, as the kernel reports it (brief 20-ci-noise).

run.sh mounts a tmpfs over each store directory for both runtimes, so the
timed phases measure the product rather than the shared runner's disk sync.
`start` records each directory's mount from /proc/self/mountinfo, never
assumed; `end` adds the space the run used, which is what sized the tmpfs.
"""
import json
import os
from pathlib import Path
import re
import sys

# The service's state (control.sqlite, blobs) and evidence (the journal and
# its index) directories, as control/chrome/ci/service.py configures them.
STORE=('/var/lib/aresos-tools','/var/lib/aresos-operation-evidence')


def decoded(field):
    # mountinfo writes space, tab, newline and backslash as octal escapes.
    return re.sub(r'\\([0-7]{3})',lambda match:chr(int(match[1],8)),field)


def mounts(text):
    table=[]
    for line in text.splitlines():
        before,after=line.split(' - ',1)
        fields=before.split();fstype,source,options=after.split(' ',2)
        table.append({'mount_point':decoded(fields[4]),'fstype':fstype,'source':decoded(source),'options':options})
    return table


def mount_of(path,table):
    """The mount a path is on: the longest mount point above it; later lines stack over earlier ones."""
    path=os.path.realpath(path);found=None
    for row in table:
        point=row['mount_point']
        if (path==point or path.startswith(point.rstrip('/')+'/')) and (found is None or len(point)>=len(found['mount_point'])):
            found=row
    return found


def usage(path):
    info=os.statvfs(path)
    return info.f_blocks*info.f_frsize,(info.f_blocks-info.f_bfree)*info.f_frsize


def record(stage,output,mountinfo=Path('/proc/self/mountinfo'),directories=STORE):
    table=mounts(mountinfo.read_text())
    if stage=='start':
        value={'directories':{}}
        for directory in directories:
            size,used=usage(directory)
            value['directories'][directory]={**mount_of(directory,table),'size_bytes':size,'used_bytes_start':used}
    else:
        value=json.loads(output.read_text())
        for directory in directories:
            # The store must still be on the mount recorded at the start.
            assert mount_of(directory,table)=={key:value['directories'][directory][key] for key in ['mount_point','fstype','source','options']},'Store mount changed during the run'
            value['directories'][directory]['used_bytes_end']=usage(directory)[1]
    output.write_text(json.dumps(value,indent=2)+'\n')
    return value


if __name__=='__main__':
    stage,output=sys.argv[1],Path(sys.argv[2])
    assert stage in {'start','end'},'latency-store.py start|end OUTPUT'
    print(json.dumps(record(stage,output),indent=2))
