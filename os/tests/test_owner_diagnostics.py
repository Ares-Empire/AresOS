"""Real refusal recorder and framed reader; only ordinary repo fixtures write."""
import contextlib
import io
import json
import os
import pathlib
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_owner_tools as common
from test_owner_devices import FixtureHost, fixture

ROOT, owner = common.ROOT, common.owner
sys.path.insert(0, str(ROOT/'os/ci'))
import owner_vm as vm
from serial_console import decode_export
from guest_shell import syntax


class DiagnosticsTest(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.root = pathlib.Path(self.stack.enter_context(tempfile.TemporaryDirectory(dir=ROOT/'os/tests')))
        self.usb = self.root/'usb'; self.usb.mkdir()
        self.payload = self.usb/'ares-tools'; common.bundle.build(self.payload)
        self.home, self.records = self.root/'uninstalled', self.root/'diagnostics'
        self.host = FixtureHost(fixture(), self.usb)
        self.stack.enter_context(patch.object(sys, 'dont_write_bytecode', True))
        self.stack.enter_context(patch.object(owner, '__file__', str(self.payload/'owner.py')))
        self.stack.enter_context(patch.object(owner, 'HOME', self.home))
        self.stack.enter_context(patch.object(owner, 'STOP_RECORDS', self.records))
        self.stack.enter_context(patch.object(owner, 'Host', return_value=self.host))
        self.stack.enter_context(patch.object(owner.os, 'geteuid', return_value=0))
        self.stack.enter_context(patch.object(owner.os, 'umask'))
        self.stack.enter_context(patch.object(owner.sys.stdin, 'isatty', return_value=True))
        self.stack.enter_context(patch('builtins.input', side_effect=['TARGET', 'KEEP']))
        real = pathlib.Path.lstat
        def metadata(path, *args, **kwargs):
            info = real(path, *args, **kwargs)
            # Explicit POSIX-metadata adapter for unprivileged DrvFS tests.
            # Every access, byte write and parser still executes unchanged.
            if path in (self.root, self.records) and stat.S_ISDIR(info.st_mode):
                return SimpleNamespace(st_mode=stat.S_IFDIR|0o700, st_uid=0)
            return info
        self.stack.enter_context(patch.object(pathlib.Path, 'lstat', metadata))

    def stop(self, args, message):
        original = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.stack.enter_context(patch.object(owner.sys, 'argv', ['at', *args]))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaisesRegex((owner.Stop, ValueError), message):
            owner.main()
        self.assertFalse(self.home.exists())
        self.assertFalse(any(r.get('mutation') for r in self.host.trace))
        for path, raw in original.items(): self.assertEqual((self.root/path).read_bytes(), raw)
        records = list(self.records.glob('*.json'))
        self.assertEqual(len(records), 1)
        self.assertEqual(set(p.relative_to(self.root) for p in self.root.rglob('*') if p.is_file())-set(original),
            {records[0].relative_to(self.root)})
        result = json.loads(records[0].read_text())
        self.assertEqual(result['status'], 'stopped')
        self.assertIn('Boot0001* Fixture Linux\tHD(', result['firmware']['stdout'])
        self.assertIn('Full diagnostics: '+str(self.records)+' (private)', out.getvalue())
        self.assertNotIn('Boot0001', out.getvalue())
        return result

    def test_install_mapping_stop_saves_exact_raw_text_before_any_installation(self):
        read = self.host.read
        from owner_devices import fixture_firmware
        # A refusal fixture must change the authoritative dp GUID as well;
        # changing display text alone is intentionally irrelevant in 14z.
        raw = fixture_firmware('20000002-1111-2222-3333-444444444444',0x12c000)
        def response(*command, **kw):
            if command == ('efibootmgr', '-v'): return raw
            return read(*command, **kw)
        self.stack.enter_context(patch.object(self.host, 'read', side_effect=response))
        result = self.stop(['install'], 'efibootmgr grammar|uniquely map')
        self.assertEqual(result['firmware']['stdout'], raw)

    def test_early_disk_refusal_still_collects_firmware_without_operational_mutations(self):
        self.host.tree['blockdevices'][1]['children'][0]['mountpoints'] = ['/protected']
        self.stop(['install'], 'Protected disk is mounted')

    def test_invalid_arguments_are_never_copied_into_private_records(self):
        result = self.stop(['install', 'DO_NOT_RECORD_ARGUMENT'], 'Unexpected arguments')
        self.assertEqual(result['command'], ['install'])
        self.assertNotIn('DO_NOT_RECORD_ARGUMENT', json.dumps(result))

    def test_bad_bundle_still_saves_firmware_without_installing(self):
        (self.payload/'at').write_text('changed')
        self.stop(['install'], 'Bundle hash mismatch')

    def test_unavailable_firmware_records_failed_attempt_and_preserves_original_stop(self):
        real = self.host.read
        def read(*command, **kw):
            if command == ('efibootmgr', '-v'):
                self.host.trace.append(dict(command=list(command), stdout='partial raw text', stderr='read failure', returncode=1, mutation=False))
                raise owner.Stop('firmware unavailable')
            return real(*command, **kw)
        self.stack.enter_context(patch.object(self.host, 'read', side_effect=read))
        self.stack.enter_context(patch.object(owner.sys, 'argv', ['at', 'install', 'invalid']))
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(owner.Stop, 'Unexpected arguments'):
            owner.main()
        result = json.loads(next(self.records.glob('*.json')).read_text())
        self.assertFalse(result['firmware']['observed'])
        self.assertEqual(result['firmware']['attempts'][0]['stdout'], 'partial raw text')
        self.assertFalse(self.home.exists())
        self.assertFalse(any(r.get('mutation') for r in self.host.trace))

    def test_refusal_never_follows_diagnostic_symlink(self):
        outside = self.root/'other'; outside.mkdir()
        self.records.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(owner.Stop, 'Unsafe private diagnostic directory'):
            owner.refusal_record(self.host, dict(status='stopped', command=['install']))
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(self.home.exists())

    def test_success_record_write_failure_exports_stopped_never_passed(self):
        home=self.root/'installed';home.mkdir();payload=home/'tools';common.bundle.build(payload)
        store=home/'records';store.mkdir()
        self.stack.enter_context(patch.object(owner,'HOME',home))
        self.stack.enter_context(patch.object(owner,'__file__',str(payload/'owner.py')))
        self.stack.enter_context(patch.object(owner,'private_tree'))
        real_stat=pathlib.Path.stat
        def metadata(path,*a,**kw):
            info=real_stat(path,*a,**kw)
            return SimpleNamespace(st_mode=stat.S_IFDIR|0o700,st_uid=0) if path==home else info
        self.stack.enter_context(patch.object(pathlib.Path,'stat',metadata))
        real_save=owner.Tools.save
        def save(tools,name,value):
            if tools.store==store:raise OSError('success record write failed')
            return real_save(tools,name,value)
        self.stack.enter_context(patch.object(owner.Tools,'save',save))
        self.stack.enter_context(patch.object(owner.Tools,'title',return_value=['handler completed']))
        self.stack.enter_context(patch.object(owner.sys,'argv',['at','title']))
        with contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(OSError,'success record write failed'):
            owner.main()
        result=json.loads(next(self.records.glob('*.json')).read_text())
        self.assertEqual(result['status'],'stopped')
        self.assertEqual(result['error'],'success record write failed')
        self.assertFalse(any(r.get('mutation') for r in self.host.trace))

    def test_last_install_step_failure_has_no_premature_success_record(self):
        self.stack.enter_context(patch.object(owner.sys,'argv',['at','install']))
        self.stack.enter_context(patch.object(pathlib.Path,'symlink_to',side_effect=OSError('short entry failed')))
        with common.private_metadata(self.home),contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(OSError,'short entry failed'):
            owner.main()
        result=json.loads(next(self.records.glob('*.json')).read_text())
        self.assertEqual(result['status'],'stopped')
        self.assertEqual(list((self.home/'records').glob('*-install.json')),[])
        self.assertTrue((self.home/'records/disks.json').is_file())
        self.assertFalse(any(r.get('mutation') for r in self.host.trace))

    def test_stopped_diagnostics_exported_before_harness_rejects_status(self):
        guest = Mock(owner_layout='de')
        raw = self.host.read('efibootmgr', '-v')
        record = dict(status='stopped', command=['install'], trace=[], firmware=dict(stdout=raw, observed=True))
        sources = []
        def capture(name, source):
            syntax(name, source); sources.append(source)
            if '# visible-echo' in source:
                from owner_console_shim import execute_echo
                return execute_echo(source)
            return [] if name == 'owner-record-list' else record
        guest.capture_json = capture
        console = vm.Console(guest); console.prompt = Mock()
        with patch.object(vm.td, 'EVIDENCE', self.root), patch.object(vm, 'type_text'), \
             self.assertRaisesRegex(AssertionError, 'Owner command failed'):
            console.run('install', 'unexpected-stop')
        saved = json.loads((self.root/'unexpected-stop-owner-diagnostics.json').read_text())
        self.assertEqual(saved, record)
        self.assertEqual(len(sources), 2+len(vm.COMMANDS['install'].splitlines()))
        self.assertEqual(sum('# visible-echo' in source for source in sources),len(vm.COMMANDS['install'].splitlines()))
        guest.screenshot.assert_not_called()

    def test_real_framed_reader_decodes_preinstall_stop_and_refuses_unsafe_records(self):
        # Run the exact reader text inside real Bash. Only /run allocation and
        # fixture POSIX metadata are adapted, as in the other framing tests.
        self.records.mkdir()
        path = self.records/'20261027T010203.000001Z-install.json'
        record = dict(status='stopped', command=['install'], firmware=dict(stdout=self.host.read('efibootmgr', '-v')))
        path.write_text(json.dumps(record)); path.chmod(0o600)
        for unsafe in (False, True):
            source = vm.diagnostic_reader([], 'install', (str(self.records),))
            shim = '''import pathlib,stat
from types import SimpleNamespace
original=pathlib.Path.lstat
def metadata(p,*a,**kw):
    value=original(p,*a,**kw)
    if str(p).startswith(@ROOT@):
        return SimpleNamespace(st_mode=(stat.S_IFDIR|0o700) if p.is_dir() else (stat.S_IFREG|0o600),st_uid=@UID@)
    return value
pathlib.Path.lstat=metadata
'''.replace('@ROOT@', repr(str(self.records))).replace('@UID@', '1000' if unsafe else '0')
            composed = vm.sw.framed('python3 -c '+shlex.quote(shim+source))
            syntax('diagnostic-reader-execution', composed)
            # Preserve the framing protocol; replace only its temporary path.
            composed = composed.replace('/run/aresos-json.XXXXXX', str(self.root/'aresos-json.XXXXXX'))
            result = subprocess.run(['bash', '--noprofile', '--norc'], input=composed, text=True, capture_output=True, timeout=15)
            if unsafe:
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('ARESOS_EXPORT_START', result.stdout)
                self.assertIn('Diagnostics are not private', result.stderr)
            else:
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(decode_export(result.stdout)), record)


if __name__ == '__main__': unittest.main()
