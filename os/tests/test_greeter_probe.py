import pathlib
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from greeter_probe import candidates, greeter_identity, wait_ready


class GreeterProbeTest(unittest.TestCase):
    def test_fixture_matches_the_pinned_image_manager_instead_of_assuming_sddm(self):
        manifest = pathlib.Path(__file__).resolve().parents[1] / 'manifest/ci/06c/image-full-1/packages.txt'
        packages = manifest.read_text().splitlines()
        self.assertIn('plasma-login-manager-6.7.5-1.fc44.x86_64', packages)
        self.assertFalse(any(package.startswith('sddm-') for package in packages))

    def test_proc_observer_reads_real_executable_effective_uid_and_environment(self):
        process = MagicMock()
        process.name = '123'
        nodes = dict(exe=Mock(), status=Mock(), environ=Mock())
        nodes['exe'].readlink.return_value = pathlib.Path('/usr/libexec/plasma-login-greeter')
        nodes['status'].read_text.return_value = 'Name:\tplasma-login-gr\nUid:\t975\t975\t975\t975\n'
        nodes['environ'].read_bytes.return_value = b'XDG_SESSION_TYPE=wayland\0XDG_VTNR=1\0'
        process.__truediv__.side_effect = lambda key: nodes[key]
        proc = Mock()
        proc.glob.return_value = [process]
        self.assertEqual(list(candidates(proc, 975))[0]['pid'], 123)
        nodes['exe'].readlink.side_effect = FileNotFoundError()
        self.assertEqual(list(candidates(proc, 975)), [])

    def test_real_greeter_identity_does_not_depend_on_logind_class_or_argv_spelling(self):
        # The first 06d run displayed a real greeter while its logind observer
        # timed out. Inspect the executable/UID/environment instead of argv or
        # assuming that the logind session metadata matches the compositor.
        for executable in ('plasma-login-greeter', '/usr/bin/plasma-login-greeter', '/usr/libexec/plasma-login-greeter'):
            for kind in ('wayland', 'x11'):
                identity = greeter_identity(executable, 975, 975, dict(XDG_SESSION_TYPE=kind, XDG_VTNR='1'))
                self.assertEqual(identity['vt'], 1)

    def test_wrong_executable_owner_type_or_vt_cannot_become_ready(self):
        environment = dict(XDG_SESSION_TYPE='wayland', XDG_VTNR='1')
        self.assertIsNone(greeter_identity('/usr/bin/kwin_wayland', 975, 975, environment))
        self.assertIsNone(greeter_identity('/usr/bin/sddm-greeter-qt6', 975, 975, environment))
        self.assertIsNone(greeter_identity('/usr/libexec/plasma-login-greeter', 1000, 975, environment))
        for env in ({}, dict(XDG_SESSION_TYPE='tty', XDG_VTNR='1'),
                    dict(XDG_SESSION_TYPE='wayland', XDG_VTNR='0'),
                    dict(XDG_SESSION_TYPE='wayland', XDG_VTNR='not-a-vt')):
            self.assertIsNone(greeter_identity('/usr/libexec/plasma-login-greeter', 975, 975, env))

    def test_process_with_active_graphical_vt_is_accepted_and_records_identity(self):
        identity = dict(pid=123, vt=1, type='wayland', uid=975)
        with patch('greeter_probe.pwd.getpwnam', return_value=Mock(pw_uid=975)), \
             patch('greeter_probe.candidates', return_value=[identity]), \
             patch('greeter_probe.subprocess.run', return_value=Mock(returncode=0)) as run, \
             patch('greeter_probe.pathlib.Path.read_text', return_value='tty1\n'):
            wait_ready()
        self.assertEqual(run.call_args_list[1].args[0], ['chvt', '1'])

    def test_active_service_without_process_or_with_wrong_active_vt_times_out(self):
        for candidates in ([], [dict(vt=1)]):
            with self.subTest(candidates=candidates), \
                 patch('greeter_probe.pwd.getpwnam', return_value=Mock(pw_uid=975)), \
                 patch('greeter_probe.candidates', return_value=candidates), \
                 patch('greeter_probe.subprocess.run', return_value=Mock(returncode=0)), \
                 patch('greeter_probe.pathlib.Path.read_text', return_value='tty3\n'), \
                 patch('greeter_probe.time.monotonic', side_effect=[0, 0, 2]), \
                 patch('greeter_probe.time.sleep'):
                with self.assertRaises(TimeoutError):
                    wait_ready(timeout=1)
