# Scoped package review — 4a4c531d

Reviewer: gpt-6.1-sol (high), read-only.

**FIX:** a withheld textarea has no `safe.value`, but compose rendering passes it
to `append()`, which calls `.replace()`. Normal read succeeds; control facts for
an adjacent Continue or Send fail before reload or withheld-form refusal.
Production-code reproduction observed zero value getters followed by that error.
Omit withheld values from compose rendering, retain unknown-history metadata,
and add ordinary-control, submit-control and removal regressions.

201 focused Node tests passed. The examined private binding, metadata-only
preparation and one-call handling otherwise meet addendum -f. Main's interactive
additions and the exact 8b7e799c service unit remain intact. Remote acceptance,
latency and final CI are outside this review. No edits, browser/profile/container
access or GitHub mutation.

CHANGES-NEEDED
