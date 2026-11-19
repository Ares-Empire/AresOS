"""Short references for what a read shows (brief 28, item 3; brief 28a, item 2).

A reference is five letters and a number, for example kqtvm5. The letters name
this run of the service; the number comes from one counter for all tabs. This
module issues references and resolves them for reads and for actions. For an
action it also keeps the fingerprint Claude last saw of the element (the
reader's digest of what it means) and moves it only when a result shows the
element again or Claude's own step acted on it.
"""
from collections import OrderedDict
import secrets
import time

from ..common import Refused
from .nodes import FINGERPRINT

CONSONANTS = "bcdfghjklmnpqrstvwxyz"
LETTERS = 5
LIMIT = 5000
STALE = "This reference isn't valid for this tab any more; read the page again."
# Brief 28a, item 6: the tab lists a `seen` can name, and the library snapshots
# whose entries chrome_open can name. A list goes with the connection; a library
# entry as its snapshot does in the extension (brief 20's `collection`): five
# minutes after its last page was asked for, thirty after it was made.
LISTS, SNAPSHOTS, SNAPSHOT_IDLE, SNAPSHOT_LIFE = 8, 2, 300, 1800
LIST_AGAIN = 'list the tabs again'
LIBRARY_AGAIN = "This library entry's list has expired or was replaced; list it again."
FOLD = "This reference names a folded run of elements, not one element; read it by ref and act on one of them."


class Stale(Refused):
    """A refusal whose message is the tool's own sentence.

    `line` is the element's present outline line where it still exists. It is
    page text, already escaped, and belongs in `untrusted_content`. `shown`
    holds the references, lines and fingerprints that line carries; whoever
    gives Claude the line records them with `returned`, so it counts as shown.
    """

    def __init__(self, line=None, shown=()):
        super().__init__("stale_reference", STALE)
        self.line = line
        self.shown = list(shown)


class Entry:
    __slots__ = ("reference", "tab", "frame", "document", "reader", "target", "line", "fingerprint")

    def __init__(self, reference, tab, frame, document, reader, target):
        self.reference = reference
        self.tab, self.frame, self.document, self.reader = tab, frame, document, reader
        # The reader's element id, or what a fold stands for (a tuple).
        self.target = target
        # What Claude last saw of it. The fingerprint holds what the line may
        # have cut or left out (the whole value, the full address).
        self.line = None
        self.fingerprint = None


class References:
    """The reference table of one run of the service. It lives in memory only."""

    def __init__(self, source=None):
        source = source or secrets.SystemRandom()
        self.letters = "".join(source.choice(CONSONANTS) for _ in range(LETTERS))
        self.counter = 0
        self.session = None
        self._tabs = {}        # tab -> OrderedDict of identity -> Entry, least recently shown first
        self._references = {}  # reference -> Entry
        self._lists = OrderedDict()      # seen -> what a tab list showed, oldest first
        self._snapshots = OrderedDict()  # snapshot -> {'created', 'used', 'entries': {reference: address}}
        self._library = {}               # reference -> snapshot
        # Brief 28a, item 5: the native dialog a result last showed Claude for a tab ({kind, text}, or None
        # for a page without one). chrome_do's dialog step answers only that dialog.
        self._dialogs = {}

    def connect(self, session):
        """Name the extension connection a read came over. Another one empties the table."""
        if session != self.session:
            self._tabs.clear()
            self._references.clear()
            self._lists.clear()
            self._snapshots.clear()
            self._library.clear()
            self._dialogs.clear()
            self.session = session

    def _next(self):
        self.counter += 1  # never reset, so no string is issued twice
        return "%s%d" % (self.letters, self.counter)

    def listed(self, record):
        """Keep what a tab list showed and return its `seen`. The last LISTS lists are kept."""
        seen = self._next()
        self._lists[seen] = record
        while len(self._lists) > LISTS:
            self._lists.popitem(last=False)
        return seen

    def seen(self, seen):
        """What the list `seen` showed, or the refusal: a list this run doesn't know (dropped, or from before a restart)."""
        record = self._lists.get(seen) if isinstance(seen, str) else None
        if record is None:
            raise Refused("stale_reference", LIST_AGAIN)
        return record

    def snapshot(self, key=None):
        """A library snapshot: the one `key` names while it lives, or a new one. Returns its key."""
        now = time.monotonic()
        for name, held in list(self._snapshots.items()):
            if now - held["used"] >= SNAPSHOT_IDLE or now - held["created"] >= SNAPSHOT_LIFE:
                self._drop_snapshot(name)
        if key in self._snapshots:
            self._snapshots[key]["used"] = now
            self._snapshots.move_to_end(key)
            return key
        key = key or self._next()
        self._snapshots[key] = {"created": now, "used": now, "entries": {}}
        while len(self._snapshots) > SNAPSHOTS:
            self._drop_snapshot(next(iter(self._snapshots)))
        return key

    def _drop_snapshot(self, key):
        for reference in self._snapshots.pop(key)["entries"]:
            self._library.pop(reference, None)

    def entry(self, key, address):
        """A reference for a library entry's full address, kept while its snapshot lives."""
        reference = self._next()
        self._snapshots[key]["entries"][reference] = address
        self._library[reference] = key
        return reference

    def library(self, reference):
        """The full address behind a library reference, or None when the reference isn't one.

        Refused when it was one whose snapshot has expired since.
        """
        key = self._library.get(reference) if isinstance(reference, str) else None
        if key is None:
            return None
        held = self._snapshots.get(key)
        now = time.monotonic()
        if held is None or now - held["used"] >= SNAPSHOT_IDLE or now - held["created"] >= SNAPSHOT_LIFE:
            if held is not None:
                self._drop_snapshot(key)
            raise Refused("stale_reference", LIBRARY_AGAIN)
        return held["entries"][reference]

    def issue(self, tab, frame, document, reader, target):
        """The reference of this element: the one it has, or a new one."""
        entries = self._tabs.setdefault(tab, OrderedDict())
        identity = (frame, document, reader, target)
        entry = entries.get(identity)
        if entry is None:
            entry = Entry(self._next(), tab, frame, document, reader, target)
            entries[identity] = entry
            self._references[entry.reference] = entry
        return entry.reference

    def resolve(self, reference, tab):
        """The entry of a reference this run issued for this tab, or the refusal."""
        entry = self._references.get(reference) if isinstance(reference, str) else None
        if entry is None or entry.tab != tab:
            raise Stale()
        return entry

    def tab_of(self, reference):
        """The tab a reference was issued for, or the refusal: one this run didn't issue or has dropped."""
        entry = self._references.get(reference) if isinstance(reference, str) else None
        if entry is None:
            raise Stale()
        return entry.tab

    def acting(self, reference, tab, session):
        """The entry an action names, or the refusal (brief 28a, item 2).

        Refused as stale: a reference this run didn't issue or has dropped, one
        issued for another tab, or one issued under another extension
        connection than the present one. A fold's reference names a run of
        children, not an element, so no action accepts it. The document, the
        reader instance, the element and the fingerprint are the caller's to
        compare with fresh facts.
        """
        entry = self.resolve(reference, tab)
        if session is None or session != self.session:
            raise Stale()
        if type(entry.target) is not int:
            raise Refused("invalid_input", FOLD)
        return entry

    def acted(self, tab, reference, change):
        """Claude's own step acted on this element: its fingerprint moves to what the reader saw right after.

        `change` is the reader's `observe` report of the element acted on. It
        counts only for this reference's element: the same document, reader
        instance and element id. The line Claude last saw stays as it was.
        """
        entry = self._references.get(reference) if isinstance(reference, str) else None
        if entry is None or entry.tab != tab or type(entry.target) is not int or not isinstance(change, dict):
            return False
        fingerprint = change.get("fingerprint")
        if [change.get("document"), change.get("reader"), change.get("element")] != [entry.document, entry.reader, "e%d" % entry.target] \
                or not isinstance(fingerprint, str) or not FINGERPRINT.fullmatch(fingerprint):
            return False
        entry.fingerprint = fingerprint
        return True

    def returned(self, tab, shown):
        """Record what a result showed Claude, then bring the tab back to its bound.

        `shown` lists (reference, line, fingerprint). The bound is applied only
        here, after a read has rendered everything, so a reference is never
        dropped between being written into a result and being returned.
        """
        entries = self._tabs.get(tab, {})
        for reference, line, fingerprint in shown:
            entry = self._references.get(reference)
            if entry is not None and entry.tab == tab:
                entry.line, entry.fingerprint = line, fingerprint
                entries.move_to_end((entry.frame, entry.document, entry.reader, entry.target))
        self.trim(tab)

    def trim(self, tab):
        """Keep the newest LIMIT entries of a tab. A dropped string never comes back."""
        entries = self._tabs.get(tab, {})
        excess = len(entries) - LIMIT
        if excess <= 0:
            return
        # First what was only counted or sits on a page Claude hasn't been
        # given, oldest first; then what was shown longest ago.
        unseen = [identity for identity, entry in entries.items() if entry.line is None]
        for identity in (unseen + [identity for identity in entries if entries[identity].line is not None])[:excess]:
            del self._references[entries.pop(identity).reference]

    def dialog_shown(self, tab, dialog):
        """A result showed Claude this tab's native dialog (the read's `dialog`), or showed it without one."""
        self._dialogs[tab] = None if dialog is None else {"kind": dialog.get("kind"), "text": dialog.get("text", "")}

    def dialog(self, tab):
        """The dialog Claude last saw in this tab, or None."""
        return self._dialogs.get(tab)

    def close(self, tab):
        """Forget a closed tab's entries. The counter goes on."""
        self._dialogs.pop(tab, None)
        for entry in self._tabs.pop(tab, {}).values():
            del self._references[entry.reference]
