"""CI regression gate: paired historical runtime controls for common runner noise."""
import json
import math
from pathlib import Path
import statistics
import sys

CALLS={'read','navigate','free_click','fill','asking_click','approval_to_done'}
INPUTS={'free_click','fill','approval_to_done'}
PHASES={'fresh','history-1000','history-4000'}


def sample_counts(targets):
    # The lead's counts (latency-targets.json): the current runtime takes 60
    # per call and history phase. The old runtime only feeds the runner-noise
    # ratio and must match the frozen 20-sample reference, so it takes the
    # reference's own count (mac-aresos-control, 2026-11-14, after run
    # 43613647256). The frozen reference keeps the count it was taken with.
    samples,old,reference=targets['samples_per_call'],targets['old_runtime_samples_per_call'],targets['measurement_samples_per_call']
    assert all(type(count) is int and count>=20 for count in (samples,old,reference)),'Sample counts must be whole numbers of at least 20'
    assert old==reference,'The old runtime must take the frozen reference count'
    return samples,old,reference


def positions(value):
    return sorted((row['phase'],row['call'],row['sample']) for row in value['input_samples'])


def p95(values):
    # The summary's rule: with 60 samples the 57th of 60, so three slow samples
    # stay above it and a fourth reaches it.
    ordered=sorted(values)
    return ordered[max(0,math.ceil(.95*len(ordered))-1)]


def validate_metric(row, samples, allow_sparse=False):
    assert type(row['samples']) is int and (1<=row['samples']<=samples if allow_sparse else row['samples']==samples)
    for stat in ['median_ms','p95_ms']:
        value=row[stat];assert type(value) in {int,float} and math.isfinite(value) and value>=0
    assert row['median_ms']<=row['p95_ms'],'Percentiles are out of order'


def metric(group,call,stat,samples):
    row=group[call]['client_total'];validate_metric(row,samples)
    return row[stat]


def active(group,call,stat,samples):
    # Paired subtraction happened before percentile calculation in the summary.
    row=group[call]['client_without_wait' if call in INPUTS else 'client_total']
    validate_metric(row,samples)
    return max(1,row[stat])


def validate_pairs(value,samples):
    pairs=value['input_samples'];expected=len(PHASES)*len(INPUTS)*samples;assert len(pairs)==expected
    identities={(row['sample'],row['phase'],row['call']) for row in pairs};assert len(identities)==expected
    assert all(row['phase'] in PHASES and row['call'] in INPUTS for row in pairs)
    for phase in PHASES:
        for call in INPUTS:
            rows=[row for row in pairs if row['phase']==phase and row['call']==call];assert len(rows)==samples
            for row in rows:
                assert row['sample'].startswith(phase+':')
                for key in ['client_ms','wait_ms']:
                    assert type(row[key]) in {int,float} and math.isfinite(row[key]) and row[key]>=0
                assert row['wait_ms']>=500 and row['client_ms']+2>=row['wait_ms'],'Total is shorter than its wait'
            for stage,values in [
                ('client_total',[row['client_ms'] for row in rows]),
                ('post_input_observation_wait',[row['wait_ms'] for row in rows]),
                ('client_without_wait',[max(0,row['client_ms']-row['wait_ms']) for row in rows])]:
                block=value['phases'][phase][call][stage];validate_metric(block,samples)
                expected={'median_ms':statistics.median(values),'p95_ms':p95(values)}
                assert all(math.isclose(block[stat],number,abs_tol=1e-6) for stat,number in expected.items()),'Summary does not match paired samples'


def check(current,baseline,reference,targets):
    assert targets['format']==1 and targets['status']=='lead-approved','Latency ceilings still require the lead decision'
    assert set(targets['ceilings_ms'])==CALLS
    for limits in targets['ceilings_ms'].values():
        assert 0<limits['median_ms']<=limits['p95_ms'] and all(math.isfinite(v) for v in limits.values())
    assert current['runtime']=='current' and baseline['runtime']=='ab7aba92'
    assert reference['current']['runtime']=='current' and reference['baseline']['runtime']=='ab7aba92'
    assert current['privacy']==baseline['privacy']==reference['privacy']==reference['current']['privacy']==reference['baseline']['privacy']
    assert current['chrome']==baseline['chrome'],'Paired measurements must use one exact Chrome package'
    samples,old_samples,reference_samples=sample_counts(targets)
    # The old runtime slows as its own history grows: its medians compare like
    # for like with the reference's only at the reference's sample positions.
    assert positions(baseline)==positions(reference['baseline']),'The old runtime must take the reference sample positions'
    for value,count in [(current,samples),(baseline,old_samples),(reference['current'],reference_samples),(reference['baseline'],reference_samples)]:
        assert set(value['phases'])==PHASES
        validate_pairs(value,count)
        for phase,group in value['phases'].items():
            assert set(group)==CALLS
            for call in CALLS:
                for stage,block in group[call].items():
                    sparse=stage=='daemon_expiry_inside_sample' or call=='navigate' and stage=='clipboard_hooks'
                    validate_metric(block,count,allow_sparse=sparse)
                if call in INPUTS:
                    wait=group[call]['post_input_observation_wait']
                    assert wait['samples']==count and 520<=wait['median_ms']<=wait['p95_ms']<=750,'Missing or changed 525 ms safety wait'
    # The lead's ceilings are absolute: a median or a p95 over its ceiling (times
    # the common runner slowdown) fails. Against the frozen reference a short
    # tail spike alone does not fail: both median and p95 must cross there, and
    # the paired old runtime absorbs runner noise. With the lead's 60 samples a
    # p95 is over a ceiling only when four or more samples are.
    rows=[];failures=[]
    for phase in sorted(PHASES):
        group=current['phases'][phase];old=baseline['phases'][phase]
        accepted=reference['current']['phases'][phase];accepted_old=reference['baseline']['phases'][phase]
        noise=statistics.median(active(old,call,'median_ms',old_samples)/active(accepted_old,call,'median_ms',reference_samples) for call in CALLS)
        assert .25<=noise<=2.5,'Runner differs too much from the reference; repeat the measurement'
        allowance=max(1,noise)
        for call in sorted(CALLS):
            stages=['service_total','service_without_bridge','bridge_round_trip','extension_total']
            if call in INPUTS:stages+=['session_rule_add','session_rule_remove','compose_binding']
            if call=='asking_click':stages+=['compose_binding']
            if call=='free_click':stages+=['clipboard_hooks']
            for stage in stages:
                validate_metric(group[call][stage],samples)
            observed={stat:active(group,call,stat,samples) for stat in ['median_ms','p95_ms']}
            allowed={'median_ms':active(accepted,call,'median_ms',reference_samples)*allowance*1.5+10,
                     'p95_ms':active(accepted,call,'p95_ms',reference_samples)*allowance*1.75+20}
            regression=all(observed[stat]>allowed[stat] for stat in observed)
            target_miss=any(metric(group,call,stat,samples)>targets['ceilings_ms'][call][stat]*allowance for stat in observed)
            if regression or target_miss:failures.append({'phase':phase,'call':call,'regression':regression,'target_miss':target_miss})
            rows.append({'phase':phase,'call':call,'runner_factor':noise,'paired_work_ms':observed,'regression_threshold_ms':allowed,
                         'client_ms':{stat:metric(group,call,stat,samples) for stat in observed},'target_miss':target_miss})
    return {'passed':not failures,'failures':failures,'measurements':rows,
            'samples_per_call':samples,'old_runtime_samples_per_call':old_samples,'reference_samples_per_call':reference_samples,
            'policy':'Lead ceilings and reference regression in every measured history phase. A call misses the lead ceilings when its median or its p95 is over the ceiling; against the reference, median and p95 must both cross. Common paired runner slowdown scales both allowances, measured with the old runtime at the reference sample count and positions; Matched per-sample waits are subtracted before percentiles; the 525 ms wait is checked separately.'}


if __name__=='__main__':
    current_path,baseline_path,reference_path,targets_path=map(Path,sys.argv[1:])
    current=json.loads(current_path.read_text());baseline=json.loads(baseline_path.read_text())
    reference_document=json.loads(reference_path.read_text())
    assert reference_document['format']==1 and reference_document['status']=='measured','Measured reference is not ready'
    reference=reference_document['profiles'][current['privacy']]
    result=check(current,baseline,reference,json.loads(targets_path.read_text()))
    (current_path.parent/'latency-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)
