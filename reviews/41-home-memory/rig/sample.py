#!/usr/bin/python3
# DEVELOPMENT AID of package 41 (measurement only): the game's memory over time, every <seconds>, until it exits.
"""usage: sample.py <game pid> <out.csv> [seconds]

Columns: monotonic ns, RSS MiB (/proc/<pid>/status, cheap: no page-table walk), memory scope current MiB, and the
scope's anon and file MiB (memory.stat). PSS needs a walk of every mapping and is taken only in snapshots."""
import os, sys, time

pid, path = int(sys.argv[1]), sys.argv[2]
every = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
cgroup = [line.split('::', 1)[1].strip() for line in open(f'/proc/{pid}/cgroup') if line.startswith('0::')][0]
base = '/sys/fs/cgroup' + cgroup
with open(path, 'a') as out:
    out.write('monotonic_ns,rss_mib,cgroup_current_mib,cgroup_anon_mib,cgroup_file_mib\n')
    while True:
        try:
            rss = next(int(line.split()[1]) for line in open(f'/proc/{pid}/status') if line.startswith('VmRSS:'))
            current = int(open(base + '/memory.current').read())
            stat = dict(line.split() for line in open(base + '/memory.stat'))
        except (OSError, StopIteration):
            break
        out.write(f'{time.monotonic_ns()},{rss // 1024},{current >> 20},{int(stat["anon"]) >> 20},{int(stat["file"]) >> 20}\n')
        out.flush()
        time.sleep(every)
