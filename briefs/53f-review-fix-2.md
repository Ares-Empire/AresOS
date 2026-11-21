# 53f review fix 2

Fixes for `reviews/53f-native-home/REVIEW-2.md` (the recheck of fix round 1, Codex `gpt-6.2-sol` `high`,
CHANGES-NEEDED). **Builder:** a Claude Opus agent, on the same branch. If this round fails its recheck too, the next
builder changes (Fable). Read AGENTS.md, `briefs/53f-native-home.md`, `briefs/53f-review-fix-1.md`, REVIEW-1,
REVIEW-2 and `reviews/53f-native-home/REPORT.md` first.

## Fix

1. **The finder never raises on any name** (REVIEW-2 finding 5, blocking). Searching `Straße` raises `TypeError`
   because `ß` casefolds to `ss` and the sort key passes a multi-character string to `unicodedata.digit`. Make the sort
   key work on every string casefolding can produce. Add a property-style test: for every code point in the BMP that
   is a letter or a number, a one-character name and a query of it neither raise nor change the result's order
   between two calls. Plain tests too: `Straße`, `ß`, `ﬁ`, `İ`, `²`, `٣`, `Ⅻ`.
2. **A click opens a house only on what is painted** (finding 2): the logo's hit area is its painted cells (or the
   exact painted outline), not an enlarged rectangle; a click on the transparent lower-right corner of a logo opens
   nothing. Test it.
3. **No stale icon results** (finding 3): clearing the finder drops any result still in flight; a failure recorded
   before a catalogue refresh never suppresses a retry after it (key failures by catalogue generation). Test both.
4. **Nothing ticks at rest** (finding 4): `malloc_trim` is scheduled only after a burst that changed more than the
   clock or the night star; idle clock and star redraws never arm it. Test: over 13 s at rest by day and by night, no
   trim timer is armed.
5. **The opt-in memory tests** fail clearly (not error) when enabled while a prerequisite is missing, as the other
   tests do under `LAPTOP_HOME_REQUIRE_HEADLESS=1`.

## Verify

Run the touched test modules by name with `LAPTOP_HOME_REQUIRE_HEADLESS=1` (never the whole `os/tests`, never
`test_owner_update`), headless and isolated as before. Add a "Review fix round 2" section to REPORT.md. After the last
push start one hosted run (`gh workflow run "OS image" --ref pkg/53f-native-home -f checks_only=true`) and put its
ID in the report. Push, then stop: never wait for or watch CI. Do not merge.
