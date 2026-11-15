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
            '[Unit]', 'Description=AresOS tool service', 'After=local-fs.target', '',
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
