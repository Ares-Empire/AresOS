"""Run from the checkout: python3 control/generate.py [--check]. No dependencies."""
import json
from pathlib import Path
import sys

from aresos_control.definitions import ACTIONS, tools_for
from aresos_control.boundary_policy import asking_rules, managed_settings, managed_mcp

ROOT = Path(__file__).resolve().parent.parent


def schema_check(schema):
    allowed = {"type", "properties", "required", "additionalProperties", "items", "enum", "minItems", "maxItems",
               "minLength", "maxLength", "minimum", "maximum", "anyOf"}
    if not isinstance(schema, dict) or not schema.keys() <= allowed:
        raise ValueError("Schema uses an unsupported keyword: " + str(schema))
    if schema.get("type") not in {None, "object", "array", "string", "integer", "number", "boolean", "null"}:
        raise ValueError("Unsupported schema type")
    for child in [*schema.get("properties", {}).values(), *schema.get("anyOf", [])]:
        schema_check(child)
    if "items" in schema:
        schema_check(schema["items"])


def generated():
    for action in ACTIONS:
        if action.result is None:
            raise ValueError("Missing result schema: " + action.name)
        schema_check(action.input)
        schema_check(action.tool()["outputSchema"])
    apps = sorted({a.app for a in ACTIONS})
    files = {}
    for app in apps:
        files[f"control/generated/{app}-tools.json"] = json.dumps(tools_for(app), indent=2) + "\n"
    from aresos_control.chrome.policy import WORDS, WORD_LIST_VERSION, FIXED_HOSTS, CDP_METHODS, HOLD_MS
    chrome_policy = {'words':[word.casefold() for word in WORDS], 'wordListVersion':WORD_LIST_VERSION,
                     'fixedHosts':FIXED_HOSTS, 'cdpMethods':CDP_METHODS, 'holdMs':HOLD_MS}
    files['control/chrome/extension/policy.js'] = 'export const POLICY = ' + json.dumps(chrome_policy, ensure_ascii=True, indent=2) + ';\n'
    ask = asking_rules()
    files["control/settings/ask-rules.json"] = json.dumps({"permissions": {"ask": ask}}, indent=2) + "\n"
    files['control/settings/managed-settings.draft.json'] = json.dumps(managed_settings(), indent=2) + '\n'
    files['control/settings/managed-mcp.json'] = json.dumps(managed_mcp(), indent=2) + '\n'
    help_text = "Usage: aresos [admin] <app> <action> [--input JSON] [--json]\n       aresos log [--input JSON]\n\nActions (input is the definition's JSON object; --help on any action shows its schema):\n"
    doc = "# Control tools (generated; do not edit)\n\nSettings and packaging are drafts. Run `python3 control/generate.py` after editing the catalogue.\n\n"
    for a in ACTIONS:
        command = f"aresos {'admin ' if a.owner_only else ''}{a.app} {a.verb}"
        help_text += f"  {command} [{a.effect}]\n"
        doc += f"## `{a.name}`\n\n`{command}`; effect **{a.effect}**; owner-only **{a.owner_only}**.\n\n{a.description}\n\nInput:\n```json\n{json.dumps(a.input, indent=2)}\n```\n\nResult data:\n```json\n{json.dumps(a.result, indent=2)}\n```\n\n"
    files["control/generated/cli-help.txt"] = help_text
    files["docs/control/TOOLS.md"] = doc + "All results use the bounded envelope `ok`, `data` or `error`, and `pending`. Each generated MCP tool includes its complete output schema.\n"
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
