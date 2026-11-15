"""The reference table, as far as reads need it (brief 28, item 3)."""
import inspect
from pathlib import Path
import random
import re
import secrets
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aresos_control.chrome import references as module
from aresos_control.chrome.references import CONSONANTS, LIMIT, STALE, References, Stale
from aresos_control.chrome.view import Reading, asked, fit, render
from aresos_control.common import Refused
from view_fixtures import SITE, frame, measure, node, references, view

# A seed under which 300 runs in a row all draw different letters (the test checks it).
SEED = 28


def issue(table, tab, element, frame=0, document="d0", reader="r0"):
    return table.issue(tab, frame, document, reader, element)


def read(table, shown, **query):
    """One whole read: render, cut to a page, record what was returned."""
    text = render(shown, table, **query)
    entry = fit([Reading(shown, text, "token", asked(**query), limit=40000)], measure(), table)[0]
    return entry["untrusted_content"]["outline"]


class Letters(unittest.TestCase):
    def test_five_consonants_from_the_systems_random_source(self):
        self.assertEqual(len(CONSONANTS), 21)
        self.assertFalse(set(CONSONANTS) & set("aeiou"))
        for _ in range(50):
            self.assertRegex(References().letters, "^[%s]{5}$" % CONSONANTS)
        drawn = []

        class Recorder(secrets.SystemRandom):
            def choice(self, sequence):
                drawn.append(sequence)
                return super().choice(sequence)
        original, secrets.SystemRandom = secrets.SystemRandom, Recorder
        try:
            table = References()
        finally:
            secrets.SystemRandom = original
        self.assertEqual(drawn, [CONSONANTS] * 5)
        self.assertEqual(len(table.letters), 5)

    def test_drawn_once_and_nothing_is_read_from_or_written_to_the_store(self):
        self.assertEqual(list(inspect.signature(References.__init__).parameters), ["self", "source"])
        source = Path(module.__file__).read_text()
        for word in ["storage", "open(", "sqlite", "Path", "os."]:
            self.assertNotIn(word, source)
        table = references("kqtvm")
        strings = [issue(table, tab, element) for tab in (1, 2) for element in range(1, 40)]
        table.connect("another connection")
        strings += [issue(table, 1, element) for element in range(1, 40)]
        self.assertTrue(all(re.fullmatch("kqtvm[1-9][0-9]*", string) for string in strings))


class Issuing(unittest.TestCase):
    def test_the_same_element_keeps_its_reference_and_another_gets_another(self):
        table = references()
        first = issue(table, 1, 5)
        self.assertEqual(first, "kqtvm1")
        self.assertEqual(issue(table, 1, 5), first)
        others = [issue(table, 1, 6), issue(table, 2, 5), issue(table, 1, 5, frame=3), issue(table, 1, 5, document="d1"),
                  issue(table, 1, 5, reader="r1"), issue(table, 1, ("fold", None, 5, "p"))]
        self.assertEqual(len({first, *others}), 7)
        self.assertEqual(issue(table, 1, ("fold", None, 5, "p")), others[-1])

    def test_one_counter_for_all_tabs(self):
        table = references()
        strings = [issue(table, tab, element) for element in range(1, 30) for tab in (1, 2, 3)]
        self.assertEqual(strings, ["kqtvm%d" % number for number in range(1, 88)])
        for index, string in enumerate(strings):
            tab = (1, 2, 3)[index % 3]
            self.assertEqual(table.resolve(string, tab).tab, tab)
            for other in {1, 2, 3} - {tab}:
                with self.assertRaises(Stale):
                    table.resolve(string, other)

    def test_an_entry_holds_where_the_element_is(self):
        table = references()
        table.connect("s1")
        entry = table.resolve(issue(table, 7, 12, frame=4, document="doc", reader="inst"), 7)
        self.assertEqual((entry.tab, entry.frame, entry.document, entry.reader, entry.target), (7, 4, "doc", "inst", 12))
        self.assertEqual((entry.line, entry.fingerprint, table.session), (None, None, "s1"))


class Refusing(unittest.TestCase):
    def stale(self, table, reference, tab):
        with self.assertRaises(Stale) as caught:
            table.resolve(reference, tab)
        self.assertEqual((caught.exception.code, str(caught.exception), caught.exception.line), ("stale_reference", STALE, None))
        self.assertIsInstance(caught.exception, Refused)

    def test_invented_foreign_and_malformed_references(self):
        table = references()
        issue(table, 1, 5)
        for invented in ["kqtvm2", "kqtvm0", "kqtvm", "bcdfg1", "kqtvm1 ", "KQTVM1", "", None, 1, ["kqtvm1"], {"a": 1}]:
            self.stale(table, invented, 1)
        self.stale(table, "kqtvm1", 2)
        self.assertEqual(table.resolve("kqtvm1", 1).target, 5)

    def test_another_connection_empties_the_table_and_the_counter_goes_on(self):
        table = references()
        table.connect("s1")
        old = [issue(table, 1, element) for element in range(1, 6)]
        table.connect("s1")
        self.assertEqual(table.resolve(old[0], 1).target, 1)
        table.connect("s2")  # Chrome or the extension restarted or reconnected
        for reference in old:
            self.stale(table, reference, 1)
        new = [issue(table, 1, element) for element in range(1, 6)]
        self.assertFalse(set(old) & set(new))
        self.assertEqual(new[0], "kqtvm6")

    def test_a_closed_tab_is_forgotten_and_its_strings_never_come_back(self):
        table = references()
        old = [issue(table, 1, element) for element in range(1, 6)]
        kept = issue(table, 2, 1)
        table.close(1)
        for reference in old:
            self.stale(table, reference, 1)
        self.assertEqual(table.resolve(kept, 2).target, 1)
        self.assertFalse(set(old) & {issue(table, 1, element) for element in range(1, 6)})


class Bound(unittest.TestCase):
    def test_the_newest_5000_of_a_tab_stay_and_a_dropped_string_is_never_issued_again(self):
        table = references()
        first = [issue(table, 1, element) for element in range(1, LIMIT + 1)]
        other_tab = issue(table, 2, 1)
        table.returned(1, [(reference, "line", {}) for reference in first])
        self.assertEqual(table.resolve(first[0], 1).line, "line")
        more = [issue(table, 1, element) for element in range(LIMIT + 1, LIMIT + 301)]
        table.returned(1, [(reference, "line", {}) for reference in more])
        for reference in first[:300]:
            with self.assertRaises(Stale):
                table.resolve(reference, 1)
        for reference in first[300:] + more:
            table.resolve(reference, 1)
        self.assertEqual(table.resolve(other_tab, 2).target, 1)  # another tab's entries don't count
        again = [issue(table, 1, element) for element in range(1, 301)]
        self.assertFalse(set(again) & set(first))
        self.assertEqual(again[0], "kqtvm%d" % (LIMIT + 302))
        self.assertEqual(len(set(first + more + again + [other_tab])), LIMIT + 601)

    def test_what_claude_was_shown_outlives_what_was_only_counted(self):
        table = references()
        shown = [issue(table, 1, element) for element in range(1, 101)]
        table.returned(1, [(reference, "line", {}) for reference in shown])
        counted = [issue(table, 1, element) for element in range(101, 101 + LIMIT + 50)]  # never returned
        table.returned(1, [])
        for reference in shown:
            self.assertEqual(table.resolve(reference, 1).line, "line")
        dropped = [reference for reference in counted if reference not in table._references]
        self.assertEqual(dropped, counted[:150])

    def test_shown_again_counts_as_new(self):
        table = references()
        early = [issue(table, 1, element) for element in range(1, 11)]
        table.returned(1, [(reference, "line", {}) for reference in early])
        rest = [issue(table, 1, element) for element in range(11, LIMIT + 1)]
        table.returned(1, [(reference, "line", {}) for reference in rest])
        table.returned(1, [(reference, "line again", {}) for reference in early])
        late = [issue(table, 1, element) for element in range(LIMIT + 1, LIMIT + 11)]
        table.returned(1, [(reference, "line", {}) for reference in late])
        for reference in early + late:
            table.resolve(reference, 1)
        for reference in rest[:10]:
            with self.assertRaises(Stale):
                table.resolve(reference, 1)

    def test_a_read_of_more_than_5000_elements_never_returns_a_dropped_reference(self):
        # 8,000 links in one tab, read in full: every reference on a returned
        # page resolves when the page is returned, though the tab keeps 5,000.
        nodes = [node(1, "main")] + [node(index + 2, "link", 1, name="L%d" % index, href=SITE + "/%d" % index)
                                     for index in range(8000)]
        table, shown = references(), view(nodes)
        cursor, pages, seen = None, [], set()
        for _ in range(4):
            text = render(shown, table, full=True)
            entry = fit([Reading(shown, text, "token", asked(full=True), cursor, 40000)], measure(), table)[0]
            pages.append(entry["untrusted_content"]["outline"])
            self.assertEqual("".join(pages), text.text[:len("".join(pages))])  # what was returned stays as it was
            for reference in re.findall(r"kqtvm\d+", pages[-1]):
                self.assertEqual(table.resolve(reference, 412).line.split()[-1], reference)
                seen.add(reference)
            self.assertLessEqual(len(table._tabs[412]), LIMIT)
            self.assertLessEqual(len(table._references), LIMIT)
            cursor = entry["cursor"]
        self.assertGreater(len(seen), LIMIT)
        # KNOWN LIMIT: the four pages showed more than 5,000 references, so
        # the first of them are dropped now. Their elements get new strings,
        # the text before the cursor is no longer what was returned, and the
        # cursor is refused instead of going on at a wrong place.
        with self.assertRaises(Refused) as caught:
            Reading(shown, render(shown, table, full=True), "token", asked(full=True), cursor, 40000)
        self.assertEqual((caught.exception.code, str(caught.exception)),
                         ("stale_reference", "The page changed; read again without the cursor."))
        dropped = [reference for reference in seen if reference not in table._references]
        self.assertTrue(dropped)
        self.assertFalse(set(dropped) & set(re.findall(r"kqtvm\d+", render(shown, table, full=True).text)))


class Runs(unittest.TestCase):
    def test_300_runs_in_a_row_and_no_reference_of_an_earlier_run_resolves_in_a_later_one(self):
        source = random.Random(SEED)
        earlier, letters = [], set()
        for run in range(300):
            table = References(source)
            letters.add(table.letters)
            table.connect("s1")
            for tab, reference in earlier:
                with self.assertRaises(Stale):
                    table.resolve(reference, tab)
            mine = [(tab, issue(table, tab, element)) for tab in (1, 2) for element in range(1, 6)]
            for tab, reference in mine:
                self.assertEqual(table.resolve(reference, tab).tab, tab)
            for tab, reference in earlier[-50:]:  # also once the new run's own numbers have passed the old ones
                with self.assertRaises(Stale):
                    table.resolve(reference, tab)
            earlier += mine
        self.assertEqual(len(letters), 300)  # the seed's property; by chance, not by proof
        self.assertEqual(len({reference for _, reference in earlier}), 3000)

    def test_the_rest_shown_honestly_two_runs_that_draw_the_same_letters(self):
        # KNOWN LIMIT (section 6): an old reference resolves in a run with the
        # same letters only where that run issued the same number for the same tab.
        old = references("kqtvm")
        a1, a2, a3 = issue(old, 1, 10), issue(old, 1, 11), issue(old, 2, 10)
        new = references("kqtvm")
        b1, b2 = issue(new, 2, 77), issue(new, 1, 88)
        self.assertEqual((a1, a2, a3, b1, b2), ("kqtvm1", "kqtvm2", "kqtvm3", "kqtvm1", "kqtvm2"))
        with self.assertRaises(Stale):
            new.resolve(a1, 1)            # that number went to another tab
        with self.assertRaises(Stale):
            new.resolve(a3, 2)            # that number wasn't issued
        self.assertEqual(new.resolve(a2, 1).target, 88)   # the limit: it names the new run's element


class WithTheView(unittest.TestCase):
    PAGE = [node(1, "main"),
            node(2, "textbox", 1, name="Notes", value="n" * 500),
            node(3, "link", 1, name="Docs", text=["Docs"], href=SITE + "/docs/reset/abc?code=sesame#top", title="Opens here"),
            node(4, "checkbox", 1, name="Mine", states=["checked", "required"])]

    def test_the_fingerprint_is_kept_apart_from_the_line_claude_saw(self):
        table = references()
        outline = read(table, view(self.PAGE))
        field, link, box = (table.resolve(reference, 412) for reference in ("kqtvm2", "kqtvm3", "kqtvm4"))
        self.assertEqual(field.line, 'textbox "Notes" = "%s"%s+305 kqtvm2' % ("n" * 195, "…"))
        self.assertIn(field.line, outline)
        self.assertEqual(field.fingerprint["value"], "n" * 500)            # whole, though the line cut it
        self.assertEqual(link.line, 'link "Docs" kqtvm3')
        self.assertEqual(link.fingerprint["href"], SITE + "/docs/reset/abc?code=sesame#top")  # full, though no line shows it
        self.assertEqual((link.fingerprint["role"], link.fingerprint["name"], link.fingerprint["title"]), ("link", "Docs", "Opens here"))
        self.assertEqual(box.fingerprint["states"], ["checked"])
        self.assertNotIn("sesame", outline)

    def test_a_reference_is_marked_as_shown_only_once_its_page_was_returned(self):
        table, shown = references(), view(self.PAGE)
        render(shown, table)
        self.assertIsNone(table.resolve("kqtvm2", 412).line)
        read(table, shown)
        self.assertIsNotNone(table.resolve("kqtvm2", 412).line)

    def test_the_same_element_keeps_its_reference_across_reads_and_kinds_of_read(self):
        table = references()
        first = read(table, view(self.PAGE))
        changed = [dict(item) for item in self.PAGE]
        changed[1]["value"] = "other"
        changed.insert(1, node(9, "p", 1, text=["new"]))
        second = read(table, view(changed))
        self.assertIn('textbox "Notes" = "other" kqtvm2', second)
        self.assertEqual(re.findall(r"kqtvm\d+", first), re.findall(r"kqtvm\d+", second))
        self.assertIn("kqtvm3", read(table, view(self.PAGE), find="docs"))
        self.assertTrue(read(table, view(self.PAGE), ref="kqtvm3").startswith('link "Docs" kqtvm3'))

    def test_every_stale_case_of_a_read_by_reference(self):
        table = references()
        read(table, view(self.PAGE))

        def stale(shown, reference="kqtvm3"):
            with self.assertRaises(Stale) as caught:
                render(shown, table, ref=reference)
            self.assertEqual(str(caught.exception), STALE)
            return caught.exception

        stale(view(self.PAGE), "kqtvm99")                                   # invented
        stale(view(self.PAGE, tab=413))                                     # issued for another tab
        stale(view(frames=[frame(self.PAGE, document="d1")]))               # a new document
        stale(view(frames=[frame(self.PAGE, reader="r1")]))                 # the reader installed anew, same document and id
        stale(view(frames=[frame(self.PAGE, frame=5)]))                     # the frame is gone
        stale(view([item for item in self.PAGE if item["id"] != 3]))        # the element is gone
        self.assertTrue(render(view(self.PAGE), table, ref="kqtvm3").text)  # and still readable where nothing changed
        stale(view(self.PAGE, session="s2"))                                # another connection
        stale(view(self.PAGE))                                              # ... which emptied the table for good

    def test_a_new_reader_instance_in_the_same_document_gets_new_references(self):
        table = references()
        first = read(table, view(self.PAGE))
        second = read(table, view(frames=[frame(self.PAGE, reader="r1")]))
        self.assertFalse(set(re.findall(r"kqtvm\d+", first)) & set(re.findall(r"kqtvm\d+", second)))

    def test_two_tabs_showing_the_same_page_share_no_reference(self):
        table = references()
        first, second = read(table, view(self.PAGE, tab=1)), read(table, view(self.PAGE, tab=2))
        mine, theirs = set(re.findall(r"kqtvm\d+", first)), set(re.findall(r"kqtvm\d+", second))
        self.assertEqual((len(mine), len(theirs), len(mine & theirs)), (4, 4, 0))
        for reference in mine:
            with self.assertRaises(Stale):
                render(view(self.PAGE, tab=2), table, ref=reference)


if __name__ == "__main__":
    unittest.main()
