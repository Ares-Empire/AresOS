"""Exercise the real account declaration with installer-owned local state."""
import pathlib
import subprocess
import tempfile
import unittest


class SysusersRebaseTest(unittest.TestCase):
    def test_preserves_recovery_admin_and_creates_locked_daily_user_idempotently(self):
        declaration = pathlib.Path(__file__).resolve().parents[1] / 'config/usr/lib/sysusers.d/aresos.conf'
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'etc').mkdir()
            original = 'root:x:0:0:root:/root:/bin/bash\nares-recovery:x:1000:1000:Recovery:/var/home/ares-recovery:/bin/bash\n'
            (root / 'etc/passwd').write_text(original)
            (root / 'etc/group').write_text('root:x:0:\nwheel:x:10:ares-recovery\nares-recovery:x:1000:\n')
            (root / 'etc/shadow').write_text('root:!:::::::\nares-recovery:!:::::::\n')
            command = ['sudo', '-n', 'systemd-sysusers', '--root=' + directory, str(declaration)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            first = (root / 'etc/passwd').read_text()
            self.assertIn(original.splitlines()[1], first)
            ares = next(line.split(':') for line in first.splitlines() if line.startswith('ares:'))
            self.assertEqual(ares[2:4], ['1001', '1001'])
            self.assertEqual(ares[5:], ['/var/home/ares', '/bin/bash'])
            self.assertIn('wheel:x:10:ares-recovery', (root / 'etc/group').read_text())
            shadow = subprocess.check_output(['sudo', '-n', 'cat', str(root / 'etc/shadow')], text=True)
            password = next(line.split(':')[1] for line in shadow.splitlines() if line.startswith('ares:'))
            self.assertTrue(password.startswith(('!', '*')))
            subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertEqual((root / 'etc/passwd').read_text(), first)
