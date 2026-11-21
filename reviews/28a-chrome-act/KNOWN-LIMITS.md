# Chrome acting: known limits

The standing limits of [package 28](../28-chrome-read/KNOWN-LIMITS.md) and section 6 of
[CONTROL.md](../../docs/design/CONTROL.md#known-limits) carry forward. This list records
the additional limits accepted while building 28a: what happens, its harm, and why it is
accepted under decision 24. Browser coverage and unfinished acceptance remain in
[PROGRESS.md](PROGRESS.md).

## Fix round 2 (2026-11-21)

- A list whose native label or value would read a protected option subtree is unread. An otherwise
  usable option in the same list can no longer be read or selected through Control, and the owner
  handles a submission that depends on the unread list. Refusing keeps the credential out and
  prevents approval from describing a choice with a partial label.

## Step 4 (2026-11-20)

Each line: what it is, the harm, and why it is accepted under decision 24. Run numbers are
Control Chrome runs; **run** marks a measured number, **read** a file, **assumed** an inference.
Step 4 checked the lines below and the four of earlier steps; it did not re-verify section 6's
list line by line. None of the lines it checked was found untrue.

### Navigation waits for the page (the lead's decision)

- **`chrome_go` and `chrome_open` take about a third of a second, most of it fixed waits.**
  They return once the page has arrived, is ready and its state token has been still for 150 ms
  (brief 28's rule), then read its outline. **Run** 44705819383: navigate 310 to 334 ms median,
  317 to 339 ms p95 over both profiles and the three history phases; about 250 ms of it are the
  100 ms poll that first sees the final token and the 150 ms quiet (**read** PROGRESS, "Step 3b,
  latency"). Brief 20's navigate took 32 to 51 ms because it returned before the page arrived.
  Group 16's "open a page and return one fact" took 379 ms in one call against brief 20's 196 ms
  in two (**run** 44705819383 against baseline 43705060936). *Harm:* each navigation costs about
  0.3 s more wall time than brief 20's navigate alone. *Accepted:* the lead's decision
  (linux-tools, 2026-11-20): the call replaces a second read and returns a loaded page; its
  ceiling is 400 / 450 ms by PR #27's rule for a call dominated by a fixed wait; the poll stays
  100 ms (a 25 ms poll until the first ready look would save up to about 75 ms at up to four
  times the page-state reads during a slow load, each walking every frame's fields).
- **Navigate's reference comparison is looser than its ceiling.** Its reference is now run
  44705819383's own numbers (positions 0 to 19 of each phase), so the paired regression
  thresholds are 476 to 509 ms median and 575 to 605 ms p95, above the 400 / 450 ceilings
  (**run** the gate replayed on 44705819383's artifacts). For navigate the ceiling decides
  alone, as it already did for `read` at 4,000 history entries (threshold 40.9 ms, ceiling 35).
  *Harm:* a navigate regression that stays under 400 / 450 ms passes. *Accepted:* the ceiling
  is absolute and scaled only by a slower runner; today's slowest phase leaves 66 ms of median
  headroom.

### Group 16's time check

- **The 1.5 x line is loose.** Each timed task's median may be 1.5 times the new tools' median of
  "that run", step 1's comparison 44463920809: F1's first read 176.8 ms, F5's click with its
  report 666.1 ms, F4 up to the question 4,340.9 ms, so 265.2, 999.15 and 6,511.35 ms. Run
  44705819383 measured 78.7, 593.2 and 4,218.3 ms: 0.30, 0.59 and 0.65 of the line (**run**,
  `efficiency-measured.json` `latency_rows`, replayed with the new baseline). The recorded
  medians come from a run where every round also ran brief 20's tasks and carry the within-run
  growth below, so F1's read could more than triple before failing; F5 and F4 are mostly brief
  20's fixed 525 ms wait per input, so the line allows about 330 ms and 2.2 s more. *Harm:* a
  moderate slowdown of a read or a step list passes group 16. *Accepted:* it is the brief's rule
  as written; PR #27's gate still bounds `read` at 35 / 60 ms and each input call at its
  ceiling in every run. Tightening it (a recorded run of the new tools alone) is the lead's.
- **Reads get slower round by round within one run, cause unknown.** In 44705819383 F1's first
  read took 50.9, 66.8, 78.7, 96.6 and 146.6 ms in its five rounds, F1's fields 42.9 to 135.7 ms,
  F3's find 55.2 to 155.7 ms (**run**). Brief 20's own tools grew the same way in 44463920809
  (`f1_first_read` 70.6 to 195.9 ms, `f2_table` 9,882 to 16,345 ms), so it isn't this package's.
  Three-tab reads and inputs don't grow. *Harm:* reads late in a long session may be slower than
  the gates measure; nothing else. *Accepted:* low harm and older than this package; PR #27's
  report already noted a long-session doubling it couldn't reproduce. Open for a later look.
- **`chrome_tabs` for 25 tabs takes about 90 ms** (**run** 44705819383: 92.6 ms median, 2,387
  characters) against brief 20's three list calls at 14.5 ms and 6,834 characters in all
  (baseline 43705060936). No budget times it; the cause wasn't analysed. *Harm:* about 80 ms per
  list. *Accepted:* low; the row's call and character budgets hold.

### Reading (found in `9b482732`)

- **Unwatched editable native buttons may appear without a name.** Fix round 1 keeps the
  button role and conservative asking behavior without showing its editable text as a name,
  in rich identity or through the compose preview. Explicit labels can still identify it.
  *Harm:* a button with no independent label is harder to identify. *Accepted:* the owner
  can inspect it directly; the tool does not trade away privacy to name it.

### Time (found in `e3da3a8d`)

- **A slow frame setup refuses an input `expired`.** `e3da3a8d` bounds the extension's waits
  before an input (each frame's control and arming replies, the reveal, the last facts read and
  the hit test) by the input's time, and checks the time again after the hit test of a pointer
  input. *Harm:* on a slow page a step near the end of a list's 12 s can be refused and counted
  in `not_run` although it would have run in time. *Accepted:* it can only stop a dispatch,
  never start or change one; Claude sends the not-run steps again.

## Limits found while building package 28a

### Forward after a restored draft

- **Forward can meet the first-input reload guard after Back restores a prior
  document.** Step 2's policy and external installs and both qualification
  repeats reported first-input loss on the restored dirty page. *Harm:* Claude
  gets a reload warning and the page stays at its prior address. *Accepted:*
  the guard preserves the draft and the owner can decide how to proceed.
  Step 3a checks this refusal and separately checks Forward on a watched
  document with a draft and two history entries.

### Shared image maps — step 2

- **A map shared by multiple images uses the first matching image.** The outline and input
  hit test use the same image lookup. If the first image is hidden and a later image is visible,
  its links can be absent from the outline. *Harm:* the owner can still use the link directly.
  The reader uses the existing hit geometry so a surfaced reference points to the image input uses.

### Large approvals — step 1d, part 2, fix 2

- **A form about a quarter bigger than F4 in affected-item fields refuses.** Conservative
  F4's approval measured 13,348 bytes, including its form and repeated affected-item fields.
  A similar form about a quarter bigger in those fields can exceed the unchanged 16,384-byte
  `ASK_LIMIT` and answer `asking_input_too_large`. *Harm:* Claude cannot send that form;
  the owner sends it himself. *Accepted:* the lead's decision of 2026-11-19 keeps every
  value and field whole and accepts F4 under a 14,000-byte regression pin. Deduplicating
  affected-item fields is a later item with its own review; the asking path is unchanged.

### An empty field with unknown history — step 1d, part 2, fix 2

- **A taken, unwatched owner page can refuse navigation even with an empty textarea.**
  Brief 20's loss guard cannot prove that field's history and reports it as the owner's
  work. *Harm:* an extra refusal; no navigation or input runs. *Accepted:* keep the guarded
  reload and ask the owner to handle the page. The browser case separately checks this
  refusal, genuine owner typing, and the successful reload/navigation of a page without
  editable fields. Changing the frozen guard belongs in a later reviewed item.

### Discard reports do not see all page work — inherited (item 6)

- **Canvas work:** the guard does not see strokes or other state kept in a canvas. Leaving or
  closing the page can lose an unsaved drawing or edit without a warning.
- **Completed wizard steps:** the guard sees present fields, not the answers kept from earlier
  steps whose fields are gone. Leaving the wizard can lose that progress without a warning.
- **A form in flight:** the guard cannot tell that a page request is still on its way to the
  server, or whether it arrived. Leaving can interrupt the send; do not assume it failed or retry it.

These are inherited limits of the field/media check, not permission to discard known work.
For those workflows the owner saves, finishes, or confirms the result in the page before leaving.
The round keeps the discard policy and reports owner typing across all fields it can inspect,
including beyond the display cap. Omitted fields, uninspected frames and unavailable reports
do not establish that all loss is Claude's typing.
