"""Replace pending status with actual terminal facts. Never pushes/dispatches."""
import hashlib,json,pathlib,re,subprocess
r=pathlib.Path.cwd();w=r/'.work/14';d=r/'os/manifest/ci/14/14zzd-round'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
round=read(d/'round.json');closed=read(d/'ledger.json');accepted=round['acceptance_met'];head=round['head']
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
report=r/'reviews/14-owner-tools/REPORT.md';text=report.read_text(encoding='utf-8')
start=text.index('## 14zzd REPORT:');end=text.index('## 14zzc REPORT:',start)
section=text[start:end];done=section.index('### Done')
links=', '.join('['+('probe 33' if row['mode']=='probe' else 'qualification 21')+'](https://github.com/Ares-Empire/AresOS/actions/runs/'+str(row['run'])+') **'+row['conclusion']+'**' for row in round['runs'])
stop=w/'14zzd/STOP-reason.txt';reason=stop.read_text().strip() if stop.exists() else 'acceptance evidence did not pass every gate'
if accepted:
 disposition=f'''## 14zzd REPORT: manifest-only fixtures; probe 33 and qualification 21 passed

**Disposition:** {links}, once each on pushed head `{head}`. Independent complete
evidence review passed; **VM acceptance is met**. There was one fast-forward push
through the installed privacy hook, no Actions rerun, no merge, and no image
build, release or publication. PR #13 is ready for review after closing checks.
This REPORT, curated evidence, ledger and actual-status guide/card update are
committed **locally only**, with no second push. Physical release is **NOT RELEASED**.

'''
else:
 disposition=f'''## 14zzd REPORT: manifest-only fixtures; STOP, no rerun

**Disposition:** {links}, once each on pushed head `{head}`. **Acceptance is not
met**: {reason}. No further push, probe, qualification or rerun was attempted.
PR #13 remains draft. This STOP report, ledger and curated diagnostics receipts
are committed **locally only**. No merge, image build or publication occurred.
Physical release is **NOT RELEASED**.

'''
section=disposition+section[done:]
section=section.replace('Fresh same-head native and VM acceptance are pending.',
 'Fresh same-head native and VM acceptance passed.' if accepted else 'This round stopped without fresh VM acceptance.')
section=section.replace("The status passages acknowledge completed Q20 scope and this round's pending\nreview changes; the closing local status will name this round's actual result.","The closing guide/card status names this round's actual result, retains the\ncompleted Q20 history and keeps every outstanding physical gate.")
section=section.replace('Ledger and billing will be rechecked immediately before each dispatch.','Ledger and billing were rechecked immediately before every attempted dispatch.')
section=section.replace('Fresh VM acceptance\nis pending.','This round\n'+('completed VM acceptance.' if accepted else 'stopped without VM acceptance.'))
actual='### Actual November round / independent review\n\n'+links+'. No run was rerun.\n\n'
for row in round['runs']:
 label='probe33' if row['mode']=='probe' else 'qualification21';p=d/(label+'-acceptance.json')
 if p.exists():
  v=read(p);actual+=f"Run {row['run']}: native **{v['native_tests']} tests / zero skips**, {v['native_seconds']:.3f} s. "
  actual+=f"Independent review: {'complete and passed' if row['accepted'] else 'incomplete; STOP'}.\n\n"
 proof=d/(label+'-artifact-review.json')
 if proof.exists():
  v=read(proof)
  if 'iso_filename_findings' in v:
   actual+=f"Artifact scan: {v['findings']} findings, comprising {len(v['iso_filename_findings'])} exact pinned public ISO listing lines and {len(v['kernel_certificate_findings'])} exact whole-line public kernel X.509 messages. Every occurrence is recorded by file, line, source-line SHA and approved-token cross-check in {label}-artifact-review.json. No ignore/rule/workflow changes.\n\n"
  else:actual+=f"Early STOP artifact scan: **{v['findings']} findings**; ISO inspection was not reached, so no ISO/certificate exception was used. No ignore/rule/workflow changes.\n\n"
 if (d/(label+'-log-review.json')).exists():
  v=read(d/(label+'-log-review.json'))
  actual+=(f"Every completed job log was scanned; {v['findings']} findings were the exact pinned cosign-installer checksum class. Unknown findings: zero.\n\n" if v['findings'] else 'Every completed job log was scanned: **zero findings**, no exception used.\n\n')
if accepted:
 reset=read(d/'layout-reset-proof.json');assert reset['status']=='passed' and all(v for v in reset.values() if isinstance(v,bool))
 actual+='''Qualification 21 passed the real bootstrap/private-copy install, prepare and
zero-mutation rerun, persistent diagnostic/export route, offline and network
boundaries, signature/private login, switch and all original layout proofs,
rollback, keep-stock and final attached/detached Windows markers. The extra
plain-US pending trial received QMP system_reset without a guest shutdown.
Next boot proved German on tty1..tty6, fresh German password/sudo login and
physical foot typing, then layout abandon and guarded reboot. Independent
review rechecked raw maps, persisted console/X11 equality, fresh-login receipts,
exact reset origin and absent tools stick. Protected-disk, BootNext, NVRAM,
detached-device and firmware audits remain unchanged and passed.

'''
actual+=f"Complete closing history: **{closed['ledger']['history']['ids_count']}/{closed['ledger']['history']['total_count']} IDs**. Package minutes **{closed['ledger']['consumed_minutes']} / 2750**; added **{closed['ledger']['consumed_minutes']-2310}** this round. Counts **{closed['ledger']['dispatch_counts']['probe']} probes / {closed['ledger']['dispatch_counts']['owner-tools']} qualifications** (last caps 34/21). Organization free **{closed['organization']['remaining_minutes']}**, reserve **150**. The saved last-dispatch package/organization comparison passed; the complete per-job charge rules and response hashes are in ledger.json. November remains free-minutes-only: no paid budget read or paid overflow; local-hook privacy reservations stay zero. No further dispatch is authorized.\n\n"
actual+='''Actual receipts are in `os/manifest/ci/14/14zzd-round/round.json`. Raw consoles,
VCSA, screenshots, varstores and owner diagnostics remain only in private retained
artifacts/local evidence; they are not committed. The whole report's outstanding
physical release gates and the existing For package 15 list still apply.

'''
section=section.replace('### Not verified / JUDGMENT-CALL / PLAN-GAP / open questions',actual+'### Not verified / JUDGMENT-CALL / PLAN-GAP / open questions')
report.write_text(text[:start]+section+text[end:],encoding='utf-8',newline='\n')
summary=('Qualification 21 passed the complete protected-second VM owner route and all safety audits, including trusted bootstrap, unplanned trial reset, German recovery login, layout abandon, the original layout proofs, rollback, keep-stock and final Windows markers.' if accepted else 'Qualification 20 remains the last accepted complete VM route. The 14zzd fixture round stopped; the new head has not met acceptance.')
summary+=' See the [14 REPORT](../reviews/14-owner-tools/REPORT.md) for exact runs and evidence. Physical installation remains **NOT RELEASED**; every laptop/media/followability gate stays open.'
changes=[]
for name in ('docs/INSTALL.md','docs/EMERGENCY.md'):
 p=r/name;before=p.read_text(encoding='utf-8');lines=before.splitlines();n=0
 for i,line in enumerate(lines):
  if name.endswith('INSTALL.md') and line.startswith(('- **VM scope passed','- **VM review round STOP')) and ('qualification 20' in line.lower() or 'VM review round STOP' in line):
   lines[i]='- **'+('VM scope passed' if accepted else 'VM review round STOP')+' — package 14:** '+summary;n+=1
  elif name.endswith('EMERGENCY.md') and line.startswith('Qualification 20 remains the last accepted complete VM route.'):
   lines[i]=summary;n+=1
 assert n==(2 if name.endswith('INSTALL.md') else 1),(name,n)
 after='\n'.join(lines)+'\n'
 blocks=lambda s:re.findall(r'```bash\n(.*?)\n```',s,re.S)
 assert blocks(before)==blocks(after),'STOP: status update changed an owner command'
 assert [x for x in before.splitlines() if '**OPEN' in x]==[x for x in after.splitlines() if '**OPEN' in x]
 assert after.count('NOT RELEASED')>=before.count('NOT RELEASED')
 p.write_text(after,encoding='utf-8',newline='\n');changes.append(dict(sha256=sha(p),path=name,status_paragraphs=n,bash_blocks_unchanged=True,open_gates_unchanged=True))
(d/'guide-status.json').write_text(json.dumps(dict(status='passed; actual terminal status only',acceptance_met=accepted,files=changes),indent=2)+'\n',encoding='utf-8',newline='\n')
print('CLOSING_REPORT_AND_GUIDES',accepted,'LOCAL ONLY; no push')
