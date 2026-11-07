"""Free filing with durable intent and reporting only after role drift."""
import imaplib
import re
import uuid

from ..adapters import Uncertain
from ..common import Refused, sha256, visible
from .roles import resolve
from .transport import folders, select, uids, fetch, ok, quote


def copyuid(client, source, target):
    rows = client.response('COPYUID')[1]
    match = re.fullmatch(rb'([1-9]\d*) ([1-9]\d*) ([1-9]\d*)', b' '.join(v for v in rows or [] if v))
    if not match or int(match[2]) != source['uid']:
        raise Uncertain('Server omitted exact COPYUID; inspect locations before repeating.')
    return {**source, 'folder': target, 'uidvalidity': int(match[1]), 'uid': int(match[3])}


def locations(mail, account, records):
    # Observations never authorize a recovery mutation.
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
        return [{'source': r['source'], 'last_known_destination': r.get('destination'),
                 'observed_locations': matches, 'scan_complete': True}
                for r, matches in zip(records, found)]
    except (Refused, OSError, imaplib.IMAP4.error, Uncertain):
        return [{'source': r['source'], 'observed_locations': matches, 'scan_complete': False,
                 'last_known_destination': r.get('destination')} for r, matches in zip(records, found)]


def folder_role(name, listed):
    if listed is None:
        return 'an unverified role'
    roles = []
    for folder in listed:
        delimiter = folder['delimiter']
        if name == folder['name'] or (delimiter and name.startswith(folder['name'] + delimiter)):
            for flag in folder['flags']:
                if flag.casefold() in {'\\trash', '\\drafts', '\\sent', '\\junk', '\\archive'}:
                    roles.append(flag[1:].title())
    return ', '.join(sorted(set(roles))) or 'an ordinary folder'


def warning(verb, listed, observed, changed):
    action = 'moving' if verb == 'move' else 'copying'
    reason = ('The special folders changed while Claude was ' + action + ' these messages. '
              if changed else 'Filing could not be fully verified while Claude was ' + action + ' these messages. ')
    reason += 'Nothing was deleted. '
    for item in observed:
        destination = item['last_known_destination']
        source = item['source']
        matches = item['observed_locations']
        if destination and destination in matches:
            reason += ('They' if verb == 'move' else 'The copies') + ' are now in ' + visible(destination['folder'])
            reason += ', which is now ' + folder_role(destination['folder'], listed)
        elif destination:
            reason += 'The last known destination is ' + visible(destination['folder'])
            reason += ' (UIDVALIDITY ' + str(destination['uidvalidity']) + ', UID ' + str(destination['uid']) + '); its current location could not be verified'
        elif source in matches:
            reason += 'The message stayed in ' + visible(source['folder'])
        else:
            reason += 'No exact destination was confirmed for the message from ' + visible(source['folder'])
        if verb == 'copy':
            reason += '; the originals ' + ('stayed in ' if source in matches else 'could not be verified in ') + visible(source['folder'])
        reason += '. '
        if not item['scan_complete']:
            reason += 'The location scan was interrupted; the listed observations are incomplete. '
    return reason + 'Check them in your mail program.'


def file_messages(mail, account, client, verb, refs, target, names, needed):
    intent_id = uuid.uuid4().hex
    key = 'mail:filing:' + intent_id
    # Include untouched batch members in reporting if a prior member hits a race.
    records = [{'source': source, 'sha256': sha256(mail.message(source, client=client)['raw']), 'destination': None}
               for source in refs]
    intent = {'id': intent_id, 'verb': verb, 'sources': refs, 'target': target, 'state': 'started', 'records': records}

    def record(state, notice=None):
        intent['state'] = state
        changes = {key: intent}
        if notice:
            changes['notice:' + intent_id] = notice
        mail.store.write(changes, 'mail_' + verb, 'Filing intent ' + intent_id,
                         outcome=state, untrusted_content={'filing': intent})

    baseline = mail.fresh_roles(account, client, names=names, needed=needed)
    record('started')  # Durable before the first remote mutation; restart never resumes it.
    changed, incomplete, listed = False, False, None
    try:
        for entry in records:
            source = entry['source']
            if mail.fresh_roles(account, client, names=names, needed=needed) != baseline:
                changed = True
                break
            mail.message(source, writable=True, client=client)
            record('started')
            client.response('COPYUID')  # Discard an old response before this one-UID command.
            ok(client.uid(verb.upper(), str(source['uid']), quote(target)), 'UID ' + verb.upper())
            try:
                entry['destination'] = copyuid(client, source, target)
            except Uncertain:
                incomplete = True
            # This LIST is after the command, including when COPYUID was omitted.
            try:
                listed = folders(client)
                changed = resolve(listed) != baseline
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

    # IMAP cannot bind a recovery destination's identity or roles atomically.
    # Preserve every surviving copy; only ordinary owner-approved deletion cleans up.
    observed = locations(mail, account, records)
    reason = warning(verb, listed, observed, changed)
    content = {'reason': reason, 'locations': observed, 'filing_id': intent_id}
    notice = {'id': intent_id, 'app': 'mail', 'state': 'partial', 'untrusted_content': content, 'ack': False}
    intent.update(reason=reason, locations=observed)
    record('partial', notice)
    return {'state': 'partial', 'items': [], 'reason': reason, 'untrusted_content': content}
