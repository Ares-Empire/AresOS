"""Stage medians and p95; nested stages are reported separately, never summed."""
import collections
import json
import math
from pathlib import Path
import statistics
import sys

root=Path(sys.argv[1]);client=json.loads((root/'latency-client.json').read_text())
rows=client['samples'];assert len(rows)==120
stages=collections.defaultdict(list)
for row in rows:stages[(row['call'],'client_total')].append(row['milliseconds'])
internal=collections.defaultdict(float)
for line in (root/'latency-service.jsonl').read_text().splitlines():
    row=json.loads(line)
    if row.get('sample') is None:continue
    internal[(row['sample'],row['call'],row['stage'])]+=row['milliseconds']
for (_,call,stage),duration in internal.items():stages[(call,stage)].append(duration)
def summary(values):
    ordered=sorted(values)
    return {'samples':len(values),'median_ms':statistics.median(values),'p95_ms':ordered[max(0,math.ceil(.95*len(values))-1)]}
result={'runtime':client['baseline'],'privacy':client['privacy'],'chrome':(root/'chrome-version.txt').read_text().strip(),
        'build':(root/'runtime-build.txt').read_text().strip(),
        'calls':{call:{stage:summary(values) for (category,stage),values in stages.items() if category==call} for call in sorted({row['call'] for row in rows})},
        'notes':['20 samples per call; owner think time absent.','Page handlers are synthetic no-op or local receiver; browser dispatch is not claimed to be pure tool CPU.','Nested stages overlap. Missing historical stages are absent, never a fabricated zero.','The fixed post-input wait is holdMs + 25 ms (525 ms at holdMs=500).']}
assert all(details['client_total']['samples']==20 for details in result['calls'].values())
(root/'latency-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
