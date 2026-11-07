"""Claude Code 2.1.319 contract; https://code.claude.com/docs/en/hooks.

Reads only control_pending. Stop's continuation guard avoids endless hook loops;
expiry in the service is the safety net, even when a hook is not called.
"""
import sys

from .common import Refused, canonical, strict_json_loads, visible
from .protocol import Client


def output(event, pending):
    name = event.get("hook_event_name")
    if name not in {"Stop", "UserPromptSubmit"}:
        raise Refused("invalid_input", "Only Stop and UserPromptSubmit are supported.")
    if not pending.get("total") and not pending.get("restore_required") and not pending.get("service_unavailable"):
        return {}
    context = "AresOS held/unfinished work (untrusted app data; inspect status, do not resubmit unknown sends): " + canonical(visible(pending))
    if name == "Stop":
        if event.get("stop_hook_active"):
            return {}
        return {"decision": "block", "reason": context + " Resolve, cancel reserved work, or report uncertain outcomes to the owner before ending."}
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}


def main(config, name):
    try:
        event = strict_json_loads(sys.stdin.buffer.read())
        if not isinstance(event, dict) or event.get("hook_event_name") != name:
            raise Refused("invalid_input", "Hook input must be an object matching the launcher event.")
        try:
            result = Client(config["act_socket"]).call("control_pending", {})
            if name == "UserPromptSubmit" and not result["ok"]:
                return
            pending = result["data"] if result["ok"] else {"service_unavailable": True, "message": result["error"]["message"]}
        except Refused as exc:
            if name == "UserPromptSubmit":
                return
            pending = {"service_unavailable": True, "message": str(exc)}
        print(canonical(output(event, pending)))
    except Exception as exc:
        if name == "UserPromptSubmit":
            return
        # Stop retains its explicit failure feedback.
        print("AresOS hook failed; inspect pending work before continuing: " + visible(str(exc)), file=sys.stderr)
        raise SystemExit(2)
