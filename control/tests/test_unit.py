"""Pin the complete service configuration; the approved IP change is narrow."""
from pathlib import Path
import unittest


class InstalledUnit(unittest.TestCase):
    def test_service_sandbox_and_launch_are_exact(self):
        unit = Path(__file__).resolve().parents[1] / 'packaging/aresos-toold.service'
        service = unit.read_text().split('[Service]\n', 1)[1].split('\n[Install]', 1)[0]
        lines = [line for line in service.splitlines() if line and not line.startswith('#')]
        self.assertEqual(lines, [
            'Type=simple', 'User=aresos-tools', 'Group=aresos-tools',
            'ExecStart=/usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 /usr/bin/python3 -I -S /usr/libexec/aresos-control/launch.py service',
            'UMask=0077', 'Restart=on-failure', 'RestartSec=2',
            'NoNewPrivileges=yes', 'ProtectSystem=strict', 'ProtectHome=yes',
            'PrivateTmp=yes', 'PrivateDevices=yes',
            'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6',
            'CapabilityBoundingSet=',
            'ReadWritePaths=/run/aresos-tools /var/lib/aresos-tools /var/lib/aresos-operation-evidence',
        ])
