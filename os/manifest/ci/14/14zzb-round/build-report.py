"""Write the final accepted round report and budget from retained facts."""
import json, pathlib, subprocess
r = pathlib.Path.cwd(); w = r / '.work/14'; out = r / 'os/manifest/ci/14/14zzb-round'
head = '211df982b5bf080b0167b8fe6e8dd3c5eb264fe8'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() == head
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def order(v):
    if isinstance(v,list): return [order(x) for x in v]
    if isinstance(v,dict):
        keys=[k for k in v if k.endswith('sha256')]
        return {k:order(v[k]) for k in keys+[k for k in v if k not in keys]}
    return v
def write(p,v): p.write_text(json.dumps(order(v),indent=2)+'\n',encoding='utf-8',newline='\n')
closed=read(out/'ledger.json'); ledger=closed['ledger']; org=closed['organization']
proof=read(out/'qualification20-acceptance.json'); probe=read(out/'probe31-acceptance.json')
facts=read(out/'terminal-facts.json')
assert proof['acceptance_met'] and proof['native_tests']==probe['native_tests']==600
assert ledger['consumed_minutes']==2301 and org['remaining_minutes']==1410
assert closed['organization_ledger_comparison']['package_increase']==closed['organization_ledger_comparison']['organization_increase']==132
assert facts['expected_refusals_zero_mutations'] and facts['final_windows_marker_boots_completed']==2

write(out/'round.json',dict(status='accepted VM qualification20; terminal success; closing commit local only',
    brief='briefs/14zzb-step-limit.md',pushed_head=head,probe31=41321806985,qualification20=41324240079,
    acceptance_met=True,pr13_ready=False,pr13_readiness='pending final local checks',
    pushes=1,probes=1,qualifications=1,reruns=0,closing_commit_local_only=True,
    consumed_minutes=2301,cap=2750,package_minutes_left=449,
    dispatch_counts={'probe':31,'owner-tools':20},dispatch_caps={'probe':32,'owner-tools':21},
    organization_included_minutes_left=1410,other_repos_reserve=150,
    push_reservation=0,closing_reservation=0,paid_budget_read=False,vm_step_limit=180,
    qualification_bound=220,probe_bound=72,vm_actual_minutes=facts['vm_seconds']/60,
    whole_job_actual_minutes=facts['whole_job_seconds']/60,
    further_dispatch_authorized=False,additional_rounds_required=0,
    physical_installation='NOT RELEASED; physical and laptop gates remain',
    owner_payload_or_fingerprint_or_runtime_changed=False,serial_plan_implemented=False))

budget=read(r/'reviews/14-owner-tools/BUDGET.json'); budget.update(ledger)
budget.update(status='14zzb accepted: probe31 and complete qualification20 passed on the same head; round closed locally',
    acceptance_met=True,package_minute_ledger_trusted=True,
    organization_ledger_comparison=closed['organization_ledger_comparison'],
    organization_budget_snapshot=org,pushed_head=head,
    this_round_starting_ledger=2144,this_round_starting_counts={'probe':30,'owner-tools':19},
    current_round=dict(brief='14zzb',probe31=41321806985,qualification20=41324240079,
        status='complete success; all independent acceptance checks passed',pushes=1,reruns=0),
    closed_round_manifest='os/manifest/ci/14/14zzb-round/round.json',
    this_round_accounting_charge_changes=[],further_dispatch_authorized=False)
write(r/'reviews/14-owner-tools/BUDGET.json',budget)

section=f'''## 14zzb REPORT: sized limits; probe 31 and complete qualification 20 passed

**Disposition:** [Probe 31](https://github.com/Ares-Empire/AresOS/actions/runs/41321806985)
and [qualification 20](https://github.com/Ares-Empire/AresOS/actions/runs/41324240079)
both completed **successfully**, once each, on the same pushed head
`{head}`. Independent evidence review passed. **Acceptance is met** for this
package's VM scope. There was **one fast-forward push through the privacy hook**,
no rerun, no merge, no image build or publication. This closing REPORT, ledger
and curated evidence commit is **local only**. PR readiness: FINAL_READINESS.
Physical installation remains **NOT RELEASED**.

'''
section+=(w/'14zzb/report-prefix.md').read_text(encoding='utf-8')
section+='''### Verified: actual probe and qualification

- Probe 31: **600 native tests / 142.001s / zero skips**; the mandatory unchanged
  30-second timing test passed. Actual kernel negative control saw 0 press / 1
  release with the old getter, and 1 / 1 with the separate-client fix. Twenty
  native loop checks, 37 SHA/syntax-verified transfers, one AT keyboard boot,
  57 static key mappings and seven healthy xHCI checkpoints passed. Raw replay:
  three protected captures, four zero-write/unmap samples, three BootNext
  replays and two NVRAM/all-variable delta replays.
- Qualification 20: **600 native tests / 202.315s / zero skips**, mandatory timing
  case and real-kernel negative/positive counter proof passed. Twenty native
  loop checks, 38 physical owner-action records and **633 SHA/syntax-verified
  root-only tmpfs transfers** passed. Every one of the **23 hidden-input
  readiness/completion pairs** and pre-Enter/counter proofs passed, without
  recording values. All three public handoffs passed. Five distinct prompt
  waits each used one observer-authorized Enter resync. Nine actual AT keyboard
  boots each checked 57 mappings; all **104** xHCI health checkpoints were healthy.
- Independent replay of actual raw qualification files passed: **16 protected
  captures, 17 zero-write/unmap samples, 16 decoded-varstore/BootNext replays,
  15 NVRAM rule replays and 15 complete variable-delta recomputations**. This
  includes `default-stock` and both final Windows stages, not just the prior tail.
- Complete log scans passed with **four** approved pinned cosign action checksum
  occurrences in each run. Probe artifacts: **509 = 507 exact public ISO-name
  lines + two whole kernel certificate messages**. Qualification artifacts:
  **527 = 507 ISO lines + 20 whole kernel certificate messages**. Every occurrence
  is recorded by file, line, label and whole-line SHA in the artifact review.
  Whole-source classification and the redacted token-position cross-check passed;
  **zero unknown findings**, zero native-log findings, no new ignore/rule entry.
- The first local qualification reviewer glob selected 12 files: three handoff
  receipts plus their transport and public-echo companions. The selector now
  requires `-handoff-<integer>.json`. The assertion still requires exactly three
  receipts and every original field check; every other AST node is identical.
  **Six tests / 0.037s** cover the real 12-file set and missing/extra/wrong-field
  refusals. Original dispatch-time bytes, the corrected reviewer and tests are
  archived. The complete local acceptance gate then passed. This was a zero-cost
  read-only reviewer correction; no CI rerun or pushed-tree change.

### Acceptance evidence for every remaining stage

| Stage | Retained qualification 20 evidence |
| --- | --- |
| Offline install / first stock boot | `owner-tools-result.json` records offline install, hardware boot, Windows round trip, hot-plugged tools, removal before every reboot, prepare, zero-mutation rerun, unchanged state after network and export. |
| Plain US failure and revert | `layout-us-begin`, rejected second-console login, `layout-unproved-reboot-refusal` with zero mutations, `layout-us-revert`, fresh German login, `layout-reverted-proof` and `layout-revert-finish` passed. |
| US International success | `layout-intl-begin`, fresh tty4 password login, `layout-intl-proof`, finish, subsequent `aresos-intl` system check, tty3 login/password sudo and physical foot typing passed under `us-intl`. |
| Back to German | `layout-de-begin`, fresh tty4 login, `layout-back-de-proof`, finish and subsequent `aresos-back-de` system/console/foot checks passed under `de`. |
| Rollback | `owner-rollback` passed on AresOS, followed by refreshed title and reboot. `rollback-stock` common boot verified the saved stock identity and physical checks. |
| Guard on booted stock | `rollback-from-stock-refused` returned the expected STOP with **zero mutations**. |
| Keep stock / default | `owner-keep-stock`, refreshed `owner-keep-stock-title` and reboot passed. `default-stock-check` and `default-stock-default-verified-deployments.json` confirm the saved stock identity first, booted and pinned, with no staged work; console, login/sudo, greeter and foot checks passed. |
| Final Windows | `final-unattended-windows` and `final-detached-windows` marker boots both completed, with tools absent and raw protected-disk, BootNext, NVRAM and full-variable audits passed. |

The completed VM step took **117.67 minutes** (below 180); setup before it took
**13.68 minutes**, post-step work **0.15 minutes**, and the whole job **131.50
minutes** (below 220). Full observed stage timings and action result/hash bindings
are in [terminal facts](../../os/manifest/ci/14/14zzb-round/terminal-facts.json).
The acceptance summaries and private artifact identities are archived under
[this round](../../os/manifest/ci/14/14zzb-round/round.json); raw consoles,
screenshots, varstores and diagnostics remain only in the retained private artifacts.

### Budget: complete history and organization comparison

| Point | Added package minutes | Package total / 2750 | Organization used / free |
| --- | ---: | ---: | ---: |
| Before this round | 0 | 2144 | 433 / 1567 |
| Probe 31 | 25 | 2169 | 458 / 1542 |
| Qualification 20 | 132 | **2301** | **590 / 1410** |

History completeness is proven against **153/153 IDs over two pages**. Counts
are **31 probes / 20 owner-tools qualifications**, below caps **32 / 21**.
The package has **449 minutes left**; organization reserve stays **150**.
Saved pre-qualification package and organization totals both increased by
**132**, so there is no undercount. Earlier ordered job charges did not change
in this limit-only round; the historical probe-29 accounting correction remains
recorded. Each job's charge rule and source-response SHA are in the ledger.
November is **free-minutes-only**: no paid budget API read, no paid overflow,
zero paid Actions-minute quantity/amount. Push and closing reservations remain
zero under 14zw's local-hook decision. No further dispatch is authorized.

### Not verified / release gate

No real laptop, physical USB restore/copy, physical installation, physical F12
boot, firmware, hardware keyboard or laptop-side followability gate was exercised.
The existing INSTALL, EMERGENCY and RELEASE-GATE remain unchanged and truthful;
physical release remains NOT RELEASED. The existing **For package 15** list below
still applies. The nine local-host limitations remain documented; native CI ran
all 600 tests without skips. No Gradle or Minecraft process was started.

### JUDGMENT-CALL / PLAN-GAP / open questions

The 180/220 limits are the integrator's decision. The conservative comparable
tail selection and the exact Q17 completion correction are documented above;
the resulting margin fits before any dispatch. No product choice, audit,
predicate, retry policy or owner command changed. No serial plan was implemented.
There is no remaining VM acceptance gap and no further round is needed for this
brief. Owner/integrator review and the physical release gates remain; never merge.

'''
report=r/'reviews/14-owner-tools/REPORT.md'
old=report.read_text(encoding='utf-8'); first='# 14: checked owner tools\n\n'
assert old.startswith(first) and '## 14zzb REPORT' not in old
report.write_text(first+section+old[len(first):],encoding='utf-8',newline='\n')
print('REPORT_AND_BUDGET_PREPARED accepted; final local checks/readiness pending; no push')
