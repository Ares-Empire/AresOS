"""Pinned -no-reboot/-no-shutdown host reset, with the original safety tail."""
import pathlib
import tempfile
import unittest
import ast
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch
import test_owner_tools as common
import owner_vm as vm


class ResetTest(unittest.TestCase):
    def test_firmware_audit_class_is_unchanged_from_reviewed_parent(self):
        source=(common.ROOT/'os/ci/two_disk_vm.py').read_text()
        node,=[n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='Audit']
        proof=json.loads((common.ROOT/'os/manifest/ci/14/14zzc-preflight/source-proof.json').read_text())
        body=''.join(source.splitlines(keepends=True)[node.lineno-1:node.end_lineno])
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),proof['audit_source_sha256'])
    def guest(self,reason='host-qmp-system-reset',guest_triggered=False):
        g=object.__new__(vm.Guest)
        events=[]
        def qmp(command,*unused):
            if command=='system_reset':events.append(dict(event='SHUTDOWN',data=dict(guest=guest_triggered,reason=reason)))
            elif command=='quit':events.append(dict(event='SHUTDOWN',data=dict(guest=False,reason='host-qmp-quit')))
        g.monitor=SimpleNamespace(command=Mock(side_effect=qmp),events=events,reader=Mock())
        g.process=Mock(returncode=0);g.media_absent=Mock();g.writes=Mock()
        g.transcript=g.boot_transcript='';g.authentication_started=False;g.secrets=[]
        return g

    def test_exact_host_qmp_shutdown_retains_original_counter_and_closing_audits(self):
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as directory, \
                patch.object(vm.td,'EVIDENCE',pathlib.Path(directory)),patch.object(vm.owner_xhci,'checkpoint'):
            g=self.guest();g.hard_reset('trial')
            self.assertTrue(g.stopped_events_verified)
            g.writes.assert_called_once_with('trial')
            self.assertEqual(g.monitor.command.call_args_list[0].args,('system_reset',))
            self.assertEqual(g.monitor.command.call_args_list[-1].args,('quit',))
            self.assertTrue((pathlib.Path(directory)/'trial-hard-reset.json').is_file())

    def test_wrong_reason_or_guest_origin_never_passes(self):
        for reason,triggered in [('guest-reset',True),('host-qmp-quit',False),('host-qmp-system-reset',True)]:
            with self.subTest(reason=reason,guest=triggered),patch.object(vm.owner_xhci,'checkpoint'):
                g=self.guest(reason,triggered)
                with self.assertRaises(AssertionError):g.hard_reset('trial')
                g.writes.assert_not_called()

    def test_attached_tools_refuses_before_qmp_reset(self):
        g=self.guest();g.media_absent.side_effect=AssertionError('stick attached')
        with self.assertRaisesRegex(AssertionError,'stick attached'):g.hard_reset('trial')
        g.monitor.command.assert_not_called()

if __name__=='__main__':unittest.main()
