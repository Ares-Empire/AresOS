import pathlib,json,re,base64,sys
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/ci'))
from owner_console import screen
b=r/'.work/14/run-40596167369';e=b/'evidence/two-disk'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
idle=read(e/'tools-stock-physical-idle.json')
raw=base64.b64decode(idle['raw'],validate=True)
assert raw==(e/'tools-stock-physical-idle-timeout-1.vcsa').read_bytes()
full,line=screen(raw)
transport=read(e/'tools-stock-physical-idle-transport.json')
record=read(e/'tools-stock-failure-counter.json')
native=(b/'native.log').read_text(encoding='utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',native)
assert m and int(m[1])==422 and re.search(r'Z OK\s*$',native,re.M)
assert idle['ready'] is False and idle['foreground_shell'] is False and transport['verified'] is True
out=(e/'tools-stock-physical-idle.txt').read_text(encoding='utf-8')
assert 'ARESOS_CMD_DONE:0' in out
value=dict(status='STOP: post-sudo physical idle observer rejected; transport completed successfully',
    run=40596167369,head=read(b/'receipt.json')['head'],phase='console.become_root -> after_hidden(tools-stock)',
    ready=idle['ready'],echo_enabled=idle['echo_enabled'],foreground_shell=idle['foreground_shell'],
    reader_seconds=840,outer_execution_seconds=900,uart_done_zero=True,checksum_framed_json_decoded=True,
    staged_sha_and_syntax_verified=transport['verified'],
    screen=dict(rows=raw[0],columns=raw[1],cursor_x=raw[2],cursor_y=raw[3],
        cursor_line_is_root_style_prompt=bool(re.search(r'root@[^\n]*#$',line)),
        any_root_style_prompt=bool(re.search(r'root@[^\n]*#',full)),
        sudo_prompt_present='password for ares-recovery' in full),
    process_pid_or_cmdline_exported=False,underlying_foreground_identity='not retained; cannot prove the process/proxy causing the rejected idle observation',
    owner_install_started=False,tools_media_hotplug_started=False,private_registry_login_typed=False,
    prepare_or_network_checkpoint_reached=False,verify_switch_layout_rollback_keep_stock_reached=False,
    failure_counter=record,native_tests=int(m[1]),native_seconds=float(m[2]),native_skips=0,
    prior_account_login_receipt_may_share_stage_prefix=True,
    evidence_note='tools-stock-hidden-completed.json belongs to the earlier account login; root completion was not accepted. Same-prefix readiness filenames may overwrite earlier observations.',
    inference='A root-style screen prompt is a display observation, not proof of foreground Bash or root UID; no idle/Enter predicate relaxed')
(b/'14zd-owner-stop-observations.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n')
print(json.dumps({k:value[k] for k in ('status','phase','ready','echo_enabled','foreground_shell','uart_done_zero','screen','native_tests','native_seconds')}))
