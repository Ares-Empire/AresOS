"""Real Dovecot APPEND/SEARCH observations survive both post-APPEND writes."""
import errno
from unittest.mock import patch

from aresos_control.common import Refused
from aresos_control.engine import Engine
from smtp_fixture import SMTPFixture
from support import MailCase


class LiveResults23(MailCase):
    def test_review23_live_send_and_repair_return_duplicates_on_warning_or_end_marker_enospc(self):
        for repairing in (False, True):
            for failed_write in ('warning', 'end'):
                with self.subTest(repairing=repairing, failed_write=failed_write):
                    directory = self.root / (str(repairing) + failed_write)
                    directory.mkdir()
                    with SMTPFixture(directory) as smtp:
                        account = {**self.account, 'smtp_host': 'localhost', 'smtp_port': smtp.port}
                        self.engine.store.write({'mail:account:box': account}, 'fixture', 'Synthetic TLS submission')
                        approval = self.approval()
                        operation_id = approval['operation_id']
                        verb, args = 'send', approval
                        if repairing:
                            original_local = self.mail.local_stage
                            def local(operation, which):
                                if which == 'sent_copy':
                                    raise Refused('stage_missing', 'Synthetic missing Sent stage')
                                return original_local(operation, which)
                            with patch.object(self.mail, 'local_stage', side_effect=local):
                                self.assertEqual(self.send(approval)['state'], 'partial')
                            verb, args = 'operation_repair', {'operation_id': operation_id, 'stage': 'sent_copy'}
                        append, write = self.mail.append, self.engine.store.write
                        def duplicate(*values, **kwargs):
                            # Fixture: one earlier server copy lands with our APPEND.
                            append(*values, **kwargs)
                            return append(*values, **kwargs)
                        def persist(changes, action, summary, *values, **kwargs):
                            fail = (action == 'mail_sent_copy_check' if failed_write == 'warning' else
                                    action == 'mail_sent_copy_attempt' and summary == 'Sent APPEND attempt ended')
                            if fail:
                                with patch.object(self.engine.store.journal, 'write', side_effect=OSError(errno.ENOSPC, 'Synthetic disk full')):
                                    return write(changes, action, summary, *values, **kwargs)
                            return write(changes, action, summary, *values, **kwargs)
                        with patch.object(self.mail, 'append', side_effect=duplicate) as appends, \
                             patch.object(self.engine.store, 'write', side_effect=persist):
                            result = self.call(verb, args)
                        self.assertFalse(result['ok'], result)
                        self.assertEqual(result['error']['code'], 'storage_limit')
                        self.assertIn('Disk full', result['error']['message'])
                        observation = result['observations']['evidence'][operation_id]
                        self.assertEqual(len(observation['sent']), 2)
                        self.assertIn('2 copies', observation['sent_copy_warning'])
                        self.assertEqual(result['observations']['stages'][operation_id]['sent_copy'], 'done')
                        self.assertEqual(appends.call_count, 1)
                        self.engine.close()
                        self.engine = Engine(self.root / 'state', self.root / 'independent')
                        self.mail = self.engine.adapters['mail']
                        status = self.data('operation_status', {'operation_id': operation_id})
                        self.assertEqual(len(status['evidence']['sent']), 2)
                        self.assertIn(status['operation']['state'], {'partial', 'unknown'})
                        self.call('send', approval)
                        self.assertEqual(len(smtp.arrivals()), 1)
                        self.assertEqual(len(self.mail.sent_matches(account, self.mail.message_id(operation_id))), 2)
