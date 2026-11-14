# 20, integrate: the shared-file changes the side builds need, the service unit, green twice

The core build (`briefs/20-continue-3.md`) and the two side builds (`briefs/20-adapters.md`, PR #29, and
`briefs/20-qualification.md`, PR #30) are merged into `pkg/20-chrome` by the package lead. The side builds left
the shared files alone and listed what they need there. This run makes those changes, applies the lead's decision
on the service unit, and brings the integrated head to green twice. The earlier briefs stand; where they differ,
this brief wins. The stop rule is `20-continue-2.md`'s.

**Never start, read or touch Chrome, Chromium or any browser profile on this Mac: every browser test runs only in
containers on GitHub's Linux runners through the control-chrome workflow; locally run only plain-Python and Node
tests that start no browser.**

## 1. What the adapters need (`reviews/20-chrome/ADAPTERS-REPORT.md`, "Shared-file integration required")

- The question names the recognised adapter action, as the page shows it: Gemini says it asks a question (with its
  text), Gmail's inbox `#` says it **deletes** the selected message, never "activate 'Selected message'". The
  semantic kind is private in the payload today; carry it into the sentence without letting page text choose it.
- Gmail's question names the attachments (count, names and sizes) with the account, To, Cc, hidden Bcc, subject
  and text, as section 6's question rule says.
- Register every new group 4, 10 and 11 case name from `control/chrome/ci/sites/` in `verdicts.mjs`'s required set
  and its support inventory. The three strict wording tests (`GROUP 10 ADAPTER Gemini question uses its required
  semantic name`, `... Gmail question names its attachments`, `... Gmail deletion shortcut question names the
  deletion`) must pass unchanged.

## 2. What qualification needs (`reviews/20-chrome/QUALIFICATION-REPORT.md`, H1 to H6)

- **H1, the service unit (lead's decision 2026-11-09, option a, narrowly):** in
  `control/packaging/aresos-toold.service` set `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6` and remove
  `IPAddressDeny=any`. Keep everything else exactly (User, NoNewPrivileges, ProtectSystem=strict, ProtectHome,
  PrivateTmp, PrivateDevices, the empty CapabilityBoundingSet, ReadWritePaths, UMask). Add a short comment that
  Mail's IMAP and SMTP and the daily record fetch need it. Add a static test that pins every sandbox line of the
  unit, so nothing else loosens silently. The record fetch keeps its verified TLS, bounds and offline-safe refusals
  as built; the verifier's cache and config stay private under `/var/lib/aresos-tools`.
- **H2, the verifier:** don't install anything on this Mac. In the report, name the dependency for the image: `gh`
  2.102 or later, or Sigstore's Python library if you judge it the better pinned choice; say which and why. Record
  H1 and H2 as "unit fixed here, live check in brief 18c", not as an open PLAN-GAP.
- **H3:** run the conservative-mode browser cases it lists at the integrated head, with the receiver's log.
- **H4:** test group 12 needs 18d's precedence harness. It stays a stated gap until 18d merges; never set it true.
- **H5:** in `verdicts.mjs`, one failed adapter disables only that adapter; a shared prerequisite failure still
  disables what depends on it.
- **H6:** stays as reported (production publication runs only on `main`).

## 3. Popups a Claude tab opens (lead's decision, 2026-11-10)

Chrome doesn't let the extension put the page script into a popup before its first script. Popups therefore follow
the owner's rule for taken tabs exactly (`briefs/20-continue-3.md` part 1, "Taking an already-open tab of his"):
Claude reads a popup at once; its first act reloads it only when it was loaded by GET and shows no unsaved typing
and no playing media; otherwise the tool reports first and acts only on the explicit repeat. A popup loaded by a
form submission (POST, any non-GET, a `window.open` with a form target) is refused with "open its address in a
Claude tab". After the reload every old reference is stale. Conditions:
1. **Chrome stays normal.** Popup windows can't hold tab groups: don't move the popup into a normal window,
   re-parent it or change its window type. "Joins the group" means the extension's own record. Show the owner that
   the popup is Claude's in a way that changes neither the page nor the window (for example the action badge for
   that window), and say exactly how in the report.
2. Only popups whose opener is a Claude-group tab qualify, and only while that opener is still in the group. A popup
   from any other tab stays untouched, as before.
3. The reload keeps the popup's opener relationship.
4. Tests, with the receiver's log: an opener page that waits for a `postMessage` from its popup still completes its
   flow after the reload; a POST-loaded popup is refused with no second request reaching the receiver; unsaved
   typing reports, then the explicit repeat reloads; a popup from a non-Claude tab stays untouched.
5. It is a decided rule, not a PLAN-GAP; the report states it exactly, and the lead writes it into section 6.

## 4. Green twice

Regenerate every generated file. On the final head, the whole Chrome set (test groups 1 to 11 and 13, by name,
both install modes) and the base, Mail and boundary workflows pass twice, apart from what is a stated gap (group
12; the owner-Enter PLAN-GAP if the core run left it). Fold the side reports' final state into
`reviews/20-chrome/REPORT.md` (keep `ADAPTERS-REPORT.md` and `QUALIFICATION-REPORT.md` as they are, and link them):
the 13 groups with test names and run IDs, the feature → tool → test map, PLAN-GAPs, JUDGMENT-CALLs, the DevTools
commands added to the fixed list, the reload behaviour, the image handoffs (the excluded-sites setting, the
verifier, the unit), what moving onto 18d and 19b will take, and the run counts per branch.

**The owner-Enter case:** if it passes in CI, write it as "passes in CI, panel to confirm", not as closed; the review
panel's injection and binding angles confirm it from the receiver's log first.

**Runs:** `pkg/20-chrome` may use about **115** runs of `control-chrome.yml` in all (count them with `gh run list
--branch pkg/20-chrome --workflow control-chrome.yml`); if it would pass 115, say so in the report and stop.

## Rules for this run

As `briefs/20-continue.md`, "Rules for this run", on branch `pkg/20-chrome`; the draft PR #27 exists. Read the
specification from `origin/main` with `git show` after `git fetch origin main`. `control/packaging/` is in scope
for the unit change above only.
