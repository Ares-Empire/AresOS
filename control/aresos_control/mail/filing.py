"""Free filing with durable intent and reporting only after role drift."""
import imaplib
import re
import time
import uuid

from ..adapters import Uncertain
from ..common import Refused, canonical, digest, sha256, visible
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


# Leave room for the pending catalogue and its repeated notices in a 48 KiB result.
NOTICE_LIMIT = 3
FOLDER_LIMIT = 3
FOLDER_CHARS = 64
LOCATION_PAGE_BYTES = 12 * 1024


def rename_folder(mail, account, client, source, target, roles_before):
    filing_id = uuid.uuid4().hex
    intent = {'id': filing_id, 'source': source['folder'], 'target': target,
              'message_count': len(source['uids']), 'roles_before': roles_before, 'state': 'started'}
    key = 'mail:rename:' + filing_id
    mail.store.write({key: intent}, 'mail_folder_rename', 'folder rename intent',
                     outcome='started', untrusted_content={'rename': intent})
    ok(client.rename(quote(source['folder']), quote(target)), 'Rename folder')
    try:
        listed = folders(client)
        entry = next((f for f in listed if f['name'] == target), None)
        if entry is None:
            raise Uncertain('Renamed folder missing from LIST')
        roles = sorted({f.title() for f in entry['flags'] if f.casefold() in {
            '\\all', '\\archive', '\\drafts', '\\flagged', '\\junk', '\\sent', '\\trash', '\\important'}})
        role = ', '.join(roles) if roles else folder_role(target, listed)
        needs_notice = bool(roles) or role != 'an ordinary folder'
        intent['roles_after'] = resolve(listed)
    except (Refused, OSError, imaplib.IMAP4.error, Uncertain):
        role, needs_notice = 'an unverified role', True
    intent.update(state='partial' if needs_notice else 'done', observed_role=role)
    changes = {key: intent}
    result = {'account': account['id'], 'folder': target, 'state': intent['state']}
    if needs_notice:
        reason = ('The special folders changed while Claude was moving this folder. '
                  'Nothing was deleted. It is now ' + short_name(target) + ', inside ' + role +
                  '. Check it in your mail program.')
        content = {'filing_id': filing_id, 'message_count': intent['message_count'], 'reason': reason,
                   'folders': [short_name(source['folder']), short_name(target)], 'folders_more': 0,
                   'folders_more_text': ''}
        changes['notice:' + filing_id] = {'id': filing_id, 'app': 'mail', 'state': 'partial',
            'untrusted_content': content, 'ack': False, 'created_at': time.time_ns()}
        result.update(state='partial', reason=visible(reason), untrusted_content=visible(content))
    mail.store.write(changes, 'mail_folder_rename', 'folder rename checked',
                     outcome=intent['state'], untrusted_content={'rename': intent})
    return result


def short_name(name):
    return name[:FOLDER_CHARS] + ('…' if len(name) > FOLDER_CHARS else '')


def warning(verb, listed, observed, changed):
    action = 'moving' if verb == 'move' else 'copying'
    reason = ('The special folders changed while Claude was ' + action + ' these messages. '
              if changed else 'Filing could not be fully verified while Claude was ' + action + ' these messages. ')
    reason += 'Nothing was deleted. '
    filed = [item for item in observed if item['last_known_destination']]
    if filed:
        destination = filed[0]['last_known_destination']
        if all(item['last_known_destination'] in item['observed_locations'] for item in filed):
            reason += ('They' if verb == 'move' else 'The copies') + ' are now in ' + short_name(destination['folder'])
            reason += ', which is now ' + folder_role(destination['folder'], listed)
        else:
            reason += 'The last known destination is ' + short_name(destination['folder']) + '; its current location could not be verified'
        if verb == 'copy':
            present = all(item['source'] in item['observed_locations'] for item in observed)
            source_names = {item['source']['folder'] for item in observed}
            source_text = short_name(next(iter(source_names))) if len(source_names) == 1 else 'their source folders'
            reason += '; the originals ' + ('stayed in ' if present else 'could not be verified in ') + source_text
        reason += '. '
    else:
        reason += 'No exact destination was confirmed. '
    if len(filed) != len(observed):
        reason += 'Some messages were not confirmed filed; read the exact location pages. '
    if any(not item['scan_complete'] for item in observed):
        reason += 'The location scan was interrupted; the listed observations are incomplete. '
    return reason + 'Check them in your mail program.'


def summary(intent):
    names = {intent['target']} | {r['folder'] for r in intent['sources']}
    names.update(ref['folder'] for item in intent.get('locations', []) for ref in item['observed_locations'])
    return {'reason': intent['reason'], 'filing_id': intent['id'], 'message_count': len(intent['sources']),
            'folders': [short_name(name) for name in sorted(names)[:FOLDER_LIMIT]],
            'folders_more': max(0, len(names) - FOLDER_LIMIT),
            'folders_more_text': 'and ' + str(len(names) - FOLDER_LIMIT) + ' more' if len(names) > FOLDER_LIMIT else ''}


def audit_content(content):
    # Old audit rows are immutable, but their display must not reintroduce the
    # entire pre-paging location report (or a batch of enormous Message-IDs).
    if 'filing' in content:
        intent = content['filing']
        if 'records' in intent or 'locations' in intent:
            return {'filing': {'filing_id': intent['id'], 'state': intent['state'],
                              'message_count': len(intent['sources']), 'locations_action': 'mail_filing_locations'}}
    if 'references' in content:
        return {'message_count': len(content['references']), 'locations_action': 'mail_filing_locations'}
    return content


def public_notice(store, notice):
    content = notice['untrusted_content']
    # Old round-10 notices may already contain megabytes. Do not repeat their detail.
    if 'locations' in content:
        intent = store.get('mail:filing:' + notice['id'])
        if intent:
            intent['reason'] = warning(intent['verb'], None, intent.get('locations', []), True)
            content = summary(intent)
        else:
            content = {'filing_id': notice['id'], 'reason': 'Filing needs inspection. Nothing was deleted. Check the exact location pages and your mail program.'}
    return {'operation_id': notice['id'], 'app': notice['app'], 'state': notice['state'],
            'untrusted_content': visible(content)}


def notice_page(store, args=None, app=None):
    args = args or {}
    values = [n for _, n in store.items('notice:') if not n.get('ack') and (app is None or n['app'] == app)]
    values.sort(key=lambda n: (n.get('created_at', 0), n['id']), reverse=True)
    token = digest(['filing-notices', app, [n['id'] for n in values]])
    offset = 0
    if 'cursor' in args:
        try:
            version, index = args['cursor'].split(':')
            offset = int(index)
            if version != token or not 0 <= offset <= len(values):
                raise ValueError()
        except ValueError as exc:
            raise Refused('stale_reference', 'Notices changed; read again without cursor.') from exc
    end = min(offset + args.get('limit', NOTICE_LIMIT), len(values))
    return {'items': [public_notice(store, n) for n in values[offset:end]], 'total': len(values),
            'cursor': f'{token}:{end}' if end < len(values) else None}


def location_pages(observed):
    # Ordinary records remain structured. A single record can itself be enormous
    # (identical wire bytes at thousands of UIDs, or one long Message-ID).
    # JSON fragments preserve that record without truncation or an oversize page.
    pages, page = [], {'locations': [], 'fragments': []}
    for index, item in enumerate(observed):
        item = visible(item)
        encoded = canonical(item)
        if len(encoded) > LOCATION_PAGE_BYTES - 100:
            if page['locations']:
                pages.append(page)
                page = {'locations': [], 'fragments': []}
            # canonical() is ASCII; serializing this string costs at most twice
            # its length. Fragments concatenate before JSON decoding.
            for offset in range(0, len(encoded), 6000):
                pages.append({'locations': [], 'fragments': [{'message_index': index, 'offset': offset,
                    'total_characters': len(encoded), 'json': encoded[offset:offset + 6000]}]})
        else:
            candidate = {'locations': page['locations'] + [item], 'fragments': []}
            if len(canonical(candidate)) > LOCATION_PAGE_BYTES:
                pages.append(page)
                page = {'locations': [item], 'fragments': []}
            else:
                page = candidate
    if page['locations'] or not pages:
        pages.append(page)
    return pages


def location_page(store, args):
    filing_id = args['filing_id']
    prefix = 'mail:filing-locations:' + filing_id + ':'
    meta = store.get(prefix + 'meta')
    legacy_pages = None
    if meta is None:
        intent = store.get('mail:filing:' + filing_id)
        if not intent or 'locations' not in intent:
            raise Refused('stale_reference', 'No recorded filing locations for this id; inspect the filing audit entry.')
        legacy_pages = location_pages(intent['locations'])
        meta = {'pages': len(legacy_pages), 'total_messages': len(intent['locations'])}
    offset = 0
    if 'cursor' in args:
        try:
            owner, index = args['cursor'].split(':')
            offset = int(index)
            if owner != filing_id or not 0 <= offset < meta['pages']:
                raise ValueError()
        except ValueError as exc:
            raise Refused('stale_reference', 'Location cursor belongs to another filing or page; read again without cursor.') from exc
    page = legacy_pages[offset] if legacy_pages is not None else store.get(prefix + str(offset))
    return {'filing_id': filing_id, 'total_messages': meta['total_messages'], 'untrusted_content': page,
            'cursor': f'{filing_id}:{offset + 1}' if offset + 1 < meta['pages'] else None}


def file_messages(mail, account, client, verb, refs, target, names, needed):
    intent_id = uuid.uuid4().hex
    key = 'mail:filing:' + intent_id
    # Include untouched batch members in reporting if a prior member hits a race.
    records = [{'source': source, 'sha256': sha256(mail.message(source, client=client)['raw']), 'destination': None}
               for source in refs]
    intent = {'id': intent_id, 'verb': verb, 'sources': refs, 'target': target, 'state': 'started', 'records': records}

    def record(state, notice=None, pages=None):
        intent['state'] = state
        changes = {key: intent}
        if notice:
            changes['notice:' + intent_id] = notice
        if pages is not None:
            prefix = 'mail:filing-locations:' + intent_id + ':'
            changes.update({prefix + str(i): page for i, page in enumerate(pages)})
            changes[prefix + 'meta'] = {'pages': len(pages), 'total_messages': len(records)}
        mail.store.write(changes, 'mail_' + verb, 'Filing intent ' + intent_id,
                         outcome=state, untrusted_content={'filing': {'filing_id': intent_id, 'state': state,
                             'message_count': len(records), 'locations_action': 'mail_filing_locations'}})

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
    intent.update(reason=reason, locations=observed)
    content = summary(intent)
    notice = {'id': intent_id, 'app': 'mail', 'state': 'partial', 'untrusted_content': content,
              'ack': False, 'created_at': time.time_ns()}
    pages = location_pages(observed)
    record('partial', notice, pages)
    first = location_page(mail.store, {'filing_id': intent_id})
    return {'state': 'partial', 'items': [], 'reason': visible(reason),
            'untrusted_content': {**visible(content), **first['untrusted_content'], 'cursor': first['cursor']}}
