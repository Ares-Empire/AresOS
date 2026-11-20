"""Brief 28a, item 6: the smaller tools, offered since item 8's step 1d.

- `tabs`: every tab of every normal window (and of the popup windows) in one
  list, the extension's all-tabs reply written as text: whose a tab is (who
  opened it), its marks, its title and its address in the short form. The
  result carries `seen`, which names what this list showed of each tab: its top
  document and full address (the address alone for a tab asleep).
- `seen_entry`: what a list showed of one tab, for chrome_take (the extension
  checks it before it does anything) and chrome_open (which opens that address).
- `close`: closes Claude's own tabs only, each through brief 20's guard; a
  kept tab carries its reason, and a loss report of its own.
- `library`: brief 20's downloads, bookmarks and history in one call, every
  address in the short form and every entry with a reference chrome_open takes.
- `show`: the tab in front of its window, and the window in front.
"""
from ..common import Refused, visible
from . import loss
from .address import public_address
from .policy import allowed_url, hostname
from .references import LIST_AGAIN
from .view import quoted

PAGE_TABS, TITLE, ADDRESS = 200, 80, 60
KINDS = ('downloads', 'bookmarks', 'history')
MARK = '…'

TAKEN_CLOSE = "this is the owner's tab; release it"
HIS_CLOSE = "this is one of the owner's tabs; he closes it himself"
ONE_AT_A_TIME = 'close tabs with unsaved work one at a time'
NO_TAB = 'no tab has this number; list the tabs'
UPLOAD_RELOAD = (loss.MESSAGE + ' Reload the tab first (chrome_take with reload: true for a taken tab, '
                 'chrome_go with to: reload for a popup), then repeat the upload.')


def cut(text, limit):
    return text if len(text) <= limit else text[:limit] + MARK


def title(text):
    """A title as a list shows it: page text, quoted, cut at TITLE characters."""
    return quoted(cut(text if isinstance(text, str) else '', TITLE))


def address(url):
    """An address as a list shows it: the short form, cut at ADDRESS characters."""
    return cut(public_address(url, short=True), ADDRESS)


def every_tab(chrome):
    """The extension's all-tabs reply, checked: one row per tab, from this connection."""
    reply = chrome.bridge.call('tabs')
    rows = reply.get('tabs') if isinstance(reply, dict) else None
    if reply.get('session') != chrome.bridge.session or not isinstance(rows, list) or \
            not all(isinstance(row, dict) and type(row.get('tab')) is int and type(row.get('window')) is int and
                    isinstance(row.get('url'), str) for row in rows):
        raise Refused('transport_error', "The tab list didn't have the agreed shape; nothing of it is shown.")
    return reply['session'], rows


def marks(chrome, row, hosts):
    shown = [mark for mark, on in (('*', row.get('active')), ('pinned', row.get('pinned')),
                                   ('sound', row.get('audible') and not row.get('muted')), ('muted', row.get('muted')),
                                   ('asleep', row.get('asleep')), ('popup', row.get('popup'))) if on is True]
    try:
        allowed_url(row['url'], hosts)
    except Refused:
        return shown + ['no']
    if row['url'] != 'about:blank' and chrome.store.get('chrome:readonly:' + hostname(row['url']), False):
        shown.append('look')
    return shown


def line(row):
    whose = row.get('whose') if row.get('whose') in ('claude', 'his', 'taken') else 'his'
    return ' '.join([str(row['tab']), whose, *row['marks'], title(row.get('title')), address(row['url'])])


def render(rows):
    """One page of the list: a window's line when the window changes, Claude's group as a block within it."""
    out, window, grouped = [], None, False
    for row in rows:
        if row['window'] != window:
            window, grouped = row['window'], False
            out.append('window %d%s' % (window, ' (in front)' if row.get('front') is True else ''))
        if row.get('group') is True and not grouped:
            out.append('  group Claude')
        grouped = row.get('group') is True
        out.append(('    ' if grouped else '  ') + line(row))
    return '\n'.join(out)


def tabs(chrome, args):
    if set(args) - {'cursor'}:
        raise Refused('invalid_input', 'chrome_tabs takes only cursor.')
    mode = chrome.mode()
    if 'cursor' in args:
        seen, _, start = args['cursor'].partition('.') if isinstance(args['cursor'], str) else ('', '', '')
        record = chrome.references.seen(seen)
        if record['session'] != chrome.bridge.session:
            raise Refused('stale_reference', LIST_AGAIN)
        if not (start.isascii() and start.isdigit()) or not 0 < int(start) < len(record['rows']):
            raise Refused('invalid_input', "This cursor isn't one this tool returned; list the tabs again without it.")
        offset = int(start)
    else:
        session, rows = every_tab(chrome)
        chrome.references.connect(session)
        hosts = chrome.read_owner_hosts()
        for row in rows:
            row['marks'] = marks(chrome, row, hosts)
        # What `seen` binds: each tab's top document and full address; for a tab asleep, the address alone.
        record = {'session': session, 'rows': rows,
                  'tabs': {row['tab']: {'url': row['url'], 'document': None if row.get('asleep') is True else row.get('document')}
                           for row in rows}}
        seen, offset = chrome.references.listed(record), 0
    end = offset + PAGE_TABS
    return {'seen': seen, 'total': len(record['rows']),
            'cursor': '%s.%d' % (seen, end) if end < len(record['rows']) else None,
            'untrusted_content': {'list': render(record['rows'][offset:end])}, 'version_notice': mode['notice']}


def seen_entry(chrome, seen, tab):
    """What the list `seen` showed of `tab`: its full address and top document (None for a tab asleep)."""
    record = chrome.references.seen(seen)
    entry = record['tabs'].get(tab) if record['session'] == chrome.bridge.session else None
    if entry is None:
        raise Refused('stale_reference', LIST_AGAIN)
    return dict(entry)


def show(chrome, args):
    if set(args) != {'tab'} or type(args['tab']) is not int:
        raise Refused('invalid_input', 'chrome_show takes one tab.')
    chrome.mode()
    reply = chrome.bridge.call('show', tab=args['tab'])
    return {'shown': reply.get('shown'), 'window': reply.get('window')}


def close(chrome, args):
    tabs_ = args.get('tabs')
    if set(args) - {'tabs', 'discard_unsaved'} or not isinstance(tabs_, list) or not 1 <= len(tabs_) <= 20 or \
            not all(type(tab) is int for tab in tabs_) or len(set(tabs_)) != len(tabs_):
        raise Refused('invalid_input', 'Name 1 to 20 tabs, each once.')
    discard = args.get('discard_unsaved', False)
    if discard is True and len(tabs_) > 1:
        # One OK never covers a tab whose report he didn't see.
        raise Refused('invalid_input', ONE_AT_A_TIME)
    chrome.mode(acting=True)
    _, rows = every_tab(chrome)
    listed = {row['tab']: row for row in rows}
    closed, kept = [], []
    for tab in tabs_:
        row = listed.get(tab)
        shown = {'title': title(row.get('title')), 'url': address(row['url'])} if row else {}
        def keep(code, message, content=None):
            entry = {'tab': tab, 'code': code, 'message': message}
            if shown or content:
                entry['untrusted_content'] = {**shown, **(content or {})}
            kept.append(entry)
        if row is None:
            keep('stale_reference', NO_TAB)
        elif row.get('whose') == 'taken':
            keep('refused', TAKEN_CLOSE)
        elif row.get('whose') != 'claude':
            keep('refused', HIS_CLOSE)
        else:
            try:
                chrome.free('close_tab', tab=tab, discard_unsaved=discard is True)
            except Refused as exc:
                # A loss refusal's report is this tab's own (item 5b): its fixed message, the labels as data.
                keep(exc.code, str(exc), exc.untrusted_content)
                continue
            closed.append({'tab': tab, 'untrusted_content': shown})
    return {'closed': closed, 'kept': kept}


def library_entry(kind, item):
    """One entry as chrome_library shows it, its address short; the full address stays behind its reference."""
    item = item if isinstance(item, dict) else {}
    url = item.get('url') if isinstance(item.get('url'), str) and item.get('url') else None
    if kind == 'downloads':
        shown = {'file': visible(str(item.get('filename', ''))), 'state': visible(str(item.get('state', '')))}
    else:
        shown = {'title': visible(str(item.get('title', '')))}
        if kind == 'history' and isinstance(item.get('lastVisitTime'), (int, float)):
            shown['visited'] = item['lastVisitTime']
    if url is not None:
        shown['url'] = public_address(url, short=True)
    return shown, url


def library(chrome, args):
    if args.get('kind') not in KINDS or set(args) - {'kind', 'text', 'cursor', 'limit'}:
        raise Refused('invalid_input', 'kind is downloads, bookmarks or history; with it only text, cursor and limit.')
    mode = chrome.mode()
    reply = chrome.bridge.call(args['kind'], **{key: args[key] for key in ('text', 'cursor', 'limit') if key in args})
    if not isinstance(reply, dict) or reply.get('session') != chrome.bridge.session or not isinstance(reply.get('items'), list):
        raise Refused('transport_error', "The library list didn't have the agreed shape; nothing of it is shown.")
    references = chrome.references
    references.connect(reply['session'])
    # The snapshot the extension keeps for this list, named by its cursor once it has one.
    named = args.get('cursor') or reply.get('cursor')
    snapshot = references.snapshot(named.partition(':')[0] if isinstance(named, str) else None)
    items = []
    for item in reply['items']:
        shown, url = library_entry(args['kind'], item)
        if url is not None:
            shown['ref'] = references.entry(snapshot, url)
        items.append(shown)
    return {'kind': args['kind'], 'total': reply.get('total'), 'cursor': reply.get('cursor'),
            'untrusted_content': {'items': items}, 'version_notice': mode['notice']}
