"""Pin the complete service configuration; the approved IP change is narrow."""
from pathlib import Path
import unittest


class InstalledUnit(unittest.TestCase):
    def test_service_sandbox_and_launch_are_exact(self):
        # The whole file, comments and blank lines included: linux-tools pins
        # it byte for byte from 8b7e799c.
        unit = Path(__file__).resolve().parents[1] / 'packaging/aresos-toold.service'
        self.assertEqual(unit.read_text().split('\n'), [
            '# DRAFT: install only after owner configuration and brief 18b image qualification.',
            '[Unit]', 'Description=AresOS tool service', 'After=local-fs.target',
            '# A service that fails at every start ends failed within about 15 s (RestartSec=2); one crash still restarts.',
            'StartLimitIntervalSec=30', 'StartLimitBurst=5', '',
            '[Service]',
            'Type=simple', 'User=aresos-tools', 'Group=aresos-tools',
            'ExecStart=/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I -S /usr/libexec/aresos-control/launch.py service',
            'UMask=0077', 'Restart=on-failure', 'RestartSec=2',
            'NoNewPrivileges=yes', 'ProtectSystem=strict', 'ProtectHome=yes',
            'PrivateTmp=yes', 'PrivateDevices=yes',
            '# Mail IMAP/SMTP and the daily qualification record fetch need IP networking.',
            'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6',
            'CapabilityBoundingSet=',
            'ReadWritePaths=/run/aresos-tools /var/lib/aresos-tools /var/lib/aresos-operation-evidence',
            '',
            '[Install]', 'WantedBy=multi-user.target', '',
        ])

    def test_start_limit_ends_a_failing_service_within_about_15_seconds(self):
        # Brief 18e, item 4 (18c step 2b: 41 restarts in 90 s, never failed). systemd refuses the start that exceeds
        # StartLimitBurst within StartLimitIntervalSec; with RestartSec=2 the sixth start comes after about 10 to
        # 15 s, so the burst must fit in the interval, while one crash of a running service still restarts.
        lines = (Path(__file__).resolve().parents[1] / 'packaging/aresos-toold.service').read_text().split('\n')
        unit = lines[lines.index('[Unit]'):lines.index('[Service]')]
        service = lines[lines.index('[Service]'):lines.index('[Install]')]
        value = lambda section, key: next(line.split('=', 1)[1] for line in section if line.startswith(key + '='))
        interval, burst, delay = int(value(unit, 'StartLimitIntervalSec')), int(value(unit, 'StartLimitBurst')), int(value(service, 'RestartSec'))
        self.assertEqual(value(service, 'Restart'), 'on-failure')
        self.assertGreaterEqual(burst, 2)
        # Starts that fail at once: the refused start comes after `burst` restart delays.
        self.assertLessEqual(burst * delay, 15)
        self.assertGreater(interval, burst * (delay + 1))
