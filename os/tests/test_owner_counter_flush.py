"""Local models only. Mandatory real uinput regression runs natively or in guest."""
import ast
import hashlib
import inspect
import json
import pathlib
import shlex
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'os/ci'))
import owner_key_counter as counter
import owner_counter_kernel as kernel
import owner_vm as vm
import owner_login
from guest_shell import syntax


def result():
    def row(press):
        counts = dict(press=press, release=1, repeat=0, syn_dropped=0)
        return dict(counts=counts, press_before_release=press,
                    comparison=counter.compare(dict(complete=True, counts=counts), dict(key_event_count=2)))
    return dict(status='passed', real_kernel=True, skipped=False,
                negative_control=row(0), fixed=row(1))


class CounterFlushTest(unittest.TestCase):
    def test_state_query_opens_and_closes_an_independent_client_even_on_error(self):
        for fail in (False, True):
            with patch.object(counter.os,'open',return_value=202) as opened, patch.object(counter.os,'close') as closed, \
                    patch.object(kernel.fcntl,'ioctl',side_effect=OSError('public fixture') if fail else None) as ioctl:
                if fail:
                    with self.assertRaises(OSError): counter.released('/dev/input/fixture')
                else: self.assertTrue(counter.released('/dev/input/fixture'))
                self.assertEqual(opened.call_args.args[0],'/dev/input/fixture')
                self.assertEqual(ioctl.call_args.args[0],202)
                closed.assert_called_once_with(202)

    def test_all_readers_use_paths_for_state_and_no_getter_on_counting_fd(self):
        observe = ast.parse(inspect.getsource(counter.observe))
        calls = [n for n in ast.walk(observe) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='released']
        self.assertEqual([ast.unparse(n.args[0]) for n in calls],['device'])
        startup = inspect.getsource(counter.start)
        self.assertLess(startup.index('repeat = settings(query, device)'),startup.index('fd = os.open(device'))
        self.assertIn('assert released(ticket[\'device\'])',inspect.getsource(owner_login.login_initialize))
        self.assertNotIn('ioctl',inspect.getsource(counter.observe))
        compile(counter.source(),'counter guest','exec')
        compile(owner_login.guest_source(),'login guest','exec')

    def test_exact_preceding_kernel_flush_call_is_negative_control(self):
        binding=json.loads((ROOT/'os/tests/fixtures/owner-tools/counter-flush-source.json').read_text())
        raw=(ROOT/binding['path']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),binding['sha256'])
        old=raw.decode()
        function = next(n for n in ast.parse(old).body if isinstance(n,ast.FunctionDef) and n.name=='released')
        legacy = ast.parse(inspect.getsource(kernel.legacy_query)).body[0]
        # Same request/buffer/mutate flag as the faulty observer, with a real
        # kernel negative control as well as the positive queued-press proof.
        def ioctls(tree):
            return [ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='ioctl']
        self.assertEqual(ioctls(function),ioctls(legacy))
        self.assertIn('queued(fd)',inspect.getsource(kernel.exercise))

    def test_guest_fallback_is_syntax_checked_and_mandatory_before_hidden_typing(self):
        source=kernel.guest_source();compile(source,'real uinput guest','exec')
        syntax('mandatory-counter-proof',vm.sw.framed('python3 -c '+shlex.quote(source)))
        guest=Mock();guest.capture_json.return_value=result()
        native=dict(status='guest-required',sha='a'*40,skipped=False)
        with patch.object(pathlib.Path,'read_text',return_value=json.dumps(native)), patch.dict(vm.os.environ,GITHUB_SHA='a'*40), patch.object(vm.td,'save') as save:
            vm.Guest.counter_kernel_proof(guest)
        guest.capture_json.assert_called_once()
        self.assertEqual(save.call_args.args[1]['location'],'guest-before-hidden-input')
        body=inspect.getsource(vm.Guest.login_live)
        self.assertIn('self.counter_kernel_proof()',body)

    def test_native_proof_is_reused_but_missing_or_wrong_identity_refuses(self):
        native=dict(result(),sha='a'*40,location='native')
        for change in ({},{'sha':'b'*40},{'skipped':True},{'status':'unknown'}):
            guest=Mock();receipt=dict(native,**change)
            with patch.object(pathlib.Path,'read_text',return_value=json.dumps(receipt)), patch.dict(vm.os.environ,GITHUB_SHA='a'*40), patch.object(vm.td,'save'):
                if change:
                    with self.assertRaises(AssertionError): vm.Guest.counter_kernel_proof(guest)
                else: vm.Guest.counter_kernel_proof(guest)
            guest.capture_json.assert_not_called()

    def test_native_missing_device_defers_and_existing_device_failure_stops(self):
        with patch.object(pathlib.Path,'exists',return_value=False), patch.object(kernel,'prove') as prove, \
                patch.object(pathlib.Path,'write_text') as write,patch.dict(kernel.os.environ,GITHUB_SHA='a'*40):
            kernel.native()
        prove.assert_not_called()
        self.assertEqual(json.loads(write.call_args.args[0])['status'],'guest-required')
        with patch.object(pathlib.Path,'exists',return_value=True), patch.object(kernel,'prove',side_effect=AssertionError('STOP: kernel fixture')), \
                patch.object(pathlib.Path,'write_text') as write,patch.dict(kernel.os.environ,GITHUB_SHA='a'*40):
            with self.assertRaises(AssertionError):kernel.native()
        write.assert_not_called()

    def test_comparison_remains_exact_for_missing_press_or_release(self):
        for p,r in ((32,33),(33,32),(32,32),(33,33)):
            value=dict(complete=True,counts=dict(press=p,release=r,repeat=0,syn_dropped=0))
            self.assertEqual(counter.compare(value,dict(key_event_count=66))['matches'],p==r==33)


if __name__ == '__main__': unittest.main()
