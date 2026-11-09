"""Exercise the real account declaration with installer-owned local state."""
import pathlib
import subprocess
import tempfile
import unittest


class SysusersRebaseTest(unittest.TestCase):
    def test_preserves_recovery_admin_and_creates_locked_daily_admin_idempotently(self):
        # Owner, 2026-11-09: the daily account is an administrator behind its
        # own password. The image sets none, so it stays locked until he does.
        declaration = pathlib.Path(__file__).resolve().parents[1] / 'config/usr/lib/sysusers.d/aresos.conf'
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'etc').mkdir()
            original = 'root:x:0:0:root:/root:/bin/bash\nares-recovery:x:1000:1000:Recovery:/var/home/ares-recovery:/bin/bash\n'
            (root / 'etc/passwd').write_text(original)
            (root / 'etc/group').write_text('root:x:0:\nwheel:x:10:ares-recovery\nares-recovery:x:1000:\n')
            (root / 'etc/shadow').write_text('root:!:::::::\nares-recovery:!:::::::\n')
            (root / 'etc/gshadow').write_text('root:::\nwheel:::ares-recovery\nares-recovery:!::\n')
            command = ['sudo', '-n', 'systemd-sysusers', '--root=' + directory, str(declaration)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            first = (root / 'etc/passwd').read_text()
            self.assertIn(original.splitlines()[1], first)
            ares = next(line.split(':') for line in first.splitlines() if line.startswith('ares:'))
            self.assertEqual(ares[2:4], ['1001', '1001'])
            self.assertEqual(ares[5:], ['/var/home/ares', '/bin/bash'])
            groups = (root / 'etc/group').read_text()
            wheel = next(line.split(':') for line in groups.splitlines() if line.startswith('wheel:'))
            self.assertEqual(wheel[2], '10')
            self.assertEqual(wheel[3].split(','), ['ares-recovery', 'ares'])
            self.assertIn('ares:x:1001:', groups.splitlines())
            gshadow = subprocess.check_output(['sudo', '-n', 'cat', str(root / 'etc/gshadow')], text=True)
            wheel_shadow = next(line.split(':') for line in gshadow.splitlines() if line.startswith('wheel:'))
            self.assertEqual(wheel_shadow[3].split(','), ['ares-recovery', 'ares'])
            shadow = subprocess.check_output(['sudo', '-n', 'cat', str(root / 'etc/shadow')], text=True)
            password = next(line.split(':')[1] for line in shadow.splitlines() if line.startswith('ares:'))
            self.assertTrue(password.startswith(('!', '*')))
            subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertEqual((root / 'etc/passwd').read_text(), first)
            self.assertEqual((root / 'etc/group').read_text(), groups)

    def test_existing_daily_account_joins_wheel_on_upgrade_without_other_changes(self):
        # A laptop that already ran an earlier image has ares outside wheel and
        # may have a password set by then; boot-time sysusers adds only wheel.
        declaration = pathlib.Path(__file__).resolve().parents[1] / 'config/usr/lib/sysusers.d/aresos.conf'
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'etc').mkdir()
            passwd = ('root:x:0:0:root:/root:/bin/bash\n'
                      'ares-recovery:x:1000:1000:Recovery:/var/home/ares-recovery:/bin/bash\n'
                      'ares:x:1001:1001:AresOS daily session:/var/home/ares:/bin/bash\n')
            shadow = 'root:!:::::::\nares-recovery:!:::::::\nares:$6$FIXTURE$NOT-A-REAL-HASH:20000:0:99999:7:::\n'
            (root / 'etc/passwd').write_text(passwd)
            (root / 'etc/shadow').write_text(shadow)
            (root / 'etc/group').write_text('root:x:0:\nwheel:x:10:ares-recovery\nares-recovery:x:1000:\nares:x:1001:\n')
            (root / 'etc/gshadow').write_text('root:::\nwheel:::ares-recovery\nares-recovery:!::\nares:!::\n')
            command = ['sudo', '-n', 'systemd-sysusers', '--root=' + directory, str(declaration)]
            subprocess.run(command, check=True, capture_output=True, text=True)
            self.assertEqual((root / 'etc/passwd').read_text(), passwd)
            self.assertEqual(subprocess.check_output(['sudo', '-n', 'cat', str(root / 'etc/shadow')], text=True), shadow)
            self.assertIn('wheel:x:10:ares-recovery,ares', (root / 'etc/group').read_text().splitlines())
