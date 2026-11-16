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

Group 16's second half, the read rows: each task of the new read
(chrome_outline, OUTLINE_ROWS) is checked against its budget and against the
baseline's task of the same row (efficiency-baseline.json): its calls and its
characters in every measured run may be no more than the budget's and the
baseline's. Its time may be no more than 1.10 times brief 20's median for the
same row in the same run plus 50 ms, the latency comparison's rule; for the
first read of F1 that comparison is the one the brief names, and it is written
as an entry for the baseline file's latency_comparisons. The step fails when a
row misses, after the record is written.
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from aresos_control.common import display_json  # noqa: E402
from aresos_control.definitions import instructions_for, tools_for  # noqa: E402
from aresos_control.results import bound_result  # noqa: E402

FORMAT = 1
BASELINE = Path(__file__).resolve().parent / "efficiency-baseline.json"
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
# "Latency": the new read takes at most this times brief 20's median plus this, in one run.
SLOWER, SLACK_MS = 1.10, 50.0
COMPARED = "outline_f1_first_read"


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
            if ["chrome_" + tool for tool in timing["tools"]] != [action for _, action, _, _ in recorded]:
                raise ValueError(name + ": the recorded calls differ from the timed calls")
            per_run.append({"run": timing["run"], "tools": timing["tools"], "milliseconds": timing["milliseconds"],
                            "characters": [count for _, _, count, _ in recorded],
                            "refusals": [{"action": action, "code": code} for _, action, _, code in recorded if code]})
        tools = {tuple(run["tools"]) for run in per_run}
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
            "tools": ["chrome_" + tool for tool in per_run[0]["tools"]],
            "outcome": "refused" if per_run[0]["refusals"] else "done",
            "refusals": per_run[0]["refusals"],
            "characters": int(statistics.median(totals)),
            "characters_per_run": totals,
            "characters_per_call": [int(statistics.median(column)) for column in zip(*(run["characters"] for run in per_run))],
            "milliseconds": round(statistics.median(run["milliseconds"] for run in per_run), 1),
            "milliseconds_per_run": [round(run["milliseconds"], 1) for run in per_run],
            "warmup_milliseconds": [round(run["milliseconds"], 1) for run in tasks[name]["warmup"]],
        }
    return {
        "format": FORMAT,
        "what": "Brief 28's efficiency baseline: brief 20's tools on the group 16 fixtures, used as well as they allow "
                "(control/chrome/ci/efficiency-probe.mjs). Characters are the JSON text of each tool result as "
                "Claude receives it; wall time is the median of the measured runs after one warm-up. A task whose "
                "outcome is \"refused\" ends in the refusal listed: brief 20's tools can't finish that row.",
        "run_id": runner.get("run_id"),
        "sha": runner.get("sha"),
        "runner": {key: runner.get(key) for key in ("runner", "cpu", "cpus", "memory_bytes", "node", "chrome")},
        "measured_runs": len(next(iter(tasks.values()))["measured"]) if tasks else 0,
        "tasks": out,
        "sizes": sizes(),
        "latency_comparisons": [],
    }


def read_rows(summary, baseline):
    """Group 16's read rows of this run: each new-read task against its budget and its baseline row.

    Returns the rows, the latency comparison (an entry for the baseline file's
    latency_comparisons) and the misses, each a sentence; no miss means the rows hold.
    """
    tasks, frozen = summary["tasks"], baseline["tasks"]
    rows, misses = {}, []
    for name, row in OUTLINE_ROWS.items():
        if name not in tasks:
            misses.append("%s: not measured" % name)
            continue
        new, base, now = tasks[name], frozen[row["baseline"]], tasks.get(row["baseline"])
        if now is None:
            misses.append("%s: brief 20's %s was not measured in this run" % (name, row["baseline"]))
            continue
        if (new["row"], new["outcome"]) != (base["row"], "done"):
            misses.append("%s: row %r, outcome %s; expected the baseline's row %r, done" % (name, new["row"], new["outcome"], base["row"]))
        most = max(new["characters_per_run"])
        limit_ms = round(SLOWER * now["milliseconds"] + SLACK_MS, 1)
        checks = [("calls", new["calls"], row["calls"]), ("calls against the baseline", new["calls"], base["calls"]),
                  ("characters in a run against the baseline", most, base["characters"]),
                  ("milliseconds against brief 20's in this run", new["milliseconds"], limit_ms)]
        if row["characters"] is not None:
            checks.insert(1, ("characters in a run", most, row["characters"]))
        for what, measured, allowed in checks:
            if measured > allowed:
                misses.append("%s: %s %s, allowed %s" % (name, what, measured, allowed))
        rows[name] = {"row": new["row"], "baseline": row["baseline"], "budget": {"calls": row["calls"], "characters": row["characters"]},
                      "calls": new["calls"], "characters": new["characters"], "most_characters_in_a_run": most,
                      "milliseconds": new["milliseconds"], "baseline_calls": base["calls"], "baseline_characters": base["characters"],
                      "brief_20_milliseconds_this_run": now["milliseconds"], "milliseconds_allowed": limit_ms}
    comparison = None
    if COMPARED in rows:
        old, new = tasks[OUTLINE_ROWS[COMPARED]["baseline"]], tasks[COMPARED]
        comparison = {"run_id": summary["run_id"], "sha": summary["sha"], "row": new["row"], "runs": summary["measured_runs"],
                      "old": {"tool": "chrome_read", "milliseconds": old["milliseconds"], "milliseconds_per_run": old["milliseconds_per_run"]},
                      "new": {"tool": "chrome_outline", "milliseconds": new["milliseconds"], "milliseconds_per_run": new["milliseconds_per_run"]},
                      "rule": "new median <= %.2f x old median + %d ms" % (SLOWER, SLACK_MS),
                      "allowed_milliseconds": rows[COMPARED]["milliseconds_allowed"],
                      "passed": new["milliseconds"] <= rows[COMPARED]["milliseconds_allowed"]}
    return rows, comparison, misses


def main(argv):
    if len(argv) not in (2, 3):
        raise SystemExit(__doc__)
    summary = summarize(argv[1])
    rows, comparison, misses = read_rows(summary, json.loads(BASELINE.read_text()))
    summary.update(read_rows=rows, latency_comparison=comparison, read_row_misses=misses)
    target = Path(argv[2]) if len(argv) == 3 else Path(argv[1]) / "efficiency-measured.json"
    target.write_text(json.dumps(summary, indent=2) + "\n")
    for name, task in summary["tasks"].items():
        print("EFFICIENCY %s: %d calls, %d characters, %.1f ms, %s" % (name, task["calls"], task["characters"], task["milliseconds"],
                                                                 task["outcome"]))
    print("EFFICIENCY sizes:", json.dumps(summary["sizes"]))
    print("EFFICIENCY latency comparison:", json.dumps(comparison))
    for miss in misses:
        print("EFFICIENCY MISS", miss)
    if misses:
        raise SystemExit("Group 16's read rows missed %d check(s); see EFFICIENCY MISS above." % len(misses))
    print("EFFICIENCY read rows hold:", ", ".join(rows))


if __name__ == "__main__":
    main(sys.argv)
