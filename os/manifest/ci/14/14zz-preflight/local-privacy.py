"""Exact-range aresync privacy proof. Never reads or records private terms."""
import datetime, hashlib, json, pathlib, re, subprocess

ROOT=pathlib.Path.cwd()
WORK=ROOT/'.work/14'
BASH='C:/Program Files/Git/bin/bash.exe'
CHECKER=pathlib.Path('C:/Users/pab/aresync/privacy-check.sh')
POSIX_CHECKER='/c/Users/pab/aresync/privacy-check.sh'
BRANCH='pkg/14-owner-tools'

def out(*args):
    return subprocess.check_output(args,text=True,encoding='utf-8').strip()

def checked_output(result):
    text=result.stdout+result.stderr
    skipped='personal terms check skipped' in ' '.join(text.casefold().split())
    assert result.returncode==0,'STOP: aresync privacy checker blocked or failed; no bypass'
    assert not skipped,'STOP: aresync personal terms check skipped'
    return dict(exit_code=0,personal_terms_skipped_warning_absent=True)

def standard_input(head, remote):
    assert re.fullmatch('[0-9a-f]{40}',head) and re.fullmatch('[0-9a-f]{40}',remote)
    return f'refs/heads/{BRANCH} {head} refs/heads/{BRANCH} {remote}\n'

def run_with_lf(command,data,timeout=600):
    # Windows text pipes translate LF to CRLF; Bash keeps CR in the last SHA.
    result=subprocess.run(command,input=data.encode('ascii'),capture_output=True,timeout=timeout)
    return subprocess.CompletedProcess(command,result.returncode,
        result.stdout.decode('utf-8',errors='replace'),result.stderr.decode('utf-8',errors='replace'))

def identity():
    setting=subprocess.run(['git','config','--get','core.hooksPath'],capture_output=True,text=True)
    assert setting.returncode==1 and not setting.stdout,'STOP: core.hooksPath overrides the verified repository hook'
    hook=pathlib.Path(out('git','rev-parse','--git-path','hooks/pre-push'))
    text=hook.read_text(encoding='utf-8')
    expected=f'''#!/bin/sh
# aresync privacy pre-push v1
if [ ! -x '{POSIX_CHECKER}' ]; then
  echo '[aresync privacy] checker missing or not executable; reinstall the hook from the current aresync folder.' >&2
  exit 1
fi
exec '{POSIX_CHECKER}' pre-push "$@"
'''
    assert text==expected,'STOP: installed pre-push hook differs from the verified aresync entry point'
    subprocess.run([BASH,'--noprofile','--norc','-c','test -x "$1" && test -x "$2"','bash',
        hook.as_posix(),POSIX_CHECKER],check=True,capture_output=True)
    checker=CHECKER.read_text(encoding='utf-8')
    # Execute the checker's own resolver, not a second candidate selection recipe.
    match=re.search(r'(?ms)^gitleaks_bin\(\) \{\n.*?^\}',checker)
    assert match is not None,'STOP: checker gitleaks resolver changed'
    program=match[0]+'\np=$(gitleaks_bin) || exit 1\nprintf "%s\\n" "$p"\n"$p" version\n'
    resolved=out(BASH,'--noprofile','--norc','-c',program).splitlines()
    assert len(resolved)==2 and re.fullmatch(r'v?\d+\.\d+\.\d+',resolved[1]),'STOP: cannot record actual hook gitleaks version'
    binary=out(BASH,'--noprofile','--norc','-c','cygpath -w "$1"','bash',resolved[0])
    return dict(hook=dict(sha256=hashlib.sha256(hook.read_bytes()).hexdigest(),path='repository git hooks/pre-push'),
        checker=dict(sha256=hashlib.sha256(CHECKER.read_bytes()).hexdigest(),path='aresync/privacy-check.sh'),
        gitleaks=dict(sha256=hashlib.sha256(pathlib.Path(binary).read_bytes()).hexdigest(),path='hook-resolved gitleaks',version=resolved[1]),
        core_hooks_path_override=False)

def precheck(head,remote,url):
    assert out('git','rev-parse','HEAD')==head
    ids=out('git','rev-list',head,'--not',remote,'--remotes').splitlines()
    assert ids,'STOP: empty push range cannot prove execution of personal-term checks'
    before=identity()
    data=standard_input(head,remote)
    result=run_with_lf([BASH,'--noprofile','--norc',POSIX_CHECKER,'pre-push','origin',url],data)
    log=WORK/'14zz/pre-push-check.log'
    log.write_text(result.stdout+result.stderr,encoding='utf-8',newline='\n')
    value=dict(status='STOP',head=head,remote_before=remote,checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        standard_stdin=data,commits_checked=ids,identity=before,exit_code=result.returncode,
        log=dict(sha256=hashlib.sha256(log.read_bytes()).hexdigest(),path=log.relative_to(ROOT).as_posix()),
        terms_values_read_or_recorded_by_agent=False,terms_checked_only_by_aresync=True,
        command='aresync/privacy-check.sh pre-push origin <origin-url>',no_verify=False)
    target=WORK/'14zz-prepush-privacy.json'
    target.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    if result.stdout:print(result.stdout,end='')
    if result.stderr:print(result.stderr,end='')
    value.update(checked_output(result))
    assert identity()==before,'STOP: privacy checker/hook/scanner changed during precheck'
    value['status']='passed'
    target.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
    return value

def verify(proof,head):
    assert proof['status']=='passed' and proof['head']==head and proof['exit_code']==0
    assert proof['personal_terms_skipped_warning_absent'] is True and proof['no_verify'] is False
    assert proof['commits_checked'] and proof['standard_stdin']==standard_input(head,proof['remote_before'])
    assert proof['identity']==identity(),'STOP: privacy checker/hook/scanner changed after precheck'
    log=ROOT/proof['log']['path']
    assert hashlib.sha256(log.read_bytes()).hexdigest()==proof['log']['sha256']
    assert 'personal terms check skipped' not in ' '.join(log.read_text(encoding='utf-8').casefold().split())
    return proof
