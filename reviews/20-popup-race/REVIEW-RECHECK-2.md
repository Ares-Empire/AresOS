# Package re-check 2 (`b6d223fa..2d27248c`, Claude Opus, 2026-11-15)

**Verdict: SAFE.** Both fixes do what they should, and nothing else changed between `b6d223fa` and `2d27248c`.

**FIX 1 (notify only counts the workflow's own issues and comments): closed.**
- **A stranger's issue with the same title** is ignored, so notify opens its own issue. Notify now keeps only issues opened by `github-actions[bot]` with type `Bot`, and skips pull requests. A stranger's account can't have a `[bot]` name, because GitHub reserves that suffix for apps.
- **A stranger's comment with the same text** no longer stops the workflow from commenting. New text is compared only with the workflow's issue body and its own comments. I checked this one separately: when I dropped only the comment-author filter, the stranger-comment test row failed.
- **No 200-issue cut-off any more:** the issue list is paginated, 100 per page.
- **No new way to misfire.** I ran the exact `gh api` calls read-only against the real repo:
  - The encoded `creator=github-actions%5Bbot%5D` returns #74 as `github-actions[bot]`/`Bot`, not a pull request.
  - The output is one compact JSON object per line, even for #74's multi-line body, so the line-by-line parsing works.
  - #74's only comment comes back as `carlsenares`/`User`, so it is not counted.
  - If the `creator` filter ever matched nothing, the worst case is a duplicate issue, never trusting someone else's.
- When a gh call is refused, the error still shows gh's own text (`gh api --paginate failed: …`).
- The stale "issues and pull requests" comment is fixed. The `attestation.py` stub now returns empty output and expects one lookup, then one issue created. That matches the new calls.

**Tests and probes**
- `test_publisher` and `test_qualification` pass in a fresh scratch copy of `2d27248c`.
- All 9 `qualifyfix-*` probes are rejected, each for its stated reason:
  - **trusts-strangers** and **pull-request-as-issue:** notify picks the wrong issue, not #5, and the "someone else's issue means a new issue" check fails.
  - **lists-every-author:** the assertion that the call carries `creator=…` fails.
  - **re-pointed duplicate-issues and repeated-comments:** they fail on an unexpected new issue and on the wrong comment decision.
  - **hides-gh-errors:** the error comes out as a raw `CalledProcessError`, not `SystemExit`.

**FIX 2 (repo-relative paths): closed.** The record diff only strips the worktree's absolute prefix from the 29 node test paths, and no absolute paths are left. The driver change isn't in this diff, so I didn't review it.

**Checked:** read `git diff b6d223fa..2d27248c` (5 files). Ran the publisher and qualification tests, the 9 probes, and the one manual comment-filter mutation, all in the reviewer's scratch directory (not committed). Made two read-only `gh api` calls. No browser was started, and the worktree is unchanged.
