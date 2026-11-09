import unittest
from unittest.mock import patch

from aresos_control.chrome.exclusions import owner_hosts
from aresos_control.chrome.policy import allowed_url, FIXED_HOSTS
from aresos_control.common import Refused


class Exclusions(unittest.TestCase):
    def test_owner_entries_are_protected_runtime_setting_and_empty_is_allowed(self):
        with patch('aresos_control.chrome.exclusions.Boundary.read', return_value={'format':1,'hosts':[]}) as read:
            self.assertEqual(owner_hosts(), [])
            self.assertEqual(read.call_args.args[1], '/etc/aresos/control/chrome-excluded-sites.json')
        with patch('aresos_control.chrome.exclusions.Boundary.read', return_value={'format':1,'hosts':['approval.test']}):
            for address in ['https://approval.test/', 'http://sub.approval.test/']:
                with self.assertRaises(Refused):
                    allowed_url(address, owner_hosts())
            self.assertEqual(allowed_url('https://other.test/', owner_hosts()), 'https://other.test/')
        self.assertEqual(FIXED_HOSTS, ['claude.ai','console.anthropic.com','platform.claude.com'])

    def test_missing_unreadable_and_unsafe_settings_refuse_plainly(self):
        for message in ['missing','unreadable','must be owned by root','must not be group- or world-writable','symlink']:
            with self.subTest(message=message), patch('aresos_control.chrome.exclusions.Boundary.read', side_effect=Refused('boundary_not_installed',message)):
                with self.assertRaises(Refused) as error: owner_hosts()
                self.assertEqual(error.exception.code, 'chrome_settings_unavailable')
                self.assertIn('refuses reads and actions', str(error.exception))

    def test_malformed_settings_fail_closed(self):
        for value in [{}, {'format':1,'hosts':'approval.test'}, {'format':1,'hosts':['https://approval.test']}, {'format':1,'hosts':['*.approval.test']}, {'format':1,'hosts':['UPPER.test']}, {'format':1,'hosts':['a..test']}]:
            with self.subTest(value=value), patch('aresos_control.chrome.exclusions.Boundary.read', return_value=value):
                with self.assertRaises(Refused): owner_hosts()
