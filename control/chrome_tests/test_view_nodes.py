"""The node list of the reader's `outline` command, checked where it enters the service (brief 28, item 1)."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.nodes import DEPTH_LIMIT, NODE_LIMIT, ROLES, STATES, Malformed, View, options
from view_fixtures import f1, f2, f3, f4, frame, node, reply

SENTINEL = "SENTINEL-PAGE-TEXT"


def base():
    return reply([node(1, "main"),
                  node(2, "p", 1, text=["See the ", 3, " for week 46."]),
                  node(3, "link", 2, name="timetable", text=["timetable"], href="https://fixture.example/t"),
                  node(4, "form", 1, name="Filter", method="get", action="https://fixture.example/t", hidden=["csrf"]),
                  node(5, "combobox", 4, name="Semester", chosen="Winter", option_count=2,
                       options=[{"label": "Winter", "value": "w", "chosen": True}, {"label": "Summer", "value": "s"}]),
                  node(6, "password", 4, name="Password", unread=True),
                  node(7, "textbox", 4, name="Code", unread=True, filled=True),
                  node(8, "checkbox", 4, name="Mine", states=["checked", "required"])])


class Accepted(unittest.TestCase):
    def test_a_reply_becomes_a_tree_in_document_order(self):
        view = View(base())
        document = view.top
        self.assertEqual((view.session, view.tab, document.frame, document.document, document.reader), ("s1", 412, 0, "d0", "r0"))
        self.assertEqual([root.id for root in document.roots], [1])
        self.assertEqual([child.id for child in document.nodes[1].children], [2, 4])
        self.assertEqual([child.id for child in document.nodes[4].children], [5, 6, 7, 8])
        self.assertEqual(document.nodes[2].text, ["See the ", 3, " for week 46."])
        self.assertEqual(document.nodes[3].key, (0, 3))
        self.assertEqual((document.nodes[7].unread, document.nodes[7].filled), (True, True))
        self.assertEqual((document.nodes[6].unread, document.nodes[6].filled, document.nodes[6].value), (True, None, None))
        self.assertEqual(document.nodes[8].states, {"checked", "required"})
        self.assertEqual([(option.label, option.value, option.chosen, option.disabled) for option in document.nodes[5].options],
                         [("Winter", "w", True, False), ("Summer", "s", False, False)])

    def test_the_fixtures_are_valid_replies(self):
        for fixture in (f1, f2, f3, f4):
            self.assertGreater(len(list(View(fixture()).nodes())), 25)

    def test_a_role_that_is_not_on_the_list_is_no_role_and_nothing_of_it_is_kept(self):
        for role in ['button" kqtvm5', "\nbutton \"Send\" kqtvm5", "BUTTON", " button ", "x" * 10000, "generic", ""]:
            with self.subTest(role=role[:20]):
                view = View(reply([node(1, role, name="x")]))
                self.assertIsNone(view.top.nodes[1].role)

    def test_the_role_list_and_the_states_are_the_briefs(self):
        landmarks = "main navigation banner contentinfo complementary region search form"
        structure = ("article group list listitem table row cell columnheader rowheader figure img separator toolbar "
                     "dialog alertdialog alert status tooltip progressbar frame")
        text = "h1 h2 h3 h4 h5 h6 p text"
        controls = ("link button textbox searchbox combobox listbox option checkbox radio radiogroup switch slider "
                    "spinbutton tab tablist tabpanel menu menubar menuitem menuitemcheckbox menuitemradio tree treeitem "
                    "grid gridcell password")
        self.assertEqual(ROLES, set(" ".join([landmarks, structure, text, controls]).split()))
        self.assertEqual(len(ROLES), 8 + 20 + 8 + 26)
        self.assertEqual(STATES, tuple("checked selected disabled required invalid expanded collapsed current readonly".split()))

    def test_a_dialog_reply_has_no_frames(self):
        view = View({"session": "s1", "tab": 3, "url": "https://fixture.example/", "title": "x",
                     "dialog": {"kind": "confirm", "text": "Leave?"}, "frames": []})
        self.assertEqual(view.dialog, {"kind": "confirm", "text": "Leave?"})
        self.assertIsNone(view.top)

    def test_keys_of_the_reply_and_the_frame_that_the_view_does_not_use_are_ignored(self):
        raw = base()
        raw["group"] = 7
        raw["frames"][0]["browser_document"] = "x"
        self.assertEqual(View(raw).tab, 412)

    def test_all_options_of_one_field(self):
        self.assertEqual([option.label for option in options([{"label": "A"}, {"label": "B", "disabled": True}])], ["A", "B"])
        for broken in [None, [{"value": "x"}], [{"label": 5}], [{"label": "A", "more": 1}], [{"label": "A", "chosen": "yes"}], ["A"]]:
            with self.assertRaises(Malformed):
                options(broken)


class Refused(unittest.TestCase):
    """Each malformed reply is refused whole, and the message holds nothing a page wrote."""

    def refused(self, change, rule):
        raw = base()
        change(raw)
        with self.assertRaises(Malformed) as caught:
            View(raw)
        self.assertIn(rule, str(caught.exception))
        self.assertNotIn(SENTINEL, str(caught.exception))
        self.assertTrue(str(caught.exception).startswith("outline reply, "))

    def nodes(self, raw):
        return raw["frames"][0]["nodes"]

    def test_the_reply_and_its_frames(self):
        for broken in [None, [], "x", 5]:
            with self.assertRaises(Malformed):
                View(broken)
        self.refused(lambda raw: raw.pop("session"), "session")
        self.refused(lambda raw: raw.update(session=""), "session")
        self.refused(lambda raw: raw.update(tab="412"), "tab")
        self.refused(lambda raw: raw.update(tab=True), "tab")
        self.refused(lambda raw: raw.update(title=5), "title")
        self.refused(lambda raw: raw.update(dialog=SENTINEL), "dialog")
        self.refused(lambda raw: raw.update(dialog={"text": SENTINEL}), "dialog")
        self.refused(lambda raw: raw.update(frames={}), "frames is a list")
        self.refused(lambda raw: raw["frames"].append(SENTINEL), "a frame is an object")
        self.refused(lambda raw: raw["frames"][0].update(frame="0"), "frame is a number")
        self.refused(lambda raw: raw["frames"][0].update(document=""), "document")
        self.refused(lambda raw: raw["frames"][0].pop("reader"), "reader")
        self.refused(lambda raw: raw["frames"][0].update(url=5), "url")
        self.refused(lambda raw: raw["frames"][0].update(scroll=-1), "scroll")
        self.refused(lambda raw: raw["frames"][0].update(omitted="many"), "omitted")
        self.refused(lambda raw: raw["frames"][0].update(watched="yes"), "watched")
        self.refused(lambda raw: raw["frames"][0].update(nodes={}), "nodes is a list")
        self.refused(lambda raw: raw["frames"].append(frame([], frame=0, document="d9")), "a frame id is used twice")

    def test_a_node_and_its_place(self):
        self.refused(lambda raw: self.nodes(raw).append(SENTINEL), "a node is an object")
        self.refused(lambda raw: self.nodes(raw)[1].update({SENTINEL: 1}), "isn't part of the outline")
        self.refused(lambda raw: self.nodes(raw)[1].update(box=[0, 0, 1, 1]), "isn't part of the outline")
        for bad in [0, -1, "e5", True, 1.5, None]:
            self.refused(lambda raw: self.nodes(raw)[1].update(id=bad), "id is a positive number")
        self.refused(lambda raw: self.nodes(raw)[1].update(id=1), "an id is used twice")
        self.refused(lambda raw: self.nodes(raw)[1].update(parent=SENTINEL), "parent is a node's id or null")
        self.refused(lambda raw: self.nodes(raw)[1].update(parent=99), "parent is not an earlier node")
        self.refused(lambda raw: self.nodes(raw)[1].update(parent=2), "parent is not an earlier node")
        self.refused(lambda raw: self.nodes(raw)[1].update(parent=4), "parent is not an earlier node")
        self.refused(lambda raw: self.nodes(raw)[1].update(role=5), "role is a string or null")
        self.assertIn("frame 0, node 1", self.message(lambda raw: self.nodes(raw)[1].update(role=5)))

    def message(self, change):
        raw = base()
        change(raw)
        with self.assertRaises(Malformed) as caught:
            View(raw)
        return str(caught.exception)

    def test_what_a_node_holds(self):
        for key in ["name", "value", "error", "href", "method", "action", "chosen", "title"]:
            self.refused(lambda raw: self.nodes(raw)[0].update({key: [SENTINEL]}), key + " is a string")
        for bad in [SENTINEL, [{"child": 3}], [1.5], [True], [0]]:
            self.refused(lambda raw: self.nodes(raw)[1].update(text=bad), "text is a list of strings and child ids")
        self.refused(lambda raw: self.nodes(raw)[1].update(text=["a", 4]), "isn't its own child")
        self.refused(lambda raw: self.nodes(raw)[1].update(text=["a", 99]), "isn't its own child")
        self.refused(lambda raw: self.nodes(raw)[1].update(text=[3, "a", 3]), "names one twice")
        for bad in [SENTINEL, [SENTINEL], ["pressed"], ["checked", "checked"], [5]]:
            self.refused(lambda raw: self.nodes(raw)[7].update(states=bad), "states are distinct words")
        self.refused(lambda raw: self.nodes(raw)[3].update(hidden=SENTINEL), "hidden is a list of names")
        self.refused(lambda raw: self.nodes(raw)[3].update(hidden=[5]), "hidden is a list of names")
        self.refused(lambda raw: self.nodes(raw)[4].update(option_count=1), "option_count is smaller")
        self.refused(lambda raw: self.nodes(raw)[4].update(option_count="2"), "option_count is a number")
        self.refused(lambda raw: self.nodes(raw)[4].update(options=[{"label": "A", SENTINEL: 1}]), "an option holds")
        self.refused(lambda raw: self.nodes(raw)[4].update(options=[{"value": SENTINEL}]), "an option's label")
        self.refused(lambda raw: self.nodes(raw)[4].update(options=SENTINEL), "options are a list")
        self.refused(lambda raw: self.nodes(raw)[0].update(frame=3), "only a frame names a child frame")

    def test_a_field_that_is_not_read_holds_nothing_that_could_be_its_content(self):
        rule = "a field that isn't read holds no value, text or options"
        self.refused(lambda raw: self.nodes(raw)[5].update(value=SENTINEL), rule)             # role password
        self.refused(lambda raw: self.nodes(raw)[5].update(text=[SENTINEL]), rule)
        self.refused(lambda raw: (self.nodes(raw)[5].pop("unread"), self.nodes(raw)[5].update(value=SENTINEL)), rule)
        self.refused(lambda raw: self.nodes(raw)[6].update(value=SENTINEL), rule)             # unread textbox
        self.refused(lambda raw: self.nodes(raw)[6].update(chosen=SENTINEL), rule)
        self.refused(lambda raw: self.nodes(raw)[6].update(options=[{"label": SENTINEL}]), rule)
        self.refused(lambda raw: self.nodes(raw)[6].update(text=[SENTINEL]), rule)
        self.refused(lambda raw: self.nodes(raw).append(node(9, "text", 6, text=[SENTINEL])), "a field that isn't read has no children")
        self.refused(lambda raw: self.nodes(raw).append(node(9, "text", 7, text=[SENTINEL])), "a field that isn't read has no children")
        self.refused(lambda raw: self.nodes(raw)[7].update(filled=True), "filled belongs to an unread field")
        self.refused(lambda raw: self.nodes(raw)[6].update(unread=False), "unread is true or absent")
        self.refused(lambda raw: self.nodes(raw)[6].update(filled="yes"), "filled is true or false")

    def test_the_bounds_a_page_must_not_choose(self):
        many = reply([node(index + 1, "p", text=["x"]) for index in range(NODE_LIMIT + 1)])
        with self.assertRaises(Malformed) as caught:
            View(many)
        self.assertIn("more than 20000 nodes", str(caught.exception))
        View(reply([node(index + 1, "p", text=["x"]) for index in range(NODE_LIMIT)]))
        deep = reply([node(index + 1, "group", index or None) for index in range(DEPTH_LIMIT + 1)])
        with self.assertRaises(Malformed) as caught:
            View(deep)
        self.assertIn("deeper than 150 levels", str(caught.exception))
        View(reply([node(index + 1, "group", index or None) for index in range(DEPTH_LIMIT)]))

    def test_a_frame_stands_in_the_page_once_and_never_in_itself(self):
        def frames(*holders):
            return reply(frames=[frame([node(1, "frame", frame=holder)], frame=index, document="d%d" % index)
                                 for index, holder in enumerate(holders)])
        View(frames(1, 2, None))
        for holders, rule in [((1, 0), "the top frame is named"), ((1, 2, 1), "a frame is named twice"),
                              ((None, 2, 1), "a frame stands inside itself"), ((None, 1), "a frame stands inside itself")]:
            with self.assertRaises(Malformed) as caught:
                View(frames(*holders))
            self.assertIn(rule, str(caught.exception))
        nested = [frame([node(index + 1, "group", index or None) for index in range(99)] + [node(100, "frame", 99, frame=1)]),
                  frame([node(index + 1, "group", index or None) for index in range(60)], frame=1, document="d1")]
        with self.assertRaises(Malformed):
            View(reply(frames=copy.deepcopy(nested)))
        nested[1]["nodes"] = nested[1]["nodes"][:40]
        View(reply(frames=nested))


if __name__ == "__main__":
    unittest.main()
