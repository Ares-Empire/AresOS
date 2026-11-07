"""Claude Code 2.1.319 contract; https://code.claude.com/docs/en/hooks.

Reads only control_pending. Stop's continuation guard avoids endless hook loops;
expiry in the service is the safety net, even when a hook is not called.
"""
import json
import sys

from .common import Refused, canonical, visible
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


def main(config):
    event = json.loads(sys.stdin.buffer.read(65537))
    try:
        result = Client(config["act_socket"]).call("control_pending", {})
        pending = result["data"] if result["ok"] else {"service_unavailable": True, "message": result["error"]["message"]}
    except Refused as exc:
        pending = {"service_unavailable": True, "message": str(exc)}
    print(canonical(output(event, pending)))
