"""Group 12 on 18d's native CLI/Session harness, with independent HTTP arrivals."""
import hashlib
import json
import os
from pathlib import Path
from native import OUT,POLICY,Session,tool
from boundary_assertions import tool_text
from aresos_control.boundary_policy import managed_settings
from chrome_fixture import OWNER,owner_entry

SCOPES={'user':Path('/home/assistant/.claude/settings.json'),'project':Path('/home/assistant/work/.claude/settings.json'),'local':Path('/home/assistant/work/.claude/settings.local.json')}

def chrome_precedence(run,put,model_contract):
    from check import ENV
    original=POLICY.read_bytes();settings_original={path:path.read_bytes() for path in SCOPES.values()}
    approval={'question':'On https://fixture.test/, tab Synthetic fixture, read or submit the named synthetic fields?', 'operation_id':'fixture:chrome-precedence','description':{'text':'Synthetic fixed payload'}}
    summary=[]
    try:
        for skip in (False,True):
            for mode in ('missing','matching','revoked','other-account','positive'):
                case='chrome-'+('skip-' if skip else 'normal-')+mode
                policy=managed_settings()
                if mode=='positive':
                    for verb in ('submit','read_typed_fields'):policy['permissions']['ask'].remove('mcp__chrome__'+verb)
                POLICY.write_text(json.dumps(policy))
                for scope,path in SCOPES.items():
                    put(path,json.dumps({'permissions':{'allow':['mcp__chrome__tabs','mcp__chrome__submit_trusted','mcp__chrome__submit','mcp__chrome__read_typed_fields']}} if scope=='user' else {}))
                put(OWNER,json.dumps(owner_entry('missing' if mode=='positive' else mode)),uid=0)
                flags=['-p','--output-format','stream-json','--verbose']+(['--dangerously-skip-permissions'] if skip else [])
                blocks=[tool('mcp__chrome__tabs',{},'chrome-tabs'),tool('mcp__chrome__submit',approval,'chrome-submit'),
                        tool('mcp__chrome__read_typed_fields',approval,'chrome-typed'),tool('mcp__chrome__submit_trusted',approval,'chrome-trusted')]
                before=(OUT/'stub.txt').read_text()
                with Session(blocks,'precedence-'+case) as session:
                    result=run(['/usr/local/bin/claude',*flags],'precedence-'+case,
                        env=dict(ENV,ARESOS_BOUNDARY_CASE=case,ENABLE_TOOL_SEARCH='false'),input='Execute the fixed Chrome precedence test.\n',timeout=90,required=False)
                    assert result.returncode==0 and len(session.results)==4,(case,result,session.results)
                    if case=='chrome-normal-missing':
                        hashes=model_contract(session.requests)
                        (OUT/'chrome-precedence-instructions.json').write_text(json.dumps(hashes,indent=2))
                    delta=(OUT/'stub.txt').read_text()[len(before):]
                    counts={verb:delta.count('POST /precedence/chrome-'+verb+'/'+case+' HTTP/1.1') for verb in ('tabs','submit','typed','trusted')}
                    expected={'tabs':1,'submit':int(mode=='positive'),'typed':int(mode=='positive'),'trusted':int(mode=='matching')}
                    assert counts==expected,(case,counts,delta)
                    for block,verb in [('chrome-tabs','tabs'),('chrome-submit','submit'),('chrome-typed','typed'),('chrome-trusted','trusted')]:
                        row=session.results[block]
                        assert bool(row.get('is_error'))==(counts[verb]==0),(case,block,row)
                        if counts[verb]:assert 'FIXTURE_CHROME_'+verb.upper()+'_RAN' in tool_text(row)
                    events=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
                    init=[row for row in events if row.get('type')=='system' and row.get('subtype')=='init']
                    assert len(init)==1 and init[0]['permissionMode']==('bypassPermissions' if skip else 'default'),init
                    summary.append({'case':case,'mode':init[0]['permissionMode'],'owner_entry':mode,'arrivals':counts,
                        'receiver_delta_sha256':hashlib.sha256(delta.encode()).hexdigest()})
                    print('CHROME_PRECEDENCE '+json.dumps(summary[-1],sort_keys=True),flush=True)
                (OUT/'chrome-precedence.json').write_text(json.dumps({'head':os.environ.get('RUNTIME_COMMIT',os.environ.get('GITHUB_SHA')),'run':os.environ.get('GITHUB_RUN_ID'),'cases':summary,'instructions':hashes},indent=2))
    finally:
        POLICY.write_bytes(original);OWNER.unlink(missing_ok=True)
        for path,data in settings_original.items():path.write_bytes(data)
