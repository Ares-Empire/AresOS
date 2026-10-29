"""Pinned ostree hold identity; no privileged process or disk operations."""
import ast
import copy
import inspect
import json
import pathlib
import tempfile
import unittest
from unittest.mock import Mock, patch

import test_owner_tools as common
import test_stock_prepare as prepare

ROOT, owner = common.ROOT, common.owner
FIXTURE = ROOT/'os/tests/fixtures/owner-tools/finalize-hold.json'


class FinalizeHoldTest(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads(FIXTURE.read_text())
        self.hold = self.fixture['unit_derived_hold']
        self.scope = {'__name__': 'fixture'}
        exec(compile(prepare.program(prepare.PAUSE, 'PAUSE_STOCK'), str(prepare.PAUSE), 'exec'), self.scope)

    def classify(self, rows):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            root = pathlib.Path(directory)
            for index, row in enumerate(rows, 1):
                process = root/str(index)
                process.mkdir()
                (process/'exe').write_text(row['exe'])
                (process/'cmdline').write_bytes(('\0'.join(row['cmdline'])+'\0').encode())
                (process/'cgroup').write_text(row['cgroup'])
            with patch.object(pathlib.Path, 'readlink', lambda p: pathlib.PurePosixPath(p.read_text())):
                return self.scope['deployment_processes'](root)

    def refuse(self, rows, state=None):
        with patch('subprocess.run') as run, patch('subprocess.Popen') as popen, patch('subprocess.check_call') as call:
            with self.assertRaisesRegex(owner.Stop, 'client active|transaction active or unknown'):
                owner.idle(state or common.stock(), rows)
            run.assert_not_called();popen.assert_not_called();call.assert_not_called()

    def test_pinned_units_distinguish_hold_from_shutdown_finalizers(self):
        proof=json.loads((ROOT/'os/manifest/ci/14/14zq-finalize-sources/index.json').read_text())
        hold, final, bootc=proof['units']
        self.assertEqual(hold['exec_start'], ['+/usr/bin/ostree admin finalize-staged --hold'])
        self.assertEqual(hold['cgroup'], self.hold['cgroup'].strip().split('::')[1])
        self.assertEqual(final['exec_start'], [])
        self.assertEqual(final['exec_stop'], ['/usr/bin/ostree admin finalize-staged'])
        self.assertEqual(bootc['exec_start'], [])
        self.assertEqual(bootc['exec_stop'], ['/usr/bin/bootc composefs-finalize-staged'])
        self.assertFalse(proof['path_units_present'])
        self.assertIn('Wants=ostree-finalize-staged-hold.service', final['dependencies'])

    def test_real_classifier_retained_q12_daemon_and_unit_derived_hold_pass_idle(self):
        self.assertFalse(self.fixture['retained_q12']['post_staging_process_list_retained'])
        retained=[r['process'] for r in self.fixture['retained_q12']['records']]
        owner.idle(common.stock(), self.classify(retained))
        rows=self.classify(retained+[self.hold])
        self.assertTrue(rows[0]['excluded_as_daemon'])
        self.assertFalse(rows[1]['excluded_as_daemon'])
        self.assertTrue(rows[1]['excluded_as_system_helper'])
        owner.idle(common.stock(), rows)
        self.assertFalse(self.scope['deployment_client'](rows[1]))

    def test_wrong_cgroup_or_any_argv_change_or_exe_remains_client(self):
        variants=[]
        for cgroup in ('0::/user.slice/session-1.scope\n','0::/system.slice/ostree-finalize-staged-hold.service/child\n',
                       '0::/system.slice/ostree-finalize-staged-hold.service-evil\n',
                       '0::/system.slice/ostree-finalize-staged.service\n',
                       self.hold['cgroup']+'1:name=systemd:/system.slice/ostree-finalize-staged-hold.service\n'):
            variants.append(dict(self.hold,cgroup=cgroup))
        for argv in (['ostree','admin','finalize-staged','--hold'],self.hold['cmdline'][:-1],
                     self.hold['cmdline']+['--extra'],['/usr/bin/ostree','admin','finalize-staged','--hold=true']):
            variants.append(dict(self.hold,cmdline=argv))
        for exe in ('/tmp/ostree','/usr/bin/ostree (deleted)'):
            variants.append(dict(self.hold,exe=exe))
        for variant in variants:
            with self.subTest(variant=variant):
                rows=self.classify([variant]);self.assertFalse(rows[0]['excluded_as_system_helper']);self.refuse(rows)

    def test_real_clients_and_shutdown_finalizers_still_block(self):
        for exe,argv,unit in (
            ('bootc',['/usr/bin/bootc','upgrade'],'bootc-fetch-apply-updates.service'),
            ('rpm-ostree',['/usr/bin/rpm-ostree','upgrade'],'uupd.service'),
            ('ostree',['/usr/bin/ostree','admin','deploy'],'ostree-finalize-staged-hold.service'),
            ('ostree',['/usr/bin/ostree','admin','finalize-staged'],'ostree-finalize-staged.service'),
            ('bootc',['/usr/bin/bootc','composefs-finalize-staged'],'bootc-finalize-staged.service')):
            with self.subTest(argv=argv):
                rows=self.classify([dict(exe='/usr/bin/'+exe,cmdline=argv,cgroup='0::/system.slice/'+unit+'\n')])
                self.assertFalse(rows[0]['excluded_as_system_helper']);self.refuse(rows)

    def test_active_or_unknown_transaction_blocks_even_exact_hold(self):
        rows=self.classify([self.hold])
        for transaction in (['upgrade','owner','socket'],{},False):
            state=common.stock();state['rpm']['transaction']=transaction;self.refuse(rows,state)
        state=common.stock();state['rpm'].pop('transaction');self.refuse(rows,state)

    def test_one_classification_filter_in_owner_and_both_pause_bodies(self):
        first=prepare.program(prepare.PAUSE,'PAUSE_STOCK');second=prepare.program(prepare.PIN,'PAUSE_STOCK')
        self.assertEqual(first,second)
        node=next(n for n in ast.parse(first).body if isinstance(n,ast.FunctionDef) and n.name=='deployment_client')
        actual=ast.parse(inspect.getsource(owner.deployment_client)).body[0]
        self.assertEqual(ast.dump(node),ast.dump(actual))
        self.assertIn('any(deployment_client(p)', first)

    def test_owner_diagnostics_records_classification_before_refusal(self):
        rows=self.classify([self.hold,dict(self.hold,cgroup='0::/user.slice/session-1.scope\n')])
        tools=object.__new__(owner.Tools);tools.pause={'deployment_processes':lambda:rows};tools.host=Mock(trace=[])
        observed=tools.processes();self.refuse(observed)
        self.assertEqual(tools.host.trace,[dict(observation='deployment-processes',processes=rows,mutation=False)])
        self.assertTrue(rows[0]['excluded_as_system_helper']);self.assertFalse(rows[1]['excluded_as_system_helper'])

    def staged_tools(self, directory):
        fixture=self.fixture['staged_gate_fixture']
        tools=object.__new__(owner.Tools);tools.store=pathlib.Path(directory);tools.payload=ROOT/'os/owner-tools/payload'
        tools.release=json.loads((ROOT/'os/manifest/release.json').read_text())
        tools.host=Mock(trace=[])
        tools.host.json.side_effect=lambda *argv:copy.deepcopy(fixture['after']['rpm' if argv[0]=='rpm-ostree' else 'bootc'])
        tools.pause={'deployment_processes':lambda:self.classify([self.hold])}
        tools.save('prepared',fixture['saved']);tools.save('network-verified',{})
        tools.save('disks',dict(target='TARGET',protected='KEEP'))
        return tools,fixture

    def test_staged_title_records_and_reboot_keep_fresh_title_and_media_guards(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            tools,fixture=self.staged_tools(directory)
            tools.save('title',dict(state=fixture['before'],bls=fixture['pre_stage_bls_subset']))
            disk=dict(target=dict(path='/dev/FIXTURE',serial='TARGET'),esp_guid='fixture-esp')
            with patch.object(owner,'resolved_bls',return_value=fixture['pre_stage_bls_subset']), \
                 patch.object(owner,'runtime_state',return_value={}),patch.object(owner,'disk_record',return_value=disk), \
                 patch.object(owner,'media_module',return_value=Mock(find=Mock(return_value=None))):
                with self.assertRaisesRegex(owner.Stop,'Title is stale'):tools.reboot()
                tools.host.mutate.assert_not_called()
                self.assertIn('staged True', '\n'.join(tools.title()))
                self.assertIn('EFI PARTUUID fixture-esp',tools.records())
                tools.reboot();tools.host.mutate.assert_called_once_with('systemctl','reboot')

    def test_staged_verify_layout_and_recovery_keep_their_state_refusals(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            tools,_=self.staged_tools(directory)
            with patch.object(owner,'disk_record'),patch.object(owner,'authentication') as auth, \
                 patch.object(tools,'script') as script,patch.object(tools,'set_keyboard') as keyboard:
                for method in (tools.verify,lambda:tools.layout('begin','us'),tools.recover,lambda:tools.recover(True)):
                    with self.subTest(method=method):
                        with self.assertRaises(owner.Stop):method()
                auth.assert_not_called();script.assert_not_called();keyboard.assert_not_called();tools.host.mutate.assert_not_called()


if __name__=='__main__':unittest.main()
