"""Local dispatch confirmation. The returned run URL is authoritative identity.

No mutation/retry POST is implemented here. HTTP retries are the existing guard's
bounded read-only policy. Metadata visibility may settle for at most six GETs.
"""
import re,time

FIELDS=('id','head_sha','head_branch','event','display_title','path','run_attempt')
WAITS=(1,2,4,8,16)


def returned_run_id(output,repo):
    match=re.fullmatch(r'https://github\.com/'+re.escape(repo)+r'/actions/runs/([1-9][0-9]*)\s*',output)
    assert match,'STOP: dispatch did not return exactly one canonical run URL; never repeat POST'
    return int(match[1])


def confirm(output,repo,head,branch,title,api,record,sleep=time.sleep):
    run_id=returned_run_id(output,repo)
    expected=dict(id=run_id,head_sha=head,head_branch=branch,event='workflow_dispatch',display_title=title,
                  path='.github/workflows/os-image.yml',run_attempt=1)
    observations=[]
    for attempt in range(1,len(WAITS)+2):
        value=api('actions/runs/'+str(run_id))
        actual={k:value.get(k) for k in FIELDS}
        mismatch={k:dict(expected=want,actual=actual[k]) for k,want in expected.items() if actual[k]!=want}
        observations.append(dict(attempt=attempt,identity=actual,status=value.get('status'),conclusion=value.get('conclusion'),mismatch=mismatch))
        record(dict(returned_run_id=run_id,max_reads=6,post_retried=False,observations=observations,
                    status='confirmed' if not mismatch else 'waiting' if attempt<=len(WAITS) else 'stopped'))
        if not mismatch:
            return value
        if attempt<=len(WAITS):sleep(WAITS[attempt-1])
    raise AssertionError('STOP: returned run identity did not settle within six reads; never repeat POST')
