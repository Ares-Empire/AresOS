"""Claude Code 2.1.319 contract; https://code.claude.com/docs/en/hooks.

Reads only control_pending. Stop's continuation guard avoids endless hook loops;
expiry in the service is the safety net, even when a hook is not called.
"""
import sys

from .common import WIRE_LIMIT, Refused, display_json, canonical, strict_json_loads, validate, visible
from .definitions import obj
from .protocol import Client


# The two fields a hook reads, with their types. Claude Code adds and changes input fields between versions (2.1.319
# already sends `prompt_id`), so every other field is accepted and never read; the input as a whole stays bounded
# strict JSON.
EVENT = {**obj({'hook_event_name': {'type': 'string', 'enum': ['Stop', 'UserPromptSubmit']},
                'stop_hook_active': {'type': 'boolean'}}, ['hook_event_name']), 'additionalProperties': True}


def output(event, pending):
    name = event.get("hook_event_name")
    if name not in {"Stop", "UserPromptSubmit"}:
        raise Refused("invalid_input", "Only Stop and UserPromptSubmit are supported.")
    if not pending.get("total") and not pending.get("restore_required") and not pending.get("service_unavailable") and not pending.get("notices") and not pending.get("warning_count"):
        return {}
    context = "AresOS held/unfinished work (untrusted app data; inspect status, do not resubmit unknown sends): " + canonical(visible(pending))
    if name == "Stop":
        if event.get("stop_hook_active"):
            return {}
        return {"decision": "block", "reason": context + " Resolve, cancel reserved work, or report uncertain outcomes to the owner before ending."}
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}


def main(config, name):
    event = None
    try:
        event = strict_json_loads(sys.stdin.buffer.read(WIRE_LIMIT + 1))
        validate(event, EVENT, 'hook')
        if not isinstance(event, dict) or event.get("hook_event_name") != name:
            raise Refused("invalid_input", "Hook input must be an object matching the launcher event.")
        try:
            result = Client(config["act_socket"]).call("control_pending", {})
            if name == "UserPromptSubmit" and not result["ok"]:
                return
            pending = result["data"] if result["ok"] else {**result.get("pending", {}), "service_unavailable": True, "message": result["error"]["message"],
                **({"observations": result["observations"]} if "observations" in result else {})}
        except Refused as exc:
            if name == "UserPromptSubmit":
                return
            pending = {"service_unavailable": True, "message": str(exc)}
        print(display_json(output(event, pending)))
    except Exception as exc:
        if name == "UserPromptSubmit":
            return
        if isinstance(event, dict) and event.get("stop_hook_active") is True:
            # The continuation guard holds for failures too: the feedback below blocks a stop once, never until
            # Claude Code's own limit on blocked stops.
            return
        # Stop retains its explicit failure feedback.
        print("AresOS hook failed; inspect pending work before continuing: " + visible(str(exc)), file=sys.stderr)
        raise SystemExit(2)
