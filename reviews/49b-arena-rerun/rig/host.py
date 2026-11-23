#!/usr/bin/python3
"""Privacy-safe host context: no command lines, user names, desktop titles or global process dumps."""
import json, os, pathlib, subprocess, sys, time


def context():
    mem = {line.split(':')[0]: int(line.split()[1]) for line in pathlib.Path('/proc/meminfo').read_text().splitlines()
           if line.split(':')[0] in {'MemAvailable', 'MemFree', 'SwapTotal', 'SwapFree'}}
    # Executable basenames and counts establish interference without publishing arguments or personal paths.
    counts = {}
    for proc in pathlib.Path('/proc').iterdir():
        if proc.name.isdigit():
            try:
                name = (proc / 'comm').read_text().strip()
                if name in {'java', 'node', 'python3', 'chrome', 'chromium', 'codex', 'claude', 'Xwayland', 'labwc', 'cage'}:
                    counts[name] = counts.get(name, 0) + 1
            except OSError:
                pass
    return {'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'monotonic_ns': time.monotonic_ns(),
            'loadavg': list(os.getloadavg()), 'memory_kib': mem, 'process_counts': counts}


if __name__ == '__main__':
    pathlib.Path(sys.argv[1]).write_text(json.dumps(context(), indent=1) + '\n')
