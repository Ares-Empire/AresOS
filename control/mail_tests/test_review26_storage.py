"""Admission recovery uses the very next call on the same Store."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
from aresos_control.engine import Engine
from aresos_control.space import SAFETY_FLOOR
import test_review_fixes_23 as prior


class Storage26(unittest.TestCase):
    setUp = prior.Results23.setUp

    def test_review26_startup_index_refusal_rechecks_on_next_write(self):
        root = self.root
        self.engine.close()
        with patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=SAFETY_FLOOR)):
            self.engine = Engine(root / 'state', root / 'evidence')
        store = self.engine.store
        self.assertIsNone(store.index)
        self.assertFalse(store.write_failed)
        self.assertIsNotNone(store.index_refusal)
        store.write({'fixture:recovered': True}, 'fixture', 'Healthy disk without restart')
        self.assertTrue(store.get('fixture:recovered'))
        self.assertIsNotNone(store.index)
        self.assertIsNone(store.index_refusal)

    def test_review26_admission_and_retention_refusals_retry_without_restart(self):
        store = self.engine.store
        for phase in ('disk', 'history', 'records', 'blob'):
            with self.subTest(phase=phase):
                if phase == 'disk':
                    scope = patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=0))
                    call = lambda: store.write({'fixture:next': phase}, 'fixture', 'Admission retry')
                elif phase == 'history':
                    scope = patch('aresos_control.retention.HISTORY_BYTES', 0)
                    call = lambda: store.write({'fixture:next': phase}, 'fixture', 'History retry')
                elif phase == 'records':
                    scope = patch('aresos_control.retention.COMPOSITION_COUNT', 0)
                    call = lambda: store.write({'mail:composition:fixture': {'id': 'fixture'}}, 'fixture', 'Count retry')
                else:
                    scope = patch('aresos_control.retention.BLOB_COUNT', 0)
                    call = lambda: self.engine.blobs.put(b'Synthetic admission recovery')
                with scope, self.assertRaises(Refused) as caught:
                    call()
                self.assertEqual(caught.exception.code, 'storage_limit')
                self.assertFalse(store.write_failed)
                call()

    def test_review26_failed_index_retry_preserves_live_journal_head(self):
        import errno
        store = self.engine.store
        store.write({}, 'fixture', 'Committed head before index retry')
        sequence, head_hash = store.sequence, store.head_hash
        store.index.close()
        store.index = None
        with patch.object(store, '_index_record', side_effect=OSError(errno.EIO, 'Synthetic index I/O failure')):
            with self.assertRaises(OSError):
                store.require_index()
        self.assertEqual((store.sequence, store.head_hash), (sequence, head_hash))
        store.write({}, 'fixture', 'Healthy retry uses the original journal head')
        self.assertEqual(store.sequence, sequence + 1)
