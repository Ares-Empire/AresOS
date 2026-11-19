# 53d review fix 2

Fixes for `reviews/53d-world-search/REVIEW-2.md` (the recheck of fix round 1, Codex `gpt-6.2-sol` `high`,
CHANGES-NEEDED). **Builder:** a Claude agent on **Fable 5.2**. The focus handoff has now failed two rounds, each
review finding the next case, so the builder changes, per the handoff's rule. Read AGENTS.md,
`briefs/53d-world-search.md`, `briefs/53d-review-fix-1.md`, REVIEW-1, REVIEW-2 and `reviews/53d-world-search/REPORT.md`
first. The rebase onto package 56 stays a later step.

## The lead's design for this round

Stop excluding bad cases one by one. Allow only states known to be safe.

1. **The handoff: the world must be the only active window.**
   - **The helper:**
     - it always sends the activation request on Super, even when the world already looks active;
     - it uncovers and sends `shell_search` only after a compositor update (a complete batch of
       foreign-toplevel events, up to its `done`) in which the world's window is activated **and no other toplevel is
       activated**;
     - a split update where the world and another window are both active waits for the next batch, within the 1 s
       bound.
   - **The activation that Super caused is marked.** If the search is called off before it lands (not ready, a new
     connection, the 1 s bound), that activation **uncovers nothing**. The world simply has the focus, and no
     window is minimized.
   - **Tests:**
     - the split update in one batch and across batches;
     - the world already looking active;
     - a `ready: false` heartbeat during the handoff (nothing minimized, no event);
     - the 1 s bound.
2. **Drafts: an allowlist.** Super replaces only screens known to hold nothing typed:
   - no screen;
   - the player's inventory and any container screen (closed normally first, with `closeContainer()`);
   - the pause menu;
   - the Apps screen while its search box is empty.
   
   **Every other screen is left alone and the event is ignored:** vanilla, other mods', and AresOS's own (New Home
   chooser, recovery and setup screens). Remove the editor list; the allowlist replaces it.
   
   **Tests:**
   - the New Home chooser with a custom seed, Tab to a button, then Super: the chooser and seed stay;
   - the book-signing case stays;
   - each allowlisted screen is replaced;
   - one unknown screen is left alone.
3. **Pinned best hit** (REVIEW-2 finding 6, nonblocking): pin it only when the layout has at least four result slots;
   otherwise the list scrolls as before. Test with a two-slot layout.

## Verify

- `mod/dev/build.sh`, then `mod/dev/client-test.sh` **twice**. It takes the client-test lock, and on exit 75 wait and
  retry, never `--force`. Commit before a suite run; afterwards restore only the rewritten tracked screenshots, and
  delete untracked ones written for other packages.
- The touched helper modules pass, in-process and each run by name (never the whole `os/tests`, never
  `test_owner_update`). Run a mutation check like round 1's on the new handoff rule.
- Add a "Review fix round 2" section to REPORT.md.
- After the last push, start one hosted run (`gh workflow run "OS image" --ref pkg/53d-world-search -f
  checks_only=true`) and put its ID in the report.
- Push, then stop: never wait for or watch CI. Do not merge.
