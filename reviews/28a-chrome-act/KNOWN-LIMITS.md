# Chrome acting: known limits

The standing limits of [package 28](../28-chrome-read/KNOWN-LIMITS.md) and section 6 of
[CONTROL.md](../../docs/design/CONTROL.md#known-limits) carry forward. This list records
the additional limits accepted while building 28a: what happens, its harm, and why it is
accepted under decision 24. Browser coverage and unfinished acceptance remain in
[PROGRESS.md](PROGRESS.md).

## Limits found while building package 28a

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
