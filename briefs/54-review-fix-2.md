# 54, review fix 2: a pending replacement remembers where it came from

`reviews/54-town-one-line/REVIEW-2.md` (Codex `gpt-6-astra` `high`, head `a5c5d4fe`) confirmed three things:
- the unchanged-ID category move is fixed and covered;
- the 200-tick bound starts at the first real build;
- `WAY`, rebuild, ordinary changes and per-world state are unchanged.

It found two more cases in the same place: a replacement whose old logo came down but whose new one waits for its place to load. They predate package 54, which made them visible. Close the whole class this time, not only the two instances.

**Builder:** Codex `gpt-6.1-sol`, `xhigh`. **Review:** a fresh Codex `gpt-6-astra` `high` context, checking only this fix.

## What changes

1. **One record per pending replacement** (`TownKeeper.java:434`, `:467`, `:509`, `:524`, `:539`). It holds:
   - the app;
   - the operation that started it (renewal or move);
   - the original place;
   - whether the old logo really came down.

   Its outcome is decided when it ends, from that record:
   - **Built at the original place:** `RENEWED`.
   - **Built somewhere else:** `MOVED`, whatever the operation started as, including a renewal whose place became obstructed or whose category changed meanwhile.
   - **The app is no longer wanted before it was built,** and the old logo had come down: one `DOWN` line. If the old logo still stands, nothing is pending, and the ordinary removal path speaks.
   - **The app comes back while its replacement is pending:** it continues as that same pending replacement and is said once when it completes.
   - **A pending replacement never adds to the first build's count.**
2. **The client assertion (nit, `TownArrivalClientGameTest.java:158`).** Check that the line comes at completion, within a small delivery tolerance of `controlled.completed`, and that the deadline is measured from `controlled.first`.

## Tests

- **A table-driven keeper test** over:
  - the operation {renewal, move};
  - the destination at completion {original place, different place, obstructed so it goes elsewhere};
  - the outcome {completes, cancelled, cancelled then the app returns};
  - repeated passes.

  Each combination expects exactly one line with the right kind, or none where the brief says none. Include the two cases REVIEW-2 describes.
- **The earlier unit and keeper tests** still pass.
- **The builds:** `mod/dev/build.sh` twice and `mod/dev/client-test.sh` once.

## Rules

As in `briefs/54-review-fix-1.md`:
- **The lock:** package 49b's measurements are running. Check the client-test lock is free with `/usr/bin/flock -n ~/.cache/aresos-dev/client-test.lock true` before each build, and wait while it's held.
- **On exit 75:** wait about five minutes and retry, at most six times.
- **Commits:** end each commit with the trailer line `Codex-Model: gpt-6.1-sol xhigh`.
- **Where it goes:** merge origin/main first if it has moved. Push to `pkg/54-town-one-line` and comment on PR #108.
- **Never** merge, push to main or use `--no-verify`.
