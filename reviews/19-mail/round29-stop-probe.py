"""Reproduce round 29's restore dependency; this is not an acceptance test.

Run from the worktree root with PYTHONPATH=control. All data is synthetic,
under this worktree's .work/, and no mail transport is used.
"""
from pathlib import Path
import shutil
import sqlite3
import tempfile

from aresos_control.engine import Engine
from aresos_control.recovery import open_filings, recover_intents


def probe(backup_before_intent, acknowledge=True):
    work = Path(__file__).resolve().parents[2] / '.work' / 'round29'
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work) as temporary:
        root = Path(temporary)
        state, independent = root / 'state', root / 'independent'
        engine = Engine(state, independent)
        try:
            def backup():
                connection = sqlite3.connect(root / 'backup.sqlite')
                try:
                    engine.store.db.backup(connection)
                finally:
                    connection.close()

            if backup_before_intent:
                backup()
            key = 'mail:rename:synthetic-open'
            source = {'id': 'synthetic-open', 'account': 'synthetic', 'source': 'Source',
                      'target': 'Target', 'message_count': 1, 'roles_before': {}, 'state': 'started'}
            engine.store.write({key: source}, 'mail_folder_rename', 'Synthetic interrupted check')
            if acknowledge:
                recover_intents(engine.store)
            if not backup_before_intent:
                backup()
            if acknowledge:
                engine.dispatch('mail_notice_ack', {'operation_id': source['id']})
                assert engine.store.get(key)['check_open']
                assert engine.store.get('notice:' + source['id'])['ack']
            else:
                assert engine.store.get('notice:' + source['id']) is None
            assert key in open_filings(engine.store)
            # Neither the source nor its warning/acknowledgement appears in
            # any compact operation record. Hashes cannot reconstruct them.
            records = list(engine.store.events)
            assert all(record['operations'] == [] for record in records)
            assert all(set(record) == {'format', 'seq', 'previous', 'time',
                                       'generation', 'operations', 'hash'} for record in records)
            engine.close()
            engine = None
            shutil.copyfile(root / 'backup.sqlite', state / 'control.sqlite')
            engine = Engine(state, independent)
            assert engine.store.locked
            engine.dispatch('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
            assert not engine.store.locked
            if backup_before_intent:
                assert engine.store.get(key) is None
                assert engine.store.get('notice:' + source['id']) is None
                assert not open_filings(engine.store)
                if acknowledge:
                    print('REPRODUCED: backup before intent -> acknowledged-but-open check disappears after restore.')
                else:
                    print('REPRODUCED: open check without any occurrence -> check disappears after restore.')
            else:
                assert key in open_filings(engine.store)
                assert not engine.store.get('notice:' + source['id'])['ack']
                print('REPRODUCED: backup before acknowledgement -> acknowledged recovery warning returns after restore.')
        finally:
            if engine is not None:
                engine.close()


if __name__ == '__main__':
    probe(backup_before_intent=True, acknowledge=False)
    probe(backup_before_intent=True)
    probe(backup_before_intent=False)
    print('STOP-CONDITION evidence only; round-29 fixes are not implemented or verified.')
