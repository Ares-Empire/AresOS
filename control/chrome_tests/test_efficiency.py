"""Brief 28, group 16 without a browser: the efficiency summary's counting."""
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aresos_control.common import display_json  # noqa: E402
from aresos_control.definitions import instructions_for, tools_for  # noqa: E402
from workflow_steps import workflow_structure  # noqa: E402

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

    def task(self, name, run, results, milliseconds, warmup=None, tools=None, refusals=None):
        warmup = run == 0 if warmup is None else warmup
        for index, (action, result) in enumerate(results):
            call = {"task": name, "run": run, "warmup": warmup, "index": index, "action": "chrome_" + action,
                    "arguments": {}, "result": result}
            if (refusals or {}).get(index):
                call["expected_refusal"] = refusals[index]
            self.calls.append(call)
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

    def test_only_the_refusal_a_task_expected_may_fail_a_call(self):
        # Brief 20 can't send F4 (run 43698395453): its row records the refusal.
        refused = {"ok": False, "error": {"code": "asking_input_too_large", "message": "The whole approval exceeds 16384 bytes"},
                   "pending": {"items": [], "total": 0, "cursor": None}}
        for run in range(6):
            self.record.task("f4_fill_send", run, [("read", page("form")), ("click", refused)], 1.0,
                             refusals={1: "asking_input_too_large"})
            self.record.task("f3_find_link", run, [("find", page("link"))], 1.0)
        result = summary.summarize(self.record.write())
        task = result["tasks"]["f4_fill_send"]
        self.assertEqual(task["outcome"], "refused")
        self.assertEqual(task["refusals"], [{"action": "chrome_click", "code": "asking_input_too_large"}])
        self.assertEqual(task["characters"], len(display_json(page("form"))) + len(display_json(refused)))
        self.assertEqual((result["tasks"]["f3_find_link"]["outcome"], result["tasks"]["f3_find_link"]["refusals"]), ("done", []))
        # Another code than the expected one, or a refusal nobody expected, fails the summary.
        for refusals in ({1: "refused"}, None):
            self.record = Record(self.temporary.name)
            for run in range(6):
                self.record.task("f4_fill_send", run, [("read", page("form")), ("click", refused)], 1.0, refusals=refusals)
            with self.assertRaisesRegex(ValueError, "run 0: chrome_click failed"):
                summary.summarize(self.record.write())
        # A row that ends differently in one measured run is no baseline.
        self.record = Record(self.temporary.name)
        for run in range(6):
            click = ("click", page("sent")) if run == 4 else ("click", refused)
            self.record.task("f4_fill_send", run, [("read", page("form")), click], 1.0, refusals={1: "asking_input_too_large"})
        with self.assertRaisesRegex(ValueError, "ended differently"):
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


def probe_tasks():
    """The tasks of efficiency-probe.mjs as its source lists them: name, row, plan and the refusal a task expects.

    The laptop has no Node, so the list is read from the text; a task written in another shape fails the count.
    """
    source = (ROOT / "chrome/ci/efficiency-probe.mjs").read_text()
    block = source[source.index("export const TASKS=["):source.index("// Checks a recorded call sequence against a plan")]
    heads = list(re.finditer(r"\{name:'([a-z0-9_]+)',row:'((?:[^'\\]|\\.)*)',plan:\[([^\]]*)\]", block))
    if len(heads) != len(re.findall(r"\bname:'", block)):
        raise AssertionError("a task of TASKS isn't written as {name:'…',row:'…',plan:[…]")
    tasks = []
    for index, head in enumerate(heads):
        body = block[head.end():heads[index + 1].start() if index + 1 < len(heads) else len(block)]
        tasks.append({"name": head.group(1), "row": head.group(2).replace("\\'", "'"),
                      "plan": re.findall(r"'([a-z_]+\*?)'", head.group(3)),
                      "refusals": re.findall(r"\{refusal:'([a-z_]+)'\}", body)})
    return tasks


def follows_plan(tools, plan):
    """followsPlan of efficiency-probe.mjs: `x*` matches zero or more x."""
    index = 0
    for step in plan:
        if step.endswith("*"):
            while index < len(tools) and tools[index] == step[:-1]:
                index += 1
            continue
        if index >= len(tools) or tools[index] != step:
            return False
        index += 1
    return index == len(tools)


class EfficiencyBaselineTest(unittest.TestCase):
    """control/chrome/ci/efficiency-baseline.json: run 43705060936's efficiency-measured.json, committed unchanged.

    Brief 28a fails a number worse than this file's, so it is frozen: only `latency_comparisons` may grow.
    """

    BASELINE = ROOT / "chrome/ci/efficiency-baseline.json"
    # sha256 of the file without `latency_comparisons`, as canonical JSON.
    FROZEN = "361f7c07e3a779b9f04c03227672f65f0dcf593884523ad41d233ca84fbe56ce"

    def setUp(self):
        self.baseline = json.loads(self.BASELINE.read_text())

    def test_it_holds_every_task_of_the_probe_with_the_same_plan_and_outcome(self):
        tasks = probe_tasks()
        self.assertEqual(len(tasks), 11)
        self.assertEqual(list(self.baseline["tasks"]), [task["name"] for task in tasks])
        for task in tasks:
            with self.subTest(task=task["name"]):
                row = self.baseline["tasks"][task["name"]]
                self.assertEqual((row["row"], row["plan"]), (task["row"], task["plan"]))
                self.assertEqual(row["outcome"], "refused" if task["refusals"] else "done")
                self.assertEqual([refusal["code"] for refusal in row["refusals"]], task["refusals"])
                tools = [tool.removeprefix("chrome_") for tool in row["tools"]]
                self.assertTrue(follows_plan(tools, task["plan"]), tools)
                self.assertEqual(row["calls"], len(tools))
                self.assertEqual(len(row["characters_per_call"]), row["calls"])
                self.assertEqual(len(row["characters_per_run"]), self.baseline["measured_runs"])
                self.assertEqual(len(row["milliseconds_per_run"]), self.baseline["measured_runs"])
                self.assertGreater(row["characters"], 0)
                self.assertGreater(row["milliseconds"], 0)

    def test_f4s_row_is_brief_20s_refusal(self):
        # The lead's decision (2026-11-15): brief 20's tools can't send F4, and the baseline says so.
        row = self.baseline["tasks"]["f4_fill_send"]
        self.assertEqual(row["outcome"], "refused")
        self.assertEqual(row["refusals"], [{"action": "chrome_click", "code": "asking_input_too_large"}])
        self.assertEqual(row["tools"], ["chrome_read", "chrome_fill_form", "chrome_find", "chrome_click"])
        self.assertEqual([name for name, task in self.baseline["tasks"].items() if task["outcome"] != "done"], ["f4_fill_send"])

    def test_it_is_one_green_runs_record_and_stays_as_committed(self):
        self.assertEqual(self.baseline["format"], summary.FORMAT)
        self.assertEqual(self.baseline["run_id"], "43705060936")
        self.assertEqual(self.baseline["measured_runs"], 5)
        self.assertEqual(self.baseline["runner"]["runner"]["environment"], "github-hosted")
        self.assertEqual(set(self.baseline["sizes"]), {"tools", "descriptions", "instructions",
                                                       "descriptions_and_instructions", "names_and_input_schemas"})
        self.assertIsInstance(self.baseline["latency_comparisons"], list)
        frozen = {key: value for key, value in self.baseline.items() if key != "latency_comparisons"}
        digest = hashlib.sha256(json.dumps(frozen, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, self.FROZEN, "the baseline's numbers changed; only latency_comparisons may be added to")

    def test_the_task_list_is_read_whole_and_a_plan_is_followed_exactly(self):
        self.assertTrue(follows_plan(["read", "read", "read"], ["read", "read*"]))
        self.assertTrue(follows_plan(["find", "click"], ["find", "find*", "click"]))
        self.assertFalse(follows_plan(["find", "click", "submit"], ["find", "find*", "click"]))
        self.assertFalse(follows_plan(["click"], ["find", "find*", "click"]))
        self.assertFalse(follows_plan([], ["read"]))
        tasks = {task["name"]: task for task in probe_tasks()}
        self.assertEqual(tasks["f4_fill_send"]["refusals"], ["asking_input_too_large"])
        self.assertEqual(tasks["f2_table"]["plan"], ["read*"])
        self.assertEqual(tasks["f1_everything"]["row"], "F1: everything, the read and each cursor it returns")


class EfficiencyWiringTest(unittest.TestCase):
    """The probe runs inside the latency harness: one docker command, the plain leg, after the gate."""

    def test_the_probe_shares_the_latency_pairs_docker_command(self):
        pair = (ROOT / "chrome/ci/latency-pair.sh").read_text()
        self.assertEqual(pair.count("docker run"), 1)
        self.assertIn('      latency_container "$latency_revision" "$latency_out"\n', pair)
        self.assertIn('    latency_container current "$efficiency_out" -e EFFICIENCY_PROBE=true -e ImageOS -e ImageVersion'
                      ' -e RUNNER_ENVIRONMENT -e RUNNER_ARCH\n', pair)
        self.assertIn('    test "${LATENCY_PRIVACY:-}" = plain\n', pair)
        self.assertIn('    python3 control/chrome/ci/efficiency-summary.py "$efficiency_out"\n', pair)
        # The probe's options come before the mount and the image, never after.
        self.assertIn(' -e GITHUB_SHA "$@" -v "$out:/out" "aresos-latency-$revision"\n', pair)
        browser = (ROOT / "chrome/ci/browser.mjs").read_text()
        self.assertIn("if(process.env.LATENCY_PROBE==='true'&&process.env.EFFICIENCY_PROBE==='true')", browser)

    def test_the_workflow_runs_it_after_the_gate_in_the_plain_leg_and_keeps_its_record(self):
        _, steps = workflow_structure((ROOT.parent / ".github/workflows/control-chrome.yml").read_text())
        latency = [step for step in steps if step["job"] == "latency"]
        names = [step["name"] for step in latency]
        pair = dict(latency[names.index("Paired current and historical measurements on the same runner")]["keys"])
        gate = names.index("Require lead ceilings and reject paired latency regressions")
        probe = names.index("Efficiency tasks with brief 20's tools")
        self.assertEqual(probe, gate + 1)
        self.assertEqual(pair["id"], "pair")
        self.assertEqual(pair["run"], "bash control/chrome/ci/latency-pair.sh")
        keys = dict(latency[probe]["keys"])
        self.assertEqual(keys["run"], "bash control/chrome/ci/latency-pair.sh efficiency")
        self.assertEqual(keys["if"], "${{ !cancelled() && !inputs.latency_probe && matrix.privacy == 'plain'"
                                     " && steps.pair.outcome == 'success' }}")
        self.assertEqual(keys["env.LATENCY_PRIVACY"], "${{ matrix.privacy }}")
        uploads = [dict(step["keys"]) for step in latency if dict(step["keys"]).get("with.path") == ".work/latency-out/efficiency/"]
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0]["with.name"], "chrome-efficiency-${{ github.run_id }}-${{ github.run_attempt }}")
        self.assertEqual(uploads[0]["if"], "${{ always() && matrix.privacy == 'plain' }}")


if __name__ == "__main__":
    unittest.main()
