"""Local synthetic route; no VM, hardware query, dispatch or credentials."""
import hashlib
import json
import pathlib
import sys

r=pathlib.Path.cwd()
sys.path[:0]=[str(r/'os/tests'),str(r/'os/ci')]
import checkout_sources as checkout
import test_owner_walk

walk=test_owner_walk.walk(ps2=True)
assert len([s for s in walk['hidden_shapes'] if s['phase']=='left'])==27
assert len([s for s in walk['hidden_shapes'] if s['phase']=='handoff'])==3
assert {'final-unattended-windows','final-detached-windows'}<=set(walk['markers'])
commands=walk.pop('commands');walk.pop('typed');visible=walk.pop('visible_blocks')
folder=r/'os/manifest/ci/14/host-walk'
old=json.loads((folder/'result.json').read_text())
sources={row['path'] for row in old['sources']}
sources.update(p.relative_to(r).as_posix() for p in (r/'os/owner-tools').glob('*.py'))
payload=json.loads((r/'os/owner-tools/payload/SHA256.json').read_text())
sources.update('os/owner-tools/payload/'+row['path'] for row in payload)
sources.update(('os/owner-tools/payload/SHA256.json','os/owner-tools/payload/SHA256SUMS'))
sources.update(p.relative_to(r).as_posix() for p in (r/'os/tests').glob('test_owner_*.py'))
sources.update(('os/ci/two_disk_vm.py','os/tests/test_owner_setup_resume.py','os/tests/test_owner_abandon.py','os/tests/test_owner_bootstrap.py','os/tests/test_owner_reset.py','os/tests/serial_pty.py','os/tests/owner-tools.Tests.ps1','os/manifest/ci/14/14zzc-preflight/source-proof.json','docs/install-tools/OwnerTools.psm1','docs/INSTALL.md','docs/EMERGENCY.md'))
sources.update(('os/tests/test_owner_step_limits.py','os/manifest/ci/14/14zzc-timing/projection.json','.github/workflows/os-image.yml'))
sources.update(('os/tests/owner_bundle_fixture.py','os/tests/owner_fuse_shim.py','briefs/14zze-checkout-bytes.md'))
sources.update(('.gitattributes','os/ci/checkout_sources.py','os/tests/test_checkout_sources.py','os/tests/fixtures/owner-tools/14zzd-checkout-sources.json'))
sources.update(('os/tests/test_rehearsal_budget.py','os/tests/test_rehearsal_history.py','os/tests/test_rehearsal_retry.py'))
sources.update(('os/tests/test_job_accounting.py','os/tests/test_cosign_log_class.py','os/tests/test_owner_guard.py','os/tests/test_keyboard_release.py','os/tests/test_installer_webui.py','reviews/14-owner-tools/classify-artifacts.py','os/ci/rehearsal-packages.json','os/tests/fixtures/owner-tools/14zy-probe29-job.json','os/tests/fixtures/owner-tools/14zz-accounting-source.json','os/tests/fixtures/owner-tools/14zz-cosign-log-sources.json','os/tests/fixtures/owner-tools/cosign-step.template','os/tests/fixtures/owner-tools/cosign-combined.template','os/manifest/ci/14/14zz-cosign/action.yml.template','os/manifest/ci/14/14zz-cosign/source.json','os/manifest/ci/14/14zz-cosign/LICENSE'))
sources.update(('os/ci/owner_counter_kernel.py','os/tests/test_owner_counter_flush.py','os/tests/fixtures/owner-tools/counter-14zx-released.py','os/tests/fixtures/owner-tools/counter-flush-source.json'))
sources.update(p.relative_to(r).as_posix() for p in (r/'os/manifest/ci/14/14zu-local').iterdir() if p.suffix=='.gz')
sources.update(('os/ci/rehearsal_guard.py','os/tests/test_organization_budget.py','os/tests/test_owner_guard.py','os/ci/owner_xhci.py','os/ci/keyboard_vm.py','os/tests/test_owner_ps2.py',
 'os/manifest/ci/14/14zu-local/sources.json','os/manifest/ci/14/14zu-local/source-proof.json',
 'os/manifest/ci/14/14zu-local/walk.py','os/manifest/ci/14/14zu-local/source-proof.py',
 'os/tests/test_owner_records_prompt.py','os/tests/fixtures/owner-console/14zt-q15-shape.json','os/tests/test_owner_layout_adapter.py','os/tests/fixtures/owner-tools/dumpkeys-us-intl.json','os/tests/fixtures/owner-tools/layout-adapter-sources.json','os/tests/owner_shim.py','os/tests/test_serial_staging.py'))
old.update(visible_command_blocks=[dict(sha256=hashlib.sha256(text.encode()).hexdigest(),characters=len(text),profile=profile) for text,profile in visible], trusted_bootstrap=True, abandoned_trial_reset=True, status='passed',kind='local synthetic PS2/xHCI health route, not VM qualification',
 stages=walk['stages'],markers=walk['markers'],checks=walk['checks'],
 cluttered_prompt_waits=walk['prompt_waits'],fresh_idle_answers=walk['fresh_idle_answers'],prompt_resyncs=walk['resyncs'],
 hidden_read_receipts=walk['hidden_reads'],hidden_transition_shapes=walk['hidden_shapes'],cursor_wait_shapes=walk['wait_shapes'],
 typed_profiles=sorted({row['profile'] for row in walk['physical_cases']}),ps2_health=True,physical_typing_cases=walk['physical_cases'],
 sources=checkout.records(r,sorted(sources)),binding_format='git-checkout-bytes-v1')
old.pop('local_suite',None);old.pop('tests',None)
old['current_verification']='os/manifest/ci/14/14zze-preflight/preparation.json'
(folder/'result.json').write_text(json.dumps(old,indent=2)+'\n',encoding='utf-8',newline='\n')
(folder/'guest-commands.json').write_text(json.dumps(commands,indent=2)+'\n',encoding='utf-8',newline='\n')
result=dict(sources=old['sources'],binding_format='git-checkout-bytes-v1',trusted_bootstrap=True,abandoned_trial_reset=True,visible_command_blocks=len(visible),status='passed',kind='local synthetic guest responses; no VM qualification',
 stages=walk['stages'],markers=walk['markers'],cluttered_prompt_waits=len(walk['prompt_waits']),
 idle_authorized_resyncs=len(walk['resyncs']),hidden_pairs=27,public_handoffs=3,
 health_boundaries=len([name for name,source in commands if name.endswith('-xhci-health')]),
 composed_guest_commands=len(commands),strict_bash_syntax=True,uncovered_waits=[],
 keyboard='real public_typing/physical_input/type_text/physical_keys/Guest.keys; only QMP send recorded; physical redraw simulated',physical_typing_cases=walk['physical_cases'],
 clutter='Q15 exact geometry/content shape after tools-stock; synthetic healthy kernel journal. The historical VCSA remains clutter only and never grants authority.',
 pending='Actual PS2 event delivery, FUSE hotplug and health timing need November native/VM runs')
(r/'os/manifest/ci/14/14zze-preflight/walk.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
