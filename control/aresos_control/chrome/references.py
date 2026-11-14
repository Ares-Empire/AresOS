"""Short references for what a read shows (brief 28, item 3).

A reference is five letters and a number, for example kqtvm5. The letters name
this run of the service; the number comes from one counter for all tabs. This
module issues references and resolves them for reads. Acting on one, and the
comparison with its fingerprint, are brief 28a's.
"""
from collections import OrderedDict
import secrets

from ..common import Refused

CONSONANTS = "bcdfghjklmnpqrstvwxyz"
LETTERS = 5
LIMIT = 5000
STALE = "This reference isn't valid for this tab any more; read the page again."


class Stale(Refused):
    """A refusal whose message is the tool's own sentence.

    `line` is the element's present outline line where it still exists. It is
    page text, already escaped, and belongs in `untrusted_content`.
    """

    def __init__(self, line=None):
        super().__init__("stale_reference", STALE)
        self.line = line


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

    def connect(self, session):
        """Name the extension connection a read came over. Another one empties the table."""
        if session != self.session:
            self._tabs.clear()
            self._references.clear()
            self.session = session

    def issue(self, tab, frame, document, reader, target):
        """The reference of this element: the one it has, or a new one."""
        entries = self._tabs.setdefault(tab, OrderedDict())
        identity = (frame, document, reader, target)
        entry = entries.get(identity)
        if entry is None:
            self.counter += 1  # never reset, so no string is issued twice
            entry = Entry("%s%d" % (self.letters, self.counter), tab, frame, document, reader, target)
            entries[identity] = entry
            self._references[entry.reference] = entry
        return entry.reference

    def resolve(self, reference, tab):
        """The entry of a reference this run issued for this tab, or the refusal."""
        entry = self._references.get(reference) if isinstance(reference, str) else None
        if entry is None or entry.tab != tab:
            raise Stale()
        return entry

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

    def close(self, tab):
        """Forget a closed tab's entries. The counter goes on."""
        for entry in self._tabs.pop(tab, {}).values():
            del self._references[entry.reference]
