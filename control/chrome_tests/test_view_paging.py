"""The pages of a read (brief 28, item 2): `max`, cursors, the line that is too long, and 48 KiB as sent."""
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.nodes import View
from aresos_control.chrome.references import Stale
from aresos_control.chrome.view import (HITS, Failure, Reading, Text, asked, cursor_at, cut, fit, render, start_from,
                                        wire)
from aresos_control.common import RESULT_LIMIT, Refused
from view_fixtures import f1, f3, measure, node, references, sent, view

MARK = "…"
NOTICE = "Chrome 158.0.1.0 is newer than the version this tool was checked with; it works in its careful mode."
PENDING = {"items": [{"operation_id": "chrome-7f3a", "app": "chrome", "state": "reserved", "expires": 1700000000,
                      "untrusted_content": {"description": "Send the form \"Order\" to fixture.example"}}],
           "total": 1, "cursor": None,
           "notices": [{"operation_id": "chrome-51c0", "app": "chrome", "state": "unknown",
                        "untrusted_content": {"warning": "A click was dispatched and its outcome is not known."}}]}
ESCAPE = re.compile(r"\\u[0-9a-f]{4}|\\.|.", re.DOTALL)


def pages(shown, table=None, limit=6000, measured=None, tabs=1, **query):
    """Read one query to its end, as the adapter will: the same call again with each cursor."""
    table = table or references()
    cursor, entries = None, []
    while True:
        reading = Reading(shown, render(shown, table, **query), "token", asked(**query), cursor, limit)
        entry = fit([reading], measured or measure(), table)[0]
        entries.append(entry)
        cursor = entry["cursor"]
        if cursor is None:
            return entries
        assert len(entries) < 2000, "paging doesn't end"


def outlines(entries):
    return [entry["untrusted_content"]["outline"] for entry in entries]


class Cut(unittest.TestCase):
    TEXT = "\n".join("line %d" % index for index in range(10))  # 10 lines of 6 characters

    def test_a_page_ends_at_the_last_line_end_that_fits(self):
        self.assertEqual(cut(self.TEXT, 0, 1000, 10 ** 6), (len(self.TEXT), False))
        self.assertEqual(cut(self.TEXT, 0, 20, 10 ** 6), (14, False))       # two lines with their breaks
        self.assertEqual(cut(self.TEXT, 0, 21, 10 ** 6), (21, False))       # exactly three
        self.assertEqual(cut(self.TEXT, 14, 20, 10 ** 6), (28, False))      # the next page goes on after it
        self.assertEqual(cut(self.TEXT, 63, 20, 10 ** 6), (69, False))      # the last line has no break
        self.assertEqual(cut(self.TEXT, 69, 20, 10 ** 6), (69, False))
        self.assertEqual(cut("", 0, 1000, 10 ** 6), (0, False))

    def test_the_bytes_as_sent_end_a_page_before_the_characters_do(self):
        self.assertEqual(wire('a"b\\c\nd'), 10)                             # quote, backslash and break cost two
        self.assertEqual((wire("ü"), wire(MARK), wire("→·›"), wire("\U0001f600"), wire("\x01")), (6, 6, 18, 12, 6))
        self.assertEqual(cut(self.TEXT, 0, 1000, 16), (14, False))          # each line is 8 bytes as sent
        self.assertEqual(cut(self.TEXT, 0, 1000, 15), (7, False))
        umlauts = "\n".join(["ü" * 10] * 4)                            # each line 60 bytes and a break
        self.assertEqual(cut(umlauts, 0, 1000, 130), (22, False))

    def test_a_line_that_does_not_fit_is_continued_inside_it(self):
        text = "short\n" + "x" * 50 + "\nend"
        self.assertEqual(cut(text, 0, 20, 10 ** 6), (6, False))             # first what fits whole
        self.assertEqual(cut(text, 6, 20, 10 ** 6), (26, True))             # then max characters of the long line
        self.assertEqual(cut(text, 26, 20, 10 ** 6), (46, True))
        self.assertEqual(cut(text, 46, 20, 10 ** 6), (60, False))           # its rest and the line after it
        self.assertEqual(cut("ü" * 50, 0, 1000, 60), (10, True))       # the bytes bound inside a line too

    def test_a_page_never_ends_inside_an_escape(self):
        text = 'p "' + '\\"' * 10 + "\\\\" * 10 + "\\u000a" * 10 + '"'
        for limit in range(1, 30):
            position, parts = 0, []
            while position < len(text):
                end, _ = cut(text, position, limit, 10 ** 6)
                self.assertGreater(end, position)                           # always at least one character
                parts.append(text[position:end])
                position = end
            self.assertEqual("".join(parts), text)
            for part in parts:
                self.assertEqual("".join(ESCAPE.findall(part)), part)
                self.assertTrue(all(len(token) != 1 or token != "\\" for token in ESCAPE.findall(part)), (limit, part))
                self.assertNotRegex(part, r"(^|[^\\])(\\\\)*\\$")            # no page ends in half an escape
        self.assertEqual(cut("\\u202e" * 3, 0, 4, 10 ** 6), (6, True))      # one escape is longer than max: it stays whole
        self.assertEqual(cut("\U0001f600" * 3, 0, 1000, 5), (1, True))      # and one character costs more than the bytes left

    def test_find_pages_hold_at_most_20_hits(self):
        text = "\n".join("hit %d" % index for index in range(45))
        end, mid_line = cut(text, 0, 10 ** 6, 10 ** 6, HITS)
        self.assertEqual((text[:end].count("\n"), mid_line), (20, False))
        self.assertEqual(text[end:].split("\n")[0], "hit 20")


class Cursors(unittest.TestCase):
    TEXT = "\n".join("line %d" % index for index in range(100))

    def test_a_cursor_goes_on_where_the_page_ended(self):
        cursor = cursor_at(self.TEXT, 70, "token", asked(ref="kqtvm5"))
        self.assertRegex(cursor, r"^70\.[0-9a-f]{16}\.[0-9a-f]{16}$")
        self.assertEqual(start_from(cursor, self.TEXT, "token", asked(ref="kqtvm5")), 70)
        self.assertEqual(start_from(None, self.TEXT, "token", asked()), 0)

    def test_another_query_is_invalid_input(self):
        cursor = cursor_at(self.TEXT, 70, "token", asked(ref="kqtvm5", find="x", role="link", full=False))
        for other in [asked(ref="kqtvm6", find="x", role="link"), asked(find="x", role="link"), asked(ref="kqtvm5", find="y", role="link"),
                      asked(ref="kqtvm5", find="x"), asked(ref="kqtvm5", find="x", role="button"),
                      asked(ref="kqtvm5", find="x", role="link", full=True), asked()]:
            with self.assertRaises(Refused) as caught:
                start_from(cursor, self.TEXT, "token", other)
            self.assertEqual(caught.exception.code, "invalid_input")
            self.assertIn("belongs to another read", str(caught.exception))

    def test_another_state_token_is_a_stale_reference(self):
        cursor = cursor_at(self.TEXT, 70, "token", asked())
        for text, token in [(self.TEXT, "another token"), (self.TEXT.replace("line 3\n", "line three\n"), "token"),
                            (self.TEXT[:70], "token"), (self.TEXT[:40], "token"), ("", "token")]:
            with self.assertRaises(Refused) as caught:
                start_from(cursor, text, token, asked())
            self.assertEqual((caught.exception.code, str(caught.exception)),
                             ("stale_reference", "The page changed; read again without the cursor."))
        # What comes after the cursor may differ: only what was returned is bound.
        self.assertEqual(start_from(cursor, self.TEXT[:70] + "something else", "token", asked()), 70)

    def test_a_cursor_this_tool_did_not_return_is_invalid_input(self):
        good = cursor_at(self.TEXT, 70, "token", asked())
        for forged in ["", "70", "70.x", good + ".1", "+" + good, " " + good, good.replace("70", "7_0"), "0" * 10 + good[2:],
                       "-1" + good[2:], 70, ["70"], {"position": 70}, True]:
            with self.assertRaises(Refused) as caught:
                start_from(forged, self.TEXT, "token", asked())
            self.assertEqual(caught.exception.code, "invalid_input", forged)
        for moved in ["71" + good[2:], "0" + good[2:], "69" + good[2:]]:    # another position than the one returned
            with self.assertRaises(Refused) as caught:
                start_from(moved, self.TEXT, "token", asked())
            self.assertEqual(caught.exception.code, "stale_reference")


class WholeTexts(unittest.TestCase):
    def test_a_text_of_100000_characters_comes_back_whole(self):
        long = "".join("%09d " % index for index in range(10000))
        table, shown = references(), view([node(1, "p", text=[long])])
        self.assertEqual(render(shown, table).text, 'p "%s"%s+99,800 kqtvm1' % (long[:200], MARK))
        entries = pages(shown, table, limit=1000, ref="kqtvm1")
        self.assertEqual("".join(outlines(entries)), 'p "%s" kqtvm1' % long)
        self.assertEqual(len(entries), 101)
        self.assertEqual([entry["mid_line"] for entry in entries], [True] * 100 + [False])
        self.assertEqual([entry["characters"] for entry in entries], [1000] * 100 + [11])
        self.assertEqual({entry["total"] for entry in entries}, {100011})
        self.assertTrue(all(entry["characters"] >= 1 for entry in entries))

    def test_a_table_row_wider_than_max_comes_back_whole(self):
        nodes = [node(1, "table", name="Wide"), node(2, "row", 1)] + [node(3 + index, "cell", 2, text=["cell %04d " % index * 9]) for index in range(40)]
        table, shown = references(), view(nodes)
        render(shown, table)
        whole = render(shown, table, ref="kqtvm1").text
        entries = pages(shown, table, limit=1000, ref="kqtvm1")
        self.assertEqual("".join(outlines(entries)), whole)
        self.assertEqual([entry["mid_line"] for entry in entries], [False] + [True] * (len(entries) - 2) + [False])
        self.assertEqual(outlines(entries)[0], 'table "Wide" kqtvm1\n')        # the line that fits, then the wide row
        self.assertGreater(len(entries), 4)

    def test_a_value_of_20000_characters_read_in_full_comes_back_whole(self):
        value = "".join("%04d\n" % index for index in range(4000))            # every break is an escape of six characters
        table, shown = references(), view([node(1, "form", name="F"), node(2, "textbox", 1, name="Notes", value=value)])
        render(shown, table)
        entries = pages(shown, table, limit=1000, ref="kqtvm2", full=True)
        whole = "".join(outlines(entries))
        self.assertEqual(whole, 'textbox "Notes" = "%s" kqtvm2' % value.replace("\n", "\\u000a"))
        self.assertEqual(len(whole), 16000 + 4000 * 6 + 27)
        for page in outlines(entries)[:-1]:
            self.assertNotRegex(page, r"\\(u[0-9a-f]{0,3})?$")                   # never inside an escape
        self.assertTrue(all(entry["mid_line"] for entry in entries[:-1]))

    def test_full_on_f1_returns_every_paragraph_and_field_in_two_pages(self):
        entries = pages(View(f1()), limit=40000, full=True)
        self.assertEqual(len(entries), 2)
        text = "".join(outlines(entries))
        self.assertEqual((text.count('\np "Paragraph') + 1, text.count("textbox"), text.count(MARK)), (120, 80, 0))
        self.assertTrue(all(len(sent([entry]).encode()) <= RESULT_LIMIT for entry in entries))
        self.assertEqual([entry["mid_line"] for entry in entries], [False, False])

    def test_find_is_paged_by_20_hits(self):
        entries = pages(View(f3()), limit=40000, find="of the listing")
        self.assertEqual([page.count("link ") for page in outlines(entries)], [20] * 14 + [19])
        self.assertEqual(len("".join(outlines(entries)).split("\n")), 299)


class Envelope(unittest.TestCase):
    """48 KiB as the result is sent, with a pending operation and the version notice in it."""

    def check(self, entries, reads=1):
        for entry in entries:
            self.assertLessEqual(len(sent([entry] * reads, NOTICE, PENDING).encode()), RESULT_LIMIT)
            self.assertGreaterEqual(entry["characters"], 1)

    def test_text_outside_ascii_stays_inside_48_kib_and_advances(self):
        text = "äöü中文 " * 20000                       # 120,000 characters, 6 bytes each but the spaces
        table, shown = references(), view([node(1, "p", text=[text])])
        render(shown, table)
        entries = pages(shown, table, limit=40000, measured=measure(NOTICE, PENDING), ref="kqtvm1")
        self.check(entries)
        self.assertEqual("".join(outlines(entries)), 'p "%s" kqtvm1' % text)
        self.assertGreater(len(entries), 12)                                   # the bytes end each page, not max
        self.assertTrue(all(entry["characters"] < 10000 for entry in entries))
        self.assertGreater(min(len(sent([entry], NOTICE, PENDING).encode()) for entry in entries[:-1]), RESULT_LIMIT - 16)

    def test_a_text_made_of_quotes_stays_inside_48_kib_and_advances(self):
        text = '"' * 60000                                                    # two characters each, four bytes as sent
        table, shown = references(), view([node(1, "p", text=[text])])
        render(shown, table)
        entries = pages(shown, table, limit=40000, measured=measure(NOTICE, PENDING), ref="kqtvm1")
        self.check(entries)
        self.assertEqual("".join(outlines(entries)), 'p "%s" kqtvm1' % ('\\"' * 60000))
        self.assertGreater(len(entries), 4)                                    # 12,000 quotes a page, not 20,000
        self.assertTrue(all(page.count("\\") == page.count('"') or index in (0, len(entries) - 1)
                            for index, page in enumerate(outlines(entries))))

    def test_characters_outside_the_first_plane_cost_twelve_bytes(self):
        text = "\U0001f600" * 20000
        table, shown = references(), view([node(1, "p", text=[text])])
        render(shown, table)
        entries = pages(shown, table, limit=40000, measured=measure(NOTICE, PENDING), ref="kqtvm1")
        self.check(entries)
        self.assertEqual("".join(outlines(entries)), 'p "%s" kqtvm1' % text)

    def test_five_tabs_each_get_their_share_and_their_cursor(self):
        table = references()
        texts = ["\u00fc" * 100, '"' * 100, "plain text " * 10, None, "\u4e2d" * 100]
        shown = [view([node(1, "main")] + ([node(2 + index, "p", 1, text=[text]) for index in range(300)] if text else
                                           [node(2, "p", 1, text=["short"])]), tab=tab)
                 for tab, text in zip(range(1, 6), texts)]
        measured = measure(NOTICE, PENDING)

        def readings(cursors):
            return [Reading(tab, render(tab, table, full=True), "token %d" % tab.tab, asked(full=True), cursor, 40000)
                    for tab, cursor in zip(shown, cursors)]
        entries = fit(readings([None] * 5), measured, table)
        self.assertLessEqual(measured(entries), RESULT_LIMIT)
        self.assertEqual([entry["tab"] for entry in entries], [1, 2, 3, 4, 5])
        share = (RESULT_LIMIT - measured([reading.entry() for reading in readings([None] * 5)])) // 5
        self.assertGreater(share, 8000)
        used = [wire(entry["untrusted_content"]["outline"]) for entry in entries]
        for index in (0, 1, 2, 4):                               # a full share each, to the last line that fits
            self.assertLessEqual(used[index], share)
            self.assertGreater(used[index], share - 700)
            self.assertIsNotNone(entries[index]["cursor"])
            self.assertTrue(entries[index]["untrusted_content"]["outline"].endswith("\n"))
        # The short tab doesn't use its share, and nobody else gets it.
        self.assertEqual((entries[3]["cursor"], entries[3]["untrusted_content"]["outline"]), (None, 'main kqtvm4\n  p "short"'))
        self.assertLess(used[3], 40)
        self.assertLess(measured(entries), RESULT_LIMIT - share + 700)
        # Each tab goes on by itself with its own cursor, and not with another tab's.
        for index in (0, 1, 2, 4):
            alone = readings([entry["cursor"] if position == index else None for position, entry in enumerate(entries)])[index]
            more = fit([alone], measured, table)[0]
            whole = render(shown[index], table, full=True).text
            self.assertEqual(entries[index]["untrusted_content"]["outline"] + more["untrusted_content"]["outline"],
                             whole[:entries[index]["characters"] + more["characters"]])
            self.assertGreater(more["characters"], entries[index]["characters"])   # alone it has the whole envelope
            with self.assertRaises(Refused) as caught:
                readings([entries[index]["cursor"]] * 5)
            self.assertEqual(caught.exception.code, "stale_reference")

    def test_five_tabs_of_one_long_line_each_advance_inside_it(self):
        table = references()
        shown = [view([node(1, "p", text=[text * 30000])], tab=tab) for tab, text in zip(range(1, 6), ["\u00fc", '"', "x", "\u4e2d", "\U0001f600"])]
        measured = measure(NOTICE, PENDING)
        cursors, parts = [None] * 5, [""] * 5
        for _ in range(3):
            entries = fit([Reading(tab, render(tab, table, full=True), "token", asked(full=True), cursor, 40000)
                           for tab, cursor in zip(shown, cursors)], measured, table)
            self.assertLessEqual(measured(entries), RESULT_LIMIT)
            self.assertGreater(measured(entries), RESULT_LIMIT - 100)             # every share is used
            self.assertEqual([entry["mid_line"] for entry in entries], [True] * 5)
            self.assertTrue(all(entry["characters"] >= 1 for entry in entries))
            cursors = [entry["cursor"] for entry in entries]
            parts = [part + entry["untrusted_content"]["outline"] for part, entry in zip(parts, entries)]
        for tab, part in zip(shown, parts):
            self.assertEqual(part, render(tab, table, full=True).text[:len(part)])

    def test_three_thousand_characters_a_tab_unless_claude_says_otherwise(self):
        table = references()
        shown = [View({**f1(), "tab": tab}) for tab in (1, 2, 3)]
        entries = fit([Reading(tab, render(tab, table), "token", asked(), None, 3000) for tab in shown], measure(), table)
        self.assertEqual([(entry["total"] > 3000, entry["characters"] <= 3000, entry["cursor"] is not None, entry["mid_line"])
                          for entry in entries], [(True, True, True, False)] * 3)

    def test_a_tab_that_cannot_be_read_gets_its_error_and_the_others_are_returned(self):
        table = references()
        good = view([node(1, "main"), node(2, "p", 1, text=["fine"])], tab=1)
        refusals = [Failure(2, Refused("refused", "This tab is not one of Claude's.")),
                    Failure(3, Refused("not_read", "Time ran out; read this tab by itself.")),
                    Failure(4, Stale('p "now \\"here\\""'))]
        entries = fit([Reading(good, render(good, table), "token", asked())] + refusals, measure(), table)
        self.assertEqual(entries[0]["untrusted_content"]["outline"], 'main kqtvm1\n  p "fine"')
        self.assertEqual(entries[1:], [
            {"tab": 2, "error": {"code": "refused", "message": "This tab is not one of Claude's."}},
            {"tab": 3, "error": {"code": "not_read", "message": "Time ran out; read this tab by itself."}},
            {"tab": 4, "error": {"code": "stale_reference", "message": "This reference isn't valid for this tab any more; read the page again."},
             "untrusted_content": {"line": 'p "now \\"here\\""'}}])
        self.assertEqual(fit(refusals, measure(), table), entries[1:])           # no tab could be read

    def test_the_entry_of_a_read(self):
        table, shown = references(), View(f1())
        entry = fit([Reading(shown, render(shown, table), "token", asked(), until_met=False)], measure(), table)[0]
        self.assertEqual(list(entry), ["tab", "whose", "characters", "total", "cursor", "mid_line", "typed_fields",
                                       "untrusted_content", "until_met"])
        self.assertEqual({key: value for key, value in entry.items() if key != "untrusted_content"},
                         {"tab": 412, "whose": "claude", "characters": 3258, "total": 3258, "cursor": None, "mid_line": False,
                          "typed_fields": 0, "until_met": False})
        self.assertEqual(list(entry["untrusted_content"]), ["url", "title", "scroll", "dialog", "outline"])
        self.assertNotIn("until_met", fit([Reading(shown, render(shown, table), "token", asked())], measure(), table)[0])
        self.assertEqual(Reading(shown, Text(), "token", asked()).limit, 6000)

    def test_notices_that_leave_no_room_are_said_and_nothing_is_cut_silently(self):
        table, shown = references(), View(f1())
        crowded = {"items": [], "total": 0, "cursor": None, "notices": [{"untrusted_content": {"warning": "w" * 49000}}]}
        with self.assertRaises(Refused) as caught:
            fit([Reading(shown, render(shown, table), "token", asked())], measure(NOTICE, crowded), table)
        self.assertEqual(caught.exception.code, "result_too_large")
        tight = {"items": [], "total": 0, "cursor": None, "notices": [{"untrusted_content": {"warning": "w" * 47000}}]}
        entries = pages(shown, table, measured=measure(NOTICE, tight))
        self.assertGreater(len(entries), 1)                                    # smaller pages, and still to the end
        self.assertEqual("".join(outlines(entries)), render(shown, table).text)
        self.assertTrue(all(measure(NOTICE, tight)([entry]) <= RESULT_LIMIT for entry in entries))


if __name__ == "__main__":
    unittest.main()
