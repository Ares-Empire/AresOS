"""Brief 28, group 16: turns an efficiency probe's record into its numbers.

usage: efficiency-summary.py <probe output directory> [<output file>]

Characters are counted on each result as Claude receives it: the text the MCP
proxy sends (proxy.serve: display_json(bound_result(result))). Calls and tools
must be the same in every measured run; the wall time of a task is the median
of the measured runs, after the warm-up. A call may fail only with the refusal
its task expected (the probe marks it); the task's outcome is then "refused".
The sizes of what a session loads are measured from the same tree: tool
descriptions plus the server instructions, and tool names plus input schemas
as compact JSON.

Group 16 compares calls and characters with the frozen baseline and the brief's
budgets. Brief 28a's latency check after brief 20's tools are removed: each task
the side-by-side comparison timed (TIMED_TASKS) may take at most 1.5 times the
new tools' median of that comparison run, as efficiency-baseline.json records
it (its latency_comparisons entries of run COMPARISON_RUN), at its median of
this run's measured samples.
"""
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from aresos_control.common import display_json  # noqa: E402
from aresos_control.definitions import APPS, instructions_for, tools_for  # noqa: E402
from aresos_control.results import bound_result  # noqa: E402

FORMAT = 1
BASELINE = Path(__file__).resolve().parent / "efficiency-baseline.json"
# Brief 28a, item 7: main's catalogue measured at the package's start, and the pinned final totals.
START = ROOT / "chrome_tests/fixtures/28a-instructions/baseline.json"
# Brief 28, "Tests", group 16: each new-read task, the baseline task of the same
# row, and its budget (None: the row names only its calls).
OUTLINE_ROWS = {
    "outline_f1_first_read": {"baseline": "f1_first_read", "calls": 1, "characters": 6000},
    "outline_f1_everything": {"baseline": "f1_everything", "calls": 3, "characters": 75000},
    "outline_f1_fields": {"baseline": "f1_fields", "calls": 1, "characters": 6000},
    "outline_f2_table": {"baseline": "f2_table", "calls": 1, "characters": 23600},
    "outline_f3_find_link": {"baseline": "f3_find_link", "calls": 1, "characters": 800},
    "outline_three_tabs": {"baseline": "three_tabs", "calls": 1, "characters": None},
}
MEASURED_RUNS = 5
# Brief 28a, "Latency: old and new in one run": the three tasks timed with brief 20's tools and the new ones
# in one run, and that run: step 1's comparison (step 1d, a2ad7c7d; the lead, linux-tools, 2026-11-20). Its
# entries in the baseline file's latency_comparisons hold the new tools' medians the check that stays compares with.
TIMED_TASKS = ("outline_f1_first_read", "act_f5_free_click", "act_f4_to_question")
COMPARISON_RUN = "44463920809"
RECORDED_LIMIT = 1.5


def received(result):
    """The characters of a result as the MCP proxy hands it to Claude."""
    return len(display_json(bound_result(result)))


def sizes(app="chrome"):
    tools = tools_for(app)
    descriptions = sum(len(tool["description"]) for tool in tools)
    instructions = len(instructions_for(app))
    schemas = sum(len(tool["name"]) + len(json.dumps(tool["inputSchema"], ensure_ascii=True, separators=(",", ":")))
                  for tool in tools)
    return {"tools": len(tools), "descriptions": descriptions, "instructions": instructions,
            "descriptions_and_instructions": descriptions + instructions, "names_and_input_schemas": schemas}


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def summarize(directory):
    directory = Path(directory)
    calls, timings = lines(directory / "efficiency-calls.jsonl"), lines(directory / "efficiency-tasks.jsonl")
    runner = json.loads((directory / "efficiency-runner.json").read_text())
    order, tasks = [], {}
    for timing in timings:
        if timing["task"] not in tasks:
            order.append(timing["task"])
            tasks[timing["task"]] = {"warmup": [], "measured": []}
        tasks[timing["task"]]["warmup" if timing["warmup"] else "measured"].append(timing)
    characters = {}
    for call in calls:
        refusal = None
        if not call["result"].get("ok"):
            refusal = (call["result"].get("error") or {}).get("code")
            if refusal is None or call.get("expected_refusal") != refusal:
                raise ValueError("%s run %s: %s failed" % (call["task"], call["run"], call["action"]))
        key = (call["task"], call["run"])
        characters.setdefault(key, []).append((call["index"], call["action"], received(call["result"]), refusal))
    out = {}
    for name in order:
        runs = tasks[name]["measured"]
        if not runs or not tasks[name]["warmup"]:
            raise ValueError(name + ": a warm-up and measured runs are both required")
        per_run = []
        for timing in runs:
            recorded = sorted(characters.get((name, timing["run"]), []))
            names = timing.get("names") or ["chrome_" + tool for tool in timing["tools"]]
            if names != [action for _, action, _, _ in recorded]:
                raise ValueError(name + ": the recorded calls differ from the timed calls")
            per_run.append({"run": timing["run"], "tools": timing["tools"], "names": names,
                            "measures": timing.get("measures") or {}, "milliseconds": timing["milliseconds"],
                            "characters": [count for _, _, count, _ in recorded],
                            "refusals": [{"action": action, "code": code} for _, action, _, code in recorded if code]})
        tools = {tuple(run["names"]) for run in per_run}
        if len(tools) != 1:
            raise ValueError(name + ": the measured runs made different calls: " + repr(sorted(tools)))
        refusals = {json.dumps(run["refusals"]) for run in per_run}
        if len(refusals) != 1:
            raise ValueError(name + ": the measured runs ended differently: " + repr(sorted(refusals)))
        totals = [sum(run["characters"]) for run in per_run]
        out[name] = {
            "row": runs[0].get("row"),
            "plan": runs[0].get("plan"),
            "calls": len(per_run[0]["tools"]),
            "tools": per_run[0]["names"],
            "outcome": "refused" if per_run[0]["refusals"] else "done",
            "refusals": per_run[0]["refusals"],
            "characters": int(statistics.median(totals)),
            "characters_per_run": totals,
            "characters_per_call": [int(statistics.median(column)) for column in zip(*(run["characters"] for run in per_run))],
            "milliseconds": round(statistics.median(run["milliseconds"] for run in per_run), 1),
            "milliseconds_per_run": [run["milliseconds"] for run in per_run],
            "warmup_milliseconds": [round(run["milliseconds"], 1) for run in tasks[name]["warmup"]],
        }
        measured = sorted({key for run in per_run for key in run["measures"]})
        if measured:
            out[name]["measures_per_run"] = {key: [run["measures"].get(key) for run in per_run] for key in measured}
    return {
        "format": FORMAT,
        "what": "Group 16's public Chrome tasks. Characters are counted as Claude receives them. "
                "Wall time is the median of the measured runs after a warm-up.",
        "run_id": runner.get("run_id"),
        "sha": runner.get("sha"),
        "runner": {key: runner.get(key) for key in ("runner", "cpu", "cpus", "memory_bytes", "node", "chrome")},
        "measured_runs": len(next(iter(tasks.values()))["measured"]) if tasks else 0,
        "tasks": out,
        "sizes": sizes(),
    }


def read_rows(summary, baseline):
    """Check the read rows against their budgets and the frozen baseline."""
    tasks, frozen = summary["tasks"], baseline["tasks"]
    rows, misses = {}, []
    for name, row in OUTLINE_ROWS.items():
        if name not in tasks:
            misses.append("%s: not measured" % name)
            continue
        new, base = tasks[name], frozen[row["baseline"]]
        if (new["row"], new["outcome"]) != (base["row"], "done"):
            misses.append("%s: row %r, outcome %s; expected the baseline's row %r, done" % (name, new["row"], new["outcome"], base["row"]))
        most = max(new["characters_per_run"])
        checks = [("calls", new["calls"], row["calls"]), ("calls against the baseline", new["calls"], base["calls"]),
                  ("characters in a run against the baseline", most, base["characters"])]
        if row["characters"] is not None:
            checks.insert(1, ("characters in a run", most, row["characters"]))
        for what, measured, allowed in checks:
            if measured > allowed:
                misses.append("%s: %s %s, allowed %s" % (name, what, measured, allowed))
        rows[name] = {"row": new["row"], "baseline": row["baseline"], "budget": {"calls": row["calls"], "characters": row["characters"]},
                      "calls": new["calls"], "characters": new["characters"], "most_characters_in_a_run": most,
                      "milliseconds": new["milliseconds"], "baseline_calls": base["calls"], "baseline_characters": base["characters"]}
    return rows, misses


# Brief 28a, group 16's acting rows: each task, the frozen baseline's task of the same row, its budget
# (None: the row names only its calls), and what else the row bounds. F4's baseline is brief 20's
# refusal: "not worse" means the outcome and the calls, and its characters aren't compared.
ACT_ROWS = {
    "act_open_fact": {"baseline": "open_fact", "calls": 1, "characters": None},
    "act_f4_fill_send": {"baseline": "f4_fill_send", "calls": 3, "characters": None, "compare_characters": False,
                         "measures": {"approval_bytes": 9000}},
    "act_f7_three_pages": {"baseline": "f7_three_pages", "calls": 3, "characters": None},
    "act_f5_free_click": {"baseline": "f5_free_click", "calls": 1, "characters": 2500},
    "act_list_25_tabs": {"baseline": "list_25_tabs", "calls": 1, "characters": 3500},
}
INSTRUCTIONS_MOST, EVERY_APP_MOST = 2800, 4096


def act_rows(summary, baseline):
    """Group 16's acting rows of this run against their budgets and the frozen baseline; returns rows and misses."""
    tasks, frozen = summary["tasks"], baseline["tasks"]
    rows, misses = {}, []
    for name, row in ACT_ROWS.items():
        if name not in tasks:
            misses.append("%s: not measured" % name)
            continue
        new, base = tasks[name], frozen[row["baseline"]]
        if (new["row"], new["outcome"]) != (base["row"], "done"):
            misses.append("%s: row %r, outcome %s; expected the baseline's row %r, done" % (name, new["row"], new["outcome"], base["row"]))
        most = max(new["characters_per_run"])
        checks = [("calls", new["calls"], row["calls"]), ("calls against the baseline", new["calls"], base["calls"])]
        if row["characters"] is not None:
            checks.append(("characters in a run", most, row["characters"]))
        if row.get("compare_characters", True):
            checks.append(("characters in a run against the baseline", most, base["characters"]))
        bounded = {}
        for key, limit in row.get("measures", {}).items():
            values = (new.get("measures_per_run") or {}).get(key) or []
            if len(values) != len(new["characters_per_run"]) or not all(isinstance(value, int) for value in values):
                misses.append("%s: %s not measured in every run" % (name, key))
                continue
            bounded[key] = {"most": max(values), "allowed": limit, "per_run": values}
            checks.append((key + " in a run", max(values), limit))
        for what, measured, allowed in checks:
            if measured > allowed:
                misses.append("%s: %s %s, allowed %s" % (name, what, measured, allowed))
        rows[name] = {"row": new["row"], "baseline": row["baseline"], "budget": {"calls": row["calls"], "characters": row["characters"]},
                      "tools": new["tools"], "calls": new["calls"], "characters": new["characters"], "most_characters_in_a_run": most,
                      "milliseconds": new["milliseconds"], "baseline_calls": base["calls"], "baseline_characters": base["characters"],
                      "baseline_outcome": base["outcome"], **({"measures": bounded} if bounded else {})}
    return rows, misses


def latency_rows(summary, baseline):
    """Each timed task's median in this run, at most 1.5 times the new tools' median recorded for it.

    The recorded median is the comparison run's (COMPARISON_RUN), one entry per
    task in the baseline file's latency_comparisons. A sample's distance from
    this run's own median isn't checked.
    """
    rows, misses = {}, []
    for name in TIMED_TASKS:
        task = summary["tasks"].get(name)
        samples = task.get("milliseconds_per_run", []) if task else []
        if len(samples) != MEASURED_RUNS or not all(type(ms) in {int, float} and math.isfinite(ms) and ms > 0 for ms in samples):
            misses.append("%s: expected %d measured samples with positive milliseconds" % (name, MEASURED_RUNS))
            continue
        entries = [entry for entry in baseline.get("latency_comparisons", [])
                   if entry.get("run_id") == COMPARISON_RUN and (entry.get("new") or {}).get("task") == name]
        recorded = entries[0]["new"].get("milliseconds") if len(entries) == 1 else None
        if type(recorded) not in {int, float} or not math.isfinite(recorded) or recorded <= 0:
            misses.append("%s: the baseline file records no single new-tools median of run %s for it" % (name, COMPARISON_RUN))
            continue
        median = statistics.median(samples)
        allowed = RECORDED_LIMIT * recorded
        rows[name] = {"median_milliseconds": median, "recorded_median_milliseconds": recorded, "recorded_run": COMPARISON_RUN,
                      "allowed_milliseconds": allowed, "milliseconds_per_run": samples}
        if median > allowed:
            misses.append("%s: median %.3f ms, allowed %.3f ms (1.5 times its new-tools median %.1f ms in run %s)"
                          % (name, median, allowed, recorded, COMPARISON_RUN))
    return rows, misses


def size_rows(sizes_now, start=None):
    """The size rows: not above main's at 28a's start, the server instructions within 2,800, every app within 4,096."""
    start = start if start is not None else json.loads(START.read_text())
    main, misses = start["sizes"], []
    rows = {"descriptions_and_instructions": {"measured": sizes_now["descriptions_and_instructions"], "allowed": main["descriptions_and_instructions"],
                                              "pinned": start.get("final_sizes", {}).get("descriptions_and_instructions")},
            "names_and_input_schemas": {"measured": sizes_now["names_and_input_schemas"], "allowed": main["names_and_input_schemas"],
                                        "pinned": start.get("final_sizes", {}).get("names_and_input_schemas")},
            "instructions": {"measured": sizes_now["instructions"], "allowed": INSTRUCTIONS_MOST},
            "every_app_instructions": {"measured": {app: len(instructions_for(app)) for app in sorted(APPS)}, "allowed": EVERY_APP_MOST}}
    for name, row in rows.items():
        measured = row["measured"]
        for what, value in (measured.items() if isinstance(measured, dict) else [(name, measured)]):
            if value > row["allowed"]:
                misses.append("%s: %s, allowed %s" % (what, value, row["allowed"]))
    return rows, misses


def main(argv):
    if len(argv) not in (2, 3):
        raise SystemExit(__doc__)
    summary = summarize(argv[1])
    baseline = json.loads(BASELINE.read_text())
    rows, misses = read_rows(summary, baseline)
    acting, act_misses = act_rows(summary, baseline)
    latency, latency_misses = latency_rows(summary, baseline)
    sized, size_misses = size_rows(summary["sizes"])
    summary.update(read_rows=rows, read_row_misses=misses,
                   act_rows=acting, act_row_misses=act_misses, latency_rows=latency, latency_misses=latency_misses,
                   size_rows=sized, size_row_misses=size_misses)
    target = Path(argv[2]) if len(argv) == 3 else Path(argv[1]) / "efficiency-measured.json"
    target.write_text(json.dumps(summary, indent=2) + "\n")
    for name, task in summary["tasks"].items():
        print("EFFICIENCY %s: %d calls, %d characters, %.1f ms, %s" % (name, task["calls"], task["characters"], task["milliseconds"],
                                                                 task["outcome"]))
    print("EFFICIENCY sizes:", json.dumps(summary["sizes"]))
    for name, row in latency.items():
        print("EFFICIENCY latency", name, json.dumps(row))
    every = misses + act_misses + latency_misses + size_misses
    for miss in every:
        print("EFFICIENCY MISS", miss)
    if every:
        raise SystemExit("Group 16's rows missed %d check(s); see EFFICIENCY MISS above." % len(every))
    print("EFFICIENCY rows hold:", ", ".join([*rows, *acting, *sized]))


if __name__ == "__main__":
    main(sys.argv)
