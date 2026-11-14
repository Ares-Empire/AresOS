"""Hooks of "his own", for the CI guest only (package 18c, B2 checks 6 and 9).

`own-hook.py EVENT LOG`: appends the event Claude Code passed on stdin as one JSON line to LOG. For Stop and
UserPromptSubmit it stands for a notification hook he set up himself and prints nothing. For PermissionRequest it is
check 9's user-level allow hook and approves the request, as B1's container case does.
"""
import json
import sys


def main(event_name, log):
    event = json.load(sys.stdin)
    with open(log, 'a') as stream:
        stream.write(json.dumps({'event': event_name, 'input': event}) + '\n')
    if event_name == 'PermissionRequest':
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PermissionRequest',
                                                 'decision': {'behavior': 'allow'}}}))


if __name__ == '__main__':
    main(*sys.argv[1:3])
