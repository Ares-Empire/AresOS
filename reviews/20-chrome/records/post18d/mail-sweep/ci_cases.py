"""Per-flow sweep cases and seconds from `gh run view <id> --log` output.

Usage: ci_cases.py OUT.json label=run_id:log_path ...
Reads only the sweep's own 'Review26 modes: <flow> {...}; elapsed=Ns' lines.
A cancelled job contributes only the flows it finished.
"""
import ast
import json
import re
import sys

LINE = re.compile(r"^(sweep \((\d+)\))\t.*Review26 modes: (\S+) (\{.*?\}); elapsed=([0-9.]+)s")


def parse(path):
    flows = {}
    with open(path, encoding='utf-8', errors='replace') as stream:
        for line in stream:
            match = LINE.match(line)
            if not match:
                continue
            _, shard, flow, modes, elapsed = match.groups()
            if flow == '***':
                flow = 'password'  # GitHub masks the word in logs.
            modes = ast.literal_eval(modes)
            cases = modes.get('single', 0) + modes.get('persistent', 0) + modes.get('pairs', 0)
            flows[flow] = {'shard': int(shard), **modes, 'cases': cases, 'seconds': float(elapsed),
                           'ms_per_case': round(float(elapsed) / cases * 1000, 2)}
    return flows


def main():
    report = {}
    for argument in sys.argv[2:]:
        label, rest = argument.split('=', 1)
        run, path = rest.split(':', 1)
        flows = parse(path)
        cases = sum(f['cases'] for f in flows.values())
        seconds = sum(f['seconds'] for f in flows.values())
        report[label] = {'run': run, 'flows_finished': len(flows), 'cases': cases,
                         'seconds': round(seconds, 1), 'ms_per_case': round(seconds / cases * 1000, 2) if cases else None,
                         'flows': flows}
    with open(sys.argv[1], 'w') as out:
        json.dump(report, out, indent=1, sort_keys=True)
    for label, entry in report.items():
        print(label, entry['run'], entry['flows_finished'], entry['cases'], entry['seconds'], entry['ms_per_case'])


if __name__ == '__main__':
    main()
