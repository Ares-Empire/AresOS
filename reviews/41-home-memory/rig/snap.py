#!/usr/bin/python3
# DEVELOPMENT AID of package 41 (measurement only): one memory snapshot of the game.
"""usage: snap.py <game pid> <label> <out folder>

Writes <out>/snap-<label>.json and the raw jcmd outputs: the process's RSS and PSS (/proc), its memory scope's
current and peak use (cgroup v2: what MemoryHigh acts on), the Java heap (jcmd GC.heap_info), native memory
(jcmd VM.native_memory summary; the game runs with -XX:NativeMemoryTracking=summary) and its GPU memory
(nvidia-smi). The PID is given, never searched for."""
import json, os, re, subprocess, sys, time
import xml.etree.ElementTree as ET

pid, label, out = int(sys.argv[1]), sys.argv[2], sys.argv[3]
jcmd = os.path.join(os.environ.get('JAVA_HOME') or os.path.expanduser('~/.local/opt/jdk-25'), 'bin/jcmd')
snap = {'label': label, 'monotonic_ns': time.monotonic_ns(), 'time': time.strftime('%H:%M:%S')}


def kib_fields(path, names):
    values = {}
    with open(path) as source:
        for line in source:
            key, _, rest = line.partition(':')
            if key in names:
                values[key] = int(rest.split()[0]) // 1024  # MiB
    return values


snap['status_mib'] = kib_fields(f'/proc/{pid}/status', {'VmRSS', 'VmHWM', 'RssAnon', 'RssFile', 'RssShmem', 'VmSwap'})
snap['smaps_rollup_mib'] = kib_fields(f'/proc/{pid}/smaps_rollup', {'Rss', 'Pss', 'Pss_Anon', 'Pss_File', 'Pss_Shmem', 'Swap'})
cgroup = [line.split('::', 1)[1].strip() for line in open(f'/proc/{pid}/cgroup') if line.startswith('0::')][0]
base = '/sys/fs/cgroup' + cgroup
snap['cgroup'] = cgroup
mib = lambda name: int(open(os.path.join(base, name)).read()) // 2**20
snap['cgroup_mib'] = {'current': mib('memory.current'), 'peak': mib('memory.peak'),
                      'swap': mib('memory.swap.current'), 'high': open(os.path.join(base, 'memory.high')).read().strip()}
stat = dict(line.split() for line in open(os.path.join(base, 'memory.stat')))
snap['cgroup_mib'].update({key: int(stat[key]) // 2**20 for key in ('anon', 'file', 'kernel', 'shmem') if key in stat})
snap['cgroup_events'] = dict((k, int(v)) for k, v in (line.split() for line in open(os.path.join(base, 'memory.events'))))


def run(*command):
    return subprocess.run(command, capture_output=True, text=True, timeout=60).stdout


heap = run(jcmd, str(pid), 'GC.heap_info')
open(os.path.join(out, f'heap-{label}.txt'), 'w').write(heap)
match = re.search(r'total reserved (\d+)K, committed (\d+)K, used (\d+)K', heap)
if match:
    snap['heap_mib'] = {'reserved': int(match[1]) // 1024, 'committed': int(match[2]) // 1024, 'used': int(match[3]) // 1024}
match = re.search(r'region size (\d+)K, (\d+) young .*?, (\d+) survivors', heap)
if match:
    snap['heap_regions'] = {'region_kib': int(match[1]), 'young': int(match[2]), 'survivors': int(match[3])}
nmt = run(jcmd, str(pid), 'VM.native_memory', 'summary', 'scale=MB')
open(os.path.join(out, f'nmt-{label}.txt'), 'w').write(nmt)
snap['nmt_committed_mib'] = {}
for name, committed in re.findall(r'^-?\s*([A-Za-z][A-Za-z ]*?) \(reserved=\d+MB, committed=(\d+)MB', nmt, re.M):
    snap['nmt_committed_mib'][name.strip()] = int(committed)
match = re.search(r'Total: reserved=\d+MB, committed=(\d+)MB', nmt)
if match:
    snap['nmt_committed_mib']['Total'] = int(match[1])
try:
    root = ET.fromstring(run('/usr/bin/nvidia-smi', '-q', '-x'))
    gpu = root.find('gpu')
    snap['gpu_total_used_mib'] = int(gpu.find('fb_memory_usage/used').text.split()[0])
    for process in gpu.iter('process_info'):
        if process.findtext('pid') == str(pid):
            snap['gpu_process_mib'] = int(process.findtext('used_memory').split()[0])
except Exception as error:  # GPU numbers are a bonus; never fail the snapshot for them
    snap['gpu_error'] = repr(error)
json.dump(snap, open(os.path.join(out, f'snap-{label}.json'), 'w'), indent=1)
print(f"{label}: RSS {snap['status_mib'].get('VmRSS')} MiB, PSS {snap['smaps_rollup_mib'].get('Pss')} MiB, "
      f"heap {snap.get('heap_mib')}, NMT {snap['nmt_committed_mib'].get('Total')} MiB, "
      f"cgroup {snap['cgroup_mib']['current']}/{snap['cgroup_mib']['peak']} MiB, GPU {snap.get('gpu_process_mib')} MiB")
