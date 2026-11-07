"""Free filing with durable intent and exact, immediate rollback on role drift."""
import imaplib
import re
import uuid

from ..adapters import Uncertain
from ..common import Refused, sha256
from .roles import resolve
from .transport import folders, select, uids, fetch, ok, quote


def copyuid(client, source, target):
    rows = client.response('COPYUID')[1]
    match = re.fullmatch(rb'([1-9]\d*) ([1-9]\d*) ([1-9]\d*)', b' '.join(v for v in rows or [] if v))
    if not match or int(match[2]) != source['uid']:
        raise Uncertain('Server omitted exact COPYUID; inspect locations before repeating.')
    return {**source, 'folder': target, 'uidvalidity': int(match[1]), 'uid': int(match[3])}


def locations(mail, account, records):
    # Reporting only: never use a Message-ID/hash search to authorize undo.
    found = [[] for _ in records]
    try:
        with mail.transport.imap(account) as client:
            for folder in folders(client):
                if any(v.casefold() == '\\noselect' for v in folder['flags']):
                    continue
                validity = select(client, folder['name'])
                for uid in uids(client):
                    raw, _ = fetch(client, uid, mail.wires.limit)
                    for record, matches in zip(records, found):
                        if sha256(raw) == record['sha256']:
                            matches.append({**record['source'], 'folder': folder['name'], 'uidvalidity': validity, 'uid': uid})
        return [{'source': r['source'], 'observed_locations': matches, 'scan_complete': True}
                for r, matches in zip(records, found)]
    except (Refused, OSError, imaplib.IMAP4.error):
        return [{'source': r['source'], 'observed_locations': matches, 'scan_complete': False,
                 'last_known_destination': r.get('destination')} for r, matches in zip(records, found)]


def file_messages(mail, account, client, verb, refs, target, names, needed):
    intent_id = uuid.uuid4().hex
    key = 'mail:filing:' + intent_id
    intent = {'id': intent_id, 'verb': verb, 'sources': refs, 'target': target, 'state': 'started', 'records': []}

    def record(state):
        intent['state'] = state
        mail.store.write({key: intent}, 'mail_' + verb, 'Filing intent ' + intent_id,
                         outcome=state, untrusted_content={'filing': intent})

    baseline = mail.fresh_roles(account, client, names=names, needed=needed)
    record('started')  # Durable before the first remote mutation; restart never resumes it.
    records, changed, incomplete = intent['records'], False, False
    try:
        for source in refs:
            if mail.fresh_roles(account, client, names=names, needed=needed) != baseline:
                changed = True
                break
            message = mail.message(source, writable=True, client=client)
            entry = {'source': source, 'sha256': sha256(message['raw']), 'destination': None}
            records.append(entry)
            record('started')
            client.response('COPYUID')  # Discard an old response before this one-UID command.
            ok(client.uid(verb.upper(), str(source['uid']), quote(target)), 'UID ' + verb.upper())
            try:
                entry['destination'] = copyuid(client, source, target)
            except Uncertain:
                incomplete = True
            # This LIST is after the command, including when COPYUID was omitted.
            try:
                changed = resolve(folders(client)) != baseline
            except Refused:
                changed = True
            record('started')
            if changed or incomplete:
                break
    except (Refused, OSError, imaplib.IMAP4.error, Uncertain):
        incomplete = True

    if not changed and not incomplete:
        record('done')
        return {'state': 'done', 'items': [r['destination'] for r in records]}

    # Roll back the whole attempted batch, never unrelated Deleted messages. Only
    # the server's exact COPYUID map grants permission to mutate a destination UID.
    for entry in reversed(records):
        destination = entry['destination']
        if destination is None:
            incomplete = True
            continue
        try:
            original = entry['source']
            if verb == 'move':
                if select(client, original['folder']) != original['uidvalidity']:
                    raise Refused('stale_reference', 'Source folder changed during filing.')
            message = mail.message(destination, writable=True, client=client)
            if sha256(message['raw']) != entry['sha256']:
                raise Refused('stale_reference', 'Destination bytes changed during filing.')
            if verb == 'move':
                client.response('COPYUID')
                ok(client.uid('MOVE', str(destination['uid']), quote(original['folder'])), 'Undo UID MOVE')
                restored = copyuid(client, destination, original['folder'])
                # The source namespace must still be the one that was approved for filing.
                if restored['uidvalidity'] != original['uidvalidity']:
                    raise Refused('stale_reference', 'Original source folder no longer exists.')
                check = mail.message(restored, client=client)
                if sha256(check['raw']) != entry['sha256']:
                    raise Refused('stale_reference', 'Returned message differs.')
                entry['returned'] = restored
            else:
                ok(client.uid('STORE', str(destination['uid']), '+FLAGS.SILENT', '(\\Deleted)'), 'Mark exact copy for removal')
                ok(client.uid('EXPUNGE', str(destination['uid'])), 'Remove exact copy')
                if destination['uid'] in uids(client):
                    raise Refused('stale_reference', 'Copy still present after undo.')
                mail.message(original, client=client)
                entry['returned'] = original
        except (Refused, OSError, imaplib.IMAP4.error, Uncertain):
            incomplete = True
    state = 'partial' if incomplete else 'refused'
    reason = ('Filing or exact undo incomplete; inspect each observed folder and UID; never retry automatically.' if incomplete
              else 'special folders changed during the move; ' + ('the messages were returned' if verb == 'move' else 'the copies were removed'))
    observed = locations(mail, account, records)
    intent.update(reason=reason, locations=observed)
    record(state)
    return {'state': state, 'items': [], 'reason': reason, 'untrusted_content': {'locations': observed, 'filing_id': intent_id}}
