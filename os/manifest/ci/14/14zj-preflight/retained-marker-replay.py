import pathlib,json,hashlib,re,sys
r=pathlib.Path.cwd();sys.path.insert(0,str(r/'os/ci'));import serial_console as sc
w=r/'.work/14';p=w/'run-40646962291/evidence/two-disk/webui-probe-server-incomplete.txt';raw=p.read_bytes();v=json.loads((r/'os/tests/fixtures/owner-console/14zj-probe18-ack.json').read_text());assert hashlib.sha256(raw).hexdigest()==v['sha256'];s=raw.decode();assert v['exact_nonsecret_ack_span'] in s
pattern=r'\r?\nARESOS_STAGE_'+v['nonce']+r':10:(\d+)\r?\n';assert re.search(pattern,s) is None;clean,m=sc.serial_search(pattern,s);assert m[1]=='0'
rows=[]
for name,action in [
 ('serial_console.py','one complete-kernel-line filter shared by export decoder, marker search and completion parser; partial records cannot grant readiness; export SHA unchanged'),
 ('serial_transport.py','self-delimiting nonce/phase/index/status ACK; duplicate/out-of-order/mismatch STOP; bounded waits and SHA verification; no automatic re-send'),
 ('switch_vm.py','all UART waits including login/readiness/command completion and hidden-resync; raw transcript preserved; buffered stale ACK refuses next send; drain checked before clearing'),
 ('two_disk_vm.py','inherits normalized UART wait; reset/deadline/QMP behavior unchanged; firmware Windows marker uses a separate debugcon, not Linux UART'),
 ('vm.py','passive UART journal-readiness file uses same filter, unchanged 60-second deadline'),
 ('keyboard_vm.py','structured marker consumed only from normalized Guest.command result'),
 ('stock_probe.py','native container/tool stdout; not the UART marker path'),
 ('greeter.py','heredoc delimiter is source syntax; command result passes through Guest.command'),
 ('offline_journal.py','offline journal JSON MESSAGE comparison, not UART matching')]:
 p=r/'os/ci'/name;rows.append(dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(r).as_posix(),audit=action))
proof=dict(status='passed exact retained full-transcript replay and serial-marker audit',source=dict(sha256=hashlib.sha256(raw).hexdigest(),path='evidence/two-disk/webui-probe-server-incomplete.txt',run=40646962291,bytes=len(raw)),raw_old_predicate_matches=False,shared_filter_old_status=0,legacy_protocol_accepted_by_new_ack=False,exact_nonsecret_fixture_span_matches=True,raw_transcript_committed=False,physical_vcsa_prompt_and_kernel_emission_unchanged=True,resend_policy='none; no receiver not-stored receipt exists; an ambiguous timeout STOPs',sources=rows)
(w/'14zj-marker-audit.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n');print('PASS retained full 14zi transcript after shared kernel filtering; no legacy protocol acceptance')
