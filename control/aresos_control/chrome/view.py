"""The new Chrome read, on the service's side (brief 28, items 2 and 3).

The reader collects nodes (`nodes.py`); this module renders them: the outline
with its folds, a part by reference, `full`, `find`, and the pages of a result.
It needs no browser. The adapter calls, in this order:

    view = View(reply)                           the reader's reply, checked
    text = render(view, references, ...)         the whole text of one query
    reading = Reading(view, text, token, ...)    one tab's answer, at its cursor
    entries = fit([reading, ...], measure, references)   the `reads` of the result

Everything a page wrote reaches a line through `quoted` and nothing else, and
every address through `public_address`.
"""
import functools
import hashlib
import json
import re

from ..common import RESULT_LIMIT, Refused, canonical, visible
from .address import MARK, public_address, site_of
from .nodes import ROLES, STATES
from .references import Stale

CUT = 200               # characters of page text on one line
NEIGHBOURS = 8          # more children of one role in a row are folded
NEIGHBOURS_SHOWN = 5
FORM_FIELDS = 40        # a form shows this many fields
OPTIONS = 12            # more options than this are a count
FORM_OPTIONS = 50       # a form read by reference lists this many per field
HITS = 20               # hits of `find` on one page
CONTEXT = 60            # characters either side of a hit in a long text
PATH = 80               # characters of a hit's path
PATH_NAME = 24          # characters of one name in a path
SMALLEST_SHARE = 64     # bytes of outline below which a page isn't worth sending

FIELDS = frozenset("textbox searchbox combobox listbox checkbox radio switch slider spinbutton password".split())
CONTROLS = frozenset((
    "link button textbox searchbox combobox listbox option checkbox radio radiogroup switch "
    "slider spinbutton tab tablist tabpanel menu menubar menuitem menuitemcheckbox "
    "menuitemradio tree treeitem grid gridcell password").split())
# What can be read by itself and so carries a reference without being a control.
READABLE = frozenset((
    "form table list main navigation banner contentinfo complementary region search dialog "
    "alertdialog article frame").split())
TABLES = frozenset(("table", "grid"))
# A hit's path names these also without a name (section 7, decision 2).
PATH_ROLES = frozenset("main navigation banner contentinfo complementary form dialog table".split())
LISTS = frozenset(("combobox", "listbox"))
METHODS = frozenset(("get", "post", "dialog"))
# What the fingerprint keeps of the states: ticked, selected, expanded.
_STATE_FACTS = frozenset(("checked", "selected", "expanded", "collapsed"))


def quoted(text):
    """The one way anything a page wrote gets into a line.

    The base's `visible` escapes control and direction-changing characters,
    line breaks and the backslash; then the quote itself is escaped. So what
    stands between two unescaped quotes is page text, and nothing else is.
    """
    return '"' + visible(text).replace('"', '\\"') + '"'


def number(value):
    return format(value, ",")


def squash(text):
    return "".join(text.split())


def shown_role(node):
    """The role a line shows: one from the list, `text` for bare text, or none.

    `text` is the role of an element with a name or text of its own and no
    other role; without either it is nothing, also when the reader said `text`.
    """
    if node.role and node.role != "text":
        return node.role
    return "text" if node.name or any(type(part) is str and part.strip() for part in node.text) else None


def fingerprint(node):
    """What brief 28a compares before it acts, kept apart from the line Claude saw."""
    return {"role": shown_role(node), "name": node.name, "title": node.title, "href": node.href,
            "value": node.value, "unread": node.unread, "filled": node.filled, "chosen": node.chosen,
            "options": [(option.label, option.value, option.chosen, option.disabled) for option in node.options],
            "states": sorted(node.states & _STATE_FACTS)}


class Text:
    """The whole text of one query, and where each reference stands in it."""

    def __init__(self, text="", marks=()):
        self.text = text
        self.marks = list(marks)

    def shown(self, end):
        """What Claude has been given once the text up to `end` is returned."""
        return [(reference, line, facts) for offset, reference, line, facts in self.marks if offset <= end]


class _Line:
    def __init__(self, depth, start=""):
        self.text = "  " * depth + start
        self.marks = []
        self.inline = None  # where a part in brackets began, while it is written

    def add(self, text):
        self.text += text


class _Buffer:
    def __init__(self):
        self.lines = []
        self.marks = []
        self.size = 0

    def add(self, line):
        start = self.size + 1 if self.lines else 0
        self.marks += [(start + column, reference, shown, facts) for column, reference, shown, facts in line.marks]
        self.lines.append(line.text)
        self.size = start + len(line.text)

    def text(self):
        return "\n".join(self.lines)


class _FormFold:
    """The fields of a form after the 40th."""

    def __init__(self, form, hidden):
        self.form, self.hidden, self.written = form, hidden, False


class _Renderer:
    def __init__(self, view, references, full=False):
        self.view, self.references, self.full = view, references, full
        self.out = _Buffer()
        self.site = site_of(view.url)
        self._content, self._plains, self._names, self._parents = {}, {}, {}, None
        self._hidden = {}   # a form field beyond the 40th -> its fold
        self._forms = 0     # how many forms the element being written stands in
        self._detail = 0    # inside a form read by reference

    # --- the tree as the outline shows it ---------------------------------

    def _ordered(self, node):
        """An element's own runs of text and its children, in the order of the page.

        Runs that stand next to each other are one run: inline formatting is
        text, not structure (section 7, decision 6).
        """
        named = {part for part in node.text if type(part) is int}
        parts = []
        for part in node.text:
            if type(part) is not str:
                parts.append(node.document.nodes[part])
            elif parts and type(parts[-1]) is str:
                parts[-1] += part
            else:
                parts.append(part)
        return parts + [child for child in node.children if child.id not in named]

    def _plain(self, node):
        """Nothing but text, down to the last child."""
        if node.key not in self._plains:
            self._plains[node.key] = (node.role in (None, "text") and not node.name and node.value is None and
                                      not node.unread and all(self._plain(child) for child in node.children))
        return self._plains[node.key]

    def _flow(self, parts):
        """The plain text among these parts, in order."""
        return "".join(part if type(part) is str else self._flow(self._ordered(part))
                       for part in parts if type(part) is str or self._plain(part))

    def _field_names(self, node):
        """The names of the fields beside an element and directly inside it."""
        key = (node.document.frame, node.parent)
        if key not in self._names:
            beside = node.document.nodes[node.parent].children if node.parent else node.document.roots
            self._names[key] = {squash(other.name) for other in beside if other.role in FIELDS}
        return self._names[key] | {squash(child.name) for child in node.children if child.role in FIELDS}

    def _label(self, node):
        """A label whose text is its field's name: the field's line already says it."""
        if node.role not in (None, "text") or node.name:
            return False
        text = squash(self._flow(self._ordered(node)))
        return bool(text) and text in self._field_names(node)

    def _bare_item(self, node):
        """A list item that holds one element and nothing of its own: that element stands in its place.

        Its own text, a name, a value, a state or a second element keeps its line.
        """
        if node.role != "listitem" or node.name or node.value or node.states:
            return False
        content = self.content(node)
        return len(content) == 1 and type(content[0]) is not str

    def _arrange(self, parts, name=""):
        """What gets a line or stands in one, of these runs and elements.

        Text that the owner's name already says is left out, a label gives way
        to its field, an element without role, name or text gives its place to
        its children, and so does a list item that holds one element alone.
        """
        said = bool(name) and squash(self._flow(parts)) in squash(name)
        items = []
        for part in parts:
            if type(part) is str:
                if part.strip() and not said:
                    items.append(part)
            elif said and self._plain(part):
                continue
            elif self._label(part):
                items += [item for item in self.content(part) if type(item) is not str and not self._plain(item)]
            elif shown_role(part) is None or self._bare_item(part):
                items += self.content(part)
            else:
                items.append(part)
        return items

    def roots(self, document):
        return self._arrange(document.roots)

    def content(self, node):
        """What stands below an element: runs of its own text and elements, in order."""
        if node.key not in self._content:
            if node.role == "frame":
                child = self.view.frames.get(node.frame)
                self._content[node.key] = self.roots(child) if child else []
            else:
                self._content[node.key] = self._arrange(self._ordered(node), node.name)
        return self._content[node.key]

    def _lined(self, items, parent=None):
        """Every element with a line among these and below them, with the one it stands under."""
        for item in items:
            if type(item) is not str:
                yield item, parent
                yield from self._lined(self.content(item), item)

    def _unanchored(self):
        named = {node.frame for node in self.view.nodes() if node.frame is not None}
        return [document for document in self.view.documents[1:] if document.frame not in named]

    def parent(self, node):
        """The element whose line this element stands under, or None at the top."""
        if self._parents is None:
            self._parents = {}
            for document in self.view.documents[:1] + self._unanchored():
                for item, parent in self._lined(self.roots(document)):
                    self._parents[item.key] = parent
        return self._parents.get(node.key)

    # --- one line ---------------------------------------------------------

    def _reference(self, line, node, target=None):
        """End a line, or a part in brackets, with the element's reference (or a fold's)."""
        document = node.document
        reference = self.references.issue(self.view.tab, document.frame, document.document, document.reader,
                                          node.id if target is None else target)
        start = len(line.text) - len(line.text.lstrip()) if line.inline is None else line.inline
        line.add(" " + reference)
        # Where the reference ends, what Claude sees of the element, and its fingerprint.
        line.marks.append((len(line.text), reference, line.text[start:], None if target else fingerprint(node)))

    def _inline(self, line, node, lead=" "):
        """A link or control inside a sentence or a cell: [role "name" = "value" states reference].

        It carries what its line would before the reference: the value (or
        the form of a value that isn't read) and the states that are set.
        """
        role = shown_role(node)
        line.inline = len(line.text) + len(lead) + 1
        line.add(lead + "[" + role + (" " + quoted(node.name) if node.name else ""))
        value = self._value(node)
        if value:
            line.add(" = " + quoted(value))
        self._unread(line, node, role)
        self._states(line, node)
        self._reference(line, node)
        line.inline = None
        line.add("]")

    def _pieces(self, parts):
        return [("run", part) if type(part) is str else ("inline", part) for part in parts]

    def _fit(self, pieces, budget):
        """Cut a line's page text to the budget. Returns what stays and how many characters don't.

        An inline part counts with its name and its value, and is kept whole or left out whole.
        """
        kept, left_out, cut = [], 0, False
        for kind, item in pieces:
            text = item.name + (self._value(item) or "") if kind == "inline" else item
            if cut:
                left_out += len(text)  # nothing after the cut is shown
            elif budget is not None and len(text) > budget:
                cut = True
                if kind == "inline" or not budget:
                    left_out += len(text)
                else:
                    kept.append((kind, text[:budget]))
                    left_out += len(text) - budget
            else:
                kept.append((kind, item))
                if budget is not None:
                    budget -= len(text)
        return kept, left_out

    def _write(self, line, kept, left_out):
        for kind, item in kept:
            if kind == "inline":
                self._inline(line, item)
            else:
                line.add((" = " if kind == "value" else " ") + quoted(item))
        if left_out:
            line.add(MARK + "+" + number(left_out))

    def _value(self, node):
        """The value a line may show, or None. A field that isn't read never has one."""
        if node.unread or node.role == "password":
            return None
        return node.chosen if node.role in LISTS and node.chosen is not None else node.value

    def _target(self, node, role, public):
        if role == "link" and node.href is not None:
            site = site_of(node.href)
            if site is None:
                return public_address(node.href, short=True)
            return site if site != self.site else None
        if role == "frame":
            child = self.view.frames.get(node.frame)
            site = site_of(child.url) if child else None
            return site if site != self.site else None
        if role == "form":
            method = node.method.upper() if node.method and node.method.lower() in METHODS else None
            address = None if node.action is None else public_address(node.action, short=not public)
            return " ".join(part for part in (method, address) if part) or None
        return None

    def _unread(self, line, node, role):
        """What stands in place of a value that isn't read."""
        if role == "password" or node.unread and node.filled is None:
            line.add(" (not read)")
        elif node.unread:
            line.add(" (filled, not read)" if node.filled else " (empty)")

    def _states(self, line, node):
        for state in STATES:
            if state in node.states:
                line.add(" " + state)

    def _marks(self, line, node, role, rich):
        """What the tool itself says about an element, after its quoted parts."""
        self._unread(line, node, role)
        if role == "form" and node.hidden and not rich:
            line.add(" (%s hidden)" % number(len(node.hidden)))
        if node.option_count > OPTIONS and not rich:
            line.add(" (%s options)" % number(node.option_count))
        self._states(line, node)
        target = self._target(node, role, rich)
        if target:
            line.add(" → " + target)

    def _own_line(self, node, depth, parts, budget, referred=False, rich=False):
        """An element's line. `referred`: it carries a reference whatever its role."""
        role = shown_role(node)
        line = _Line(depth, role)
        pieces = ([("run", node.name)] if node.name else []) + self._pieces(parts)
        value = self._value(node)
        if value:
            pieces.append(("value", value))
        kept, left_out = self._fit(pieces, budget)
        self._write(line, kept, left_out)
        self._marks(line, node, role, rich)
        # A reference on what can be acted on, what can be read by itself, and what was cut.
        if left_out or referred or role in CONTROLS or role in READABLE:
            self._reference(line, node)
        self.out.add(line)

    def _plain_line(self, depth, text):
        self.out.add(_Line(depth, text))

    def _text_line(self, depth, parts, budget):
        """Own text of an element that stands between its children."""
        line = _Line(depth, "text")
        self._write(line, *self._fit(self._pieces(parts), budget))
        self.out.add(line)

    # --- an element and what stands below it -------------------------------

    def _stands_inline(self, node, rich):
        role = shown_role(node)
        return (role in CONTROLS and not self.content(node) and not node.options and
                not (rich and role in FIELDS))

    def _split(self, node, rich):
        """An element's first line, and the lines below it, in the order of the page."""
        items = []
        for item in self.content(node):
            fold = None if type(item) is str else self._hidden.get(item.key)
            if fold is None:
                items.append(item)
            elif fold.hidden[0] is item:
                items.append(fold)
        has_text = any(type(item) is str for item in items)
        first, blocks, segment, below = [], [], [], False
        for item in items:
            if type(item) is str or has_text and not isinstance(item, _FormFold) and self._stands_inline(item, rich):
                (segment if below else first).append(item)
                continue
            if segment:
                blocks.append(("text", segment))
                segment = []
            blocks.append(("fold" if isinstance(item, _FormFold) else "node", item))
            below = True
        if segment:
            blocks.append(("text", segment))
        return first, blocks

    def _measure(self, write):
        """The characters a read of a folded part returns with `full`."""
        inner = _Renderer(self.view, self.references, full=True)
        inner._content, inner._plains, inner._names = self._content, self._plains, self._names
        write(inner)
        return inner.out.size

    def _fold_line(self, depth, hidden, target):
        size = self._measure(lambda inner: [inner.element(node, 0) for node in hidden])
        line = _Line(depth, "%s %s more (%s characters)" % (MARK, number(len(hidden)), number(size)))
        self._reference(line, hidden[0], target)
        self.out.add(line)

    def _form_fold(self, fold, depth):
        fold.written = True
        self._fold_line(depth, fold.hidden, ("fields", fold.form.id, fold.hidden[0].id))

    def _children(self, blocks, depth, parent, fold, budget):
        """The lines below an element: its children, and runs of its own text between them."""
        index = 0
        while index < len(blocks):
            kind, item = blocks[index]
            if kind != "node":
                if kind == "text":
                    self._text_line(depth, item, budget)
                else:
                    self._form_fold(item, depth)
                index += 1
                continue
            role = shown_role(item)
            end = index
            while end < len(blocks) and blocks[end][0] == "node" and shown_role(blocks[end][1]) == role:
                end += 1
            run = [block[1] for block in blocks[index:end]]
            # A form's fields fold by the form's own rule and no other.
            folds = fold and len(run) > NEIGHBOURS and not (self._forms and role in FIELDS)
            for node in run[:NEIGHBOURS_SHOWN] if folds else run:
                self.element(node, depth)
            if folds:
                hidden = run[NEIGHBOURS_SHOWN:]
                self._fold_line(depth, hidden, ("fold", parent.key if parent else None, hidden[0].id, role))
            index = end

    def _fields(self, form):
        """A form's fields in the order of the page."""
        fields, waiting = [], list(reversed(form.children))
        while waiting:
            node = waiting.pop()
            if shown_role(node) in FIELDS:
                fields.append(node)
            waiting += reversed(node.children)
        return fields

    def _facts(self, node, depth, whole, rich):
        """What a read by reference or with `full` adds below an element's line."""
        role = shown_role(node)
        if whole:
            address = node.href
            if role == "frame" and node.frame in self.view.frames:
                address = self.view.frames[node.frame].url
            if address is not None:
                self._plain_line(depth, "address: " + public_address(address))
            if node.title:
                self._plain_line(depth, "title: " + quoted(node.title))
        if rich and node.error:
            self._plain_line(depth, "error: " + quoted(node.error))
        if rich and role == "form" and node.hidden:
            self._plain_line(depth, "hidden: " + " | ".join(quoted(name) for name in node.hidden))

    def _option_lines(self, node, depth, whole, rich):
        if not rich and node.option_count > OPTIONS:
            return  # the line gives the count
        shown = node.options if whole or self.full or not rich else node.options[:FORM_OPTIONS]
        for option in shown:
            line = _Line(depth, "option " + quoted(option.label))
            if whole and option.value != option.label:
                line.add(" = " + quoted(option.value))
            line.add((" selected" if option.chosen else "") + (" disabled" if option.disabled else ""))
            self.out.add(line)
        if node.option_count > len(shown):
            # More than the reader sent along: the field's own reference reads them all.
            self._plain_line(depth, "%s %s more" % (MARK, number(node.option_count - len(shown))))

    def element(self, node, depth, whole=False):
        """Write an element and what stands below it. `whole` is the start of a read by reference."""
        role = shown_role(node)
        if role in TABLES:
            if whole or self.full:
                self.table(node, depth)
            else:
                self._folded_table(node, depth)
            return
        rich = self.full or whole or self._detail > 0
        fold = None
        if role == "form":
            self._forms += 1
            fields = self._fields(node)
            if whole and not self.full:
                self._detail += 1
            elif not self.full and self._forms == 1 and len(fields) > FORM_FIELDS:  # the outermost form counts
                fold = _FormFold(node, fields[FORM_FIELDS:])
                self._hidden.update((field.key, fold) for field in fold.hidden)
        budget = None if whole or self.full else CUT
        first, blocks = self._split(node, rich)
        cut_below = budget is not None and any(
            kind == "text" and self._fit(self._pieces(parts), budget)[1] for kind, parts in blocks)
        self._own_line(node, depth, first, budget, cut_below or whole, rich)
        self._facts(node, depth + 1, whole, rich)
        self._option_lines(node, depth + 1, whole, rich)
        self._children(blocks, depth + 1, node, not (whole or self.full), budget)
        if role == "form":
            if fold:
                if not fold.written:
                    self._form_fold(fold, depth + 1)
                for field in fold.hidden:
                    del self._hidden[field.key]
            self._forms -= 1
            if whole and not self.full:
                self._detail -= 1

    # --- tables -----------------------------------------------------------

    def _rows(self, table):
        """The table's header cells, and its rows as lists of cells."""
        rows = [[cell for cell in self.content(item)] for item in self.content(table)
                if type(item) is not str and shown_role(item) == "row"]
        if rows and rows[0] and all(type(cell) is not str and shown_role(cell) == "columnheader" for cell in rows[0]):
            return rows[0], rows[1:]
        return None, rows

    def _folded_table(self, node, depth):
        header, rows = self._rows(node)
        size = self._measure(lambda inner: inner.table(node, 0))
        self._own_line(node, depth, [], CUT)
        widest = max((len(row) for row in rows + ([header] if header else [])), default=0)
        self._plain_line(depth + 1, "%s %s rows, %s columns (%s characters)" %
                         (MARK, number(len(rows)), number(widest), number(size)))

    def _cell(self, line, item):
        """A cell: its text in quotes and its controls in brackets, in the order of the page."""
        pieces = []

        def collect(part):
            if type(part) is str:
                pieces.append(part.strip())
            elif shown_role(part) in CONTROLS:
                pieces.append(part)
            else:
                if part.name:
                    pieces.append(part.name)
                for below in self.content(part):
                    collect(below)

        collect(item)
        for index, piece in enumerate(pieces):
            lead = " " if index else ""
            if type(piece) is str:
                line.add(lead + quoted(piece))
            else:
                self._inline(line, piece, lead)
        if not pieces:
            line.add('""')

    def _row(self, depth, cells, start=""):
        line = _Line(depth, start)
        for index, cell in enumerate(cells):
            if index:
                line.add(" | ")
            self._cell(line, cell)
        self.out.add(line)

    def table(self, node, depth):
        """A table read whole: its line, its columns, then a line for each row.

        Every cell stays in quotes. That is what keeps a cell from writing a line.
        """
        header, _ = self._rows(node)
        self._own_line(node, depth, [], None)
        first = True
        for item in self.content(node):
            if type(item) is str:
                self._text_line(depth, [item], None)
            elif shown_role(item) != "row":
                self.element(item, depth)
            elif first and header is not None:
                self._row(depth, header, "columns: ")
                first = False
            else:
                self._row(depth, self.content(item))
                first = False

    # --- the kinds of read -------------------------------------------------

    def page(self):
        """The outline of the tab."""
        top = self.view.top
        if top is None:
            return
        fold, budget = not self.full, None if self.full else CUT
        self._children([("node", item) for item in self.roots(top)], 0, None, fold, budget)
        for document in self._unanchored():
            # A frame the page's own nodes don't place: shown after the page.
            site = site_of(document.url)
            self._plain_line(0, "frame" + (" " + quoted(document.title) if document.title else "") +
                             (" → " + site if site and site != self.site else ""))
            self._children([("node", item) for item in self.roots(document)], 1, None, fold, budget)
        omitted = sum(document.omitted for document in self.view.documents)
        if omitted:
            self._plain_line(0, "%s %s more elements, not read" % (MARK, number(omitted)))

    def locate(self, reference):
        """The elements a reference stands for, and whether it is one element."""
        entry = self.references.resolve(reference, self.view.tab)
        document = self.view.frames.get(entry.frame)
        if document is None or document.document != entry.document or document.reader != entry.reader:
            raise Stale()
        if type(entry.target) is int:
            node = document.nodes.get(entry.target)
            if node is None or shown_role(node) is None:
                raise Stale()
            return [node], True
        first = document.nodes.get(entry.target[2])
        if first is None:
            raise Stale()
        if entry.target[0] == "fields":
            form = document.nodes.get(entry.target[1])
            fields = self._fields(form) if form is not None else []
            if first not in fields:
                raise Stale(present_line(self.view, self.references, first))
            return fields[fields.index(first):], False
        _, owner, _, role = entry.target
        parent = self.parent(first)
        if (parent.key if parent else None) != owner or shown_role(first) != role or first.key not in self._parents:
            raise Stale(present_line(self.view, self.references, first))
        beside = self.content(parent) if parent else self.roots(first.document)
        hidden = []
        for item in beside[beside.index(first):]:
            if type(item) is str or shown_role(item) != role:
                break
            hidden.append(item)
        return hidden, False

    def detail(self, nodes, single, options=None):
        """A read by reference: the element with one level unfolded, or what a fold hides."""
        if single:
            node = nodes[0]
            if options is not None:
                node.options, node.option_count = options, len(options)
            ancestor = node.document.nodes.get(node.parent)
            while ancestor is not None:  # a part of a form keeps the form's rule for its fields
                if shown_role(ancestor) == "form":
                    self._forms += 1
                ancestor = node.document.nodes.get(ancestor.parent)
            self.element(node, 0, whole=True)
        else:
            for node in nodes:
                self.element(node, 0)

    # --- find --------------------------------------------------------------

    def _joined(self, node):
        """An element's text as `find` and `until` read it (section 7, decision 6).

        Its runs, with the name of each part that stands inline among them in
        its place, so "See the timetable" is found across a link. A child with
        a line of its own ends one stretch of joined text and starts the next.
        """
        items = self.content(node)
        has_text = any(type(item) is str for item in items)
        stretches, stretch = [], ""
        for item in items:
            if type(item) is str:
                stretch += item
            elif has_text and self._stands_inline(item, False):
                stretch += item.name
            else:
                stretches.append(stretch)
                stretch = ""
        return [text for text in stretches + [stretch] if text]

    def _match(self, node, needle):
        """Where an element holds the words: in its name, its joined text or a value that may be read."""
        texts = [("name", node.name)] + [("run", text) for text in self._joined(node)] + [("value", self._value(node))]
        for kind, text in texts:
            if text and needle in text.casefold():
                return kind, text
        return None

    def matches(self, needle, role=None, within=None):
        needle = needle.casefold()
        if within is None:
            starts = [(item, parent) for document in self.view.documents[:1] + self._unanchored()
                      for item, parent in self._lined(self.roots(document))]
        else:
            starts = [pair for node in within for pair in [(node, self.parent(node))] + list(self._lined(self.content(node), node))]
        for node, _ in starts:
            if role is None or shown_role(node) == role:
                found = self._match(node, needle)
                if found:
                    yield node, found

    def _path(self, node):
        """The named elements and the landmarks a hit stands in, outermost first."""
        names = []
        parent = self.parent(node)
        while parent is not None:
            role = shown_role(parent)
            if parent.name:
                names.append(role + " " + quoted(parent.name[:PATH_NAME]) + (MARK if len(parent.name) > PATH_NAME else ""))
            elif role in PATH_ROLES:
                names.append(role)
            parent = self.parent(parent)
        shown = []
        for name in names:  # from the nearest outwards, while they fit
            if len(" › ".join([name] + shown)) > PATH:
                break
            shown.insert(0, name)
        if len(shown) < len(names):
            while shown and len(" › ".join([MARK] + shown)) > PATH:  # the mark counts too
                shown.pop(0)
            shown.insert(0, MARK)
        return " › ".join(shown)

    def hit(self, node, words, kind, text):
        """A hit: the element's line, or the words with their surroundings in a long text."""
        role = shown_role(node)
        line = _Line(0, role)
        parts = [item for item in self.content(node) if type(item) is str or self._stands_inline(item, False)]
        pieces = ([("run", node.name)] if node.name else []) + self._pieces(parts)
        if self._value(node):
            pieces.append(("value", self._value(node)))
        kept, left_out = self._fit(pieces, CUT)
        if left_out:
            found = re.search(re.escape(words), text, re.IGNORECASE)
            position = found.start() if found else 0
            start, end = max(0, position - CONTEXT), min(len(text), position + len(words) + CONTEXT)
            if kind != "name" and node.name:
                line.add(" " + quoted(node.name[:CONTEXT]) + (MARK if len(node.name) > CONTEXT else ""))
            line.add((" = " if kind == "value" else " ") + (MARK if start else "") + quoted(text[start:end]) +
                     (MARK if end < len(text) else ""))
        else:
            self._write(line, kept, 0)
        self._marks(line, node, role, False)
        self._reference(line, node)
        path = self._path(node)
        if path:
            line.add(" · in " + path)
        self.out.add(line)


def present_line(view, references, node):
    """An element's line as it is now, for a refusal's `untrusted_content`."""
    if shown_role(node) is None:
        return None
    renderer = _Renderer(view, references)
    renderer._own_line(node, 0, [] if shown_role(node) in TABLES else renderer._split(node, False)[0], CUT)
    return renderer.out.text()


def render(view, references, ref=None, full=False, find=None, role=None, options=None):
    """The whole text of one read of one tab, before it is cut into pages.

    `options` are all options of the list field `ref` names, from the reader's
    `options` command (`nodes.options`). Raises `Stale` for a reference that
    can't be read and `Refused` for a role that isn't one.
    """
    references.connect(view.session)
    if role is not None and role not in ROLES:
        raise Refused("invalid_input", "role isn't one of the outline's roles.")
    renderer = _Renderer(view, references, full)
    try:
        if view.dialog is not None:
            return Text()
        start = None if ref is None else renderer.locate(ref)
        if find is not None:
            for node, (kind, text) in renderer.matches(find, role, start and start[0]):
                renderer.hit(node, find, kind, text)
        elif start is None:
            renderer.page()
        else:
            renderer.detail(*start, options=options)
    except BaseException:
        references.trim(view.tab)  # a read that fails returns nothing, so nothing waits for the bound
        raise
    return Text(renderer.out.text(), renderer.out.marks)


def contains(view, words):
    """Whether the words are in the page as `find` would find them. Issues no reference."""
    return next(_Renderer(view, None).matches(words), None) is not None


def typed_fields(view):
    """How many fields the read shows as (filled, not read): what the asking read could return."""
    return sum(1 for node in view.nodes() if node.unread and node.filled and node.role != "password")


def header(view):
    """What a result says about the tab around its outline. All of it is page text."""
    top = view.top
    return {"url": public_address(view.url), "title": visible(view.title),
            "scroll": "%d/%d" % (top.scroll, top.height) if top else "0/0",
            "dialog": None if view.dialog is None else visible(view.dialog)}


# --- pages ------------------------------------------------------------------

# An escape of `quoted` is never divided: \\ and \" and \u with its digits.
_TOKEN = re.compile(r"\\u[0-9a-f]{4,6}|\\.|.", re.DOTALL)


def wire(text):
    """The bytes a text takes in the result as it is sent: ASCII JSON."""
    return len(json.dumps(text, ensure_ascii=True)) - 2


_token_wire = functools.lru_cache(maxsize=4096)(wire)


def cut(text, start, characters, size, lines=None):
    """Where the page that starts at `start` ends, and whether that is inside a line.

    A page ends at the last line end that fits `characters` and `size` bytes as
    sent. When not even one line fits, it ends inside the line, after at least
    one character, and the next page goes on there.
    """
    end, spent, count, stop = start, 0, 0, start
    while end < len(text) and (lines is None or count < lines):
        stop = text.find("\n", end) + 1 or len(text)
        cost = wire(text[end:stop])
        if stop - start > characters or spent + cost > size:
            break
        end, spent, count = stop, spent + cost, count + 1
    if end > start or start >= len(text):
        return end, False
    for token in _TOKEN.finditer(text, start, stop):
        cost = _token_wire(token.group())
        if end > start and (token.end() - start > characters or spent + cost > size):
            break
        end, spent = token.end(), spent + cost
    return end, True


def asked(ref=None, find=None, role=None, full=False):
    """The query a cursor belongs to."""
    return {"ref": ref, "find": find, "role": role, "full": bool(full)}


def _stamp(*parts):
    return hashlib.sha256(canonical(list(parts)).encode()).hexdigest()[:16]


def _state(text, position, token):
    # The state token says the page is the same; the text before the cursor
    # says the answer is the same, also where a reference was issued anew.
    return _stamp(token, hashlib.sha256(text[:position].encode("utf-8", "surrogatepass")).hexdigest())


def cursor_at(text, position, token, query):
    return "%d.%s.%s" % (position, _stamp(query), _state(text, position, token))


def start_from(cursor, text, token, query):
    """The position a cursor names, or the refusal: another query, or a page that changed."""
    if cursor is None:
        return 0
    parts = cursor.split(".") if isinstance(cursor, str) else []
    if len(parts) != 3 or not (parts[0].isascii() and parts[0].isdigit()) or len(parts[0]) > 9:
        raise Refused("invalid_input", "This cursor isn't one this tool returned; read again without it.")
    if parts[1] != _stamp(query):
        raise Refused("invalid_input", "This cursor belongs to another read; pass the same ref, find, role and full, or read again without it.")
    position = int(parts[0])
    if not 0 < position < len(text) or parts[2] != _state(text, position, token):
        raise Refused("stale_reference", "The page changed; read again without the cursor.")
    return position


class Reading:
    """One tab's answer before it is cut to a page."""

    def __init__(self, view, text, token, query, cursor=None, limit=6000, whose="claude", until_met=None):
        self.view, self.text, self.token, self.query = view, text, token, query
        self.limit, self.whose, self.until_met = limit, whose, until_met
        self.lines = HITS if query["find"] is not None else None
        self.start = start_from(cursor, text.text, token, query)

    def entry(self, end=None, mid_line=False):
        """This tab's entry in `reads`. Without `end`: the entry at its widest, to measure with."""
        text = self.text.text
        last = len(text) if end is None else end
        entry = {"tab": self.view.tab, "whose": self.whose,
                 "characters": last - (0 if end is None else self.start), "total": len(text),
                 "cursor": cursor_at(text, last, self.token, self.query) if end is None or end < len(text) else None,
                 "mid_line": mid_line, "typed_fields": typed_fields(self.view),
                 "untrusted_content": {**header(self.view), "outline": "" if end is None else text[self.start:end]}}
        if self.until_met is not None:
            entry["until_met"] = self.until_met
        return entry


class Failure:
    """A tab that couldn't be read: its error, and the element's present line where there is one."""

    def __init__(self, tab, error):
        self.tab, self.error = tab, error

    def entry(self):
        entry = {"tab": self.tab, "error": {"code": self.error.code, "message": str(self.error)}}
        if getattr(self.error, "line", None):
            entry["untrusted_content"] = {"line": self.error.line}
        return entry


def fit(parts, measure, references, limit=RESULT_LIMIT):
    """The `reads` of a result, each tab cut so that the whole result fits as it is sent.

    `parts` are the tabs in the order asked, each a `Reading` or a `Failure`.
    `measure(reads)` returns the bytes of the complete result with these
    entries: its header fields, the notice of pending operations and the
    version notice included. Each tab gets an equal share of what the fixed
    parts leave; a share that isn't used isn't passed on.
    """
    readings = [part for part in parts if isinstance(part, Reading)]
    share = (limit - measure([part.entry() for part in parts])) // max(len(readings), 1)
    if readings and share < SMALLEST_SHARE:
        raise Refused("result_too_large", "The notices of this result leave no room for a page; read and acknowledge them first.")
    entries = []
    for part in parts:
        if isinstance(part, Reading):
            end, mid_line = cut(part.text.text, part.start, part.limit, share, part.lines)
            entries.append(part.entry(end, mid_line))
            references.returned(part.view.tab, part.text.shown(end))
        else:
            entries.append(part.entry())
    return entries
