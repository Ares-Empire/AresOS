"""Smallest reproduction of the restore-lock disagreements (brief 20-restore-lock-followups).

Run from the repo root, as an ordinary user, no container:

    PYTHONDONTWRITEBYTECODE=1 python3 reviews/20-restore-lock-followups/repro.py

It uses the service's Engine, the owner oracle's decoder and page reader, and
unittest.mock. Two things are stood in for:
- the installation precondition (a root-owned managed-settings file) is read from
  the repo's draft settings, as CI installs it in its container;
- each case fails exactly the disk calls it names, with ENOSPC.
Everything lives in a temporary directory. Nothing is installed or left behind.
"""
import errno
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'control'))
SETTINGS = json.loads((REPO / 'control/settings/managed-settings.draft.json').read_text())
patch('aresos_control.boundary.Boundary.read', lambda self, path: SETTINGS).start()

from aresos_control.engine import Engine  # noqa: E402
from owner_state_oracle.compare import pages  # noqa: E402
from owner_state_oracle.records import decode  # noqa: E402

CONFIRM = {'confirm': 'invalidate earlier approvals'}
SEND = {'account': 'fixture', 'to': ['alpha'], 'cc': [], 'bcc': [], 'subject': 'Synthetic', 'text': 'Exact',
        'attachments': []}
FULL = OSError(errno.ENOSPC, 'Synthetic full disk')


def call(engine, action, arguments=None, admin=False):
    return engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': arguments or {}}, admin)


def short(reply):
    """What the caller is told about the lock: the status, and both places a lock flag can be."""
    data = reply.get('data', {}).get('restore_required', 'no such key') if reply['ok'] else 'no data'
    return (f"ok={reply['ok']} error={reply.get('error', {}).get('code')} data.restore_required={data} "
            f"pending.restore_required={reply.get('pending', {}).get('restore_required')}")


def decoded(state, evidence):
    record = decode(state, evidence)
    return (f'locked={record.locked} (head {record.head[0]}, last commit marker {max(record.committed)}, '
            f'prepared {[event["seq"] for event in record.prepared]})')


def fail_marker_sync(store):
    """Fail the journal's second sync of a write: the first is the record, the second its commit marker."""
    real, syncs = os.fsync, []

    def fsync(descriptor):
        if descriptor == store.journal.fileno():
            syncs.append(descriptor)
            if len(syncs) == 2:
                raise FULL
        return real(descriptor)
    return patch('os.fsync', fsync)


def locked_engine(root):
    """An older database under a newer independent record: the restore lock."""
    state, evidence = root / 'state', root / 'evidence'
    engine = Engine(state, evidence)
    with closing(sqlite3.connect(root / 'backup.sqlite')) as backup:
        engine.store.db.backup(backup)
    assert call(engine, 'testapp_prepare_send', SEND)['ok']
    engine.close()
    (state / 'control.sqlite').write_bytes((root / 'backup.sqlite').read_bytes())
    engine = Engine(state, evidence)
    assert engine.store.locked
    return engine, state, evidence


def item_1(rollback_fails):
    print('\n== Item 1: the confirm fails at its last disk sync;',
          'the rollback of the marker fails too (the sweep\'s persistent mode)' if rollback_fails
          else 'the marker is rolled back (the sweep\'s single mode)')
    with tempfile.TemporaryDirectory() as directory:
        engine, state, evidence = locked_engine(Path(directory))
        store = engine.store
        rollback = patch.object(store, '_truncate_journal', side_effect=FULL if rollback_fails else None,
                                wraps=None if rollback_fails else store._truncate_journal)
        with fail_marker_sync(store), rollback:
            reply = call(engine, 'control_restore_confirm', CONFIRM, admin=True)
        tail = (evidence / 'operations.jsonl').read_bytes().splitlines()[-1]
        print(' confirm                ', short(reply))
        print(' journal ends with      ', 'a commit marker' if tail.startswith(b'{"commit"') else 'a record, no marker')
        print(' oracle decodes         ', decoded(state, evidence))
        print(' running store          ', f'locked={store.locked} write_failed={store.write_failed}')
        print(' control_pending        ', short(call(engine, 'control_pending')))
        print(' aresos log             ', short(call(engine, 'control_log')))
        again = call(engine, 'control_restore_confirm', CONFIRM, admin=True)
        print(' confirm again, disk ok ', short(again))
        print('   its message          ', again['error']['message'])
        engine.close()
        engine = Engine(state, evidence)
        try:
            print(' after a restart        ', f'locked={engine.store.locked};', short(call(engine, 'control_pending')))
            print(' oracle decodes         ', decoded(state, evidence))
        finally:
            engine.close()


def item_2():
    print('\n== Item 2: the log view under a restore lock')
    with tempfile.TemporaryDirectory() as directory:
        engine, state, evidence = locked_engine(Path(directory))
        try:
            reply = call(engine, 'control_log')
            print(' aresos log             ', short(reply))
            print('   its message          ', reply['error']['message'])
            page = next(pages(lambda action, arguments: call(engine, action, arguments), 'control_log', {'limit': 5}))
            print(' page the oracle reads  ', page)
            print(' oracle: expected locked=', decode(state, evidence).locked,
                  ' observed locked=', page.get('restore_required', False))
            print(' control_pending        ', short(call(engine, 'control_pending')))
            assert call(engine, 'control_restore_confirm', CONFIRM, admin=True)['ok']
            answered = call(engine, 'control_log')
            print(' aresos log, confirmed  ', short(answered), 'data keys', sorted(answered['data']))
        finally:
            engine.close()


def item_3():
    print('\n== Item 3: an ordinary write fails at its last disk sync (no restore anywhere)')
    with tempfile.TemporaryDirectory() as directory:
        state, evidence = Path(directory) / 'state', Path(directory) / 'evidence'
        engine = Engine(state, evidence)
        store = engine.store
        with fail_marker_sync(store):
            reply = call(engine, 'testapp_prepare_send', SEND)
        print(' prepare                ', short(reply))
        print(' oracle decodes         ', decoded(state, evidence))
        print(' running store          ', f'locked={store.locked} write_failed={store.write_failed}')
        print(' control_pending        ', short(call(engine, 'control_pending')))
        engine.close()
        engine = Engine(state, evidence)
        try:
            print(' after a restart        ', f'locked={engine.store.locked};', short(call(engine, 'control_pending')))
            print(' oracle decodes         ', decoded(state, evidence))
        finally:
            engine.close()


if __name__ == '__main__':
    item_1(rollback_fails=False)
    item_1(rollback_fails=True)
    item_2()
    item_3()
