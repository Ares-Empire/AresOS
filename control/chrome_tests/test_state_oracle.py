"""The test-owned oracle must reject false warnings, missing results and replay."""
import ast
from pathlib import Path
import unittest
from chrome_oracle import expectations,identity,compare,compare_validity


class Oracle(unittest.TestCase):
    def test_s11_oracle_has_no_production_imports_or_sqlite_dependency(self):
        tree=ast.parse(Path(__file__).with_name('chrome_oracle.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):names=[item.name for item in node.names]
            elif isinstance(node,ast.ImportFrom):names=[node.module or '']
            else:continue
            self.assertTrue(all(not name.startswith(('aresos_control','sqlite3')) for name in names),names)

    def sample(self,done=False,ack=False):
        step={'kind':'activation','element':'e1'}
        source_id=identity(['session',1,step]);key='intent:chrome:'+source_id
        source={'id':source_id,'state':'done' if done else 'started'}
        rows={key:source};ever=dict(rows);acks=set()
        if done:
            source['warning_checks']={'page_activation':{'occurrence_id':source_id}}
            ever['notice:'+source_id]={'id':source_id}
            if ack:acks.add('notice:'+source_id)
        return [{'kind':'step','step':step,'tab':1,'session':'session'}],{'rows':rows,'ever':ever,'acks':acks},source_id

    def test_s11_r1_missing_warning_and_extra_live_interruption_both_fail(self):
        script,record,identifier=self.sample()
        expected=expectations(script,[],record)
        with self.assertRaises(AssertionError):compare(expected,warnings=[])
        with self.assertRaises(AssertionError):compare(expected,warnings=[identifier,'false-interruption'])
        script,record,_=self.sample(done=True,ack=True)
        self.assertEqual(expectations(script,[],record)['warnings'],set())

    def test_s11_r2_receiver_context_and_duplicate_inputs_are_independent_evidence(self):
        script,record,_=self.sample()
        for arrival in [{'operation':'op','authorized':False,'committed_submitting':True},
                        {'operation':'op','authorized':True,'committed_submitting':False}]:
            with self.assertRaises(AssertionError):expectations(script,[arrival],record)
        arrival={'operation':'op','authorized':True,'committed_submitting':True}
        with self.assertRaises(AssertionError):expectations(script,[arrival,arrival],record)

    def test_s11_round27_check_cannot_close_without_required_warning_result(self):
        script,record,identifier=self.sample(done=True)
        del record['ever']['notice:'+identifier]
        with self.assertRaises(AssertionError):expectations(script,[],record)

    def test_s11_r3_cached_refusal_or_current_verdict_fails_after_live_state_changes(self):
        op={'generation':'g','expires':100,'payload':{'process_session':'p','binding':{'session':'s','frame':0,'document':'d'}}}
        live={'generation':'g','now':1,'session':'s','process_session':'p','documents':{0:'d'}}
        compare_validity(op,'current',live)
        with self.assertRaises(AssertionError):compare_validity(op,'refused',live)
        live['session']='new'
        with self.assertRaises(AssertionError):compare_validity(op,'current',live)
