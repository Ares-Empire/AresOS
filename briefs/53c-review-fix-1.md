# 53c review fix 1

Fixes for `reviews/53c-laptop-home/REVIEW-1.md` (fresh Codex `gpt-6.2-astra` `high` review of PR #114). **Builder:**
Codex `gpt-6.2-sol` `xhigh`, on the same branch. Read AGENTS.md, `briefs/53c-laptop-home.md` and REVIEW-1 first.

## Fix

1. **Closing a background app never pulls the keyboard from the laptop home** (REVIEW-1 blocking 1,
   `aresos-shell:2628` and `:3908`). When the focus leaves an app (to the laptop home or anywhere else), the helper
   clears that app's foreground record, keeping the short handoff used for a genuine close. Tests: closing the
   foreground editor returns to the world as today; an editor closing after the owner moved to the laptop home and
   started typing leaves the keyboard there.
2. **A full-size kept town survives a restart** (REVIEW-1 should-fix 3, `aresos-laptop-home:146`). Derive the
   reader's bound from the largest town the helper accepts (200 apps, the longest names and short names in UTF-8),
   and make the writer refuse what the reader would refuse. Test a full-size multibyte save and load, then a `null`
   revision keeping it on screen.
3. **Open apps are lit from the first frame** (REVIEW-1 should-fix 6, `aresos-laptop-home:361` and `:602`; the brief's
   starting-state rule). Pass the helper's running IDs to the page as soon as the view is authenticated, without
   waiting for the catalogue; opening stays off until the reads finish. Test with a kept town and a delayed last
   catalogue page.
4. **The grid check can fail** (REVIEW-1 should-fix 5, `test_aresos_laptop_home_page.py:221`). Sample an empty plot's
   pale slab and the turf between plots in the picture, and check the rendered house bounds across streets after a
   slide. Show in the report that removing the slab CSS makes it fail.

Add REVIEW-1's blocking 2 (the fullscreen fallback can take the focus when it starts, `aresos-laptop-home:617`) and
should-fix 4 (a launch that fails after `starting` shows no reason) to the report's Known limits, one line each; the
first also goes to `docs/design/LAPTOP-HOME.md` section 6 beside the fallback, as a note for 23c's restart rule.

## Verify

Run the touched test modules by name (never the whole `os/tests`, never `test_owner_update`). After your last push,
start one hosted run (`gh workflow run "OS image" --ref pkg/53c-laptop-home -f checks_only=true`) and put its ID in
the report. Push, then stop: never wait for or watch CI. Do not merge.
