"""Claude Code 2.1.319 contract; https://code.claude.com/docs/en/hooks.

Reads only control_pending. Stop's continuation guard avoids endless hook loops;
expiry in the service is the safety net, even when a hook is not called.

The managed hooks run in every Claude Code session, but pending work and owner notices are shared by all of them.
Quiet unless used (owner, #254; lead, 2026-11-16): only a session that used the tools (`usage`) hears of them. Any
other session doesn't even connect, so it gets nothing and costs nothing, whatever fails: usage is decided first, from
the process tree and the marks alone, before the hook's input is even parsed.

Only a JSON decision ever blocks a stop; a hook never exits 2 (lead, 2026-11-16). Claude Code reads a Stop hook's exit
code 2 as "don't stop" and any other non-zero exit as a visible hook error, so a failure of the hook itself is told
(to a session that used the tools only) as a `{"decision": "block"}` like any other, and only when the input readably
says `stop_hook_active` is false, so never twice in a row (`first_stop`). The managed commands wrap Python in a shell
guard that always exits 0 (`boundary_policy.hook_command`), for what fails before this code runs.
"""
import json
import sys

from .common import WIRE_LIMIT, Refused, display_json, canonical, shortened, strict_json_loads, validate, visible
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
# What a session that used the tools hears when the Stop hook itself fails, followed by the failure.
FAILED = "AresOS hook failed; inspect pending work before continuing: "
# Input past the bound is read in steps of this size and dropped.
DRAIN_STEP = 64 * 1024


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


def read_input():
    """The hook's input: its first WIRE_LIMIT + 1 bytes (more is refused as too large), with the rest read to the end
    and dropped, so Claude Code can always write all of it, whatever the hook then does with it."""
    stream = sys.stdin.buffer
    kept = stream.read(WIRE_LIMIT + 1)
    while stream.read(DRAIN_STEP):
        pass
    return kept


def first_stop(event, raw):
    """Whether the input readably says this stop is not already a Stop hook's continuation: `stop_hook_active` false.

    From the strictly parsed event when there is one, else from the same bytes parsed leniently, for this one field
    only. Input the strict decoder refuses (a lone surrogate in a field the hook never reads, say) must not block every
    stop: Claude Code's cap on blocked stops starts again after each tool call (review 1, should-fix 1). Anything else
    (true, missing, not a boolean, input that can't be read even leniently) is not a first stop.
    """
    if event is None and raw is not None:
        try:
            event = json.loads(raw.decode('utf-8-sig', errors='replace'))
        except Exception:
            return False
    return isinstance(event, dict) and event.get("stop_hook_active") is False


def failed(exc):
    """The Stop hook's own failure, told as a decision: plain json, so it doesn't depend on what may have failed."""
    return json.dumps({"decision": "block", "reason": FAILED + shortened(visible(str(exc)))},
                      ensure_ascii=True, separators=(",", ":"))


def main(config, name):
    try:
        used = usage.used()
    except Exception:
        # `used` answers no for marks or processes it can't read, so only a bug in it raises, and that bug would reach
        # every session alike. Quiet is the safe side: the work stays held in the service, every tool result still
        # carries it, `aresos control pending` lists it, and it expires unrun.
        used = False
    if not used:
        # A session that never used the tools: no reminder, no notice, no connection. Its input isn't even parsed, so
        # nothing in it and no failure on it can reach the session; it is still read to the end.
        try:
            read_input()
        except Exception:
            pass
        return
    event = raw = None
    try:
        raw = read_input()
        event = strict_json_loads(raw)
        validate(event, EVENT, 'hook')
        if not isinstance(event, dict) or event.get("hook_event_name") != name:
            raise Refused("invalid_input", "Hook input must be an object matching the launcher event.")
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
        if not first_stop(event, raw):
            # The continuation guard holds for failures too: the feedback below blocks a stop once, never until
            # Claude Code's own limit on blocked stops (which starts again after each tool call).
            return
        # A session that used the tools hears of the failure as a decision, never through an exit code.
        print(failed(exc))
