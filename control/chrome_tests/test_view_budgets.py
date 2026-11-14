"""The read budgets of brief 28, worked through on its fixtures as node lists (group 16's read rows).

Characters are counted on the whole result as Claude receives it: the JSON
text of the tool result. The browser run of the later steps measures the same
rows on the real pages; this file shows that the format as specified meets
them, and fails when a change to the format costs more than a budget allows.

Each row gives the brief's budget, the brief's own worked numbers ("about"),
and what this renderer returns. A measured number may be below the worked one;
the test fails above the budget, and above the worked number by more than 5%.
"""
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome.nodes import View
from aresos_control.chrome.view import Reading, asked, fit, render, wire
from aresos_control.common import RESULT_LIMIT
from view_fixtures import F3_UNIQUE, f1, f2, f3, measure, references, sent


def read(shown, table, limit=6000, **query):
    """A read and its cursors: the calls a row allows, each as (outline, JSON text as sent)."""
    cursor, calls = None, []
    while True:
        reading = Reading(shown, render(shown, table, **query), "token", asked(**query), cursor, limit)
        entry = fit([reading], measure(), table)[0]
        calls.append((entry["untrusted_content"]["outline"], sent([entry])))
        cursor = entry["cursor"]
        if cursor is None:
            return calls


def reference(calls, start):
    """The reference on the first line of the first read that starts with these words."""
    return re.search(r"^%s.* (kqtvm\d+)$" % start, calls[0][0], re.MULTILINE).group(1)


class Budgets(unittest.TestCase):
    def row(self, calls, budget, worked, measured, most_calls=1):
        outline, as_sent = sum(len(call[0]) for call in calls), sum(len(call[1]) for call in calls)
        self.assertLessEqual(len(calls), most_calls)
        self.assertLessEqual(as_sent, budget)
        self.assertLessEqual(outline, worked[0] * 1.05)
        self.assertLessEqual(as_sent, worked[1] * 1.05)
        self.assertEqual((len(calls), outline, as_sent), measured)     # what PROGRESS.md reports; change both together
        for call in calls:
            self.assertEqual(len(call[1]), len(call[1].encode()))      # the result is ASCII as sent
            self.assertLessEqual(len(call[1]), RESULT_LIMIT)

    def test_f1_the_first_read(self):
        # 1 call, the whole outline, at most 6,000 characters; worked: about 3,300 of outline, about 3,900 as sent
        calls = read(View(f1()), references())
        self.row(calls, 6000, (3300, 3900), (1, 3258, 3833))
        lines = calls[0][0].split("\n")
        self.assertEqual(len(lines), 5 + 1 + 1 + 40 + 1)               # 5 paragraphs, a fold, the form, 40 fields, a fold

    def test_f1_everything(self):
        # full and max 40,000, then each cursor: at most 3 calls, at most 75,000 characters in all;
        # worked: about 60,100 of outline in 2 pages, about 61,500 as sent
        calls = read(View(f1()), references(), limit=40000, full=True)
        self.row(calls, 75000, (60100, 61500), (2, 59020, 60462), most_calls=3)

    def test_f1_the_80_fields_with_their_values(self):
        # after the first read, the form's ref: 1 further call, at most 6,000; worked: about 4,250 and about 4,950
        table, shown = references(), View(f1())
        first = read(shown, table)
        calls = read(shown, table, ref=reference(first, "form"))
        self.row(calls, 6000, (4250, 4950), (1, 4176, 4899))
        self.assertEqual(calls[0][0].count("Synthetic value"), 80)

    def test_f2_the_whole_table(self):
        # after the first read, the table's ref and max 40,000: 1 further call, at most the cells' own text plus
        # 7 characters for each cell plus 800: 23,600; worked: about 20,100 and about 23,050
        table, shown = references(), View(f2())
        first = read(shown, table)
        calls = read(shown, table, limit=40000, ref=reference(first, 'table "Stock"'))
        cells = 200 * 6
        self.assertEqual(14400 + 7 * cells + 800, 23600)
        self.row(calls, 23600, (20100 * 1.01, 23050), (1, 20129, 23066))
        rows = calls[0][0].split("\n")[2:]
        self.assertEqual((len(rows), {len(row) for row in rows}, {wire(row + "\n") for row in rows[:-1]}), (200, {99}, {113}))

    def test_f3_the_one_link_with_the_unique_name(self):
        # the read with find and role: 1 call, at most 800; worked: about 100 and about 420
        calls = read(View(f3()), references(), find=F3_UNIQUE, role="link")
        self.row(calls, 800, (100, 420), (1, 56, 385))
        self.assertEqual(calls[0][0].count("\n"), 0)

    def test_f3_read_in_full(self):
        # No budget row: the size that decision 1 of section 7 cut (a list item that holds one link gets no line).
        # Step 1 measured 18,484 of outline with a line for each of the 300 items.
        calls = read(View(f3()), references(), limit=40000, full=True)
        self.assertEqual((len(calls), len(calls[0][0]), len(calls[0][1])), (1, 13984, 15253))
        self.assertNotIn("listitem", calls[0][0])

    def test_compare_three_open_tabs_is_one_call(self):
        table = references()
        shown = [View({**fixture(), "tab": tab}) for tab, fixture in ((1, f1), (2, f2), (3, f3))]
        entries = fit([Reading(tab, render(tab, table), "token", asked(), None, 3000) for tab in shown], measure(), table)
        self.assertEqual([entry["tab"] for entry in entries], [1, 2, 3])
        self.assertTrue(all(entry["characters"] <= 3000 for entry in entries))
        self.assertLessEqual(len(sent(entries)), RESULT_LIMIT)
        self.assertEqual([entry["cursor"] is None for entry in entries], [False, True, True])   # F1 goes on with its own cursor
        self.assertEqual(len(sent(entries)), 4865)

    def test_what_a_result_holds_around_its_outline(self):
        # "A read's result has about 310 characters around its outline."
        calls = read(View(f1()), references())
        self.assertEqual(len(calls[0][1]) - wire(calls[0][0]), 318)


if __name__ == "__main__":
    unittest.main()
