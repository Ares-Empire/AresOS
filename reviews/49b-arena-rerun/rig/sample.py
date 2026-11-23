#!/usr/bin/python3
# DEVELOPMENT AID of package 49b (copied from package 41) (measurement only): the game's memory over time, every <seconds>, until it exits.
"""usage: sample.py <game pid> <out.csv> [seconds]

Columns: monotonic ns, RSS MiB (/proc/<pid>/status, cheap: no page-table walk), memory scope current MiB, the
scope's anon and file MiB (memory.stat), and the game's CPU time so far in seconds (/proc/<pid>/stat). PSS needs a walk of every mapping and is taken only in snapshots."""
import os, sys, time

pid, path = int(sys.argv[1]), sys.argv[2]
every = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
cgroup = [line.split('::', 1)[1].strip() for line in open(f'/proc/{pid}/cgroup') if line.startswith('0::')][0]
base = '/sys/fs/cgroup' + cgroup
with open(path, 'a') as out:
    out.write('monotonic_ns,rss_mib,cgroup_current_mib,cgroup_anon_mib,cgroup_file_mib,cpu_s,majflt,cgroup_swap_mib,host_available_mib,host_load1\n')
    tick = os.sysconf('SC_CLK_TCK')
    while True:
        try:
            rss = next(int(line.split()[1]) for line in open(f'/proc/{pid}/status') if line.startswith('VmRSS:'))
            current = int(open(base + '/memory.current').read())
            stat = dict(line.split() for line in open(base + '/memory.stat'))
            fields = open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()
            cpu = (int(fields[11]) + int(fields[12])) / tick
            swap = int(open(base + '/memory.swap.current').read()) >> 20
            available = next(int(line.split()[1]) // 1024 for line in open('/proc/meminfo') if line.startswith('MemAvailable:'))
        except (OSError, StopIteration):
            break
        out.write(f'{time.monotonic_ns()},{rss // 1024},{current >> 20},{int(stat["anon"]) >> 20},{int(stat["file"]) >> 20},{cpu:.2f},{fields[9]},{swap},{available},{os.getloadavg()[0]:.2f}\n')
        out.flush()
        time.sleep(every)
