"""CI regression gate: paired historical runtime controls for common runner noise."""
import json
import math
from pathlib import Path
import statistics
import sys

CALLS={'read','navigate','free_click','fill','asking_click','approval_to_done'}
INPUTS={'free_click','fill','approval_to_done'}
PHASES={'fresh','history-1000','history-4000'}


def validate_metric(row, allow_sparse=False):
    assert type(row['samples']) is int and (1<=row['samples']<=20 if allow_sparse else row['samples']==20)
    for stat in ['median_ms','p95_ms']:
        value=row[stat];assert type(value) in {int,float} and math.isfinite(value) and value>=0
    assert row['median_ms']<=row['p95_ms'],'Percentiles are out of order'


def metric(group,call,stat):
    row=group[call]['client_total'];validate_metric(row)
    return row[stat]


def active(group,call,stat):
    # Paired subtraction happened before percentile calculation in the summary.
    row=group[call]['client_without_wait' if call in INPUTS else 'client_total']
    validate_metric(row)
    return max(1,row[stat])


def validate_pairs(value):
    pairs=value['input_samples'];assert len(pairs)==180
    identities={(row['sample'],row['phase'],row['call']) for row in pairs};assert len(identities)==180
    assert all(row['phase'] in PHASES and row['call'] in INPUTS for row in pairs)
    for phase in PHASES:
        for call in INPUTS:
            rows=[row for row in pairs if row['phase']==phase and row['call']==call];assert len(rows)==20
            for row in rows:
                assert row['sample'].startswith(phase+':')
                for key in ['client_ms','wait_ms']:
                    assert type(row[key]) in {int,float} and math.isfinite(row[key]) and row[key]>=0
                assert row['wait_ms']>=500 and row['client_ms']+2>=row['wait_ms'],'Total is shorter than its wait'
            for stage,values in [
                ('client_total',[row['client_ms'] for row in rows]),
                ('post_input_observation_wait',[row['wait_ms'] for row in rows]),
                ('client_without_wait',[max(0,row['client_ms']-row['wait_ms']) for row in rows])]:
                block=value['phases'][phase][call][stage];validate_metric(block)
                expected={'median_ms':statistics.median(values),'p95_ms':sorted(values)[18]}
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
    for value in [current,baseline,reference['current'],reference['baseline']]:
        assert set(value['phases'])==PHASES
        validate_pairs(value)
        for phase,group in value['phases'].items():
            assert set(group)==CALLS
            for call in CALLS:
                for stage,block in group[call].items():
                    sparse=stage=='daemon_expiry_inside_sample' or call=='navigate' and stage=='clipboard_hooks'
                    validate_metric(block,allow_sparse=sparse)
                if call in INPUTS:
                    wait=group[call]['post_input_observation_wait']
                    assert wait['samples']==20 and 520<=wait['median_ms']<=wait['p95_ms']<=750,'Missing or changed 525 ms safety wait'
    # A short tail spike alone does not fail the run. Both median and p95 must
    # cross the threshold; 20 samples and the paired old runtime absorb noise.
    rows=[];failures=[]
    for phase in sorted(PHASES):
        group=current['phases'][phase];old=baseline['phases'][phase]
        accepted=reference['current']['phases'][phase];accepted_old=reference['baseline']['phases'][phase]
        noise=statistics.median(active(old,call,'median_ms')/active(accepted_old,call,'median_ms') for call in CALLS)
        assert .25<=noise<=2.5,'Runner differs too much from the reference; repeat the measurement'
        allowance=max(1,noise)
        for call in sorted(CALLS):
            stages=['service_total','service_without_bridge','bridge_round_trip','extension_total']
            if call in INPUTS:stages+=['session_rule_add','session_rule_remove','compose_binding']
            if call=='asking_click':stages+=['compose_binding']
            if call=='free_click':stages+=['clipboard_hooks']
            for stage in stages:
                validate_metric(group[call][stage])
            observed={stat:active(group,call,stat) for stat in ['median_ms','p95_ms']}
            allowed={'median_ms':active(accepted,call,'median_ms')*allowance*1.5+10,
                     'p95_ms':active(accepted,call,'p95_ms')*allowance*1.75+20}
            regression=all(observed[stat]>allowed[stat] for stat in observed)
            target_miss=all(metric(group,call,stat)>targets['ceilings_ms'][call][stat]*allowance for stat in observed)
            if regression or target_miss:failures.append({'phase':phase,'call':call,'regression':regression,'target_miss':target_miss})
            rows.append({'phase':phase,'call':call,'runner_factor':noise,'paired_work_ms':observed,'regression_threshold_ms':allowed,
                         'client_ms':{stat:metric(group,call,stat) for stat in observed},'target_miss':target_miss})
    return {'passed':not failures,'failures':failures,'measurements':rows,
            'policy':'Lead ceilings and reference regression in every measured history phase; median and p95 must both cross. Common paired runner slowdown scales allowance; Matched per-sample waits are subtracted before percentiles; the 525 ms wait is checked separately.'}


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
