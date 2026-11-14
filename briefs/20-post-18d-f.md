# 20, post-18d f: three changes to the late-reader work

From the security re-check of linux-tools' brief 28 (astra, `reviews/28-chrome-capability/BRIEF-SECURITY-2.md` on
branch `briefs/28-chrome-capability`). The lead weighed them and adopts all three (2026-11-13 evening), so this
package and brief 28 match. Where they differ, this brief wins over `briefs/20-post-18d-d.md` and `-e.md`.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## 1. Scope (replaces `-d`'s exemptions)

In a document the reader didn't watch from its start:
- **every `<input>` that can hold typed text, whatever its current type** (`search`, `email`, `url`, `tel`, `number`,
  `text`, unknown), and **every `<textarea>`**, shows only "filled" or "empty", and its value is read only through
  `chrome_read_typed_fields`. A type can have been switched from password, and this package's own password-kind rule
  covers masked textareas;
- **editable areas (`contenteditable`) stay read.** Add a known-limit line: a secret masked inside an editable area
  can be read. This point isn't final: the owner decides on board #216 between reading editors without asking and
  asking first for editors too. Build it as written, but keep editable areas easy to move into
  `chrome_read_typed_fields`' scope and its binding. If he picks "ask first", one small addendum follows, with a test
  of a masked, unlabelled secret revealed in an editable area before the take and read only after approval;
- checkboxes, radios, selects, ranges and date kinds keep their values;
- credential-like fields are never read.

## 2. Binding of the asking read (replaces "a changed field list re-asks")

The service **prepares** the read: the connection, the tab, each frame's document, the reader instance, the exact
element identities, and the labels shown. The question is generated from that preparation and verified like the send
input, and the approval is used once. A replaced or relabelled field, a navigated frame, or a field that became
credential-like refuses before any value is read.

Tests: a same-label replacement, duplicate and unlabelled fields, a frame navigation, an altered question, a replay.

## 3. A new hole: submitting a form that holds a withheld field

A recognised submission of a form that holds a field withheld for unknown history is refused. Today the question
neither shows nor binds that content. Known password fields keep their existing rule. The reason says: "send it
yourself, or let Claude reload the tab first". An approved asking read does not lift the refusal.

Tests: the late-shadow-root form, and a value change while the approval waits.

## The `main` merge

`main` now also has PR #43 (`1108fc30`, linux-tools):
- `aresos-toold.service` with the network lines, and `control/tests/test_unit.py`, both byte-identical to
  `8b7e799c`. Keep `control/chrome_tests/test_unit.py` as well; one pin test can go later.
- `control/boundary/`: an interactive Claude Code driver and 17 cases in `control-boundary.yml`, with tmux in the
  Dockerfile. Boundary runs take longer.
- Two fixes for flaky tests (`hostile.py` errno 104, `test_integration.py` broken pipe).
- PR #42 adds `briefs/18c-image-test.md`.

Fit these into the order after the base-URL class: `-c`, then this brief with `-d` and `-e`, then the rest of
`20-post-18d.md`.
