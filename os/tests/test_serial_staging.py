"""Real local Bash/PTY execution with limited/dropped UART-like input."""
import base64
import hashlib
import json
import os
import pathlib
import re
import shlex
import socket
import sys
import time
import unittest
import contextlib
from unittest.mock import patch

from serial_pty import Fixture, ROOT
import switch_vm as sw
import serial_transport as transport
from serial_console import encode_command, decode_export
from guest_shell import syntax
import owner_vm as vm
import owner_console

FIXTURE = ROOT/'os/tests/fixtures/owner-console/14za-login-command.json'


class StagingTest(unittest.TestCase):
    def setUp(self):self.retained=json.loads(FIXTURE.read_text())

    def passed_record(self,f):
        p=f.records/'20990101T000000.000000Z-login.json'
        p.write_text(json.dumps(dict(status='passed',command=['login'],trace=[]))+'\n')

    def test_exact_retained_bytes_parse_and_execute_with_no_quote_or_heredoc_defect(self):
        source=self.retained['script'];wire=encode_command(source)
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),self.retained['sha256'])
        self.assertEqual((len(source.encode()),len(wire.encode())),(2652,3633))
        self.assertEqual(max(map(len,wire.splitlines())),1024)
        syntax('exact-qualification4-login-reader',source)
        with Fixture(self.retained['before']) as f:
            self.passed_record(f)
            f.guest.send(wire)
            output=f.guest.wait(r'\r?\nARESOS_CMD_DONE:(\d+)\r?\n',timeout=5)
            self.assertEqual(json.loads(decode_export(output)),dict(status='passed',command=['login'],trace=[]))

    def test_lost_heredoc_terminator_reproduces_continuation_prompts_and_is_bounded(self):
        with Fixture(self.retained['before']) as f:
            self.passed_record(f)
            wire=encode_command(self.retained['script']).removesuffix('ARESOS_SCRIPT\n')
            start=time.monotonic();f.guest.send(wire)
            with self.assertRaises(TimeoutError):f.guest.wait(r'\r?\nARESOS_CMD_DONE:(\d+)\r?\n',timeout=.3)
            self.assertLess(time.monotonic()-start,2)
            self.assertIn('> ',f.guest.transcript)
            self.assertNotIn('ARESOS_EXPORT_START',f.guest.transcript)

    def test_complete_old_heredoc_also_has_continuation_prompts_while_reader_waits(self):
        with Fixture(self.retained['before']) as f:
            # Instrument the filesystem adapter, not a byte of the retained
            # script. This proves the reader started despite the PS2 output.
            adapter=f.root/'python-adapter.py'
            adapter.write_text(adapter.read_text().replace("exec(compile(source,", "(root/'reader-started').write_text('started')\nexec(compile(source,"))
            f.guest.send(encode_command(self.retained['script']))
            with self.assertRaises(TimeoutError):f.guest.wait(r'\r?\nARESOS_CMD_DONE:(\d+)\r?\n',timeout=.5)
            self.assertTrue((f.root/'reader-started').exists())
            self.assertIn('> ',f.guest.transcript)
            self.assertNotIn('ARESOS_EXPORT_START',f.guest.transcript)

    def test_burst_limited_line_drops_old_transfer_but_acknowledged_staging_completes(self):
        with Fixture(self.retained['before']) as f:
            self.passed_record(f);f.serial.limit=512
            f.guest.send(encode_command(self.retained['script']))
            with self.assertRaises(TimeoutError):f.guest.wait(r'\r?\nARESOS_CMD_DONE:(\d+)\r?\n',timeout=.3)
        with Fixture(self.retained['before']) as f:
            self.passed_record(f);f.serial.limit=512
            result=f.guest.capture_json('exact-login-result',self.retained['script'])
            self.assertEqual(result['status'],'passed')
            self.assertTrue(all(len(p)<=512 for p in f.serial.sent))
            self.assertEqual(list(f.stage.iterdir()),[])
            evidence=json.loads((f.evidence/'exact-login-result-transport.json').read_text())
            self.assertTrue(evidence['verified']);self.assertEqual(evidence['bytes'],2652)

    def test_dropped_control_newline_stops_without_a_second_write(self):
        with Fixture() as f:
            f.serial.fault=lambda data:data.removesuffix(b'\n')
            with self.assertRaises(TimeoutError):f.guest.command('drop','#'+'x'*300+'\nprintf UNREACHED',timeout=2)
            self.assertEqual(len(f.serial.sent),1)
            self.assertNotIn('UNREACHED',f.guest.transcript)
            with self.assertRaisesRegex(AssertionError,'idle authority'):f.guest.resync_after_hidden('busy')
            self.assertEqual(len(f.serial.sent),1)

    def test_missing_chunk_stops_without_retry_or_execution(self):
        with Fixture() as f:
            seen=[]
            def drop(data):
                if b'base64 -d >>' in data:seen.append(data);return b''
                return data
            f.serial.fault=drop
            with self.assertRaises(TimeoutError):f.guest.command('missing','#'+'x'*300+'\nprintf UNREACHED',timeout=2)
            self.assertEqual(len(seen),1)
            self.assertFalse(any(b'bash "$_ares_stage/script" </dev/null' in p for p in f.serial.sent))

    def test_sha_mismatch_refuses_before_run_and_cleans_owned_tmpfs_files(self):
        with Fixture() as f:
            changed=[]
            def corrupt(data):
                match=re.search(rb'printf %s ([A-Za-z0-9+/=]+)',data)
                if match and not changed:
                    raw=match[1];data=data[:match.start(1)]+(b'A' if raw[:1]!=b'A' else b'B')+raw[1:]+data[match.end(1):];changed.append(True)
                return data
            f.serial.fault=corrupt
            with self.assertRaisesRegex(AssertionError,'integrity refused'):f.guest.command('corrupt','#'+'x'*300+'\nprintf UNREACHED',timeout=2)
            self.assertTrue(changed);self.assertEqual(list(f.stage.iterdir()),[])
            self.assertFalse(any(b'bash "$_ares_stage/script" </dev/null' in p for p in f.serial.sent))

    def test_syntax_warning_refuses_without_execution_and_nothing_is_left(self):
        with Fixture() as f:
            body='#'+'x'*300+"\ncat <<'END'\nnever closed\n"
            with self.assertRaisesRegex(AssertionError,'syntax refused'):f.guest.command('warning',body,timeout=2)
            self.assertEqual(list(f.stage.iterdir()),[])
            self.assertFalse(any(b'bash "$_ares_stage/script" </dev/null' in p for p in f.serial.sent))

    def test_large_staged_result_keeps_checksum_frame_and_nonzero_status(self):
        with Fixture() as f:
            body=sw.framed("#"+'x'*500+"\nprintf '%s\\n' '{\"value\":3}'")
            self.assertEqual(f.guest.capture_json('framed',body),dict(value=3))
            with self.assertRaisesRegex(AssertionError,'exit 7'):f.guest.command('failed','#'+'x'*300+'\nexit 7',timeout=2)
            self.assertEqual(list(f.stage.iterdir()),[])

    def test_secret_script_is_refused_before_evidence_or_serial_or_staging(self):
        with Fixture() as f:
            sentinel='synthetic-hidden-input';f.guest.secrets=[sentinel]
            before=list(f.evidence.iterdir())
            with self.assertRaisesRegex(AssertionError,'Secret-bearing serial'):f.guest.command('secret','printf '+sentinel,private=True)
            self.assertEqual(f.serial.sent,[]);self.assertEqual(list(f.stage.iterdir()),[])
            self.assertEqual(list(f.evidence.iterdir()),before)
            with self.assertRaisesRegex(AssertionError,'authentication is disabled'):f.guest.prepare_registry_auth(sentinel)

    def test_nul_refuses_before_any_allocation_or_evidence(self):
        with Fixture() as f:
            before=list(f.evidence.iterdir())
            with self.assertRaisesRegex(AssertionError,'NUL'):f.guest.command('nul','#'+'x'*300+'\0')
            self.assertEqual(f.serial.sent,[]);self.assertEqual(list(f.stage.iterdir()),[])
            self.assertEqual(list(f.evidence.iterdir()),before)

    def test_root_tmpfs_and_private_metadata_refusals_never_execute_script(self):
        for tool,body,phase in (
            ('id',"printf '1000\\n'\n",'root'),
            ('findmnt',"printf 'ext4\\n'\n",'root'),
            ('stat',"printf '0:777\\n'\n",'integrity')):
            with self.subTest(tool=tool),Fixture() as f:
                f.shim(tool,body)
                with self.assertRaisesRegex(AssertionError,phase+' refused'):
                    f.guest.command('unsafe','#'+'x'*300+'\nprintf UNREACHED',timeout=2)
                self.assertEqual(list(f.stage.iterdir()),[])
                self.assertFalse(any(b'bash "$_ares_stage/script" </dev/null' in p for p in f.serial.sent))

    def test_all_staging_control_lines_and_run_group_have_strict_bash_syntax(self):
        for length in (257,2652,25000):
            steps,run=transport.plan('#'+'x'*length+'\nprintf DONE','0123456789abcdef')
            self.assertTrue(all(len(line.encode())<=512 for _,line in steps))
            syntax('staged-source-'+str(length),'#'+'x'*length+'\nprintf DONE')

    def test_result_deadlines_have_return_grace_and_do_not_poll_for_1800_seconds(self):
        self.assertLess(vm.OWNER_RESULT_WAIT,vm.OWNER_COMMAND_TIMEOUT)
        self.assertEqual((vm.OWNER_RESULT_WAIT,vm.OWNER_COMMAND_TIMEOUT),(840,900))
        self.assertIn('time.monotonic()+840',vm.diagnostic_reader([], 'login'))
        self.assertNotIn('+1800',vm.diagnostic_reader([], 'login'))
        with Fixture() as f:
            source=sw.framed('python3 -c '+shlex.quote(vm.diagnostic_reader([], 'login',timeout=.1)))
            with self.assertRaisesRegex(AssertionError,'exit 1'):f.guest.command('no-record',source,timeout=3)

    def test_later_stage_real_retained_outputs_roundtrip_without_heredoc_loss(self):
        # These are real prior observations, not fabricated owner PASS records.
        # Functional parser checks live in test_owner_retained; this check
        # exercises the byte transport/checksum for the same later-stage values.
        rows=json.loads((ROOT/'os/tests/fixtures/owner-tools/retained-parsers.json').read_text())
        values={r['kind']:r['value'] for r in rows}
        verify=ROOT/'os/manifest/ci/11n/probe-1/two-disk/live-release-signature-proof.json'
        cases=[('verify-package11',json.loads(verify.read_text()))]
        for stage in ('after-switch-staged','aresos','aresos-us','aresos-back-de','after-rollback-queued','rollback'):
            cases.append((stage,{k:values[stage+' '+k] for k in ('rpm-ostree-status','bootc-status','resolved-bls')}))
        cases.append(('layout-real-maps',{stage:values[stage+' keyboard'] for stage in ('aresos','aresos-us','aresos-back-de','rollback')}))
        # Package13's retained rollback is the stable stock pair which the
        # keep-stock preflight consumes; package14 keep-stock has never run.
        cases.append(('keep-stock-input',json.loads((ROOT/'os/tests/fixtures/owner-tools/rollback-deployments.json').read_text())))
        with Fixture() as f:
            f.serial.limit=512
            for stage,value in cases:
                raw=json.dumps(value,ensure_ascii=False)
                retained=f.root/(stage+'.json');retained.write_text(raw)
                # Like the real readers, transfer code to read the result;
                # the (potentially much larger) JSON travels guest-to-host.
                source=sw.framed('cat '+shlex.quote(str(retained)))
                syntax(stage,source)
                self.assertEqual(f.guest.capture_json('retained-'+stage,source),value)
            self.assertEqual(list(f.stage.iterdir()),[])

    def physical_tool(self,f):
        helper=f.root/'mock-login.py'
        helper.write_text('''import getpass,json,os,pathlib
username=input('GitHub username: ')
value=getpass.getpass('Read-only token (hidden): ')
assert username and value
del value
p=pathlib.Path(os.environ['SERIAL_FIXTURE_ROOT'])/'records/20990101T000000.000000Z-login.json'
p.write_text(json.dumps(dict(status='passed',command=['login'],trace=[]))+'\\n')
p.chmod(0o600)
print('PASS login')
''')
        return helper

    def test_hidden_read_on_physical_pty_cannot_consume_the_serial_command(self):
        with Fixture(self.retained['before']) as f:
            helper=self.physical_tool(f)
            f.physical.sendall(('python3 '+shlex.quote(str(helper))+'\n').encode())
            f.physical.until(b'GitHub username:',3)
            f.physical.sendall(b'fixture-user\n');f.physical.until(b'Read-only token (hidden):',3)
            # Actual getpass is blocked, with its real tty ECHO off. A framed
            # command on the separate controlling PTY still completes.
            fd=os.open(f.physical.slave_name,os.O_RDONLY|os.O_NOCTTY)
            try:self.assertFalse(__import__('termios').tcgetattr(fd)[3]&__import__('termios').ECHO)
            finally:os.close(fd)
            result=f.guest.capture_json('while-hidden',sw.framed("printf '%s\\n' '{\"separate_tty\":true}'"))
            self.assertTrue(result['separate_tty'])
            sentinel=b'synthetic-hidden-input';f.physical.sendall(sentinel+b'\n');f.physical.until(b'PASS login',3)
            self.assertNotIn(sentinel,bytes(f.physical.output))

    def test_real_foreground_observer_distinguishes_idle_readline_from_hidden_reader(self):
        with Fixture() as f:
            fd=os.open(f.physical.slave_name,os.O_RDONLY|os.O_NOCTTY)
            try:
                # Readline on this real idle Bash has ECHO off too.
                self.assertFalse(__import__('termios').tcgetattr(fd)[3]&__import__('termios').ECHO)
                self.assertTrue(owner_console.foreground_is_shell(fd))
                f.physical.sendall(('python3 '+shlex.quote(str(self.physical_tool(f)))+'\n').encode())
                f.physical.until(b'GitHub username:',3)
                f.physical.sendall(b'fixture-user\n');f.physical.until(b'Read-only token (hidden):',3)
                self.assertFalse(__import__('termios').tcgetattr(fd)[3]&__import__('termios').ECHO)
                self.assertFalse(owner_console.foreground_is_shell(fd))
            finally:os.close(fd)
        for args in ([b'bash',b'-c',b'read'],[b'bash',b'/tmp/script'],[b'python3'],[]):
            self.assertFalse(owner_console.interactive_shell(args))

    def test_exact_login_driver_sequence_on_limited_line_drains_and_resyncs_without_secret_staging(self):
        self.login_sequence()

    def test_exact_login_driver_sequence_stops_on_lost_result_chunk_without_retry(self):
        self.login_sequence(lose_result=True)

    def login_sequence(self,lose_result=False):
        with Fixture(self.retained['before']) as f:
            helper=self.physical_tool(f);f.serial.limit=512
            sentinel='synthetic-hidden-input';f.guest.secrets=[sentinel]
            capture=f.guest.capture_json;command=f.guest.command
            dropped=[]
            def bounded(name,script,timeout=900,private=False):
                if lose_result and name.endswith('-owner-result'):
                    def drop(data):
                        if b'base64 -d >>' in data:dropped.append(True);return b''
                        return data
                    f.serial.fault=drop
                return command(name,script,min(timeout,5),private)
            f.guest.command=bounded
            def snapshot(name,source):
                # Wait receipts now have unique sequence/sample suffixes. The
                # physical PTY still waits for the same public owner prompt.
                phase=name.split('-read-wait-',1)[0].split('-wait-',1)[0]
                if phase.endswith('-input-ready'):
                    f.physical.until(b'GitHub username:',3)
                if phase.endswith('-hidden-input') and '# hidden-phase: ready' in source:
                    f.physical.until(b'Read-only token (hidden):',3)
                f.physical.settimeout(.02)
                while True:
                    try:f.physical.recv(65536)
                    except socket.timeout:break
                text=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',bytes(f.physical.output)).decode(errors='replace')
                self.assertNotIn(sentinel,text)
                lines=text.replace('\r','').split('\n')[-24:]
                # The foreground-shell observer can finish just before bash
                # prints PS1. Wait for that public prompt before snapshotting.
                if phase.endswith('-after-hidden-ready') and not lines[-1].rstrip().endswith('#'):
                    f.physical.until(b'root@bazzite:~# ',3)
                    text=bytes(f.physical.output).decode(errors='replace');lines=text.replace('\r','').split('\n')[-24:]
                if not lines[-1] and phase.endswith('-ready') and len(f.physical.sent)==0:
                    f.physical.until(b'root@bazzite:~# ',3)
                    text=bytes(f.physical.output).decode(errors='replace');lines=text.replace('\r','').split('\n')[-24:]
                cols=160;rows=24;lines=(['']*(rows-len(lines))+lines)[-rows:]
                raw=bytes([rows,cols,min(len(lines[-1]),cols-1),rows-1])+b''.join(bytes([c,7]) for line in lines for c in line.encode(errors='replace')[:cols].ljust(cols))
                (f.root/'vcsa3').write_bytes(raw)
                return capture(name,source)
            f.guest.capture_json=snapshot
            def physical(guest,text,layout=None,counts=None):
                guest.owner_input_epoch+=1
                if counts is not None:
                    for char in text:
                        keys=vm.physical_keys(char,layout or guest.owner_layout)
                        counts['key_event_count']+=2*len(keys)
                        counts['key_chord_count']+=1
                        counts['last_key_was_ret']=keys==['ret']
                if text==vm.COMMANDS['login']+'\n':text='python3 -I -B '+shlex.quote(str(helper))+' login\n'
                f.physical.sendall(text.encode())
            with patch.object(vm,'type_text',side_effect=physical),patch.object(vm.td,'EVIDENCE',f.evidence):
                console=vm.Console(f.guest)
                if lose_result:
                    start=time.monotonic()
                    with self.assertRaises(TimeoutError):console.run('login','exact-login',inputs=(('GitHub username:','fixture-user',False),(vm.TOKEN_PROMPT,sentinel,True)))
                    self.assertLess(time.monotonic()-start,30)
                    self.assertEqual(len(dropped),1)
                    self.assertFalse((f.evidence/'exact-login-owner-diagnostics.json').exists())
                else:
                    result=console.run('login','exact-login',inputs=(('GitHub username:','fixture-user',False),(vm.TOKEN_PROMPT,sentinel,True)))
                    self.assertEqual(result['status'],'passed')
                    self.assertEqual(list(f.stage.iterdir()),[])
            self.assertTrue(json.loads((f.evidence/'exact-login-serial-resync.json').read_text())['serial_input_flushed'])
            self.assertTrue(json.loads((f.evidence/'exact-login-hidden-completed.json').read_text())['foreground_shell'])
            self.assertNotIn(sentinel.encode(),b''.join(f.serial.sent))
            for path in f.evidence.iterdir():self.assertNotIn(sentinel.encode(),path.read_bytes())


if __name__=='__main__':unittest.main()
