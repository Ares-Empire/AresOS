"""The outline renderer against node lists (brief 28, item 2): the line format, the folds, the reads by reference."""
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.nodes import ROLES, STATES, View, options
from aresos_control.chrome.references import STALE, Stale
from aresos_control.chrome.view import (CONTROLS, FIELDS, READABLE, contains, header, present_line, render,
                                        typed_fields)
from aresos_control.common import Refused
from view_fixtures import F3_UNIQUE, SITE, f1, f2, f3, f4, frame, node, references, reply, view

MARK = "…"


def outline(nodes, table=None, **query):
    shown = nodes if isinstance(nodes, View) else view(nodes)
    return render(shown, table or references(), **query).text


def week():
    """The page of CONTROL.md section 6's example."""
    nodes = [node(1, "main"), node(2, "h1", 1, text=["Week 46"]),
             node(3, "p", 1, text=["Rooms change in ", 4, "."]),
             node(4, "link", 3, name="week 47", text=["week 47"], href=SITE + "/w47"),
             node(5, "button", 1, name="Next week", text=["Next week"]),
             node(6, "form", 1, name="Filter", method="get", action=SITE + "/timetable?week=46"),
             node(7, "combobox", 6, name="Semester", chosen="Winter 2026", option_count=14,
                  options=[{"label": "Winter 2026", "chosen": True}]),
             node(8, "text", 6, text=["Only my courses", 9]),
             node(9, "checkbox", 8, name="Only my courses", states=["checked"]),
             node(10, "button", 6, name="Apply", text=["Apply"]),
             node(11, "table", 1, name="Timetable")]
    for row in range(3):
        nodes.append(node(12 + 3 * row, "row", 11))
        nodes += [node(13 + 3 * row + column, "cell" if row else "columnheader", 12 + 3 * row, text=["c%d%d" % (row, column)])
                  for column in range(2)]
    nodes.append(node(30, "list", 1))
    for index in range(10):
        nodes += [node(31 + 2 * index, "listitem", 30),
                  node(32 + 2 * index, "link", 31 + 2 * index, name="Lecture %d" % index, text=["Lecture %d" % index],
                       href="https://other.example/l/%d" % index)]
    return nodes


WEEK = """main kqtvm1
  h1 "Week 46"
  p "Rooms change in " [link "week 47" kqtvm2] "."
  button "Next week" kqtvm3
  form "Filter" → GET fixture.example/timetable?… kqtvm4
    combobox "Semester" = "Winter 2026" (14 options) kqtvm5
    checkbox "Only my courses" checked kqtvm6
    button "Apply" kqtvm7
  table "Timetable" kqtvm8
    … 2 rows, 2 columns (75 characters)
  list kqtvm9
    link "Lecture 0" → other.example kqtvm10
    link "Lecture 1" → other.example kqtvm11
    link "Lecture 2" → other.example kqtvm12
    link "Lecture 3" → other.example kqtvm13
    link "Lecture 4" → other.example kqtvm14
    … 5 more (204 characters) kqtvm20"""


class Format(unittest.TestCase):
    def test_the_example_page_character_for_character(self):
        self.assertEqual(outline(week()), WEEK)

    def test_text_stands_once_in_its_order_and_wrappers_get_no_line(self):
        nodes = [node(1, "article", name="Post"),
                 node(2, "text", 1, text=["Intro ", 3, " middle ", 4, " tail ", 5, " end"]),
                 node(3, "link", 2, name="a link", text=["a link"], href=SITE + "/a"),
                 node(4, "list", 2), node(5, "button", 2, name="Go", text=["Go"]),
                 node(6, "listitem", 4, text=["one"]),
                 node(7, None, 1), node(8, "p", 7, text=["wrapped"]),          # no role, name or text: no line
                 node(9, "text", 1, text=["Email"]),                          # a label beside its field
                 node(10, "textbox", 1, name="Email", value="a@b.example"),
                 node(11, "button", 1, name="Close", text=["×"]),        # a name that isn't its text
                 node(12, "link", 1, name="Open file", text=[13, " ", 14], href=SITE + "/f"),
                 node(13, "text", 12, text=["Open"]), node(14, "text", 12, text=["file"]),
                 node(15, "text", 1, text=["Phone", 16]),                     # a label around its field
                 node(16, "textbox", 15, name="Phone", value="123"),
                 node(17, "img", 1, name="Logo"), node(18, "separator", 1), node(19, "h2", 1, text=["Sub"]),
                 node(20, "text", 1, text=["  \n "])]                         # nothing but space
        self.assertEqual(outline(nodes), """article "Post" kqtvm1
  text "Intro " [link "a link" kqtvm2] " middle "
    list kqtvm3
      listitem "one"
    text " tail " [button "Go" kqtvm4] " end"
  p "wrapped"
  textbox "Email" = "a@b.example" kqtvm5
  button "Close" "×" kqtvm6
  link "Open file" kqtvm7
  textbox "Phone" = "123" kqtvm8
  img "Logo"
  separator
  h2 "Sub\"""")

    def test_a_list_item_that_holds_one_element_alone_gives_its_place_to_it(self):
        # Decision 1 (section 7): no line for the item; its element moves up a level.
        nodes = [node(1, "list", name="L"),
                 node(2, "listitem", 1), node(3, "link", 2, name="Alone", href=SITE + "/a"),
                 node(4, "listitem", 1, text=["Own text"]),
                 node(5, "listitem", 1, text=["See ", 6]), node(6, "link", 5, name="this", href=SITE + "/b"),
                 node(7, "listitem", 1), node(8, "link", 7, name="One", href=SITE + "/c"),
                 node(9, "link", 7, name="Two", href=SITE + "/d"),
                 node(10, "listitem", 1, name="Named"), node(11, "link", 10, name="Inside", href=SITE + "/e"),
                 node(12, "listitem", 1, states=["current"]), node(13, "link", 12, name="Here", href=SITE + "/f"),
                 node(14, "listitem", 1), node(15, None, 14), node(16, "button", 15, name="Wrapped"),
                 node(17, "listitem", 1, text=[" \n "]), node(18, "list", 17), node(19, "listitem", 18),
                 node(20, "p", 19, text=["Nested"])]
        self.assertEqual(outline(nodes), """list "L" kqtvm1
  link "Alone" kqtvm2
  listitem "Own text"
  listitem "See " [link "this" kqtvm3]
  listitem
    link "One" kqtvm4
    link "Two" kqtvm5
  listitem "Named"
    link "Inside" kqtvm6
  listitem current
    link "Here" kqtvm7
  button "Wrapped" kqtvm8
  list kqtvm9
    p "Nested\"""")

    def test_elements_moved_up_from_list_items_fold_as_neighbours(self):
        nodes = [node(1, "list")]
        for index in range(9):
            nodes += [node(10 + 2 * index, "listitem", 1), node(11 + 2 * index, "link", 10 + 2 * index, name="L%d" % index, href=SITE)]
        table = references()
        self.assertEqual(outline(nodes, table), "\n".join(["list kqtvm1"] + ['  link "L%d" kqtvm%d' % (index, index + 2) for index in range(5)] +
                                                         ["  %s 4 more (68 characters) kqtvm11" % MARK]))
        self.assertEqual(outline(nodes, table, ref="kqtvm11"), "\n".join('link "L%d" kqtvm%d' % (index, index + 2) for index in range(5, 9)))
        self.assertEqual(outline(nodes, table, ref="kqtvm1", full=True).split("\n")[1:], ['  link "L%d" kqtvm%d' % (index, index + 2) for index in range(9)])

    def test_a_child_stands_inline_only_as_a_control_with_nothing_below_in_a_parent_with_text(self):
        nodes = [node(1, "p", text=["See ", 2, " and ", 3, " and ", 5]),
                 node(2, "link", 1, name="one", href=SITE + "/1"),
                 node(3, "h3", 1, text=["a heading"]),                     # no control: its own line
                 node(5, "radiogroup", 1, name="Pick"), node(6, "radio", 5, name="A"),   # a control with something below
                 node(7, "group"), node(8, "link", 7, name="alone", href=SITE + "/2")]  # the parent has no text
        self.assertEqual(outline(nodes), """p "See " [link "one" kqtvm1] " and "
  h3 "a heading"
  text " and "
  radiogroup "Pick" kqtvm2
    radio "A" kqtvm3
group
  link "alone" kqtvm4""")

    def test_every_role_of_the_list_is_shown_and_nothing_else_is_a_role(self):
        for role in sorted(ROLES - {"table", "grid"}):
            with self.subTest(role=role):
                self.assertRegex(outline([node(1, role, name="N")]), r'^%s "N"( \(not read\))?( kqtvm1)?$' % role)
                if role != "text":   # a role of the list has a line also without a name or text
                    self.assertRegex(outline([node(1, role)]), r'^%s( \(not read\))?( kqtvm1)?$' % role)
        self.assertEqual(outline([node(1, "text"), node(2, "text", 1, text=[" \n "]), node(3, "p", 2, text=["child"])]), 'p "child"')
        self.assertEqual(outline([node(1, "table", name="N")]), 'table "N" kqtvm1\n  %s 0 rows, 0 columns (16 characters)' % MARK)
        self.assertEqual(outline([node(1, "grid", name="N")]), 'grid "N" kqtvm1\n  %s 0 rows, 0 columns (15 characters)' % MARK)
        for role in ["generic", "rowgroup", "heading", "BUTTON", "link\nbutton", ""]:
            with self.subTest(role=role):
                self.assertEqual(outline([node(1, role, name="N")]), 'text "N"')
                self.assertEqual(outline([node(1, role, text=["own text"])]), 'text "own text"')
                self.assertEqual(outline([node(1, role), node(2, "p", 1, text=["child"])]), 'p "child"')

    def test_which_roles_carry_a_reference(self):
        for role in sorted(ROLES - {"table", "grid"}):
            with self.subTest(role=role):
                self.assertEqual(outline([node(1, role, name="N")]).endswith(" kqtvm1"), role in CONTROLS | READABLE)
        self.assertLessEqual(FIELDS, CONTROLS)
        self.assertEqual(READABLE & CONTROLS, set())

    def test_states_stand_in_one_order_after_the_value(self):
        self.assertEqual(outline([node(1, "textbox", name="N", value="v", states=list(reversed(STATES)))]),
                         'textbox "N" = "v" checked selected disabled required invalid expanded collapsed current readonly kqtvm1')

    def test_two_spaces_for_each_level(self):
        nodes = [node(index + 1, "group", index or None, name="g%d" % index) for index in range(5)]
        self.assertEqual(outline(nodes), "\n".join("  " * index + 'group "g%d"' % index for index in range(5)))

    def test_values(self):
        nodes = [node(1, "textbox", name="Full", value="text"), node(2, "textbox", name="Empty", value=""),
                 node(3, "slider", name="Volume", value="40"), node(4, "combobox", name="Size", chosen="M", value="m"),
                 node(5, "progressbar", name="Done", value="70"), node(6, "textbox", name="Lines", value="a\nb")]
        self.assertEqual(outline(nodes), """textbox "Full" = "text" kqtvm1
textbox "Empty" kqtvm2
slider "Volume" = "40" kqtvm3
combobox "Size" = "M" kqtvm4
progressbar "Done" = "70"
textbox "Lines" = "a\\u000ab" kqtvm5""")

    def test_where_a_link_a_form_and_a_frame_lead(self):
        nodes = [node(1, "link", name="same", href=SITE + "/a?x=1#top"),
                 node(2, "link", name="other", href="https://other.example/a?code=sesame"),
                 node(3, "link", name="plain", href="http://fixture.example/a"),
                 node(4, "link", name="port", href="https://fixture.example:8443/a"),
                 node(5, "link", name="mail", href="mailto:someone@fixture.example"),
                 node(6, "link", name="script", href='javascript:alert("x")'),
                 node(7, "link", name="broken", href="http://[::1"),
                 node(8, "link", name="no address"),
                 node(9, "form", name="Post", method="POST", action="https://owner:pw@other.example/send/reset/abc?token=sesame"),
                 node(10, "form", name="Odd", method="put\nbutton", action=SITE + "/x"),
                 node(11, "form", name="Bare")]
        self.assertEqual(outline(nodes), """link "same" kqtvm1
link "other" → other.example kqtvm2
link "plain" → http://fixture.example kqtvm3
link "port" → fixture.example:8443 kqtvm4
link "mail" → mailto:… kqtvm5
link "script" → javascript:… kqtvm6
link "broken" → … kqtvm7
link "no address" kqtvm8
form "Post" → POST other.example/send/reset/…?… kqtvm9
form "Odd" → fixture.example/x kqtvm10
form "Bare" kqtvm11""")

    def test_frames_stand_where_their_element_stands(self):
        raw = reply(frames=[
            frame([node(1, "main"), node(2, "frame", 1, name="Ad", frame=7), node(3, "p", 1, text=["after"]),
                   node(4, "frame", 1, name="Gone", frame=8)]),
            frame([node(1, "p", text=["inside"]), node(2, "link", name="Buy", href="https://other.example/buy")],
                  frame=7, document="d7", url="https://other.example/ad?session=sesame"),
            frame([node(1, "p", text=["lost"])], frame=9, document="d9", url=SITE + "/lost", title="Lost")])
        raw["frames"][0]["omitted"] = 80000
        table = references()
        self.assertEqual(outline(View(raw), table), """main kqtvm1
  frame "Ad" → other.example kqtvm2
    p "inside"
    link "Buy" → other.example kqtvm3
  p "after"
  frame "Gone" kqtvm4
frame "Lost"
  p "lost"
… 80,000 more elements, not read""")
        self.assertEqual(outline(View(raw), table, ref="kqtvm2"), """frame "Ad" → other.example kqtvm2
  address: other.example/ad?session=…
  p "inside"
  link "Buy" → other.example kqtvm3""")
        # The same element id in two frames is two elements.
        self.assertEqual(table.resolve("kqtvm3", 412).frame, 7)
        self.assertEqual(table.resolve("kqtvm2", 412).frame, 0)

    def test_a_dialog_gives_an_empty_outline_and_the_header_says_so(self):
        shown = View({"session": "s1", "tab": 3, "url": SITE + "/p?code=sesame", "title": "T\u202e\n",
                      "dialog": {"kind": "confirm", "text": 'Leave?\n"x"'}, "frames": []})
        self.assertEqual(render(shown, references()).text, "")
        self.assertEqual(header(shown), {"url": "fixture.example/p?code=" + MARK, "title": "T\\u202e\\u000a", "scroll": "0/0",
                                         "dialog": {"kind": "confirm", "text": 'Leave?\\u000a"x"'}})
        self.assertEqual(header(view([], url=SITE + "/long", title="Long")),
                         {"url": "fixture.example/long", "title": "Long", "scroll": "0/3200", "dialog": None})


class Unread(unittest.TestCase):
    """The forms of a field whose value isn't read, word for word, in every kind of read."""
    NODES = [node(1, "form", name="Sign in"),
             node(2, "password", 1, name="Password", unread=True),
             node(3, "password", 1, name="PIN"),                                   # the kind alone is enough
             node(4, "password", 1, name="Code", unread=True, filled=True),        # never more than the kind
             node(5, "textbox", 1, name="Draft", unread=True, filled=True),
             node(6, "textbox", 1, name="Nick", unread=True, filled=False),
             node(7, "textbox", 1, name="Recovery phrase", unread=True),           # kept out by its name
             node(8, "searchbox", 1, name="Find", unread=True, filled=True),
             node(9, "p", 1, text=["Type ", 10, " here"]),
             node(10, "password", 9, name="OTP", unread=True)]
    LINES = ['password "Password" (not read) kqtvm2', 'password "PIN" (not read) kqtvm3',
             'password "Code" (not read) kqtvm4', 'textbox "Draft" (filled, not read) kqtvm5',
             'textbox "Nick" (empty) kqtvm6', 'textbox "Recovery phrase" (not read) kqtvm7',
             'searchbox "Find" (filled, not read) kqtvm8']

    def test_the_outline_a_form_by_reference_and_full(self):
        table = references()
        first = outline(self.NODES, table)
        self.assertEqual(first, "\n".join(['form "Sign in" kqtvm1'] + ["  " + line for line in self.LINES] +
                                          ['  p "Type " [password "OTP" kqtvm9] " here"']))
        for text in (outline(self.NODES, table, ref="kqtvm1"), outline(self.NODES, table, full=True)):
            self.assertEqual(text, "\n".join(['form "Sign in" kqtvm1'] + ["  " + line for line in self.LINES] +
                                             ['  p "Type "', '    password "OTP" (not read) kqtvm9', '    text " here"']))
        for index, line in enumerate(self.LINES):
            self.assertEqual(outline(self.NODES, table, ref="kqtvm%d" % (index + 2)), line)
            self.assertEqual(outline(self.NODES, table, ref="kqtvm%d" % (index + 2), full=True), line)

    def test_only_what_the_asking_read_could_return_is_counted(self):
        self.assertEqual(typed_fields(view(self.NODES)), 2)   # Draft and Find; never a password kind, never an empty one
        self.assertEqual(typed_fields(view(week())), 0)
        self.assertEqual(typed_fields(View(f4())), 1)

    def test_find_never_looks_into_a_value_that_is_not_read(self):
        table = references()
        self.assertEqual(outline(self.NODES, table, find="not read"), "")
        self.assertEqual(outline(self.NODES, table, find="filled"), "")
        self.assertEqual(outline(self.NODES, table, find="nick"), 'textbox "Nick" (empty) kqtvm1 · in form "Sign in"')


class Folds(unittest.TestCase):
    def test_more_than_eight_neighbours_of_one_role_show_five(self):
        def paragraphs(count):
            return [node(1, "main")] + [node(index + 2, "p", 1, text=["Paragraph %d" % index]) for index in range(count)]
        self.assertEqual(outline(paragraphs(8)), "\n".join(["main kqtvm1"] + ['  p "Paragraph %d"' % index for index in range(8)]))
        table = references()
        self.assertEqual(outline(paragraphs(9), table),
                         "\n".join(["main kqtvm1"] + ['  p "Paragraph %d"' % index for index in range(5)] +
                                   ["  %s 4 more (63 characters) kqtvm2" % MARK]))
        hidden = "\n".join('p "Paragraph %d"' % index for index in range(5, 9))
        self.assertEqual(len(hidden), 63)
        self.assertEqual(outline(paragraphs(9), table, ref="kqtvm2"), hidden)             # exactly the neighbours left out
        self.assertEqual(outline(paragraphs(9), table, ref="kqtvm2", full=True), hidden)
        self.assertEqual(outline(paragraphs(11), table, ref="kqtvm2").count("\n"), 5)     # as they are then

    def test_a_run_is_children_in_a_row_with_the_same_role(self):
        nodes = [node(index + 1, "p" if index != 6 else "h2", text=["Item %d" % index]) for index in range(14)]
        self.assertNotIn(MARK, outline(nodes))                                         # 6 and 7 in a row: no fold
        nodes = [node(index + 1, "p" if index % 2 else "h2", text=["Item %d" % index]) for index in range(30)]
        self.assertNotIn(MARK, outline(nodes))
        nodes = [node(1, "p", text=["own ", 2, " text ", 3] + [index + 4 for index in range(9)])]
        nodes += [node(2, "h2", 1, text=["block"]), node(3, "h2", 1, text=["block"])]
        nodes += [node(index + 4, "link", 1, name="L%d" % index, href=SITE) for index in range(9)]
        self.assertNotIn("more", outline(nodes))                                       # links inside a sentence aren't lines

    def test_long_text_is_cut_at_200_characters_and_its_reference_reads_it_whole(self):
        self.assertEqual(outline([node(1, "p", text=["x" * 200])]), 'p "%s"' % ("x" * 200))
        table = references()
        self.assertEqual(outline([node(1, "p", text=["x" * 201])], table), 'p "%s"%s+1 kqtvm1' % ("x" * 200, MARK))
        self.assertEqual(outline([node(1, "p", text=["x" * 201])], table, ref="kqtvm1"), 'p "%s" kqtvm1' % ("x" * 201))
        self.assertEqual(outline([node(1, "textbox", name="n" * 50, value="v" * 5000)]),
                         'textbox "%s" = "%s"%s+4,850 kqtvm1' % ("n" * 50, "v" * 150, MARK))
        self.assertEqual(outline([node(1, "textbox", name="n" * 300, value="v" * 10)]),
                         'textbox "%s"%s+110 kqtvm1' % ("n" * 200, MARK))
        self.assertEqual(outline([node(1, "img", name="n" * 100000)]), 'img "%s"%s+99,800 kqtvm1' % ("n" * 200, MARK))

    def test_the_cut_counts_the_whole_line_and_leaves_later_inline_children_to_the_reference(self):
        nodes = [node(1, "p", text=["x" * 150, 2, "y" * 100, 3, "z" * 10]),
                 node(2, "link", 1, name="in", href=SITE + "/i"), node(3, "link", 1, name="late", href=SITE + "/l")]
        table = references()
        self.assertEqual(outline(nodes, table), 'p "%s" [link "in" kqtvm1] "%s"%s+66 kqtvm2' % ("x" * 150, "y" * 48, MARK))
        self.assertEqual(outline(nodes, table, ref="kqtvm2"),
                         'p "%s" [link "in" kqtvm1] "%s" [link "late" kqtvm3] "%s" kqtvm2' % ("x" * 150, "y" * 100, "z" * 10))
        # Own text between block children is cut the same way, and the element gets the reference.
        nodes = [node(1, "group", text=[2, "t" * 250]), node(2, "h2", 1, text=["Head"])]
        self.assertEqual(outline(nodes), 'group kqtvm1\n  h2 "Head"\n  text "%s"%s+50' % ("t" * 200, MARK))

    def test_a_table_folds_whole_and_says_its_size(self):
        table = references()
        text = render(View(f2()), table).text
        self.assertEqual(text, """h1 "Stock"
table "Stock" kqtvm1
  … 200 rows, 6 columns (20,129 characters)
table "Orders" kqtvm2
  … 3 rows, 3 columns (231 characters)""")
        self.assertEqual(len(render(View(f2()), table, ref="kqtvm1", full=True).text), 20129)
        self.assertEqual(len(render(View(f2()), table, ref="kqtvm2", full=True).text), 231)
        ragged = [node(1, "table"), node(2, "row", 1), node(3, "cell", 2, text=["a"]), node(4, "row", 1)]
        ragged += [node(5 + index, "cell", 4, text=["b"]) for index in range(4)]
        self.assertIn("2 rows, 4 columns", outline(ragged))                 # the widest row's cells

    def test_more_than_twelve_options_are_a_count(self):
        def field(count):
            return [node(1, "listbox", name="Pick", chosen="Option 3", option_count=count,
                         options=[{"label": "Option %d" % index, "chosen": index == 3} for index in range(count)])]
        self.assertEqual(outline(field(12)), "\n".join(['listbox "Pick" = "Option 3" kqtvm1'] +
                                                      ['  option "Option %d"%s' % (index, " selected" if index == 3 else "")
                                                       for index in range(12)]))
        self.assertEqual(outline(field(13)), 'listbox "Pick" = "Option 3" (13 options) kqtvm1')

    def test_a_form_shows_its_first_40_fields_and_counts_its_hidden_ones(self):
        def form(count):
            return ([node(1, "form", name="F", hidden=["a", "b", "c"])] +
                    [node(index + 2, "textbox", 1, name="Field %d" % index, value="v") for index in range(count)] +
                    [node(900, "button", 1, name="Send")])
        lines = outline(form(40)).split("\n")
        self.assertEqual((lines[0], len(lines)), ('form "F" (3 hidden) kqtvm1', 42))
        table = references()
        lines = outline(form(41), table).split("\n")
        self.assertEqual(lines[40:], ['  textbox "Field 39" = "v" kqtvm41', "  %s 1 more (32 characters) kqtvm43" % MARK,
                                      '  button "Send" kqtvm44'])
        self.assertEqual(outline(form(41), table, ref="kqtvm43"), 'textbox "Field 40" = "v" kqtvm42')
        self.assertEqual(len('textbox "Field 40" = "v" kqtvm42'), 32)

    def test_a_forms_fields_fold_by_the_forms_rule_alone(self):
        fields = [node(1, "form", name="F")] + [node(index + 2, "checkbox", 1, name="Box %d" % index) for index in range(30)]
        self.assertNotIn(MARK, outline(fields))                                # 30 boxes in a row, all shown
        nested = [node(1, "form", name="F"), node(2, "group", 1, name="G")]
        nested += [node(index + 3, "radio", 2, name="R%d" % index) for index in range(20)]
        self.assertNotIn(MARK, outline(nested))                                # also below a group of the form
        outside = [node(1, "group", name="G")] + [node(index + 2, "checkbox", 1, name="Box %d" % index) for index in range(30)]
        self.assertIn("%s 25 more" % MARK, outline(outside))                   # outside a form they are neighbours
        texts = [node(1, "form", name="F")] + [node(index + 2, "p", 1, text=["P%d" % index]) for index in range(9)]
        self.assertIn("%s 4 more" % MARK, outline(texts))                      # and other children of a form still fold

    def test_a_form_inside_a_form_counts_with_the_outer_one(self):
        nodes = [node(1, "form", name="Outer"), node(2, "form", 1, name="Inner")]
        nodes += [node(index + 3, "textbox", 2, name="In %d" % index) for index in range(45)]
        nodes += [node(index + 60, "textbox", 1, name="Out %d" % index) for index in range(5)]
        table = references()
        lines = outline(nodes, table).split("\n")
        self.assertEqual((len(lines), lines[1], lines[41]), (43, '  form "Inner" kqtvm2', '    textbox "In 39" kqtvm42'))
        self.assertRegex(lines[42], r"^    %s 10 more \(\d+ characters\) kqtvm\d+$" % MARK)
        self.assertEqual(outline(nodes, table, ref=lines[42].split()[-1]).count("textbox"), 10)
        self.assertEqual(outline(nodes, table, ref="kqtvm2").count("textbox"), 45)

    def test_the_order_of_folding(self):
        # (1) a table folds whole, so the 60 fields in it are neither shown nor folded as fields
        nodes = [node(1, "form", name="F"), node(2, "table", 1, name="T")]
        for row in range(60):
            nodes += [node(10 + 3 * row, "row", 2), node(11 + 3 * row, "cell", 10 + 3 * row),
                      node(12 + 3 * row, "textbox", 11 + 3 * row, name="Cell %d" % row, value="v")]
        nodes += [node(400 + index, "textbox", 1, name="After %d" % index, value="v") for index in range(3)]
        text = outline(nodes)
        self.assertNotIn("Cell", text)
        self.assertIn("%s 60 rows, 1 columns" % MARK, text)
        # (2) the fields count in the order of the page, wherever they stand: 40 are in the table, 20 more hide
        self.assertEqual(text.count("After"), 0)
        self.assertRegex(text, r"\n  %s 23 more \([0-9,]+ characters\) kqtvm\d+$" % MARK)
        # (5) what is hidden is not rendered: no reference of a hidden element stands in the outline
        table = references()
        first = render(View(f1()), table).text
        shown = set(re.findall(r"kqtvm\d+", first))
        self.assertEqual(len(shown), 5 + 1 + 1 + 40 + 1)
        self.assertEqual(first.count(MARK + "+"), 5)                           # only the five shown paragraphs are cut

    def test_every_folds_count_is_the_length_of_a_full_read_of_it(self):
        for fixture, expected in ((f1(), 2), (f3(), 1), (reply(week()), 1)):
            table = references()
            text = render(View(fixture), table).text
            folds = re.findall(r"%s [0-9,]+ more \(([0-9,]+) characters\) (kqtvm\d+)" % MARK, text)
            self.assertTrue(folds)
            for count, reference in folds:
                self.assertEqual(len(render(View(fixture), table, ref=reference, full=True).text), int(count.replace(",", "")))
            self.assertEqual(len(folds), expected)

    def test_a_fold_keeps_its_reference_and_is_stale_without_its_parent_or_first_child(self):
        nodes = [node(1, "main")] + [node(index + 2, "p", 1, text=["Paragraph %d" % index]) for index in range(9)]
        table = references()
        self.assertTrue(outline(nodes, table).endswith("kqtvm2"))
        grown = nodes + [node(20, "p", 1, text=["new"]), node(21, "h2", 1, text=["end"]), node(22, "p", 1, text=["later"])]
        self.assertRegex(outline(grown, table).split("\n")[-3], r"5 more \(71 characters\) kqtvm2$")
        self.assertEqual(outline(grown, table, ref="kqtvm2").split("\n")[-1], 'p "new"')
        with self.assertRaises(Stale) as caught:                                # the first hidden child is gone
            outline([item for item in nodes if item["id"] != 7], table, ref="kqtvm2")
        self.assertEqual((str(caught.exception), caught.exception.line), (STALE, None))
        moved = [dict(item) for item in nodes] + [node(30, "group", 1, name="G")]
        moved[6]["parent"] = None
        moved[6]["text"] = ['now "elsewhere"\n']
        with self.assertRaises(Stale) as caught:                                # it stands under another parent now
            outline(moved, table, ref="kqtvm2")
        self.assertEqual((str(caught.exception), caught.exception.line), (STALE, 'p "now \\"elsewhere\\"\\u000a"'))


class Detail(unittest.TestCase):
    def test_a_table_by_reference(self):
        table = references()
        render(View(f2()), table)
        lines = render(View(f2()), table, ref="kqtvm1").text.split("\n")
        self.assertEqual(lines[0], 'table "Stock" kqtvm1')
        self.assertEqual(lines[1], "columns: " + " | ".join('"Column%02dname"' % column for column in range(6)))
        self.assertEqual(lines[2], " | ".join('"r000c%dabcdef"' % column for column in range(6)))
        self.assertEqual(len(lines), 202)
        self.assertEqual({len(line) for line in lines[2:]}, {99})      # 6 cells of 12, 12 quotes, 5 separators of 3
        self.assertEqual(render(View(f2()), table, ref="kqtvm2").text, """table "Orders" kqtvm2
"Order 0" | [link "Open" kqtvm3] | [checkbox "Select order 0" kqtvm4]
"Order 1" | [link "Open" kqtvm5] | [checkbox "Select order 1" kqtvm6]
"Order 2" | [link "Open" kqtvm7] | [checkbox "Select order 2" kqtvm8]""")

    def test_a_cell_keeps_its_text_and_controls_in_order_and_an_empty_cell_stays(self):
        nodes = [node(1, "table", name="T"), node(2, "row", 1),
                 node(3, "rowheader", 2, text=["Head"]),
                 node(4, "cell", 2, text=["See ", 5, " now"]), node(5, "link", 4, name="this", href=SITE),
                 node(6, "cell", 2),
                 node(7, "cell", 2), node(8, "p", 7, text=["one"]), node(9, "p", 7, text=["two"]),
                 node(10, "cell", 2, text=["x" * 300]),
                 node(11, "text", 1, text=["A caption"])]
        table = references()
        whole = 'table "T" kqtvm1\n"Head" | "See" [link "this" kqtvm2] "now" | "" | "one" "two" | "%s"\ntext "A caption"' % ("x" * 300)
        self.assertEqual(outline(nodes, table), 'table "T" kqtvm1\n  %s 1 rows, 5 columns (%d characters)' % (MARK, len(whole)))
        self.assertEqual(outline(nodes, table, ref="kqtvm1"), whole)

    def test_a_list_by_reference_shows_every_item_and_folds_below(self):
        nodes = [node(1, "list", name="L")]
        for index in range(12):
            nodes += [node(10 + 20 * index, "listitem", 1, text=["Item %d" % index])]
        nodes += [node(11 + index, "p", 10, text=["Sub %d" % index]) for index in range(9)]
        table = references()
        self.assertIn("%s 7 more" % MARK, outline(nodes, table))
        lines = outline(nodes, table, ref="kqtvm1").split("\n")
        self.assertEqual(lines[0], 'list "L" kqtvm1')
        self.assertEqual([line for line in lines if line.startswith("  listitem")], ['  listitem "Item %d"' % index for index in range(12)])
        self.assertEqual(lines[1:8], ['  listitem "Item 0"'] + ['    p "Sub %d"' % index for index in range(5)] +
                         ["    %s 4 more (39 characters) kqtvm2" % MARK])

    def test_a_form_by_reference(self):
        table = references()
        render(View(f4()), table)
        lines = render(View(f4()), table, ref="kqtvm1").text.split("\n")
        self.assertEqual(lines[:2], ['form "Account" → POST fixture.example/account?step=2 kqtvm1',
                                     '  hidden: "csrf" | "step" | "cart"'])
        self.assertEqual(lines[2], '  textbox "Line 0" = "Value 0" kqtvm2')
        country = lines.index('  combobox "Country" = "Country 7" kqtvm18')
        self.assertEqual(lines[country + 1:country + 9], ['    option "Country %d"%s' % (index, " selected" if index == 7 else "")
                                                          for index in range(8)])
        self.assertEqual(lines[country + 51], "    %s 150 more" % MARK)          # 50 here, all by the field's own reference
        tail = lines[country + 52:]
        self.assertEqual(tail, ['  combobox "Size" = "M" kqtvm19', '    option "S"', '    option "M" selected', '    option "L"',
                                '  textbox "Email" = "not-an-address" required invalid kqtvm20',
                                '    error: "Enter a valid address"',
                                '  password "Password" (not read) kqtvm21', '  password "One-time code" (not read) kqtvm22',
                                '  textbox "Code" (filled, not read) kqtvm23', '  textbox "Nickname" (empty) kqtvm24',
                                '  spinbutton "Age" = "30" kqtvm25', '  slider "Volume" = "40" kqtvm26',
                                '  searchbox "Find" kqtvm27', '  switch "Dark" kqtvm28', '  button "Save" kqtvm29'])
        many = [node(1, "form", name="F")] + [node(index + 2, "textbox", 1, name="Field %d" % index, value="v") for index in range(60)]
        self.assertEqual(outline(many).count("textbox"), 40)
        table = references()
        outline(many, table)
        self.assertEqual(outline(many, table, ref="kqtvm1").count("textbox"), 60)   # every field

    def test_a_text_a_link_and_a_list_field_by_reference(self):
        nodes = [node(1, "p", text=["t" * 1000]),
                 node(2, "link", name="Docs", href="https://other.example/docs/reset/abc?page=2&code=sesame#top", title="Opens\nhere"),
                 node(3, "combobox", name="Country", chosen="B", option_count=60,
                      options=[{"label": "A", "value": "a"}, {"label": "B", "value": "B", "chosen": True}]),
                 node(4, "textbox", name="Mail", value="x", states=["invalid"], error='Not "valid"', title="Your address")]
        table = references()
        self.assertEqual(outline(nodes, table), """p "%s"…+800 kqtvm1
link "Docs" → other.example kqtvm2
combobox "Country" = "B" (60 options) kqtvm3
textbox "Mail" = "x" invalid kqtvm4""" % ("t" * 200))
        self.assertEqual(outline(nodes, table, ref="kqtvm1"), 'p "%s" kqtvm1' % ("t" * 1000))
        self.assertEqual(outline(nodes, table, ref="kqtvm2"), """link "Docs" → other.example kqtvm2
  address: other.example/docs/reset/…?page=2&code=…#top
  title: "Opens\\u000ahere\"""")
        every = options([{"label": "Option %d" % index, "value": "o%d" % index, "chosen": index == 1, "disabled": index == 2}
                         for index in range(60)])
        lines = outline(nodes, table, ref="kqtvm3", options=every).split("\n")
        self.assertEqual(lines[:4], ['combobox "Country" = "B" kqtvm3', '  option "Option 0" = "o0"',
                                     '  option "Option 1" = "o1" selected', '  option "Option 2" = "o2" disabled'])
        self.assertEqual(len(lines), 61)
        self.assertEqual(outline(nodes, table, ref="kqtvm3").split("\n"),
                         ['combobox "Country" = "B" kqtvm3', '  option "A" = "a"', '  option "B" selected', "  %s 58 more" % MARK])
        self.assertEqual(outline(nodes, table, ref="kqtvm4"), """textbox "Mail" = "x" invalid kqtvm4
  title: "Your address"
  error: "Not \\"valid\\"\"""")

    def test_full_folds_nothing_and_cuts_nothing(self):
        table = references()
        text = render(View(f1()), table, full=True).text
        lines = text.split("\n")
        self.assertEqual(lines[:120], ['p "%s"' % ("Paragraph %d " % index + "readable article text " * 20).strip() for index in range(120)])
        self.assertEqual(lines[120], "form → GET fixture.example/long kqtvm1")
        self.assertEqual(lines[121:], ['  textbox "Field %d" = "Synthetic value %d" kqtvm%d' % (index, index, index + 2) for index in range(80)])
        self.assertNotIn(MARK, text)
        week_full = outline(week(), full=True)
        self.assertEqual(week_full.count("Lecture"), 10)
        self.assertIn('  table "Timetable" kqtvm8\n  columns: "c00" | "c01"\n  "c10" | "c11"\n  "c20" | "c21"\n', week_full)
        self.assertIn('    combobox "Semester" = "Winter 2026" kqtvm5\n      option "Winter 2026" selected\n      %s 13 more\n' % MARK, week_full)
        self.assertNotIn("characters)", week_full)
        table = references()
        outline(week(), table)
        self.assertEqual(outline(week(), table, ref="kqtvm9", full=True).count("Lecture"), 10)   # the element and everything under it

    def test_the_present_line_of_an_element(self):
        shown = view([node(1, "main"), node(2, "textbox", 1, name='N"\n', value="v" * 300), node(3, None, 1)])
        self.assertEqual(present_line(shown, references(), shown.top.nodes[2]), 'textbox "N\\"\\u000a" = "%s"%s+103 kqtvm1' % ("v" * 197, MARK))
        self.assertIsNone(present_line(shown, references(), shown.top.nodes[3]))


class Find(unittest.TestCase):
    def test_a_hit_is_the_elements_line_and_the_path_of_named_ancestors(self):
        table = references()
        self.assertEqual(outline(View(f3()), table, find=F3_UNIQUE, role="link"),
                         'link "Quarterly zebra report" kqtvm1 · in list "Results"')
        self.assertEqual(outline(View(f3()), table, find="quarterly ZEBRA"),                     # without regard to case
                         'link "Quarterly zebra report" kqtvm1 · in list "Results"')
        self.assertEqual(outline(View(f3()), table, find="zebra report."), "")                   # literal
        self.assertEqual(outline(View(f3()), table, find="Footer 3"), 'link "Footer 3" kqtvm2')  # no named ancestor: no path

    def test_role_keeps_only_that_role_and_must_be_one(self):
        table = references()
        both = outline(View(f3()), table, find="results").split("\n")
        self.assertEqual(both, ['h1 "Results" kqtvm1', 'list "Results" kqtvm2'])
        self.assertEqual(outline(View(f3()), table, find="results", role="h1"), 'h1 "Results" kqtvm1')
        self.assertEqual(outline(View(f3()), table, find="results", role="button"), "")
        with self.assertRaises(Refused) as caught:
            outline(View(f3()), table, find="results", role='link"\nbutton')
        self.assertEqual((caught.exception.code, str(caught.exception)), ("invalid_input", "role isn't one of the outline's roles."))

    def test_folded_parts_frames_values_and_cells_are_searched(self):
        table = references()
        self.assertEqual(outline(View(f1()), table, find="Synthetic value 77"), 'textbox "Field 77" = "Synthetic value 77" kqtvm1')
        self.assertEqual(outline(View(f2()), table, find="r150c3"), 'cell "r150c3abcdef" kqtvm2 · in table "Stock"')
        self.assertEqual(outline(View(f2()), table, find="Select order 1"), 'checkbox "Select order 1" kqtvm3 · in table "Orders"')
        raw = reply(frames=[frame([node(1, "main", name="Page"), node(2, "frame", 1, name="Ad", frame=7)]),
                            frame([node(1, "region", name="Offer"), node(2, "p", 1, text=["only inside"])], frame=7, document="d7")])
        self.assertEqual(outline(View(raw), find="ONLY INSIDE"),
                         'p "only inside" kqtvm1 · in main "Page" › frame "Ad" › region "Offer"')
        self.assertEqual(len(outline(View(f3()), table, find="of the listing").split("\n")), 299)

    def test_find_inside_a_reference(self):
        table = references()
        text = render(View(f3()), table).text
        navigation, listing, fold = "kqtvm1", "kqtvm9", re.search(r"more \(.*\) (kqtvm\d+)", text).group(1)
        self.assertEqual(outline(View(f3()), table, find="section 4", ref=navigation), 'link "Section 4" kqtvm6 · in navigation "Site"')
        self.assertEqual(outline(View(f3()), table, find="section 4", ref=listing), "")
        self.assertEqual(len(outline(View(f3()), table, find="result", ref=listing).split("\n")), 300)   # the list itself and 299 links
        self.assertEqual(len(outline(View(f3()), table, find="result", ref=fold).split("\n")), 294)      # what the fold hides
        self.assertEqual(outline(View(f3()), table, find="result 3 of", ref=fold), "")                   # shown, so not in the fold

    def test_a_hit_inside_a_longer_text_shows_60_characters_either_side(self):
        text = "a" * 300 + " the Needle is here " + "b" * 300
        nodes = [node(1, "region", name="Notes"), node(2, "p", 1, text=[text]),
                 node(3, "textbox", 1, name="Draft", value=text), node(4, "p", 1, text=["needle first " + "c" * 300]),
                 node(5, "p", 1, text=["d" * 300 + " needle"])]
        self.assertEqual(outline(nodes, find="needle").split("\n"), [
            'p %s"%s the Needle is here %s"%s kqtvm1 · in region "Notes"' % (MARK, "a" * 55, "b" * 51, MARK),
            'textbox "Draft" = %s"%s the Needle is here %s"%s kqtvm2 · in region "Notes"' % (MARK, "a" * 55, "b" * 51, MARK),
            'p "needle first %s"%s kqtvm3 · in region "Notes"' % ("c" * 53, MARK),
            'p %s"%s needle" kqtvm4 · in region "Notes"' % (MARK, "d" * 59)])

    def test_the_path_has_at_most_80_characters(self):
        nodes = [node(1, "main", name="Top"), node(2, "region", 1, name="A region with quite a long name indeed"),
                 node(3, "article", 2, name="Article"), node(4, "group", 3, name="G"), node(5, "p", 4, text=["needle"])]
        path = 'main "Top" \u203a region "A region with quite a lo"%s \u203a article "Article" \u203a group "G"' % MARK
        self.assertEqual(len(path), 79)                          # a name is cut at 24 characters
        self.assertEqual(outline(nodes, find="needle"), 'p "needle" kqtvm1 \u00b7 in ' + path)
        nodes[0]["name"] = "Top 2"                               # 81 characters: the outermost gives way
        self.assertEqual(outline(nodes, find="needle"), 'p "needle" kqtvm1 \u00b7 in ' + path.replace('main "Top"', MARK))
        nodes[3]["name"] = "\n" * 24                             # 24 line breaks are 144 characters once escaped
        self.assertEqual(outline(nodes, find="needle"), 'p "needle" kqtvm1 \u00b7 in ' + MARK)

    def test_contains_is_what_find_would_find_and_issues_nothing(self):
        shown = View(f1())
        self.assertTrue(contains(shown, "synthetic VALUE 79"))        # a field's value, in a folded part
        self.assertTrue(contains(shown, "Paragraph 119 readable"))
        self.assertFalse(contains(shown, "Synthetic value 80"))
        hidden = view([node(1, "password", name="Password", unread=True), node(2, "textbox", name="Code", unread=True, filled=True)])
        self.assertTrue(contains(hidden, "code"))
        self.assertFalse(contains(hidden, "filled"))


if __name__ == "__main__":
    unittest.main()
