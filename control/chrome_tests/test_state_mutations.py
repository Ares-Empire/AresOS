"""Each panel fix has a removal mutation killed by a focused regression.

Mutations run in disposable copies inside this worktree, never in the checkout
being tested and never against a browser or the owner's application state.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

CONTROL=Path(__file__).resolve().parents[1]
WORK=CONTROL.parent/'.work'/'state-mutations'


class Mutations(unittest.TestCase):
    def test_s1_to_s12_removal_mutations_fail(self):
        cases=[
            ('S1 restore','aresos_control/storage.py',[("    def _restore_chrome(self):\n","    def _restore_chrome(self):\n        return\n")],
             'test_state_fixes.StateFixes.test_s1_restore_reconciles_revocation_readonly_and_qualification_offline'),
            ('S1 qualification','aresos_control/chrome/qualification.py',[("self.store.chrome_state.get('chrome:qualification'","self.store.get('chrome:qualification'")],
             'test_state_fixes.StateFixes.test_s1_readable_policy_rollback_cannot_hide_committed_qualification'),
            ('S1 large qualification','aresos_control/storage.py',[("            if key=='chrome:qualification':","            if False:")],
             'test_state_fixes.StateFixes.test_s1_large_qualification_history_restores_without_a_large_rewrite'),
            ('S2 status','aresos_control/engine.py',[("        if app == 'chrome' or op is None or op.get('app') == 'chrome':\n            op=self.adapters['chrome'].committed.get('op:'+op_id)\n",'')],
             'test_state_fixes.StateFixes.test_s2_failed_completion_marker_never_reports_uncommitted_done'),
            ('S2 pending','aresos_control/engine.py',[("yield from self.adapters['chrome'].pending_rows()","yield from ()")],
             'test_state_fixes.StateFixes.test_s2_readable_rollback_pending_uses_committed_reservation'),
            ('S3 terminal','aresos_control/storage.py',[("                if value['state']=='reserved':","                if value['state']=='failed':\n                    value.update(state='unknown',ack=False)\n                elif value['state']=='reserved':")],
             'test_state_fixes.StateFixes.test_s3_cancel_and_expiry_ack_survive_rollback_restore_archive_restart'),
            ('S4 retirement','aresos_control/retention.py',[("    from .warnings import source_notices\n    changes={}","    return\n    from .warnings import source_notices\n    changes={}")],
             'test_state_fixes.StateFixes.test_s4_more_than_512_completed_checks_leave_room_for_chrome_and_mail'),
            ('S4 receipts','aresos_control/chrome/adapter.py',[("        if source is None:source=self.committed.historical(key)","        if source is None:pass")],
             'test_state_fixes.StateFixes.test_s4_retirement_keeps_warning_ack_and_dedup_identity_in_history'),
            ('S4 archive admission','aresos_control/engine.py',[("            self.store.archiving=True\n            try:retention.retire_chrome(self.store)\n            finally:self.store.archiving=False", "            retention.retire_chrome(self.store)")],
             'test_state_fixes.StateFixes.test_s4_archive_retires_checks_even_above_the_shared_history_quota'),
            ('S5 live check','aresos_control/recovery.py',[("    if include_checks:\n        keys.update(open_filings(store))","    keys.update(key for key,value in store.iter_items('intent:chrome:') if value.get('state')=='started')\n    if include_checks:\n        keys.update(open_filings(store))"),("        if key.startswith('intent:chrome:'):continue","        if False:continue"),("if (key, notice_id) not in candidates and not (include_checks", "if (key, notice_id) not in candidates and not key.startswith('intent:chrome:') and not (include_checks")],
             'test_state_fixes.StateFixes.test_s5_clean_stopped_submission_has_no_interruption_warning'),
            ('S5 startup','aresos_control/recovery.py',[("if not persist and notice.get('app')=='chrome':","if False:"),("if current.get('state') in {'done','failed'}:","if False:")],
             'test_state_crashes.CrashCuts.test_s11_actual_process_cuts_before_and_after_input_keep_every_committed_view'),
            ('S6 lost queue','aresos_control/chrome/adapter.py',[("            self.reconcile_checks(facts,queued)","            pass")],
             'test_state_fixes.StateFixes.test_s6_lost_queue_resolves_native_check_and_preserves_uncertain_occurrence'),
            ('S6 stale queue returns','aresos_control/chrome/adapter.py',[("                if source.get('resumable') is False:","                if False:")],
             'test_state_fixes.StateFixes.test_s6_a_stale_step_cannot_be_prepared_if_the_same_queue_entry_returns'),
            ('S6 read-gated queue loss','aresos_control/chrome/adapter.py',[("    def reconcile_open_checks(self):\n","    def reconcile_open_checks(self):\n        return\n")],
             'test_state_fixes.StateFixes.test_s6_notices_and_pending_resolve_lost_queues_without_page_reads'),
            ('S6 unavailable queue','aresos_control/chrome/adapter.py',[("if exc.code not in {'chrome_unavailable','transport_error'}:raise","if True:raise")],
             'test_state_fixes.StateFixes.test_s6_unavailable_queue_keeps_its_committed_open_check_readable'),
            ('S7 admission','aresos_control/engine.py',[("                        and request.get('action')!='chrome_drop'\n",'')],
             'test_state_fixes.StateFixes.test_s7_drop_spends_cancel_reservation_at_history_and_physical_boundaries'),
            ('S8 public archive','aresos_control/engine.py',[("if exc.code!='owner_state_unavailable':raise","if True:raise")],
             'test_state_fixes.StateFixes.test_s8_archive_remains_publicly_reachable_above_index_bound_and_after_restart'),
            ('S8 Mail preservation','aresos_control/engine.py',[("                result=self._pending(app,args,False,include_chrome=False)","                result={'items':[],'total':0,'cursor':None}")],
             'test_state_fixes.StateFixes.test_s8_index_bound_keeps_readable_mail_warnings_and_their_continuation'),
            ('S9 Mail continuation','aresos_control/engine.py',[("            total=chrome_total+other_total","            total=chrome_total")],
             'test_state_fixes.StateFixes.test_s9_mail_only_and_mixed_fallback_keep_all_remaining_counts'),
            ('S10 chronology','aresos_control/chrome/adapter.py',[("notice.get('created_at',int(created*1_000_000_000))","created")],
             'test_state_fixes.StateFixes.test_s10_mixed_notice_pages_use_nanosecond_chronology'),
            ('S11 oracle','chrome_tests/chrome_oracle.py',[("    assert set(warnings)==expected['warnings'],('warning mismatch',set(warnings),expected['warnings'])","    pass")],
             'test_state_oracle.Oracle.test_s11_r1_missing_warning_and_extra_live_interruption_both_fail'),
            ('S12 dialog','aresos_control/chrome/adapter.py',[("'tree':tree[offset:end],'dialog':visible(facts.get('dialog'))}","'tree':tree[offset:end]},'dialog':visible(facts.get('dialog'))")],
             'test_state_fixes.StateFixes.test_s12_every_page_text_copy_is_inside_untrusted_content'),
            ('S12 stages','aresos_control/engine.py',[("        elif op['app']=='chrome':\n            outcome={'untrusted_content':visible(outcome)}\n",'')],
             'test_state_fixes.StateFixes.test_s12_every_page_text_copy_is_inside_untrusted_content'),
        ]
        WORK.mkdir(parents=True,exist_ok=True)
        for label,file,replacements,test in cases:
            with self.subTest(mutation=label),tempfile.TemporaryDirectory(dir=WORK) as directory:
                root=Path(directory)
                shutil.copytree(CONTROL,root/'control',ignore=shutil.ignore_patterns('__pycache__','node_modules'))
                path=root/'control'/file;text=path.read_text()
                for before,after in replacements:
                    self.assertEqual(text.count(before),1,(label,before))
                    text=text.replace(before,after,1)
                path.write_text(text)
                environment={**os.environ,'PYTHONPATH':str(root/'control')+os.pathsep+str(root/'control'/'chrome_tests')}
                result=subprocess.run([sys.executable,'-B','-m','unittest',test],cwd=root,env=environment,capture_output=True,text=True,timeout=60)
                self.assertNotEqual(result.returncode,0,(label,'mutation survived',result.stdout+result.stderr))
                self.assertIn('FAILED (',result.stderr,(label,result.stdout+result.stderr))
                self.assertNotIn('Failed to import test module',result.stderr)
                print('STATE MUTATION KILLED',label,test,flush=True)
