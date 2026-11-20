#!/usr/bin/python3
"""Snapshot before any perturbation; PROBE then records trim, GC, heap info and the post-GC trim separately.

Anonymous mappings cannot reliably be assigned to a native allocator from smaps alone. Report anonymous,
[heap] (glibc's brk only), JVM heap (from GC.heap_info address), jemalloc library maps, NVIDIA and other files.
No claim is made that an anonymous VMA belongs to jemalloc rather than glibc or the JVM.
"""
import json, os, pathlib, re, subprocess, sys, time
import xml.etree.ElementTree as ET
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from host import context
from scope import jcmd


def kib_fields(path, names):
    return {key: int(rest.split()[0]) // 1024 for key, _, rest in
            (line.partition(':') for line in pathlib.Path(path).read_text().splitlines()) if key in names}


def memory(pid):
    cgroup = next(line.split('::', 1)[1].strip() for line in pathlib.Path(f'/proc/{pid}/cgroup').read_text().splitlines()
                  if line.startswith('0::'))
    base = pathlib.Path('/sys/fs/cgroup') / cgroup.lstrip('/')
    stat = dict(line.split() for line in (base / 'memory.stat').read_text().splitlines())
    fields = pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return {'status_mib': kib_fields(f'/proc/{pid}/status', {'VmRSS', 'VmHWM', 'RssAnon', 'RssFile', 'RssShmem', 'VmSwap'}),
            'smaps_rollup_mib': kib_fields(f'/proc/{pid}/smaps_rollup', {'Rss', 'Pss', 'Pss_Anon', 'Pss_File', 'Pss_Shmem', 'Swap'}),
            'cgroup': cgroup,
            'cgroup_mib': {**{key: int((base / name).read_text()) // 2**20 for key, name in
                              [('current', 'memory.current'), ('peak', 'memory.peak'), ('swap', 'memory.swap.current')]},
                           'high': (base / 'memory.high').read_text().strip(),
                           **{key: int(stat[key]) // 2**20 for key in ('anon', 'file', 'kernel', 'shmem') if key in stat}},
            'cgroup_events': {k: int(v) for k, v in (line.split() for line in (base / 'memory.events').read_text().splitlines())},
            'majflt': int(fields[9]), 'minflt': int(fields[7]), 'host': context(),
            'zram_mm_stat': {p.parent.name: [int(n) for n in p.read_text().split()]
                             for p in pathlib.Path('/sys/block').glob('zram*/mm_stat')}}


def smaps_classes(source, heap_range=None):
    classes = {}
    category = 'anonymous-unattributed'
    for line in source.splitlines():
        header = re.match(r'^([0-9a-f]+)-([0-9a-f]+)\s+\S+\s+\S+\s+\S+\s+\S+\s*(.*)', line)
        if header:
            start, end = int(header[1], 16), int(header[2], 16)
            name = header[3]
            if heap_range and heap_range[0] <= start < heap_range[1]: category = 'java-heap'
            elif name == '[heap]': category = 'glibc-brk'
            elif 'jemalloc' in name: category = 'jemalloc-library'
            elif '/dev/nvidiactl' in name: category = 'nvidiactl'
            elif 'nvidia' in name.lower(): category = 'nvidia-other'
            elif name.startswith('/'): category = 'other-files'
            elif name.startswith('[stack'): category = 'stack'
            else: category = 'anonymous-unattributed'
        elif ':' in line and line.split(':')[0] in {'Size', 'Rss', 'Pss', 'Anonymous', 'Swap', 'Private_Dirty'}:
            key, rest = line.split(':', 1)
            fields = classes.setdefault(category, {})
            fields[key + '_kib'] = fields.get(key + '_kib', 0) + int(rest.split()[0])
    return classes


def snapshot(pid, label, out):
    out = pathlib.Path(out)
    snap = {'label': label, 'monotonic_ns': time.monotonic_ns(), 'time': time.strftime('%H:%M:%S'), **memory(pid)}
    frozen = os.environ.get('PKG49_FROZEN') == '1'
    snap['frozen'] = frozen
    probe = os.environ.get('PKG49_PROBE') == '1'
    heap = ''
    snap['nmt_committed_mib'] = {}
    # Save the smaps before attaching or perturbing the process; never retain mapping paths in public output.
    raw_smaps = pathlib.Path(f'/proc/{pid}/smaps').read_text()
    if not frozen:
        if probe:
            records = [jcmd(pid, 'System.trim_native_heap')]
            snap['after_trim'] = memory(pid)
            records.append(jcmd(pid, 'GC.run'))
            snap['after_gc'] = memory(pid)
            records.append(jcmd(pid, 'System.trim_native_heap'))
            snap['after_gc_trim'] = memory(pid)
            (out / f'probe-{label}.json').write_text(json.dumps(records, indent=1) + '\n')
            snap['probe_commands_ok'] = all(c['exit'] == 0 for c in records)
        result = jcmd(pid, 'GC.heap_info')
        if result['exit']:
            raise RuntimeError(result)
        heap = result['stdout']
        (out / f'heap-{label}.txt').write_text(heap)
        match = re.search(r'total reserved (\d+)K, committed (\d+)K, used (\d+)K', heap)
        if match:
            snap['heap_mib'] = dict(zip(('reserved', 'committed', 'used'), (int(n) // 1024 for n in match.groups())))
        if os.environ.get('PKG49_NMT', '1') == '1':
            executable = pathlib.Path(os.environ.get('JAVA_HOME', os.path.expanduser('~/.local/opt/jdk-25'))) / 'bin/jcmd'
            result = subprocess.run([str(executable), str(pid), 'VM.native_memory', 'summary', 'scale=MB'],
                                    capture_output=True, text=True, timeout=60)
            if result.returncode: raise RuntimeError(result.stderr)
            nmt = result.stdout
            (out / f'nmt-{label}.txt').write_text(nmt)
            for name, committed in re.findall(r'^-?\s*([A-Za-z][A-Za-z ]*?) \(reserved=\d+MB, committed=(\d+)MB', nmt, re.M):
                snap['nmt_committed_mib'][name.strip()] = int(committed)
            match = re.search(r'Total: reserved=\d+MB, committed=(\d+)MB', nmt)
            if match: snap['nmt_committed_mib']['Total'] = int(match[1])
        else:
            executable = pathlib.Path(os.environ.get('JAVA_HOME', os.path.expanduser('~/.local/opt/jdk-25'))) / 'bin/jcmd'
            result = subprocess.run([str(executable), str(pid), 'VM.native_memory', 'summary'],
                                    capture_output=True, text=True, timeout=60)
            (out / f'nmt-{label}.txt').write_text(result.stdout)
            if result.returncode or 'Native memory tracking is not enabled' not in result.stdout:
                raise RuntimeError('NMT=0 requested but the JVM did not confirm tracking is disabled')
            snap['nmt_disabled_confirmed'] = True
    match = re.search(r'\[(0x[0-9a-f]+),\s*(0x[0-9a-f]+)\)', heap)
    snap['smaps_classes'] = smaps_classes(raw_smaps, tuple(int(n, 16) for n in match.groups()) if match else None)
    try:
        result = subprocess.run(['/usr/bin/nvidia-smi', '-q', '-x'], capture_output=True, text=True, timeout=15)
        gpu = ET.fromstring(result.stdout).find('gpu')
        snap['gpu_total_used_mib'] = int(gpu.findtext('fb_memory_usage/used').split()[0])
        for process in gpu.iter('process_info'):
            if process.findtext('pid') == str(pid): snap['gpu_process_mib'] = int(process.findtext('used_memory').split()[0])
    except Exception as error:
        snap['gpu_error'] = repr(error)
    (out / f'snap-{label}.json').write_text(json.dumps(snap, indent=1) + '\n')
    print(f"{label}: RSS {snap['status_mib'].get('VmRSS')} MiB; heap {snap.get('heap_mib')}; "
          f"scope {snap['cgroup_mib']['current']} MiB; swap {snap['cgroup_mib']['swap']} MiB; majflt {snap['majflt']}")


if __name__ == '__main__':
    snapshot(int(sys.argv[1]), *sys.argv[2:])
