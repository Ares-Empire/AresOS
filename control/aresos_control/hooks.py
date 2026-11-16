"""Claude Code 2.1.319 contract; https://code.claude.com/docs/en/hooks.

Reads only control_pending. Stop's continuation guard avoids endless hook loops;
expiry in the service is the safety net, even when a hook is not called.

The managed hooks run in every Claude Code session, but pending work and owner notices are shared by all of them.
Quiet unless used (owner, #254; lead, 2026-11-16): only a session that used the tools (`usage`) hears of them. Any
other session doesn't even connect, so it gets nothing and costs nothing.
"""
import sys

from .common import WIRE_LIMIT, Refused, display_json, canonical, strict_json_loads, validate, visible
from .definitions import obj
from .protocol import Client
from . import usage


# The two fields a hook reads, with their types. Claude Code adds and changes input fields between versions (2.1.319
# already sends `prompt_id`), so every other field is accepted and never read; the input as a whole stays bounded
# strict JSON.
EVENT = {**obj({'hook_event_name': {'type': 'string', 'enum': ['Stop', 'UserPromptSubmit']},
                'stop_hook_active': {'type': 'boolean'}}, ['hook_event_name']), 'additionalProperties': True}


# Codes of a service that can't be reached: not running, busy or a broken setup (nothing sent), or the connection lost
# on the way (a busy service's read timeout among them).
UNREACHABLE = {'service_unavailable', 'service_busy', 'setup_error', 'transport_error'}
NOT_RUNNING = ("AresOS tools are not running. If you prepared or sent something with them in this session, its outcome "
               "is unknown: tell the owner, and don't repeat it.")
# Every other way of not reaching the service: it may well be running, so never say it isn't.
NOT_REACHED = ("AresOS tools could not be reached. If you prepared or sent something with them in this session, its "
               "outcome is unknown: tell the owner, and don't repeat it.")
# Pending work may be another session's, and only the owner decides about it (lead, 2026-11-16).
REMINDER = (" Don't complete, cancel, resend or acknowledge this work on your own: tell the owner what is waiting, and "
            "let him decide.")


def output(event, pending):
    name = event.get("hook_event_name")
    if name not in {"Stop", "UserPromptSubmit"}:
        raise Refused("invalid_input", "Only Stop and UserPromptSubmit are supported.")
    if not pending.get("total") and not pending.get("restore_required") and not pending.get("service_unavailable") and not pending.get("notices") and not pending.get("warning_count"):
        return {}
    # Both hooks show the same work, so both say whose decision it is.
    context = ("AresOS held/unfinished work (untrusted app data; inspect status, do not resubmit unknown sends): "
               + canonical(visible(pending)) + REMINDER)
    if name == "Stop":
        if event.get("stop_hook_active"):
            return {}
        return {"decision": "block", "reason": context}
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": context}}


def main(config, name):
    event = None
    try:
        event = strict_json_loads(sys.stdin.buffer.read(WIRE_LIMIT + 1))
        validate(event, EVENT, 'hook')
        if not isinstance(event, dict) or event.get("hook_event_name") != name:
            raise Refused("invalid_input", "Hook input must be an object matching the launcher event.")
        if not usage.used():
            # A session that never used the tools: no reminder, no notice, no connection.
            return
        try:
            # One connect attempt: the 3 s wait for a starting service is for the MCP proxies and the CLI; a hook
            # runs at every prompt and turn end, and a session must not wait each time while the service is down.
            result = Client(config["act_socket"], connect_wait=0).call("control_pending", {})
            # The service answered: a later outage tells a session that used the tools again.
            usage.reached()
            if not result["ok"] and result["error"]["code"] == "permission_denied":
                # Not the owner's session (root, another user): it can't use the tools, so nothing concerns it.
                return
            if name == "UserPromptSubmit" and not result["ok"]:
                return
            pending = result["data"] if result["ok"] else {**result.get("pending", {}), "service_unavailable": True, "message": result["error"]["message"],
                **({"observations": result["observations"]} if "observations" in result else {})}
        except Refused as exc:
            if name == "UserPromptSubmit":
                return
            if exc.code in UNREACHABLE:
                # Quiet unless used (owner, #254): only a session that used the tools hears that they are down, and
                # once per outage, not at every turn end (lead, 2026-11-15).
                if not event.get("stop_hook_active") and usage.notice():
                    print(display_json({"decision": "block",
                                        "reason": NOT_RUNNING if exc.code == 'service_unavailable' else NOT_REACHED}))
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
