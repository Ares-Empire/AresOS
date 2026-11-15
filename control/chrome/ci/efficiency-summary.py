"""Brief 28, group 16: turns an efficiency probe's record into its numbers.

usage: efficiency-summary.py <probe output directory> [<output file>]

Characters are counted on each result as Claude receives it: the text the MCP
proxy sends (proxy.serve: display_json(bound_result(result))). Calls and tools
must be the same in every measured run; the wall time of a task is the median
of the measured runs, after the warm-up. The sizes of what a session loads are
measured from the same tree: tool descriptions plus the server instructions,
and tool names plus input schemas as compact JSON.
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
        if not call["result"].get("ok"):
            raise ValueError("%s run %s: %s failed" % (call["task"], call["run"], call["action"]))
        key = (call["task"], call["run"])
        characters.setdefault(key, []).append((call["index"], call["action"], received(call["result"])))
    out = {}
    for name in order:
        runs = tasks[name]["measured"]
        if not runs or not tasks[name]["warmup"]:
            raise ValueError(name + ": a warm-up and measured runs are both required")
        per_run = []
        for timing in runs:
            recorded = sorted(characters.get((name, timing["run"]), []))
            if ["chrome_" + tool for tool in timing["tools"]] != [action for _, action, _ in recorded]:
                raise ValueError(name + ": the recorded calls differ from the timed calls")
            per_run.append({"run": timing["run"], "tools": timing["tools"], "milliseconds": timing["milliseconds"],
                            "characters": [count for _, _, count in recorded]})
        tools = {tuple(run["tools"]) for run in per_run}
        if len(tools) != 1:
            raise ValueError(name + ": the measured runs made different calls: " + repr(sorted(tools)))
        totals = [sum(run["characters"]) for run in per_run]
        out[name] = {
            "calls": len(per_run[0]["tools"]),
            "tools": ["chrome_" + tool for tool in per_run[0]["tools"]],
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
                "Claude receives it; wall time is the median of the measured runs after one warm-up.",
        "run_id": runner.get("run_id"),
        "sha": runner.get("sha"),
        "runner": {key: runner.get(key) for key in ("runner", "cpu", "cpus", "memory_bytes", "node", "chrome")},
        "measured_runs": len(next(iter(tasks.values()))["measured"]) if tasks else 0,
        "tasks": out,
        "sizes": sizes(),
        "latency_comparisons": [],
    }


def main(argv):
    if len(argv) not in (2, 3):
        raise SystemExit(__doc__)
    summary = summarize(argv[1])
    target = Path(argv[2]) if len(argv) == 3 else Path(argv[1]) / "efficiency-measured.json"
    target.write_text(json.dumps(summary, indent=2) + "\n")
    for name, task in summary["tasks"].items():
        print("EFFICIENCY %s: %d calls, %d characters, %.1f ms" % (name, task["calls"], task["characters"], task["milliseconds"]))
    print("EFFICIENCY sizes:", json.dumps(summary["sizes"]))


if __name__ == "__main__":
    main(sys.argv)
