"""The node list of the reader's `outline` command (brief 28, item 1).

This is where what a page wrote enters the service, so the reply is checked
before anything is rendered from it. A reply that doesn't have this shape is
refused whole. The messages name the place and the rule, never a value.

What the reader sends (section 7 of brief 28 decides 4 and 6):

- **Ids are positive integers**, in the reply and when the service sends one
  back (`options`, brief 28a's commands). A string can't be told from a run
  of text in `text`, so it is refused.
- **`text` is the element's own text in the order of the page:** a string for
  each run, and a child's id where that child stands between runs.
- **Inline formatting is text, not structure.** An element without a role of
  its own from the list (`b`, `strong`, `i`, `em`, `code`, `span`, `small`,
  `mark`, `abbr`, `sub`, `sup`, `time`, `u`, `s`, `q`, `cite`, `kbd` and the
  like) gets no node. Its text joins the run it stands in, at its place. What
  it holds that has a node (a link, a control) is a child of the nearest
  element that has a node, named in that element's `text` where it stands.
  Only links and controls stand between runs that way. So
  `<p>Order <b>confirmed</b> today, see <i>the <a>timetable</a></i>.</p>`
  is one `p` node with `"text": ["Order confirmed today, see the ", 12, "."]`
  and the link 12 as its child. The service joins runs that stand next to
  each other, so `["Order ", "confirmed", " today"]` reads the same; the
  reader may send either. White space is as the page shows it, collapsed
  across the formatting's edges.
"""

ROLES = frozenset((
    # landmarks
    "main navigation banner contentinfo complementary region search form "
    # structure
    "article group list listitem table row cell columnheader rowheader figure img separator "
    "toolbar dialog alertdialog alert status tooltip progressbar frame "
    # text
    "h1 h2 h3 h4 h5 h6 p text "
    # controls
    "link button textbox searchbox combobox listbox option checkbox radio radiogroup switch "
    "slider spinbutton tab tablist tabpanel menu menubar menuitem menuitemcheckbox "
    "menuitemradio tree treeitem grid gridcell password").split())
# In the order a line shows them.
STATES = ("checked", "selected", "disabled", "required", "invalid", "expanded", "collapsed",
          "current", "readonly")
NODE_LIMIT = 20000
# How deep elements may stand in each other, frames included. The renderer
# walks the tree by recursion, so a page must not choose its depth.
DEPTH_LIMIT = 150

_NODE_KEYS = frozenset((
    "id parent role name text value unread filled error states href method action hidden "
    "option_count chosen options title frame").split())
_OPTION_KEYS = frozenset(("label", "value", "chosen", "disabled"))


class Malformed(ValueError):
    """The reader's reply doesn't have the agreed shape."""


def _need(condition, where, rule):
    if not condition:
        raise Malformed("outline reply, %s: %s" % (where, rule))


def _is_int(value, least=0):
    return type(value) is int and value >= least


def _is_text(value):
    return type(value) is str


class Option:
    __slots__ = ("label", "value", "chosen", "disabled")

    def __init__(self, raw, where):
        _need(type(raw) is dict and set(raw) <= _OPTION_KEYS, where, "an option holds label, value, chosen and disabled only")
        _need(_is_text(raw.get("label")), where, "an option's label is a string")
        _need(_is_text(raw.get("value", "")), where, "an option's value is a string")
        _need(all(type(raw.get(key, False)) is bool for key in ("chosen", "disabled")), where, "chosen and disabled are true or false")
        self.label = raw["label"]
        self.value = raw.get("value", raw["label"])
        self.chosen = raw.get("chosen", False)
        self.disabled = raw.get("disabled", False)


def options(raw, where="options"):
    """The options of one list field, as the reader's `options` command returns them."""
    _need(type(raw) is list, where, "options are a list")
    return [Option(option, where) for option in raw]


class Node:
    """One element as the reader saw it. `children` and `document` are set by the frame."""
    __slots__ = ("id", "parent", "role", "name", "text", "value", "unread", "filled", "error",
                 "states", "href", "method", "action", "hidden", "option_count", "chosen",
                 "options", "title", "frame", "children", "document", "depth")

    def __init__(self, raw, where):
        _need(type(raw) is dict, where, "a node is an object")
        _need(set(raw) <= _NODE_KEYS, where, "a node holds a key that isn't part of the outline")
        _need(_is_int(raw.get("id"), 1), where, "id is a positive number")
        _need(raw.get("parent") is None or _is_int(raw["parent"], 1), where, "parent is a node's id or null")
        _need(raw.get("role") is None or _is_text(raw["role"]), where, "role is a string or null")
        for key in ("name", "value", "error", "href", "method", "action", "chosen", "title"):
            _need(raw.get(key) is None or _is_text(raw[key]), where, key + " is a string")
        text = raw.get("text", [])
        _need(type(text) is list and all(_is_text(part) or _is_int(part, 1) for part in text), where,
              "text is a list of strings and child ids")
        states = raw.get("states", [])
        _need(type(states) is list and all(_is_text(state) and state in STATES for state in states) and
              len(set(states)) == len(states), where, "states are distinct words of the state list")
        hidden = raw.get("hidden", [])
        _need(type(hidden) is list and all(_is_text(name) for name in hidden), where, "hidden is a list of names")
        _need(raw.get("unread") in (None, True), where, "unread is true or absent")
        _need(raw.get("filled") is None or type(raw["filled"]) is bool, where, "filled is true or false")
        _need(raw.get("option_count") is None or _is_int(raw["option_count"]), where, "option_count is a number")
        _need(raw.get("frame") is None or _is_int(raw["frame"]), where, "frame is a frame's id")

        self.id = raw["id"]
        self.parent = raw.get("parent")
        # A word that isn't on the list is no role: nothing else of it is kept.
        self.role = raw["role"] if raw.get("role") in ROLES else None
        self.name = raw.get("name") or ""
        self.text = text
        self.value = raw.get("value")
        self.unread = raw.get("unread") is True
        self.filled = raw.get("filled")
        self.error = raw.get("error") or ""
        self.states = frozenset(states)
        self.href = raw.get("href")
        self.method = raw.get("method")
        self.action = raw.get("action")
        self.hidden = hidden
        self.chosen = raw.get("chosen")
        self.options = options(raw.get("options", []), where)
        self.option_count = raw.get("option_count", len(self.options))
        self.title = raw.get("title") or ""
        self.frame = raw.get("frame")
        self.children = []
        self.document = None
        self.depth = 0

        _need(self.option_count >= len(self.options), where, "option_count is smaller than the options given")
        _need(self.frame is None or self.role == "frame", where, "only a frame names a child frame")
        _need(self.filled is None or self.unread, where, "filled belongs to an unread field")
        # The password rule, checked once more where the data arrives: a
        # field that is kept out carries nothing that could hold its content.
        if self.unread or self.role == "password":
            _need(self.value is None and self.chosen is None and not self.options and not self.text, where,
                  "a field that isn't read holds no value, text or options")

    @property
    def key(self):
        return (self.document.frame, self.id)


class Document:
    """One readable frame of a tab: its identity and its nodes."""

    def __init__(self, raw, where):
        _need(type(raw) is dict, where, "a frame is an object")
        _need(_is_int(raw.get("frame")), where, "frame is a number")
        for key in ("document", "reader"):
            _need(_is_text(raw.get(key)) and raw[key], where, key + " is a non-empty string")
        for key in ("url", "title"):
            _need(_is_text(raw.get(key, "")), where, key + " is a string")
        for key in ("scroll", "height", "omitted"):
            _need(_is_int(raw.get(key, 0)), where, key + " is a number")
        _need(type(raw.get("watched", False)) is bool, where, "watched is true or false")
        _need(type(raw.get("nodes")) is list, where, "nodes is a list")

        self.frame = raw["frame"]
        self.document = raw["document"]
        self.reader = raw["reader"]
        self.watched = raw.get("watched", False)
        self.url = raw.get("url", "")
        self.title = raw.get("title", "")
        self.scroll = raw.get("scroll", 0)
        self.height = raw.get("height", 0)
        self.omitted = raw.get("omitted", 0)
        self.nodes = {}
        self.roots = []
        for index, item in enumerate(raw["nodes"]):
            place = "%s, node %d" % (where, index)
            node = Node(item, place)
            node.document = self
            _need(node.id not in self.nodes, place, "an id is used twice")
            if node.parent is None:
                self.roots.append(node)
            else:
                # Document order: a parent stands before its children, so no loop can form.
                _need(node.parent in self.nodes, place, "parent is not an earlier node")
                parent = self.nodes[node.parent]
                _need(not parent.unread and parent.role != "password", place, "a field that isn't read has no children")
                parent.children.append(node)
                node.depth = parent.depth + 1
            self.nodes[node.id] = node
        for node in self.nodes.values():
            inline = [part for part in node.text if type(part) is int]
            _need(len(set(inline)) == len(inline) and
                  all(part in self.nodes and self.nodes[part].parent == node.id for part in inline),
                  "%s, node with id %d" % (where, node.id), "text names a node that isn't its own child, or names one twice")


class View:
    """One tab as the reader returned it."""

    def __init__(self, raw):
        _need(type(raw) is dict, "reply", "the reply is an object")
        _need(_is_text(raw.get("session")) and raw["session"], "reply", "session is a non-empty string")
        _need(_is_int(raw.get("tab")), "reply", "tab is a number")
        for key in ("url", "title"):
            _need(_is_text(raw.get(key, "")), "reply", key + " is a string")
        dialog = raw.get("dialog")
        _need(dialog is None or type(dialog) is dict and _is_text(dialog.get("kind")) and _is_text(dialog.get("text", "")),
              "reply", "dialog is null or holds a kind and a text")
        _need(type(raw.get("frames")) is list, "reply", "frames is a list")

        self.session = raw["session"]
        self.tab = raw["tab"]
        self.url = raw.get("url", "")
        self.title = raw.get("title", "")
        self.dialog = None if dialog is None else {"kind": dialog["kind"], "text": dialog.get("text", "")}
        self.documents = [Document(frame, "frame %d" % index) for index, frame in enumerate(raw["frames"])]
        self.frames = {}
        for document in self.documents:
            _need(document.frame not in self.frames, "frames", "a frame id is used twice")
            self.frames[document.frame] = document
        _need(sum(len(document.nodes) for document in self.documents) <= NODE_LIMIT, "frames",
              "more than %d nodes" % NODE_LIMIT)
        # A frame stands in the page once, under the frame element that names
        # it, and never in itself.
        holders = {}
        for node in self.nodes():
            if node.frame is not None:
                _need(node.frame not in holders and node.frame != self.documents[0].frame, "frames",
                      "a frame is named twice, or the top frame is named")
                holders[node.frame] = node
        for document in self.documents:
            depth, holder, seen = 0, holders.get(document.frame), {document.frame}
            while holder is not None:
                _need(holder.document.frame not in seen, "frames", "a frame stands inside itself")
                seen.add(holder.document.frame)
                depth += holder.depth + 1
                holder = holders.get(holder.document.frame)
            _need(depth + max((node.depth for node in document.nodes.values()), default=0) < DEPTH_LIMIT, "frames",
                  "elements stand deeper than %d levels" % DEPTH_LIMIT)

    @property
    def top(self):
        """The top document; the reader lists it first."""
        return self.documents[0] if self.documents else None

    def nodes(self):
        for document in self.documents:
            yield from document.nodes.values()
