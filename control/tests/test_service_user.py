"""Pin the service user's fixed numbers (package 18c, agreed with linux-aresos on 2026-11-13, change 5).

/etc is per deployment while /var is shared: a user created anew with a dynamic number after a rollback and an
update could stop owning the state folders, or another system user could get the old number and read the stored
passwords. So the sysusers line fixes one number for the user and its group. 250 is above Fedora's static block
(0 to 200, /usr/share/doc/setup/uidgid) and far below the dynamic system range's frontier (allocated from 999
downward). The image tests check it against the image's own account files (os/tests/test_control_image.py).
"""
from pathlib import Path
import unittest

PACKAGING = Path(__file__).resolve().parents[1] / 'packaging'


class ServiceUser(unittest.TestCase):
    def test_the_service_user_has_one_fixed_number_and_no_login(self):
        lines = [line for line in (PACKAGING / 'aresos-tools.sysusers').read_text().splitlines()
                 if line and not line.startswith('#')]
        # No uid:gid form: sysusers then makes the group with the same number, or the build's image check fails.
        self.assertEqual(lines, ['u aresos-tools 250 "AresOS tool service" /var/lib/aresos-tools /usr/sbin/nologin'])

    def test_the_unit_and_state_folders_name_that_user(self):
        unit = (PACKAGING / 'aresos-toold.service').read_text().splitlines()
        self.assertIn('User=aresos-tools', unit)
        self.assertIn('Group=aresos-tools', unit)
        folders = [line.split() for line in (PACKAGING / 'aresos-tools.tmpfiles').read_text().splitlines()
                   if line and not line.startswith('#')]
        self.assertEqual({tuple(fields[3:5]) for fields in folders}, {('aresos-tools', 'aresos-tools')})


if __name__ == '__main__':
    unittest.main()
