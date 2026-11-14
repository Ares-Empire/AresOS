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
TARGETS=json.loads(Path(__file__).with_name('latency-targets.json').read_text())
# The lead's sample counts (latency-targets.json); the client takes them too.
# The current runtime: 60 per call and history phase.
SAMPLES=TARGETS['samples_per_call']
# The old runtime only feeds the runner-noise ratio and must match the frozen
# 20-sample reference, so it takes 20 at the reference's positions
# (mac-aresos-control, 2026-11-14, after run 43613647256).
OLD_RUNTIME_SAMPLES=TARGETS['old_runtime_samples_per_call']


def samples_for(runtime):
    if runtime=='current':return SAMPLES
    assert runtime==TARGETS['baseline'],'Unknown latency runtime'
    return OLD_RUNTIME_SAMPLES


def summary(values):
    assert values and all(isinstance(value,(int,float)) and math.isfinite(value) and value>=0 for value in values)
    ordered=sorted(values)
    return {'samples':len(values),'median_ms':statistics.median(values),'p95_ms':ordered[max(0,math.ceil(.95*len(values))-1)]}


def summarize(root):
    client=json.loads((root/'latency-client.json').read_text());rows=client['samples']
    count=samples_for(client['baseline'])
    expected=len(CALLS)*len(PHASES)*count;assert len(rows)==expected
    identities={(row['sample'],row['call']) for row in rows};assert len(identities)==expected
    assert {row['phase'] for row in rows}==PHASES
    # Every call takes positions 0 to count-1 of each history phase, the
    # positions the reference was taken at for the first 20.
    for phase in PHASES:
        for call in CALLS:
            assert {row['sample'] for row in rows if row['phase']==phase and row['call']==call}=={phase+':'+str(index) for index in range(count)},'Samples are not at positions 0 to count-1'
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
    assert all(detail['client_total']['samples']==count for group in groups.values() for detail in group.values())
    assert [row['count'] for row in history]==[1000,4000]
    return {'runtime':client['baseline'],'privacy':client['privacy'],'chrome':(root/'chrome-version.txt').read_text().strip(),
        'build':(root/'runtime-build.txt').read_text().strip(),'samples_per_call':count,'calls':groups['fresh'],'phases':groups,'input_samples':pairs,'history_fixtures':history,
        'notes':[f'{count} samples per call and history phase; owner think time absent.',
            'Retained history is disposable synthetic timing input shaped from a real completed free input, not receiver or qualification evidence.',
            'Page handlers are no-op/local receiver; browser dispatch is not pure tool CPU.',
            'Nested stages overlap. Missing historical stages are absent, never fabricated zeros.',
            'Client outside service includes daemon expiry/queueing, IPC and framing; only complete expiry sweeps wholly inside a sample receive the daemon stage.',
            'The unchanged fixed post-input wait is holdMs + 25 ms (525 ms at holdMs=500).']}


if __name__=='__main__':
    root=Path(sys.argv[1]);result=summarize(root)
    (root/'latency-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
