"""Run from the checkout: python3 control/generate.py [--check]. No dependencies."""
import json
from pathlib import Path
import sys

from aresos_control.definitions import ACTIONS, tools_for

ROOT = Path(__file__).resolve().parent.parent


def generated():
    apps = sorted({a.app for a in ACTIONS})
    files = {}
    for app in apps:
        files[f"control/generated/{app}-tools.json"] = json.dumps(tools_for(app), indent=2) + "\n"
    ask = [f"mcp__{a.app}__{a.verb}" for a in ACTIONS if a.effect in {"send", "delete"} and not a.owner_only]
    files["control/settings/ask-rules.json"] = json.dumps({"permissions": {"ask": ask}}, indent=2) + "\n"
    help_text = "Usage: aresos [admin] <app> <action> [--input JSON] [--json]\n       aresos log [--input JSON]\n\nActions (input is the definition's JSON object; --help on any action shows its schema):\n"
    doc = "# Control tools (generated; do not edit)\n\nSettings and packaging are drafts. Run `python3 control/generate.py` after editing the catalogue.\n\n"
    for a in ACTIONS:
        command = f"aresos {'admin ' if a.owner_only else ''}{a.app} {a.verb}"
        help_text += f"  {command} [{a.effect}]\n"
        doc += f"## `{a.name}`\n\n`{command}`; effect **{a.effect}**; owner-only **{a.owner_only}**.\n\n{a.description}\n\nInput:\n```json\n{json.dumps(a.input, indent=2)}\n```\n\n"
    files["control/generated/cli-help.txt"] = help_text
    files["docs/control/TOOLS.md"] = doc + "All results use the bounded envelope `ok`, `data` or `error`, and `pending`. Result JSON schema:\n\n```json\n" + json.dumps(ACTIONS[0].tool()["outputSchema"], indent=2) + "\n```\n"
    return files


def main():
    drift = []
    for name, content in generated().items():
        path = ROOT / name
        if "--check" in sys.argv:
            if not path.exists() or path.read_text() != content:
                drift.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if drift:
        raise SystemExit("Generated files drifted: " + ", ".join(drift))
    print("Generated artifacts match definitions" if "--check" in sys.argv else "Generated tools, help, reference and ask rules")


if __name__ == "__main__":
    main()
