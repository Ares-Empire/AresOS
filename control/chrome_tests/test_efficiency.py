"""Brief 28, group 16 without a browser: the efficiency summary's counting."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aresos_control.common import display_json  # noqa: E402
from aresos_control.definitions import instructions_for, tools_for  # noqa: E402

SPEC = importlib.util.spec_from_file_location("efficiency_summary", ROOT / "chrome/ci/efficiency-summary.py")
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


def page(tree, cursor=None):
    return {"ok": True, "data": {"untrusted_content": {"url": "http://fixture.test:8765/", "title": "T", "tree": tree},
                                 "characters": len(tree), "cursor": cursor}, "pending": {"items": [], "total": 0, "cursor": None}}


class Record:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.calls, self.tasks = [], []

    def task(self, name, run, results, milliseconds, warmup=None, tools=None):
        warmup = run == 0 if warmup is None else warmup
        for index, (action, result) in enumerate(results):
            self.calls.append({"task": name, "run": run, "warmup": warmup, "index": index, "action": "chrome_" + action,
                               "arguments": {}, "result": result})
        self.tasks.append({"task": name, "run": run, "warmup": warmup, "milliseconds": milliseconds,
                           "tools": tools if tools is not None else [action for action, _ in results]})

    def write(self):
        (self.directory / "efficiency-calls.jsonl").write_text("".join(json.dumps(c) + "\n" for c in self.calls))
        (self.directory / "efficiency-tasks.jsonl").write_text("".join(json.dumps(t) + "\n" for t in self.tasks))
        (self.directory / "efficiency-runner.json").write_text(json.dumps(
            {"run_id": "123", "sha": "abc", "runner": {"image_os": "ubuntu24"}, "cpu": "Fixture CPU", "cpus": 4,
             "memory_bytes": 1, "node": "v22", "chrome": "Google Chrome 1"}))
        return self.directory


class EfficiencySummaryTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="pkg28-efficiency-")
        self.record = Record(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_characters_are_the_text_claude_receives_and_time_is_the_median_after_the_warm_up(self):
        first, second = page("x" * 100, cursor="c1"), page('"quoted"\n' + "é" * 10)
        for run, milliseconds in enumerate([900.0, 50.0, 30.0, 40.0, 10.0, 20.0]):
            self.record.task("f1_everything", run, [("read", first), ("read", second)], milliseconds)
        result = summary.summarize(self.record.write())
        task = result["tasks"]["f1_everything"]
        expected = len(display_json(first)) + len(display_json(second))
        self.assertEqual(task["characters"], expected)
        # Non-ASCII text arrives escaped, six characters a letter; a quote and a line break two each.
        # (against a page of 19 plain letters, the same length as this tree).
        self.assertEqual(len(display_json(second)) - len(display_json(page("z" * 19))), 2 + 6 + 2 + 2 + 6 * 10 - 19)
        self.assertEqual(task["calls"], 2)
        self.assertEqual(task["tools"], ["chrome_read", "chrome_read"])
        self.assertEqual(task["milliseconds"], 30.0)
        self.assertEqual(task["warmup_milliseconds"], [900.0])
        self.assertEqual(result["measured_runs"], 5)
        self.assertEqual(result["run_id"], "123")
        self.assertEqual(result["runner"]["cpus"], 4)
        self.assertEqual(result["latency_comparisons"], [])

    def test_characters_are_the_median_of_the_measured_runs(self):
        for run, size in enumerate([1, 10, 20, 30, 40, 50]):
            self.record.task("f3_find_link", run, [("find", page("y" * size))], 1.0)
        task = summary.summarize(self.record.write())["tasks"]["f3_find_link"]
        self.assertEqual(task["characters"], len(display_json(page("y" * 30))))
        self.assertEqual(task["characters_per_run"], [len(display_json(page("y" * size))) for size in (10, 20, 30, 40, 50)])

    def test_runs_that_made_different_calls_are_refused(self):
        for run in range(6):
            results = [("read", page("a"))] + ([("read", page("b"))] if run == 3 else [])
            self.record.task("f2_table", run, results, 1.0)
        with self.assertRaisesRegex(ValueError, "different calls"):
            summary.summarize(self.record.write())

    def test_a_failed_call_or_a_missing_warm_up_is_refused(self):
        for run in range(6):
            self.record.task("f5_free_click", run, [("click", {"ok": False, "error": {"code": "refused"}})], 1.0)
        with self.assertRaisesRegex(ValueError, "failed"):
            summary.summarize(self.record.write())
        self.record = Record(self.temporary.name)
        for run in range(1, 6):
            self.record.task("f5_free_click", run, [("click", page("c"))], 1.0, warmup=False)
        with self.assertRaisesRegex(ValueError, "warm-up"):
            summary.summarize(self.record.write())

    def test_timed_tools_must_match_the_recorded_calls(self):
        for run in range(6):
            self.record.task("open_fact", run, [("open", page("o"))], 1.0, tools=["open", "wait"])
        with self.assertRaisesRegex(ValueError, "differ from the timed"):
            summary.summarize(self.record.write())

    def test_sizes_measure_what_a_session_loads(self):
        sizes = summary.sizes()
        tools = tools_for("chrome")
        self.assertEqual(sizes["tools"], len(tools))
        self.assertEqual(sizes["instructions"], len(instructions_for("chrome")))
        self.assertEqual(sizes["descriptions_and_instructions"], sizes["descriptions"] + sizes["instructions"])
        compact = sum(len(tool["name"]) + len(json.dumps(tool["inputSchema"], separators=(",", ":"))) for tool in tools)
        self.assertEqual(sizes["names_and_input_schemas"], compact)


if __name__ == "__main__":
    unittest.main()
