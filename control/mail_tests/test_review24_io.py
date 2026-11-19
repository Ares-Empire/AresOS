"""The sweep must reach SQLite internal writes, not just Python commit calls."""
from contextlib import closing
import sqlite3
import tempfile
from pathlib import Path
import unittest

from storage_faults import OSWrites
from support import WORK


class SQLiteFaults24(unittest.TestCase):
    def test_sqlite_read_handle_close_fault_is_not_a_propagated_storage_error(self):
        with tempfile.TemporaryDirectory(dir=WORK) as root:
            path = Path(root) / 'read.sqlite'
            with closing(sqlite3.connect(path)) as db:
                db.execute('CREATE TABLE fixture (value)')
            db = sqlite3.connect(path)
            db.execute('SELECT * FROM fixture').fetchall()
            fault = OSWrites(1)
            with fault.wrap():
                db.close()
            self.assertEqual(fault.failures, [(1, 'sqlite.main.close', 'ENOSPC')])

    def test_review24_vfs_fails_internal_statement_writes_for_main_and_index_connections(self):
        with tempfile.TemporaryDirectory(dir=WORK) as root:
            for name, prefix in [('statement.sqlite', 'sqlite.main'), ('journal-index.sqlite', 'sqlite.index')]:
                with self.subTest(connection=prefix), closing(sqlite3.connect(Path(root) / name)) as db:
                    db.execute('PRAGMA cache_size=1')
                    db.execute('CREATE TABLE payload (value BLOB)')
                    sweep = OSWrites()
                    with sweep.wrap():
                        db.execute('INSERT INTO payload VALUES (?)', (b'x' * 131072,))
                    # No commit happened in that scope: these are statement and
                    # cache-spill writes made internally by the actual library.
                    self.assertIn(prefix + '.write', sweep.points)
                    db.rollback()
                    fault = OSWrites(sweep.points.index(prefix + '.write') + 1)
                    with fault.wrap(), self.assertRaises(sqlite3.Error) as caught:
                        db.execute('INSERT INTO payload VALUES (?)', (b'x' * 131072,))
                    self.assertTrue(fault.failed)
                    self.assertEqual(caught.exception.sqlite_errorcode & 255, sqlite3.SQLITE_FULL)
                    db.rollback()
                    self.assertEqual(db.execute('SELECT count(*) FROM payload').fetchone(), (0,))
