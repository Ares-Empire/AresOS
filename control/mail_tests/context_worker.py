"""Disposable R2 worker: stop at any logical write's durability fence."""
import errno
import os
from pathlib import Path
import pickle
import signal
import sys
from unittest.mock import patch

from owner_state_oracle.driver import Driver
from test_owner_state_sweep import OwnerScenario

flow, mode, occurrence, point, output = sys.argv[1:]
occurrence, output = int(occurrence), Path(output)
scenario = OwnerScenario('fixture' if flow == 'local_flag' else flow)
if flow == 'local_flag':
    reference = scenario.fixture.engine.request({'v': 1, 'method': 'call', 'action': 'testapp_list',
        'arguments': {'limit': 1}})['data']['items'][0]['reference']
    scenario.action, scenario.args = 'testapp_flag', {'reference': reference, 'flagged': True}
driver = Driver(scenario)
store = scenario.fixture.engine.store
write, precommit = store.write, driver.precommit
count, reached, blocked_keys = 0, False, []


def before_command():
    return {**precommit(), 'write_number': count}


def save():
    receiver = scenario.fixture.engine.receiver.db
    output.write_bytes(pickle.dumps({'root': str(scenario.fixture.root), 'writes': count, 'reached': reached,
        'blocked_keys': blocked_keys,
        'script': driver.oracle.script, 'servers': driver.oracle.servers,
        'receiver': {table: receiver.execute('SELECT * FROM ' + table).fetchall()
                     for table in ('arrivals', 'stages', 'config')}}))


def stop(name):
    global reached
    if count != occurrence or name != point or reached:
        return
    reached = True
    if mode == 'crash':
        save()
        os.kill(os.getpid(), signal.SIGKILL)
    raise OSError(errno.ENOSPC, 'Synthetic context write fence refused')


def persist(*args, **kwargs):
    global count, blocked_keys
    count += 1
    if count == occurrence:
        blocked_keys = [key for key, row in args[0].items() if isinstance(row, dict) and
            'context' in row and row['context'] != (store.get(key) or {}).get('context')]
    stop('before_write')
    return write(*args, **kwargs)


driver.precommit = before_command
try:
    with patch.object(store, 'write', side_effect=persist), patch.object(store, 'checkpoint', side_effect=stop), driver.observe():
        reply = scenario.call()
    driver.reply(reply)
    save()
finally:
    if mode != 'crash' or not reached:
        scenario.close()
