#!/usr/bin/python3
"""Read-only diagnosis around an owned rig game's return; does not thaw, signal or attach to the JVM."""
import json
import pathlib
import sys
import time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from scope import owned_scope

pid, unit, folder = int(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
group = owned_scope(pid, unit)
initial = pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]
deadline = time.monotonic()+20*60
end = None
with (folder/'return-observer.jsonl').open('w') as output:
    while time.monotonic() < deadline:
        marks = dict(line.split() for line in (folder/'marks.txt').read_text().splitlines())
        now = time.monotonic_ns()
        if 'return_start' not in marks:
            time.sleep(.1)
            continue
        if end is None: end = now+3*10**9
        record = {'monotonic_ns':now, 'after_return_ms':round((now-int(marks['return_start']))/1e6,3)}
        # Read the group's last counters first: it can disappear as soon as the last process is reaped.
        for name in ('cgroup.events','memory.events','memory.current','memory.peak','memory.swap.current','memory.pressure'):
            try: record[name] = (group/name).read_text().strip()
            except FileNotFoundError: record[name] = None
        try:
            fields = pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
            if fields[19] != initial:
                record['pid_reused'] = True
                output.write(json.dumps(record)+'\n'); output.flush()
                break
            record.update(state=fields[0], majflt=int(fields[9]), exit_code=int(fields[49]))
            record['status'] = '\n'.join(line for line in pathlib.Path(f'/proc/{pid}/status').read_text().splitlines()
                if line.split(':')[0] in {'State','VmRSS','VmHWM','VmSwap','SigPnd','ShdPnd'})
        except FileNotFoundError:
            record['process_gone'] = True
        output.write(json.dumps(record)+'\n'); output.flush()
        if now >= end: break
        time.sleep(.02)
