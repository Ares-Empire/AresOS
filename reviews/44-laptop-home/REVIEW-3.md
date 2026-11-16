# Package 44, the laptop-screen home: review 3

Verdict: READY

Reviewer: a fresh Claude agent on Opus 5.5. It did not build any of the package and did not write review 1 or 2. 2026-11-16, read-only, head 5b67a391 (PR #88). It reviews the delta `ac466139..5b67a391`: the day look, its grid and terraces, and the owner's answers.

Read:
- `docs/design/LAPTOP-HOME.md` in full;
- `PROGRESS.md`, `REVIEW-1.md` and `REVIEW-2.md`;
- the diff of `prototypes/street/index.html`, `tools/shots.sh` and `tools/webkit-shot.py`, and the current street page in full;
- all eleven new pictures (`day-1`, `day-2`, `day-4`, `day-6`, `day2-*`);
- `reviews/49-memory-cuts/RESEARCH.md` section 6, on branch `pkg/49-memory-cuts` (fc1d31de).

Ran (headless only):
- `tools/shots.sh check` once in the worktree. The script removes the display variables, and cage ran on its own socket.
- Everything else ran in a scratch copy of `prototypes/` and `tools/`: mutation runs, a hand-slide case, and all `street-` and `day2-` pictures made again.

I did not start the game or `client-test.sh`. All my processes have exited and `git status` is clean. I ran `git fetch` once, which updated remote refs only, to see whether 49's research is on main.

The day look does what the owner asked for. All four roads are equal and run from edge to edge, the columns line up on one lattice, the sky ends on the first street's own ground, and free places are quiet plots. It keeps everything reviews 1 and 2 required. The pictures show what the text says, and night is untouched, byte for byte.

None of the findings blocks the study as a design record. Should-fix 1 to 5 are small: a one-line prototype fix I tried out, and text edits. I would apply them before merging, because some of today's lines still say answered questions are open. Should-fix 6 goes into the build brief.

## Findings

### 1. Should-fix: by day the gold frame can stay out of view after a slide by hand

**Where:** `reviews/44-laptop-home/prototypes/street/index.html:209` (`snap`) and `:376-377` (`follow`).

**What's wrong:** `snap` rounds the needed offset away from zero, which is right only when the street starts from the middle. After a slide by hand it can round the wrong way. Steps, by day, on `?apps=45&hole=test-web-1&look=day`:
1. Click the left end sign. The street slides +196.
2. Type `tool14`.
3. `test-tool-14` becomes the best hit, but the street stays at +196. The house stays at x 1849 to 1933: off the screen's edge, counted in "4 ›" and under the fade mask.

`shown` is 143 here, and `snap(143)` gives 196 instead of 98. This breaks section 3's rule: "The gold frame is always in view … slides by as few whole columns as show the whole house". At night the same steps work: the house comes to 1796 to 1880. `check-grid-long` only types from rest, so it misses this case.

**Fix:** In `follow()`, snap into the interval the house allows instead of away from zero:
```js
const lo = EDGE - x, hi = WIDTH - EDGE - size - x;
st.set(!day ? Math.min(Math.max(st.offset, lo), hi)
  : st.offset < lo ? Math.ceil(lo / pitch) * pitch : st.offset > hi ? Math.floor(hi / pitch) * pitch : st.offset);
```
I tried this in the scratch copy:
- the hand-slide case: the house comes to 1751 to 1835;
- `check-grid-long` 9 of 9, and `check-street` 9 of 9 by day and by night;
- night is the same expression as before.

Also add the case to `check-grid-long`: click an end sign, then type a house on the other side, and expect it in view and on the lattice.

### 2. Should-fix: several lines still treat answered questions as open

**Where and the fix:** `docs/design/LAPTOP-HOME.md`.
- **:3** says the layout "is drawn and waits for his look". But he chose terraces (board #332), and section 10 says every question is settled. Replace with: "Draft. The owner chose the street by day, on terraces (2026-11-16); section 10's six questions are settled."
- **:1** The title is still "Night street". Keep the direction's name if you like, but add "(chosen: by day, on terraces)".
- **:108** "(or full colour, section 10 question 3)": question 3 is answered. Write "(section 10 question 3: dimmed until open)".
- **:610** "By day the same question stands": drop "the same question stands".
- **:563** "Day, and night if it is kept": question 2 kept night as the second look. Write "Day, and night as the second look (question 2)".
- **:743** "it is the look sections 1 and 2 describe": 2.1 now describes the day. Point to section 1 and the night column of 11.3.
- **The reserved key. He said yes. These lines don't say so yet:**
  - **:143-144 (2.2)** "would be the only way across"; **:463 (6)** "if he says yes"; **:575 (9)** "if he chose it". Section 1's "From inside the world" (:72-75) gives Esc only.
  - **Section 9 has no step that builds the key.** It needs:
    - the labwc keybind (Super pressed and released alone) and its command;
    - the window program's typing line on the top layer;
    - the mod's side: losing the keyboard to the laptop home is treated like an app in front (no pause menu, the mouse let go). Without it the brief writer can leave out a mod change.
  - REVIEW-2's should-fix 2 (where an app opened with the key appears) is now live, not hypothetical. Put its line into section 6 or make sure the build brief carries it.
  - While editing, apply REVIEW-2's nit 8 wording too: "without first freeing the pointer in the game".

### 3. Should-fix: the quote recorded for question 5 doesn't show a yes to a reserved key

**Where:** `LAPTOP-HOME.md:616`. It says "Answered (2026-11-16): yes ("so does the search menu easy access")".

**What's wrong:** The quote comes from his earlier "why night" message (:629): "generally the app menu makes sense and so does the search menu easy access". It reads at least as well as praise for typing to search. A reserved key "changes how AresOS feels", and the draft says so itself. The record should show his actual answer.

**Fix:** The lead's brief to me gives his answer as "Super to search". Quote his actual words and where he gave them, as question 1 does with board #332.

### 4. Should-fix: the report is out of step with section 10

**Where:** `reviews/44-laptop-home/PROGRESS.md`.

**What's wrong and the fix:**
- **:330** JUDGMENT-CALL 1 says "the street, by day". Add "on terraces (board #332)".
- **:340-357** JUDGMENT-CALLs 2 to 6 carry no answer. Mark them as section 10 does:
  - 3: dimmed until open;
  - 5: yes, with his words;
  - 2, 4 and 6: kept as recommended, no objection.

  Section 10 says it asks "the report's JUDGMENT-CALLs 1 to 6", and the report is what the lead commits as REPORT.
- **:21** "In short" still says "I recommend Night street". Add one line: "The owner chose the street by day, on terraces (JUDGMENT-CALL)".
- **:493** "**I chose terraces**": the designer recommended them and the owner chose. Write "I recommended terraces; the owner chose them (board #332)".
- **:44** "17 pictures": there are 28 now.

### 5. Should-fix: the new memory note contradicts the bullets above it, and its link is not on main

**Where:** `LAPTOP-HOME.md:316-329`.

**What's wrong:**
- **The bare engine has two numbers.** :324 says about 255 MiB. The note says "about 150 … instead of 356". The research's 356 was its own noisy run (±40, other WebKit sessions running). It labels the study's ~335 as comparable, but 335 is the whole home, not the bare engine.
- **:321-323 contradicts the research.** These lines say about 265 MiB "as in his session … because the NVIDIA driver's libraries are not loaded". The research found that libglvnd loads NVIDIA's libraries into every process, even when Intel draws, unless the vendor is pinned. That is the doubt REVIEW-2's should-fix 3 raised, and the research now answers it: without the pin his session is near the high end.
- **The link is not on main.** `reviews/49-memory-cuts/RESEARCH.md` exists only on `pkg/49-memory-cuts` (fc1d31de). On main it points nowhere until 49 merges.

**Fix:**
- Rewrite the bullets as one statement: about 335 MiB unpinned in his session, and about 150 to 180 MiB with the pin (research). Give each number its source.
- Name the variables: `__EGL_VENDOR_LIBRARY_FILENAMES` (Mesa's JSON) and `VK_DRIVER_FILES` (Intel's ICD). This also closes REVIEW-2's "name the variable the build rule would set".
- Decide whether the pin is a rule for the window program (section 4, "It draws on the compositor's chip") or something to measure.
- Name the branch and commit beside the path until 49 merges.

### 6. Should-fix (for the build brief): two breaks the grid check does not see

**Where:** `reviews/44-laptop-home/tools/webkit-shot.py`, `CHECK_GRID` (:115 and the lines after it).

**What's wrong:** I broke the day grid nine ways in a scratch copy and ran the matching check on each. Seven were caught:
- a middle of 200 pixels;
- sliding by pixels;
- roads not from edge to edge;
- plots only as far as the houses;
- a house half a block off its plot;
- a timer that changes the page at rest;
- (and the night page's stars, three changes).

Two were missed:
- **One street with an extra plot past `EDGE`.** The first half of `every_street_has_the_grid_columns` can never fail, because `cols` is the smallest count of all and every count is at least that. The other halves only compare the inner edges.
- **The terraces drawn 30 pixels off each street.** The ground is one painted gradient, so the check never sees it. This is the owner's own complaint: the lines don't line up with the ground.

The report says this honestly ("I did not see it fail on a broken grid"). These are the two gaps that remain.

**Fix for the build's tests:**
- Expect each street's plot count to equal `cols`, unless that street has a house past `cols`.
- Check the ground against the streets: derive the turf and bank stops from the same numbers and compare, or sample the picture's pixels at each street's turf row and road row.

## Nits

- **"Equally long with 1 app and with 45"** (`LAPTOP-HOME.md:102`, `:817`). With 45 apps the street of 20 has 10 plots a side and runs off the screen (day2-8). Say "equally long on the screen", or "except a street past 16".
- **The rest check doesn't see a canvas drawn again every frame.** I added a `requestAnimationFrame` loop that draws on a house canvas, and `check-rest` still passed 2 of 2. For the companions build, count frame callbacks as well, or keep the processor measurement beside it.
- **`shots.sh check` exits 0 when a check fails.** `webkit-shot.py` prints `wrong` and quits normally. The build's tests should fail on a non-empty `wrong`.
- **A framed house beside a cut end sits in the fade.** The day mask fades from 18 to 120 pixels. With slots 8 and 9 out of sight at rest, slot 7's house (x 85, `tool15` in day2-8) is partly faded even when it has the frame. Optional fix: fade from `EDGE/2` to `EDGE` instead.
- **`LAPTOP-HOME.md:589`** is longer than the document's line width.
- **REVIEW-2's nit 7 still applies by day.** Ledges jump while houses glide. It goes into the build brief as before.

## What I checked and found right

### 1. The owner's words and answers

- Both quotes (the "why night" message and "Yes day but it bothers me…") are the same, word for word, in the draft (:627, :782) and the report (:423, :482), with his own spelling.
- Question 1:
  - the street and day are recorded with his words;
  - terraces are recorded with board #332's "Terraces";
  - 11.6 says he was shown both grounds.
- Question 3 uses his words ("dimmed and light up when used makes sense").
- Questions 2, 4 and 6 say "Kept as recommended (2026-11-16, no objection)". That is the honest wording.
- Question 5: see finding 3.
- Nothing else claims a decision he didn't make:
  - keeping the logo form (no tiles) is the designer's call, with reasons in 11.3;
  - the grid and the plots are the designer's;
  - "not following the real clock" is a recommendation;
  - the only wording slip is the report's "I chose terraces" (finding 4).

### 2. The day keeps what reviews 1 and 2 required

- **Place-based slots.** `layout()` is unchanged apart from `grid()`: the side comes from L/R and the slot is `r(r+1)/2 + k`. `check-street` passes 9 of 9 by day, with `N0L0` free.
- **The long street.** At `CELL` 7 there are 8 columns a side, so slots 8 and 9 slide. The end signs read "‹ 2" and "2 ›" (I recomputed: slot 8 on the left at x −13, slot 8 on the right ends at 1933). Typing `tool19` slides +196, two whole columns.
- **Nothing moves at rest.** By day no stars and no timer are made. `check-rest` passed 2 of 2 by day, and on the night page it saw 3 changes (the stars).
- **Section 5 and section 6 are untouched.** No hunk of the delta touches them.

### 3. The grid code against 11.6

All recomputed:
- **`CELL`** = `floor(920 / (14 SLOTS + 13))`, held between 7 and 10, gives 10, 9, 8, 7 for 5, 6, 7, 8 slots. **`cols`** gives 5, 6, 7, 8, and `cols` is at least `SLOTS` whenever `CELL` is above 7.
- **The lattice.** `GAP` plus a house is 30 + 12 = 42 blocks, three `PITCH`es. The farthest house ends `EDGE` before the screen's edge, as the formula says.
- **Heights.**
  - The feet are at 312, 514, 716 and 918.
  - A sign of two lines fits: 120 + 9 + 3 + 50 = 182, and 202 − 16 − 4 = 182.
  - Turf is 14 + 16 + 4 = 34, the bank is 168, and the sky ends at 298.
- **Counts.** Day one has 40 plots (and 35 free ones). A plate gets 92 pixels against 84.

`shots.sh check` printed 11 lines and all passed:
- 10 of 10 on street, map, console and the day look;
- 9 of 9 for Night street's own check, by night and by day;
- 9 of 9 for the grid check on towns of 1, 24 and 45 apps, and on the lawn;
- 2 of 2 for the rest check.

Whether the checks can fail: see finding 6. The 1-app town really holds one app: the 5-app town less four holes leaves `test-web-1`.

### 4. Night is unchanged

- **The code.** The night branch keeps the same `CELL` and `PITCH` formulas, the 200-pixel middle, the same order of elements and the same star seed. The look's CSS variables keep their night values. The sign's width moved from inline style to `calc(var(--pitch) - 6px)`, which is the same width.
- **The pictures.** In the scratch copy, the current code made all ten `street-` pictures and all seven `day2-` pictures again. All 17 are byte-identical to the committed files. No `street-*.png` changed in the delta.

### 5. The docs against each other

Sections 2.1 and 3 agree with 11.6 and the code on every number. 11.3's note says which of its rows 11.6 replaces. The disagreements are in findings 2, 4 and 5.

The brief writer would be misled by:
- the reserved key still reading as optional, with no build step;
- the status line;
- the memory numbers.

### 6. Hygiene

- No personal data or names of his programs in the added text. The grep found only "texture" in "earth needs a texture".
- The pictures are 1920 x 1080 page renders of the test town, with generated logos and flat colours, no game texture. Their PNG chunks are only cICP and sRGB.
- No file under `os/` or `mod/` changed. REVIEW-1 and REVIEW-2 are not edited.

---

## Review 3, addendum (head 1bbc7322, read-only, headless)

Verdict: CHANGES-NEEDED

One finding blocks the merge, and it is a text fix. Should-fix 1 to 5 are all resolved, and nothing else regressed.

### Blocking: the reading of "homescreen" is written down as settled in several places

His answer on board #333 was: "Yes but the search bar should appear on the homescreen I'd say".

Sections 6 and 10 and JUDGMENT-CALL 5 rightly say "as the lead reads it". These places state the same reading as fact, without that label:
- `docs/design/LAPTOP-HOME.md:3-4`, the status line: "six questions are settled", with only the laptop-pointer case left open;
- `:78-80`, section 1's "Super";
- `:150-153`, section 2.2: "Super searches over the world, not here";
- `:605-623`, section 9 step 5, which treats it as decided build work;
- `PROGRESS.md:105`, `:311-313` and `:601-606`.

The open point is wider than the laptop-pointer case. In this same draft he calls the laptop-screen screen a "homescreen" three times:
- `:19`: "monitor connected" homescreen;
- `:518`: "the alternative laptop homescreen";
- `:713`: "fits as a homescreen".

So his words may mean the laptop home's own search bar, not a search over the world. The "but" supports the lead's reading, but it does not settle it. Step 5's scope depends on which he meant: a new search drawn by the mod, a new event `shell_search`, a new path from the supervisor to the helper, and minimizing a maximized app when he presses Super. That is how AresOS feels, so it is his call.

**Fix:** pick one.
- Ask him once on the board before the build brief: "Super: a search bar over the world on the monitor, or the laptop home's search bar?" Then record his answer.
- Or label the reading as the lead's, to confirm with him, in each place listed above. Widen the open point from "Super with the pointer on the laptop screen" to "which screen 'homescreen' means".

### (a) Should-fix 1 to 5: all resolved

1. **The hand-slide fix.** The `follow()` change at `prototypes/street/index.html:375-381` is the tested expression, and the night branch is unchanged. The new case `typing_after_a_hand_slide_shows_it` fails on the old page: I ran it in a scratch copy and got 9 of 10.
2. **Answered questions no longer read as open:**
   - the title and the status line;
   - section 2.1's dimmed row;
   - question 3;
   - section 9's "night as the second look";
   - section 11.4's pointer to the night look.
3. **Question 5 quotes board #333 word for word.** It also says his earlier words had been read as yes.
4. **The report is back in step:**
   - JUDGMENT-CALLs 1 to 6 carry their answers;
   - "In short" has his choice;
   - the terraces line credits him;
   - the picture count is 28;
   - the 265 MiB claim is marked corrected.
5. **Memory is now one statement with its sources:**
   - the branch and commit of the research are named;
   - the two variables are named, and both files exist on this laptop (`50_mesa.json`, `intel_icd.x86_64.json`);
   - the pin is a rule, with a test in step 3 and the supervisor's side in step 4.

### (b) The facts behind step 5 check out

- labwc 0.9.6's `labwc-config(5)` documents `onRelease="yes"` on `Super_L`.
- `aresos-desktop hide-cover` exists.
- `return_to_desktop` exists in the helper.
- `AppsScreen.java` exists.
- Nothing else in `rc.xml` binds Super alone.

Apart from the blocking finding above, the rewrite is consistent between the draft and the report.

### (c) No regression

- `tools/shots.sh check`: eleven lines, all passed:
  - 10 of 10 on street, map, console and the day look;
  - 9 of 9 for Night street's own check, by night and by day;
  - 10 of 10 for the grid check on the towns of 1, 24 and 45 apps and on the lawn;
  - 2 of 2 for the rest check.
- Section 5 is untouched.
- The worktree is clean, and none of my processes is still running.
