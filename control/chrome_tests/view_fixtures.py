"""Node lists for the view tests: what the reader's `outline` command will return.

F1, F2, F3 and F4 are brief 28's fixtures, written as the node lists their
pages give. The browser fixtures of the later steps must produce the same.
"""
import json
import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.nodes import View
from aresos_control.chrome.references import References
from aresos_control.common import canonical

SITE = "https://fixture.example"


def node(id, role=None, parent=None, **more):
    return {"id": id, "role": role, "parent": parent, **more}


def frame(nodes, frame=0, document="d0", reader="r0", url=SITE + "/", **more):
    return {"frame": frame, "document": document, "reader": reader, "watched": True, "url": url,
            "title": "", "scroll": 0, "height": 3200, "omitted": 0, "nodes": nodes, **more}


def reply(nodes=(), tab=412, session="s1", url=SITE + "/", title="Fixture", frames=None, **more):
    return {"session": session, "tab": tab, "url": url, "title": title, "dialog": None,
            "frames": frames if frames is not None else [frame(list(nodes), url=url)], **more}


def view(nodes=(), **more):
    return View(reply(nodes, **more))


def references(letters="kqtvm"):
    """A table with known letters, as if the system's random source had drawn them."""
    class Source:
        def __init__(self):
            self.letters = list(letters)

        def choice(self, _):
            return self.letters.pop(0)
    return References(Source())


def seeded(seed):
    return References(random.Random(seed))


def result(reads, notice=None, pending=None):
    """A read's result as the engine sends it."""
    return {"ok": True, "data": {"reads": reads, "version_notice": notice},
            "pending": pending if pending is not None else {"items": [], "total": 0, "cursor": None}}


def sent(reads, notice=None, pending=None):
    """The JSON text of a result as Claude receives it."""
    return canonical(result(reads, notice, pending))


def measure(notice=None, pending=None):
    return lambda reads: len(sent(reads, notice, pending).encode())


def f1():
    """Brief 20's long page: 120 paragraphs and a form of 80 labelled fields (ci/fixture.mjs, /long)."""
    nodes = [node(index + 1, "p", text=[("Paragraph %d " % index + "readable article text " * 20).strip()])
             for index in range(120)]
    nodes.append(node(121, "form", method="get", action=SITE + "/long"))
    for index in range(80):
        label, field = 122 + 2 * index, 123 + 2 * index
        nodes.append(node(label, "text", 121, text=["Field %d" % index, field]))
        nodes.append(node(field, "textbox", label, name="Field %d" % index, value="Synthetic value %d" % index))
    return reply(nodes, url=SITE + "/long", title="Long")


def f2():
    """A table of 200 rows and 6 columns with a header row, each cell 12 letters and digits; and a small table."""
    nodes = [node(1, "h1", text=["Stock"]), node(2, "table", name="Stock"), node(3, "row", 2)]
    nodes += [node(4 + column, "columnheader", 3, text=["Column%02dname" % column]) for column in range(6)]
    next_id = 10
    for row in range(200):
        nodes.append(node(next_id, "row", 2))
        nodes += [node(next_id + 1 + column, "cell", next_id, text=["r%03dc%dabcdef" % (row, column)])
                  for column in range(6)]
        next_id += 7
    nodes.append(node(next_id, "table", name="Orders"))
    for row in range(3):
        base = next_id + 1 + 6 * row
        nodes += [node(base, "row", next_id),
                  node(base + 1, "cell", base, text=["Order %d" % row]),
                  node(base + 2, "cell", base),
                  node(base + 3, "link", base + 2, name="Open", text=["Open"], href=SITE + "/order/%d" % row),
                  node(base + 4, "cell", base),
                  node(base + 5, "checkbox", base + 4, name="Select order %d" % row)]
    return reply(nodes, url=SITE + "/table", title="Table")


F3_UNIQUE = "Quarterly zebra report"


def f3():
    """A listing of 300 links in a list, with navigation and footer link groups; one name is unique."""
    nodes = [node(1, "navigation", name="Site")]
    nodes += [node(2 + index, "link", 1, name="Section %d" % index, text=["Section %d" % index],
                   href=SITE + "/section/%d" % index) for index in range(6)]
    nodes += [node(10, "main"), node(11, "h1", 10, text=["Results"]), node(12, "list", 10, name="Results")]
    for index in range(300):
        item, link = 20 + 2 * index, 21 + 2 * index
        name = F3_UNIQUE if index == 217 else "Result %d of the listing" % index
        nodes += [node(item, "listitem", 12), node(link, "link", item, name=name, text=[name], href=SITE + "/result/%d" % index)]
    nodes.append(node(700, "contentinfo"))
    nodes += [node(701 + index, "link", 700, name="Footer %d" % index, text=["Footer %d" % index],
                   href=SITE + "/footer/%d" % index) for index in range(5)]
    return reply(nodes, url=SITE + "/listing", title="Listing")


PASSWORD = "hunter2-fixture-password"


def f4():
    """A form of 25 fields: text, a date, checkboxes, radios, a list of 200 options, a required field
    with an error text, three hidden fields, and the kinds of password field."""
    nodes = [node(1, "form", name="Account", method="post", action=SITE + "/account?step=2",
                  hidden=["csrf", "step", "cart"])]
    for index in range(10):
        nodes.append(node(2 + index, "textbox", 1, name="Line %d" % index, value="Value %d" % index))
    nodes.append(node(12, "textbox", 1, name="Born", value="2001-02-03"))
    nodes += [node(13, "checkbox", 1, name="News", states=["checked"]), node(14, "checkbox", 1, name="Offers")]
    nodes.append(node(15, "radiogroup", 1, name="Plan"))
    nodes += [node(16, "radio", 15, name="Free", states=["checked"]), node(17, "radio", 15, name="Paid")]
    nodes.append(node(18, "combobox", 1, name="Country", chosen="Country 7", option_count=200,
                      options=[{"label": "Country %d" % index, "value": "c%d" % index, "chosen": index == 7}
                               for index in range(50)]))
    nodes.append(node(19, "combobox", 1, name="Size", chosen="M",
                      options=[{"label": label, "chosen": label == "M"} for label in ("S", "M", "L")]))
    nodes.append(node(20, "textbox", 1, name="Email", value="not-an-address", states=["required", "invalid"],
                      error="Enter a valid address"))
    # The password field itself, a field named like a credential, and two typed
    # fields whose history the reader doesn't know: one filled, one empty.
    nodes += [node(21, "password", 1, name="Password", unread=True),
              node(22, "password", 1, name="One-time code", unread=True),
              node(23, "textbox", 1, name="Code", unread=True, filled=True),
              node(24, "textbox", 1, name="Nickname", unread=True, filled=False),
              node(25, "spinbutton", 1, name="Age", value="30"),
              node(26, "slider", 1, name="Volume", value="40"),
              node(27, "searchbox", 1, name="Find", value=""),
              node(28, "switch", 1, name="Dark"),
              node(29, "button", 1, name="Save", text=["Save"])]
    return reply(nodes, url=SITE + "/form", title="Form")


def dump(value):
    return json.dumps(value, ensure_ascii=True)
