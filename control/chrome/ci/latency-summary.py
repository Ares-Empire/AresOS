"""Stage medians/p95 by retained-history phase; nested stages are not summed."""
import collections
import json
import math
from pathlib import Path
import statistics
import sys

CALLS={'read','navigate','free_click','fill','asking_click','approval_to_done'}
PHASES={'fresh','history-1000','history-4000'}
INPUTS={'free_click','fill','approval_to_done'}


def summary(values):
    assert values and all(isinstance(value,(int,float)) and math.isfinite(value) and value>=0 for value in values)
    ordered=sorted(values)
    return {'samples':len(values),'median_ms':statistics.median(values),'p95_ms':ordered[max(0,math.ceil(.95*len(values))-1)]}


def summarize(root):
    client=json.loads((root/'latency-client.json').read_text());rows=client['samples']
    assert len(rows)==360
    identities={(row['sample'],row['call']) for row in rows};assert len(identities)==360
    assert {row['phase'] for row in rows}==PHASES
    stages=collections.defaultdict(list)
    phases={row['sample']:row['phase'] for row in rows}
    for row in rows:
        assert row['call'] in CALLS and row['sample'].startswith(row['phase']+':')
        stages[(row['phase'],row['call'],'client_total')].append(row['milliseconds'])
    internal=collections.defaultdict(float);history=[]
    for line in (root/'latency-service.jsonl').read_text().splitlines():
        row=json.loads(line)
        if row.get('stage')=='history_fixture':history.append(row);continue
        if row.get('sample') is None:continue
        assert (row['sample'],row['call']) in identities
        internal[(row['sample'],row['call'],row['stage'])]+=row['milliseconds']
    for (sample,call,stage),duration in internal.items():stages[(phases[sample],call,stage)].append(duration)
    for row in rows:
        service=internal.get((row['sample'],row['call'],'service_total'))
        if service is not None:
            stages[(row['phase'],row['call'],'client_outside_service')].append(max(0,row['milliseconds']-service))
    pairs=[]
    for row in rows:
        if row['call'] not in INPUTS:continue
        wait=internal[(row['sample'],row['call'],'post_input_observation_wait')]
        assert wait>=500 and row['milliseconds']+2>=wait
        work=max(0,row['milliseconds']-wait)
        pairs.append({'sample':row['sample'],'phase':row['phase'],'call':row['call'],'client_ms':row['milliseconds'],'wait_ms':wait})
        stages[(row['phase'],row['call'],'client_without_wait')].append(work)
    groups={phase:{call:{stage:summary(values) for (part,category,stage),values in stages.items() if part==phase and category==call} for call in sorted(CALLS)} for phase in sorted(PHASES)}
    assert all(detail['client_total']['samples']==20 for group in groups.values() for detail in group.values())
    assert [row['count'] for row in history]==[1000,4000]
    return {'runtime':client['baseline'],'privacy':client['privacy'],'chrome':(root/'chrome-version.txt').read_text().strip(),
        'build':(root/'runtime-build.txt').read_text().strip(),'calls':groups['fresh'],'phases':groups,'input_samples':pairs,'history_fixtures':history,
        'notes':['20 samples per call and history phase; owner think time absent.',
            'Retained history is disposable synthetic timing input shaped from a real completed free input, not receiver or qualification evidence.',
            'Page handlers are no-op/local receiver; browser dispatch is not pure tool CPU.',
            'Nested stages overlap. Missing historical stages are absent, never fabricated zeros.',
            'Client outside service includes daemon expiry/queueing, IPC and framing; only complete expiry sweeps wholly inside a sample receive the daemon stage.',
            'The unchanged fixed post-input wait is holdMs + 25 ms (525 ms at holdMs=500).']}


if __name__=='__main__':
    root=Path(sys.argv[1]);result=summarize(root)
    (root/'latency-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
