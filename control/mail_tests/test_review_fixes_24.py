"""Review 16: filing facts and background causes survive failed storage."""
import errno
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
import test_review_fixes_23 as round23


class Filing24(unittest.TestCase):
    setUp = round23.Results23.setUp
    call = round23.Results23.call
    data = round23.Results23.data
    compose = round23.Results23.compose
    approval = round23.Results23.approval
    restart = round23.Results23.restart

    def test_review24_move_and_copy_keep_exact_destination_role_and_deferred_warning(self):
        for verb in ('move', 'copy'):
            with self.subTest(verb=verb):
                ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
                       'uid': 2 if verb == 'copy' else 1, 'message_id': self.imap.mid}
                self.imap.roles['Trash'] = ['\\Trash']
                self.imap.roles['Target'] = []
                write = self.engine.store.write
                def fail(changes, *args, **kwargs):
                    if self.imap.mutations:
                        raise OSError(errno.ENOSPC, 'Synthetic full disk after COPYUID')
                    return write(changes, *args, **kwargs)
                self.imap.mutations.clear()
                with patch.object(self.engine.store, 'write', side_effect=fail):
                    result = self.call(verb, {'references': [ref], 'target': 'Target'})
                    self.assertFalse(result['ok'], result)
                    self.assertIn('Disk full', result['error']['message'])
                    evidence = next(iter(result['observations']['evidence'].values()))
                    dest = {**ref, 'folder': 'Target', 'uidvalidity': self.imap.validities['Target'],
                            'uid': max(self.imap.boxes['Target'])}
                    self.assertEqual(evidence['records'][0]['destination'], dest)
                    self.assertEqual(evidence['observed_role'], 'Trash')
                    self.assertIn('which is now Trash', evidence['reason'])
                    self.assertIn(dest, evidence['locations'][0]['observed_locations'])
                    for action in ('accounts',):
                        next_result = self.call(action, {})
                        self.assertIn('which is now Trash', next_result['pending']['notices'][0]['untrusted_content']['reason'])
                    log = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_log', 'arguments': {}})
                    self.assertIn('which is now Trash', log['data']['notices'][0]['untrusted_content']['reason'])
                self.data('accounts', {})
                self.assertFalse(self.engine.store.deferred_notices)
                stored = self.engine.store.items('notice:')
                self.assertTrue(any('which is now Trash' in n['untrusted_content']['reason'] for _, n in stored))
                self.assertEqual(self.imap.mutations, [(verb.upper(), ref['uid'], 'Target')])

    def test_review24_rename_keeps_observation_and_notice_before_write(self):
        def rename(source, target):
            self.imap.boxes['Renamed'] = self.imap.boxes.pop('Source')
            self.imap.roles['Renamed'] = ['\\Trash']
            self.imap.roles.pop('Source')
            self.imap.roles['Trash'] = []
            self.imap.validities['Renamed'] = self.imap.validities.pop('Source')
            return 'OK', [b'Renamed']
        write = self.engine.store.write
        def fail(changes, *args, **kwargs):
            if 'Renamed' in self.imap.boxes:
                raise OSError(errno.ENOSPC, 'Synthetic full disk after rename')
            return write(changes, *args, **kwargs)
        with patch.object(self.imap, 'rename', side_effect=rename, create=True), \
             patch.object(self.engine.store, 'write', side_effect=fail):
            result = self.call('folder_rename', {'account': 'box', 'folder': 'Source', 'name': 'Renamed'})
            self.assertFalse(result['ok'], result)
            self.assertIn('Disk full', result['error']['message'])
            evidence = next(iter(result['observations']['evidence'].values()))
            self.assertEqual(evidence['rename']['target'], 'Renamed')
            self.assertIn('Trash', evidence['rename']['observed_role'])
            self.assertIn('special folders changed', result['pending']['notices'][0]['untrusted_content']['reason'])
        self.data('accounts', {})
        self.assertFalse(self.engine.store.deferred_notices)

    def test_review24_journal_full_after_move_keeps_warning_in_mail_and_log_while_latched(self):
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
               'uid': 1, 'message_id': self.imap.mid}
        write = self.engine.store.journal.write
        def fail(data):
            if self.imap.mutations:
                raise OSError(errno.ENOSPC, 'Synthetic full disk after MOVE')
            return write(data)
        with patch.object(self.engine.store.journal, 'write', side_effect=fail):
            result = self.call('move', {'references': [ref], 'target': 'Target'})
        self.assertFalse(result['ok'], result)
        self.assertIn('Disk full', result['error']['message'])
        evidence = next(iter(result['observations']['evidence'].values()))
        self.assertEqual(evidence['records'][0]['destination']['uid'], 1)
        self.assertEqual(evidence['observed_role'], 'Trash')
        self.assertTrue(self.engine.store.write_failed)
        self.assertFalse(self.engine.store.items('notice:'))
        for action, args in [('mail_accounts', {}), ('control_log', {})]:
            following = self.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': args})
            notices = following['data'] if action == 'control_log' else following['pending']
            self.assertIn('which is now Trash', notices['notices'][0]['untrusted_content']['reason'])
        self.assertEqual(self.imap.mutations, [('MOVE', 1, 'Target')])

