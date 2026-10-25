# Keyboard fixtures

`stock-two-bootc.json` projects the booted/rollback slots verbatim from retained
11f full-2 `stock-status.json`: same checksum, booted serial 1, rollback serial 0.
That original also has a **newer staged update**: it is deliberately removed only
in this synthetic starting-state fixture. The unmodified original must be rejected
by the repair. `stock-two-rpm.json` converts those identities into the JSON fields
emitted by rpm-ostree v2026.3 (`rpmostreed-deployment-utils.cxx` and `rust/src/daemon.rs`),
with no layering and no transaction. It is a constructed fixture, not captured rpm output.

`de-dumpkeys.txt` retains the two 13d diagnostic rows, including '+' and spaces.
`us-dumpkeys.txt` is a synthetic dumpkeys example from kbd v2.9.0 us.map's
qwerty-layout.inc (21=y, 44=z), rendered with dump.c's KT_LETTER '+' notation.
Neither synthetic fixture claims a new VM observation.
