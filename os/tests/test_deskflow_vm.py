"""Regressions in the Deskflow output gate without a QEMU boot."""
import contextlib
import errno
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci/deskflow'))
import actions  # noqa: E402
import deskflow_vm as vm  # noqa: E402


PRIMARY = {'enabled': True, 'modes': []}
CUSTOM = {'width': 1022, 'height': 766, 'current': True}


class DeskflowVMTest(unittest.TestCase):
    def test_hotplug_fails_if_drm_moves_without_labwc(self):
        for connected in (True, False):
            for original in (None, {'card1-Virtual-1'}):
                with self.subTest(connected=connected, original=original):
                    guest = Mock()
                    secondary = 'card1-Virtual-2' if original is None else 'card2-Virtual-1'
                    name = 'Virtual-2' if original is None else 'Virtual-3'
                    outputs = {vm.PRIMARY: PRIMARY}
                    if not connected:
                        outputs[name] = PRIMARY
                    guest.request.return_value = dict(outputs=outputs, connectors={
                        'card1-Virtual-1': 'connected', secondary: 'connected' if connected else 'disconnected',
                    })
                    with patch.object(vm.time, 'monotonic', side_effect=(0, 1, 13)), patch.object(vm.time, 'sleep'):
                        with self.assertRaisesRegex(AssertionError, 'labwc did not reflect'):
                            vm.wait_connector(guest, connected, original)

    def test_unverified_hotplug_requires_neither_probe_to_move_drm(self):
        guest = Mock()
        guest.request.return_value = {'connectors': {'card1-Virtual-1': 'connected'}}
        with patch.object(vm, 'wait_connector', side_effect=(None, None)) as wait:
            result = vm.hotplug(guest)
        guest.ui_info.assert_called_once_with(True)
        guest.qmp.command.assert_called_once()
        self.assertEqual(wait.call_count, 2)
        self.assertEqual(result['hotplug'], 'unverified')
        self.assertIn("the owner's direct OK", result['publication_requires'])

    def test_hotplug_fails_if_a_connected_status_node_disappears_but_labwc_keeps_output(self):
        guest = Mock()
        outputs = {vm.PRIMARY: PRIMARY, vm.SECONDARY: PRIMARY}
        primary = {'card1-Virtual-1': 'connected'}
        before = dict(outputs=outputs, connectors={**primary, 'card1-Virtual-2': 'connected'})
        after = dict(outputs=outputs, connectors=primary)
        guest.request.side_effect = (before, before, after)
        with patch.object(vm.time, 'monotonic', side_effect=(0, 1, 13)), patch.object(vm.time, 'sleep'):
            with self.assertRaisesRegex(AssertionError, 'labwc did not reflect'):
                vm.hotplug(guest)
        guest.ui_info.assert_called_once_with(False)
        guest.qmp.command.assert_not_called()

    def test_vt_checks_the_original_bus_owner_and_listener(self):
        for vt in ('tty3', 'tty1'):
            with (
                self.subTest(vt=vt),
                patch.object(actions, 'labwc_pid', return_value=1),
                patch.object(actions, 'session_log', return_value=''),
                patch.object(actions.subprocess, 'run', return_value=Mock(stdout='')),
                patch.object(actions, 'VT', Mock(**{'read_text.return_value': vt})),
            ):
                with (
                    patch.object(actions, 'session', {'uid': 1000, 'pid': 1, 'backend_owner': ':1.2'}),
                    patch.object(actions, 'backend_owner', return_value=':1.3'),
                ):
                    with self.assertRaisesRegex(AssertionError, 'original backend lost its bus name'):
                        actions.vt({'expected': vt})
                with (
                    patch.object(actions, 'session', {'uid': 1000, 'pid': 1}),
                    patch.object(actions, 'listener', Mock(**{'poll.return_value': 2})),
                ):
                    with self.assertRaisesRegex(AssertionError, 'listen-only Wayland connection ended'):
                        actions.vt({'expected': vt})

    def test_drm_control_never_accepts_a_backend_on_wayland(self):
        for state in ('none', 'listener'):
            base = (
                patch.object(actions, 'session', {'uid': 1000, 'pid': 1, 'state': state}),
                patch.object(actions, 'labwc_pid', return_value=1),
                patch.object(actions, 'session_log', return_value=''),
                patch.object(actions, 'listener', None),
                patch.object(actions.subprocess, 'run', return_value=Mock(stdout='')),
            )
            with self.subTest(state=state), contextlib.ExitStack() as stack:
                for context in base:
                    stack.enter_context(context)
                # Activated by the frontend with sharing off: running, and no Wayland connection, is fine.
                for connections in (None, 0):
                    with patch.object(actions, 'backend_connections', return_value=connections):
                        actions.check_compositor()
                with patch.object(actions, 'backend_connections', return_value=1):
                    with self.assertRaisesRegex(AssertionError, 'input portal held a Wayland connection during a DRM control case'):
                        actions.check_compositor()

    def test_the_backend_state_needs_its_worker_until_sharing_goes_off(self):
        session = {'uid': 1000, 'pid': 1, 'state': 'backend', 'backend_owner': ':1.2', 'worker': True}
        with (
            patch.object(actions, 'session', session),
            patch.object(actions, 'labwc_pid', return_value=1),
            patch.object(actions, 'session_log', return_value=''),
            patch.object(actions, 'listener', None),
            patch.object(actions.subprocess, 'run', return_value=Mock(stdout='')),
            patch.object(actions, 'backend_owner', return_value=':1.2'),
        ):
            with patch.object(actions, 'backend_connections', return_value=1):
                actions.check_compositor()
            with patch.object(actions, 'backend_connections', return_value=0):
                with self.assertRaisesRegex(AssertionError, 'Wayland worker stopped during the run'):
                    actions.check_compositor()
                del session['backend_owner']
                session['worker'] = False
                actions.check_compositor()

    def test_only_a_closed_descriptor_can_be_ignored_by_pidfd_getfd(self):
        for error in (errno.EBADF, errno.EPERM, errno.ESRCH, errno.ENOSYS):
            def failed_getfd(*_):
                actions.ctypes.set_errno(error)
                return -1

            with (
                self.subTest(error=error),
                patch.object(actions, 'session', {'runtime': pathlib.Path('/fixture'), 'wayland': 'wayland-1'}),
                patch.object(actions.os, 'pidfd_open', return_value=10),
                patch.object(actions.os, 'listdir', return_value=['7']),
                patch.object(actions.os, 'readlink', return_value='socket:[1]'),
                patch.object(actions.os, 'close') as close,
                patch.object(actions.ctypes, 'CDLL', return_value=Mock(syscall=failed_getfd)),
            ):
                if error == errno.EBADF:
                    self.assertEqual(actions.wayland_connections(42), 0)
                else:
                    with self.assertRaises(OSError) as failed:
                        actions.wayland_connections(42)
                    self.assertEqual(failed.exception.errno, error)
                close.assert_called_once_with(10)

    def test_wayland_connections_are_read_from_the_outside(self):
        import socket
        import os
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / 'wayland-1'
            server = socket.socket(socket.AF_UNIX)
            server.bind(str(path))
            server.listen(2)
            with patch.object(actions, 'session', {'runtime': pathlib.Path(folder), 'wayland': 'wayland-1'}):
                before = actions.wayland_connections(os.getpid())
                client = socket.socket(socket.AF_UNIX)
                client.connect(str(path))
                during = actions.wayland_connections(os.getpid())
                client.close()
                after = actions.wayland_connections(os.getpid())
            server.close()
        self.assertEqual((before, during, after), (0, 1, 0))

    def test_custom_verifies_each_transition(self):
        on = {'outputs': {vm.PRIMARY: {'enabled': True, 'modes': [CUSTOM]}}}
        off = {'outputs': {vm.PRIMARY: {'enabled': False}}}
        diagnostics = {'session_log': ''}
        abort = vm.GuestFailure("head_send_state: Assertion `found' failed")
        for responses, status, completed in (
            (({}, on, {}, off, {}, on), 'passed', 3),
            (({}, {'outputs': {vm.PRIMARY: PRIMARY}}, diagnostics), 'unverified', 1),
            (({}, on, {}, on, diagnostics), 'unverified', 2),
            (({}, on, {}, off, abort, diagnostics), 'compositor-assertion', 3),
        ):
            with self.subTest(status=status, completed=completed):
                guest = Mock()
                guest.request.side_effect = responses
                result = vm.custom(guest, {'outputs': {vm.PRIMARY: PRIMARY}})
                self.assertEqual(result['status'], status)
                operations = ['set-custom-mode', 'disable-output', 'reenable-custom-mode'][:completed]
                self.assertEqual([transition['operation'] for transition in result['transitions']], operations)
                if status != 'passed':
                    self.assertEqual(result['operation'], operations[-1])

    def test_incomplete_custom_evidence_is_reported_separately(self):
        @contextlib.contextmanager
        def boot(_disk, work, _evidence):
            guest = Mock()
            if work.name == 'custom-none':
                guest.request.side_effect = vm.GuestFailure('not ready')
            yield guest

        with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
            disk = pathlib.Path('vm-work/output/disk.raw')
            disk.parent.mkdir(parents=True)
            disk.touch()
            log = io.StringIO()
            with (
                patch.object(vm, 'boot', boot),
                patch.object(vm, 'regular', return_value={'status': 'passed'}) as regular,
                patch.object(vm, 'custom', side_effect=[{'status': 'unverified'}, {'status': 'compositor-assertion'}]) as custom,
                contextlib.redirect_stdout(log),
            ):
                regular.__name__ = 'regular'
                custom.__name__ = 'custom'
                vm.main()
            result = json.loads(pathlib.Path('evidence/deskflow/result.json').read_text())
        self.assertEqual(result['gate'], 'passed')
        self.assertEqual(set(result['custom_incomplete']), {'custom-none', 'custom-listener'})
        self.assertEqual(result['custom_incomplete']['custom-none']['phase'], 'readiness')
        self.assertIn('DESKFLOW_CUSTOM_EVIDENCE_INCOMPLETE', log.getvalue())
