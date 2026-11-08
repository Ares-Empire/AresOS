"""Durable caller-write holds, shared with private blob and audit admission."""
import uuid

from .common import Refused, sha256
from .space import record_budget
from .storage import sync_directory


def budget(transfer):
    return transfer['size'] + 128 * 1024


def begin(store, blobs, app, key, size, creating=False):
    export_id = uuid.uuid4().hex
    transfer = {'app': app, 'sha256': key, 'size': size,
                'created_blob': creating and not (blobs.directory / key).exists()}
    # Admit both copies before either is created. The caller hold remains
    # durable while another request, or a restarted service, does other work.
    store.ledger.admit((size + 16384 if creating else 0) + record_budget(transfer),
                       updates={'export:' + export_id: budget(transfer)})
    store.write({'export:' + export_id: transfer}, app + '_file_save', 'reserved caller export', outcome='started')
    return export_id


def get(store, export_id, app, key=None):
    transfer = store.get('export:' + export_id)
    if transfer is None or transfer['app'] != app or (key is not None and transfer['sha256'] != key):
        raise Refused('stale_reference', 'Export reservation is missing or different; request the export again.')
    return transfer


def discard_blob(store, blobs, transfer, export_id):
    key = transfer['sha256']
    if (not transfer['created_blob'] or blobs.origins(key) - {'export'} or
            any(other_id != 'export:' + export_id and other['sha256'] == key
                for other_id, other in store.iter_items('export:'))):
        return
    (blobs.directory / key).unlink(missing_ok=True)
    (blobs.directory / ('.origins-' + key)).unlink(missing_ok=True)
    sync_directory(blobs.directory)


def put(store, blobs, data):
    key = sha256(data)
    export_id = begin(store, blobs, 'mail', key, len(data), creating=True)
    try:
        blobs.put(data, origin='export')
    except BaseException:
        transfer = get(store, export_id, 'mail')
        discard_blob(store, blobs, transfer, export_id)
        store.write({'export:' + export_id: None}, 'mail_file_save', 'private export refused', outcome='refused')
        raise
    return key, export_id
