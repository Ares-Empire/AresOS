"""Brief 28, item 4: one deadline for a whole chrome_outline call.

The base's client gives up on a read after 10 seconds (`protocol.READ_TIMEOUT`)
and then can't know what ran, while the service would go on. So the call answers
by second CALL of its own clock, which starts before the engine's first look at
pending (`engine.request`) and runs until the response is built:

- that first look checks each reserved approval by second FIRST_LOOK;
- `until` waits at most to second UNTIL, `timeout_ms` counted from the start;
- every command of the read answers by second COMMANDS; with `tabs` each tab gets
  an equal share of what is left to that second when its turn comes, so time a
  tab doesn't use passes on;
- the looks after the read (the read's own measure and the engine's response)
  check approvals by second LAST_LOOKS, so that the bridge's half second of grace
  (`bridge.GRACE`) still leaves room to build the response before second CALL.

A command that doesn't answer in its time makes its tab `not_read`; an approval
whose check doesn't is `unchecked` for the rest of the call, never refused.
"""
import time

CALL, COMMANDS, UNTIL, FIRST_LOOK, LAST_LOOKS = 8.0, 7.0, 6.0, 1.0, 7.25
NOT_READ = 'time ran out; read this tab by itself'
UNCHECKED = {'validity': 'unchecked'}


class Deadline:
    def __init__(self):
        self.start = time.monotonic()
        # Set when the read begins: from then on a look at pending gets the time to LAST_LOOKS.
        self.reading = False
        # Reserved operations whose check ran out of time in this call; later looks don't ask again.
        self.unchecked = set()

    def at(self, second):
        return self.start + second

    def share(self, remaining):
        """The end of the next tab's turn: an equal part of what is left to COMMANDS among the tabs still to read."""
        now = time.monotonic()
        return now + max(0.0, self.at(COMMANDS) - now) / remaining

    def look(self):
        """When the approval checks of a look at pending have to end."""
        return self.at(LAST_LOOKS if self.reading else FIRST_LOOK)
