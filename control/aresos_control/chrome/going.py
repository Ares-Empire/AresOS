"""Brief 28a, item 4: chrome_open and chrome_go, before item 8's step 1d offers them;
and item 6's chrome_take, whose explicit reload waits and reads the same way.

Both use brief 20's `open` and `navigate` commands through `Chrome.free`, with
their rules unchanged, then wait until the page has loaded, or until `until` is
met, or until the timeout, and return the page's outline as `chrome_read` gives
it, with references ready for the next call.

**Loaded**, defined once on brief 28's `page_state`: the navigation has
arrived and the top document is `ready` and quiet (its token unchanged for
QUIET seconds). Arrived means another top document than before the call, or,
for a navigation that may stay in its document (an address other than the
present one, back, forward), another address in the same document. A reload
and the present address need a new document. With `until` the call returns as
soon as the navigation has arrived and the text condition holds; `loaded` then
says whether the page was also ready and quiet.

**A link reference keeps its recognised meaning** (CROSS-5 finding 3): it is
resolved and fingerprint-checked, and a click on its fresh target is
classified with chrome_do's rules (`Chrome.classified`). If that click would
ask, opening refuses before any tab is created or any address is followed.
The check reads facts only; it never takes or reloads the source tab.

**Time:** every call answers by second CALL of its own clock. The wait ends
by second WAIT at the latest (`timeout_ms` counts from the start of the call),
and the outline read that ends the call answers by second READ.
"""
import hashlib
import time

from ..common import RESULT_LIMIT, Refused, canonical
from . import loss
from . import view as outline_view
from .deadline import NOT_READ, Deadline
from .references import Stale

CALL, WAIT, READ = 18.0, 15.0, 17.0
TIMEOUT_MS, TIMEOUT_MAX, MAX, POLL, QUIET = 8000, 15000, 4000, .1, .15
DIRECTIONS = ('back', 'forward', 'reload')
BLANK = 'about:blank'

TAKE_FIRST = "this is one of the owner's tabs; take it, or open its address in a Claude tab"
SEEN_NEEDED = 'list the tabs and pass seen'
NOT_LINK = "This reference isn't a link to a web address; act on it with chrome_do, or read the page again."
ASKS = ("Following this link would act on the page, so it asks first; nothing was opened. "
        "Click it with chrome_do, which prepares the question.")
UNCLASSIFIED = "This link's facts couldn't be classified; nothing was opened. Read the page again."
MAY_HAVE_RUN = ("The time ran out while Chrome was opening or moving the tab; it may have happened. "
                "Read the tab or list the tabs before trying again; never repeat it blindly.")


def query(verb, args):
    """The cross-field rules of chrome_open's and chrome_go's input, which the schema subset can't say."""
    if verb == 'take':
        if 'tab' not in args or set(args) - {'tab', 'seen', 'reload'}:
            raise Refused('invalid_input', 'chrome_take takes tab, and seen and reload.')
        if 'reload' in args and type(args['reload']) is not bool:
            raise Refused('invalid_input', 'reload is true or false.')
    elif verb == 'open':
        chosen = [key for key in ('url', 'tab', 'ref') if key in args]
        if chosen not in (['url'], ['tab'], ['ref'], ['tab', 'ref']):
            raise Refused('invalid_input', 'Give exactly one of url, tab and ref; tab may come with a link\'s ref.')
        if 'seen' in args and chosen != ['tab']:
            raise Refused('invalid_input', 'seen names the tab list a tab was chosen from; give it with tab alone.')
        if 'discard_unsaved' in args:
            raise Refused('invalid_input', 'A new tab holds nothing to lose; discard_unsaved is for chrome_go.')
    else:
        if 'tab' not in args or ('url' in args) == ('to' in args):
            raise Refused('invalid_input', 'Give tab and exactly one of url and to.')
        if 'to' in args and args['to'] not in DIRECTIONS:
            raise Refused('invalid_input', 'to is back, forward or reload.')
    timeout = args.get('timeout_ms', TIMEOUT_MS)
    if type(timeout) is not int or not 0 <= timeout <= TIMEOUT_MAX:
        raise Refused('invalid_input', 'timeout_ms is a whole number from 0 to 15000.')
    limit = args.get('max', MAX)
    if type(limit) is not int or not 1000 <= limit <= 40000:
        raise Refused('invalid_input', 'max is a whole number from 1000 to 40000.')
    until = args.get('until')
    if until is not None and not (type(until) is dict and len(until) == 1 and
                                  next(iter(until)) in ('text', 'gone') and isinstance(next(iter(until.values())), str)):
        raise Refused('invalid_input', 'until is {"text": ...} or {"gone": ...}.')


def address_digest(address):
    """The digest page_state gives of a tab's full address (background.js `sha256Hex`)."""
    return hashlib.sha256(address.encode('utf-8', 'surrogatepass')).hexdigest()


class Going:
    """One chrome_open or chrome_go call on the adapter `chrome`."""

    def __init__(self, chrome, verb, args):
        query(verb, args)
        self.chrome, self.bridge, self.verb, self.args = chrome, chrome.bridge, verb, args
        self.clock = Deadline()
        self.until = args.get('until')

    def run(self):
        with self.bridge.bounded(self.clock.at(READ)):
            self.mode = self.chrome.mode(acting=True)
            going = {'open': self.open, 'go': self.go, 'take': self.take}[self.verb]()
            if isinstance(going, dict):
                return going  # a take that keeps its page
            tab, arrived = going
            loaded, until_met = (True, None if self.until is None else False) if arrived is None else self.wait(tab, arrived)
        return self.result(tab, loaded, until_met)

    # --- going -------------------------------------------------------------

    def open(self):
        """Create the Claude tab and follow the address; nothing is created before every check passed."""
        if 'ref' in self.args:
            # A library entry's reference has no page control to classify: its address keeps the free-URL policy.
            address = self.chrome.references.library(self.args['ref'])
            if address is not None and 'tab' in self.args:
                raise Refused('invalid_input', "A library entry's reference belongs to no tab; give it alone.")
            if address is None:
                address = self.linked()
        elif 'tab' in self.args:
            address = self.tab_address()
        else:
            address = self.args['url']
        self.chrome.allowed_url(address)
        opened = self.effect('open', url=address)
        tab = opened['untrusted_content']['tab']
        if address == BLANK:
            return tab, None  # nothing to load
        # The new tab showed about:blank, which no reader reads: the navigation has
        # arrived once the tab shows another address (a redirect's included).
        blank = address_digest(BLANK)
        return tab, lambda state: state.get('address') not in (None, blank)

    def go(self):
        tab = self.args['tab']
        if self.bridge.call('tab_context', tab=tab).get('control') is None:
            raise Refused('take_first', TAKE_FIRST)
        if 'url' in self.args:
            self.chrome.allowed_url(self.args['url'])
        discard = self.args.get('discard_unsaved', False)
        before = self.bridge.call('page_state', tab=tab)
        reloaded = False
        # A taken tab that hasn't had its guarded reload gets it first, as a first input does,
        # with brief 20's report of what it would lose (item 5b's envelope).
        if self.bridge.call('outline', tab=tab).get('needs_reload') is True:
            reply = self.effect('prepare_control', tab=tab, discard_unsaved=discard)
            reloaded = (reply.get('untrusted_content') or {}).get('reloaded') is True
            if self.args.get('to') == 'reload' and reloaded:
                # The guarded reload is the reload asked for: arrival is its new document.
                return tab, arrival(before, False)
            if reloaded:
                before = self.bridge.call('page_state', tab=tab)
        if 'url' in self.args:
            self.effect('navigate', tab=tab, url=self.args['url'], discard_unsaved=discard)
            # The present address needs a new document; another one may stay in this document (a fragment).
            same_document = address_digest(self.args['url']) != before.get('address')
        else:
            self.effect('navigate', tab=tab, direction=self.args['to'], discard_unsaved=discard)
            same_document = self.args['to'] != 'reload'
        return tab, arrival(before, same_document)

    def take(self):
        """Brief 20's take_tab, with the list's `seen` checked by the extension first; the explicit reload has one home here."""
        tab = self.args['tab']
        arguments = {'tab': tab}
        if 'seen' in self.args:
            arguments['seen'] = self.chrome.seen_entry(self.args['seen'], tab)
        elif self.bridge.call('tab_context', tab=tab).get('control') is None:
            raise Refused('invalid_input', SEEN_NEEDED)
        taken = self.effect('take_tab', **arguments)['untrusted_content']
        notice = self.mode['notice']
        if taken.get('owner_dialog') is True:
            return {'tab': tab, 'owner_dialog': True, 'ask_owner': taken.get('ask_owner'), 'version_notice': notice}
        if not self.args.get('reload'):
            # The page is kept: whether its reload is still due, the typed fields the reader shows as (filled,
            # not read), and what the reload would lose, as its refusal would report it (item 5b's report).
            _, view = self.chrome.outline_view(tab)
            kept = {'tab': tab, 'reload_due': view.needs_reload, 'typed_fields': outline_view.typed_fields(view)}
            if view.needs_reload:
                kept['reload_due'], report = self.loss_report(tab)
                if kept['reload_due']:
                    kept['untrusted_content'] = {'loss': report}
            return {**kept, 'version_notice': notice}
        before = self.bridge.call('page_state', tab=tab)
        reply = self.effect('prepare_control', tab=tab, discard_unsaved=True)
        if (reply.get('untrusted_content') or {}).get('reloaded') is True:
            return tab, arrival(before, False)
        return tab, None  # no reload was due: the page is as it was

    def loss_report(self, tab):
        """Whether the guarded reload is still due, and what it would lose: the extension's discard check, read only.

        Page labels stay untrusted data (item 5b). A report that can't be had is
        `unavailable`, never an empty one: Claude can't tell then what reload: true discards.
        """
        try:
            reply = self.bridge.call('loss_report', tab=tab)
        except Refused:
            return True, {'unavailable': True}
        if not isinstance(reply, dict) or reply.get('reload_due') is False:
            return (False, None) if isinstance(reply, dict) else (True, {'unavailable': True})
        return True, loss.checked(reply.get('loss'))

    def effect(self, verb, **arguments):
        """Brief 20's command through `free`: committed before it runs, recorded after."""
        try:
            return self.chrome.free(verb, **arguments)
        except Refused as exc:
            if exc.code == 'expired':
                # Given up on with no answer: the command may have run.
                raise Refused('unknown', MAY_HAVE_RUN) from None
            raise

    def tab_address(self):
        """The full address behind `tab`: the list Claude chose it from, or a Claude tab's present address."""
        tab = self.args['tab']
        if 'seen' in self.args:
            # The address the list showed, wherever the tab has gone since; the tab itself isn't touched.
            return self.chrome.seen_entry(self.args['seen'], tab)['url']
        context = self.bridge.call('tab_context', tab=tab)
        if context.get('control') is None:
            raise Refused('invalid_input', SEEN_NEEDED)
        return context['url']

    def linked(self):
        """The full address behind a link reference, if a click on it would be free; refused before any open."""
        ref = self.args['ref']
        tab = self.args['tab'] if 'tab' in self.args else self.chrome.references.tab_of(ref)
        try:
            facts, frame, _ = self.chrome.acting(tab, ref)
        except Stale:
            # chrome_open gives the message alone (item 2); Claude reads the element again.
            self.chrome.references.trim(tab)
            raise Stale() from None
        target = frame.get('target')
        href = target.get('href') if isinstance(target, dict) else None
        if not isinstance(href, str) or not href or href.casefold().startswith('javascript:'):
            raise Refused('invalid_input', NOT_LINK)
        try:
            kind, _ = self.chrome.classified('click', {}, facts, frame, self.mode)
        except Refused:
            raise  # a rule refused it (an address that isn't allowed, a read-only site): nothing was opened
        except (KeyError, TypeError, AttributeError) as exc:
            raise Refused('refused', UNCLASSIFIED) from exc
        if kind:
            raise Refused('refused', ASKS)
        return href

    # --- waiting -----------------------------------------------------------

    def wait(self, tab, arrival):
        """Whether the page loaded, and whether `until` was met (None without until).

        `arrival(state)` says whether a page_state shows the navigation arrived.
        """
        end = min(self.clock.start + self.args.get('timeout_ms', TIMEOUT_MS) / 1000, self.clock.at(WAIT))
        until_met = False if self.until is not None else None
        arrived, token, since, checked = False, None, None, None
        while True:
            try:
                state = self.bridge.call('page_state', tab=tab)
            except Refused:
                return False, until_met  # the read that ends the call says why
            now = time.monotonic()
            if state.get('dialog'):
                return False, until_met
            if not arrived:
                arrived = arrival(state)
            if arrived:
                if state.get('token') != token:
                    token, since = state.get('token'), now
                quiet = state.get('ready') is True and token is not None and now - since >= QUIET
                if self.until is None:
                    if quiet:
                        return True, None
                elif token is not None and token != checked:
                    checked = token
                    try:
                        _, view = self.chrome.outline_view(tab)
                    except Refused:
                        return False, False
                    if self.chrome.until_met(view, self.until):
                        return quiet, True
            if now >= end:
                return False, until_met
            time.sleep(max(0, min(POLL, end - now)))

    # --- the result --------------------------------------------------------

    def result(self, tab, loaded, until_met):
        chrome, notice = self.chrome, self.mode['notice']
        query_ = outline_view.asked()
        try:
            with self.bridge.bounded(self.clock.at(READ)):
                try:
                    reading = chrome.outline_tab(tab, {}, query_, self.args.get('max', MAX), None)
                except Refused as exc:
                    if exc.code == 'expired':
                        raise Refused('not_read', NOT_READ) from exc
                    raise
                pending = chrome.engine.pending('chrome', resolve_checks=False)
            if notice:
                pending = {**pending, 'chrome_version_notice': notice}
            measure = lambda reads: len(canonical({'ok': True, 'data': shaped(reads[0], loaded, until_met, notice),
                                                   'pending': pending}).encode())
            from .adapter import PENDING_DRIFT
            [entry] = outline_view.fit([reading], measure, chrome.references, RESULT_LIMIT - PENDING_DRIFT)
        except Refused as exc:
            from .adapter import TAB_ERRORS
            if exc.code not in TAB_ERRORS:
                raise
            # The page was opened or moved; what can't be read of it is the tab's error, as in chrome_read.
            failure = outline_view.Failure(tab, exc).entry()
            return {'tab': tab, 'loaded': False, 'until_met': until_met, 'error': failure['error'],
                    **({'untrusted_content': failure['untrusted_content']} if 'untrusted_content' in failure else {}),
                    'version_notice': notice}
        finally:
            chrome.references.trim(tab)
        return shaped(entry, loaded, until_met, notice)


def arrival(before, same_document):
    """Arrived: another top document than `before`, or, where the navigation may stay in its document, another address."""
    def arrived(state):
        if state.get('document') is None:
            return False
        return state['document'] != before.get('document') or \
            same_document and state.get('address') != before.get('address')
    return arrived


def shaped(entry, loaded, until_met, notice):
    """A read's tab entry in the shape chrome_open and chrome_go return."""
    content = entry['untrusted_content']
    return {'tab': entry['tab'], 'loaded': loaded, 'until_met': until_met, 'characters': entry['characters'],
            'total': entry['total'], 'cursor': entry['cursor'],
            'untrusted_content': {key: content[key] for key in ('url', 'title', 'scroll', 'outline', 'dialog')},
            'version_notice': notice}
