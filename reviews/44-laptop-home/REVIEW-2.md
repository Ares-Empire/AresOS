Verdict: READY

# Package 44, the laptop-screen home: review 2

Reviewer: a fresh Claude agent on Opus 5.5. It did not build the package and did not write review 1. 2026-11-16,
read-only, head 5f244dda (PR #88).

Read:
- the fix brief and REVIEW-1;
- the fix diff `1021c838..5f244dda`;
- `docs/design/LAPTOP-HOME.md` and `PROGRESS.md` in full;
- the Night street prototype, `shared/home.js` and both tools;
- pictures street-1, 3, 8, 9 and 10.

Checked against:
- HUB.md 2.4, 2.5 and 3.1 to 3.5;
- `aresos-shell`: hello, emit, the journal, open_app, the catalogue start and the return of focus;
- `aresos-desktop`: `ensure_helper`, `start_helper`, the environments and the runtime file;
- `rc.xml`;
- the companions runtime README.

Nothing was started: no browser, no WebKit, no compositor, no game.

All 13 findings of review 1 are closed as the fix brief chose. The new pieces work: the sliding street, full
colour, search by generic names and keywords, and the way from the world. The pictures show what the text says. The
owner can choose from the study, and a build package can follow the draft. Three things should still go into the
draft before or with the build brief (findings 1 to 3). None of them changes the direction or a JUDGMENT-CALL's
recommendation.

## Findings

### 1. Should-fix: "a view's launch does not return the focus to the world" has no mechanism in the helper, and no test

**Where:** LAPTOP-HOME.md section 5 (last bullet of "A view"). PROGRESS.md "How it lives in the session" ("When
an app that was opened from the laptop closes, the focus does not jump to the world"). Section 9, step 1.

**What's wrong:** The helper decides the return by window and by app, not by launch.
- In `aresos-shell` (around lines 3500 to 3565), `return_to_desktop()` runs when the last window of
  `self.foreground_app` closes, or of a window handed off from it.
- For discovered apps the decision is per app (`discovered_closing[app]`). Most of his apps are discovered apps.
- Only reviewed-registry launches link a window to a request (`self.handles`).

So "a launch a view asked for" has no hook. Some cases are open:
- the same app launched once from the world and once from the laptop;
- an app opened over the world (it opens on the screen the pointer is on) and closed there;
- an app opened from the laptop and then moved to the monitor.

The intent is right. Without the rule, closing a laptop app gives the focus to the world on the other screen, and
the game captures his pointer while he is working on the laptop. But a builder has to invent the rule, and step 1
does not test it.

**Fix:** Decide the rule by screen, not by who opened the app. When a window closes on a screen that is not the
world's screen, the helper does not return to the world. The helper already knows which screen each window is on,
because it uses that for `shell_covered` (HUB 3.8, "on one of the desktop's screens"). This also covers apps that
were moved between screens. If the launch-based rule stays instead, say how a discovered app's closing is assigned
to a client. Either way:
- add a test to step 1: an app closing on the laptop's screen does not send `shell_focus` / `app_closed` or
  activate the world;
- add this to the laptop trial.
The rule touches package 23c's screens, so note it for `linux-aresos` beside the PLAN-GAP if it belongs there.

### 2. Should-fix: with the reserved key, where the app opens is not said

**Where:** LAPTOP-HOME.md section 6 ("With a reserved key"), section 10 question 5, PROGRESS JUDGMENT-CALL 5.

**What's wrong:** The key opens the typing line on the laptop screen while his pointer stays in the world on the
monitor. Section 6 says "Apps open on the screen the pointer is on (23c)", so an app chosen this way opens over the
world on the monitor, not on the laptop. That is probably what he wants ("the launcher of the whole session"). But
the draft never says it, and the report's open question ("Opening an app on the monitor from the laptop … would need
one more field") suggests the opposite. He is asked to decide on the key without knowing where its apps appear.

**Fix:** Add one line to section 6, question 5 and JUDGMENT-CALL 5. For example: "Enter opens the app where his
pointer is: over the world on the monitor, as the world's own opening does. The typing line closes, and the keyboard
goes to the app." Add it to the trial.

### 3. Should-fix: the motion measurement can't be repeated from the tool, and its numbers cover less than the text suggests

**Where:** PROGRESS.md "Motion, measured" and "What it means for the companions version". LAPTOP-HOME.md section 4
"Motion" and "Memory". `tools/shots.sh`.

**What's wrong:**
- **How each set-up was made is not written down.** `shots.sh` has knobs for software drawing only
  (`PKG44_RENDERER`, `PKG44_ACCEL`). The table's rows ("compositor and GTK on the Intel chip", "GTK's OpenGL
  renderer", "Vulkan, device 0") must have come from environment variables set around the script, and none is
  named. The draft's build rule depends on them: "If they differ, the program sets GTK's renderer or device so they
  match". So do the trial in section 9 and the 248 % warning. A builder has to find again what the study already
  knew.
- **The numbers leave things out:**
  - The compositor is the parent of the measured program, not one of its children. Its own work for 60 frames a
    second is not counted. In his session that is labwc, also for the 248 % case.
  - Only one figure was measured. "The cost is per frame, not per figure" is a sound expectation, but it was not
    measured.
  - The work of the graphics chip and the battery are not in the numbers.
- **The 265 MiB depends on an unknown.** "About 265 MiB … as in his session, because the NVIDIA driver's libraries
  are not loaded" depends on how the Intel-only set-up was made. In his session the NVIDIA driver is installed, and
  GTK's Vulkan start-up may load it anyway. Until the trial shows which, 265 MiB is the low end and 335 MiB the high
  end.

The conclusion itself is sound and plainly put: about a fifth of a core on one chip, two and a half cores across
two, so draw on the compositor's chip, and give the companions a budget of their own. Only its basis needs writing
down.

**Fix:**
- Write each row's environment into the table, or better, as `PKG44_*` options in `shots.sh`.
- Name the variable the build rule would set.
- Add one line: "The compositor's own work, the graphics chip and several figures are not measured. The trial
  checks it in his session."
- Change "The web choice holds" to "holds in the headless test".
- Give memory as "265 to 335 MiB, depending on whether the NVIDIA driver loads (trial)".

### 4. Nit: other tables besides the journal are keyed by request ID alone

**Where:** LAPTOP-HOME.md section 5, "Launches are kept per client".

**What's wrong:** Besides `journal.entries`, the helper keys `checking`, `processes`, `handles`, `started` and
`deadlines` by the request ID alone. `open_app` looks in `checking` first: a matching ID adds the asking connection
to the waiting launch, so a view could get the game's launch back before the journal is ever checked. The random
part in a view's IDs makes a collision practically impossible. But the draft says only "journal entries" are keyed
by client.

**Fix:** "Every table keyed by request ID (the journal, `checking`, `processes`, `handles`, `started`, `deadlines`)
is keyed by client and request ID."

### 5. Nit: dropping unknown IDs from `publish_home` can empty the town while the helper starts

**Where:** LAPTOP-HOME.md section 5, `publish_home` ("An app whose ID the helper no longer lists is dropped").

**What's wrong:**
- A new helper starts with the reviewed registry as its catalogue (`self.catalogue_apps = self.apps`).
- It gets the discovered programs only when the first scan finishes. `start()` waits about `SCAN_SECONDS + 1` for
  that scan, and a scan blocked by a stalled mount keeps the registry list for longer.
- Most of his apps are discovered apps. A publish that arrives in that window would drop them, and the laptop would
  show an almost empty town. That is the case the rule was written to prevent.
- The bullet before it also says the helper "does not read meaning into" the home.

**Fix:** Drop an ID only against a catalogue from a finished scan, and keep it otherwise. Or leave the IDs alone:
opening an unknown ID already fails cleanly with `unknown_app`, and the mod publishes only what the system lists
(HUB 2.5).

### 6. Nit: small gaps around the view token

**Where:** LAPTOP-HOME.md section 5, section 9 step 1.

**What's wrong and the fix:**
- **The test wording contradicts the rule.** Step 1's test says a hello with the view token "is a view whatever its
  `role` says, and a mismatch is refused". The rule refuses the mismatch. Reword: "with the view token, a hello with
  `role` view is a view; any other role is refused".
- **Hellos that hold both secrets.** Say that a hello holding both the nonce and the token is refused.
- **Comparison.** Say the token is compared like the nonce (`hmac.compare_digest`, together with the instance).
- **Tests.** Add to step 1 a test that apps the helper launches never get `ARESOS_VIEW_TOKEN`. Step 4 already
  covers the supervisor's side.

### 7. Nit: two details of the sliding street

**Where:** LAPTOP-HOME.md section 3 ("Past 8 slots on a side"), section 7. `street/index.html` (`moved`).

**What's wrong and the fix:**
- **Matches out of sight.** While he types, a match out of sight is not shown. For example, `tool1` matches
  `tool17` and `tool19`, but the end signs count every hidden house, matching or not. The fix is optional: while
  typing, an end sign could say how many of its hidden houses match.
- **Companions on a sliding street.** The ledges and boxes jump by the whole offset at once, while the houses glide
  for 0.3 s (a CSS transition). The draft says companions "ride along", but they would jump ahead of their roof.
  Fix: give the snapshot the street's current offset each frame (the page moves the street itself, or reads its
  current transform).

### 8. Nit: wording

- **"The only way across without Esc"** (section 2.2, section 10 question 5, JUDGMENT-CALL 5). E and T also free the
  pointer, and so does Alt+Tab to an app that is already open. Say "the only way across without first freeing the
  pointer in the game".
- **"Reads `get_home`, `list_apps` and `apps_running` again"** (section 5). `apps_running` is an event the helper
  sends after hello. Say "reads `get_home` and `list_apps` again and gets `apps_running` after its hello".

## What I checked and found right

### Review 1's findings, closed as the fix brief chose

**1. Houses come from their places.**
- Section 3 takes the side from the place's L/R and the slot as `r(r+1)/2 + k`. That is the rank among one side's
  places in HUB 3.3's order (row, then k), since row r holds r + 1 places a side.
- The prototype's `layout()` does exactly that.
- A free place stays a gap; the other way (the side closing up) is rejected with its reason.
- `CELL` comes from the farthest slot. I recomputed: 120 / 108 / 96 / 84 at 5 / 6 / 7 / 8 slots, and 16 apps
  without gaps fill slots up to 7.
- An app without a place takes the places after its group's farthest one.
- `move` and `swap` are covered by the place rule: HUB writes `group` with a move across groups, so group and place
  always agree.
- `check-street` checks a town with `N0L0` free: `holeMovesNothing` compares against the layout with the app put
  back, `web-2` stays right and `web-3` stays left.

**2. The view token.**
- One token for the session, kept beside the instance in the runtime file.
- Accepted for `role: view` only. The role comes from what the hello holds, so a view can never displace the game.
- Not given to the game, and in both `PRIVATE_ENVIRONMENT` lists.
- Reconnects at 0.5, 1 and 2 seconds, then every 2 seconds, without counting as restarts (section 6). The last town
  is shown with opening off in between.
- The token and `LD_PRELOAD` are removed before the web view starts.
- The PLAN-GAP names the supervisor's side (23c, `linux-aresos`) in the draft and the report.
- Against `ensure_helper(restart=True)` and `start_helper`, the reasoning holds. The supervisor creates the token
  itself, so keeping it out of its own environment and handing it on explicitly works.

**3. The helper's one-client state.**
- A view's hello leaves `window_minor`, `cancel_returns()`, `windows_pending` and `desktop_connected` alone. These are
  exactly what `hello()` changes today.
- The journal is per client, with 32 entries per view. `room()` makes space by dropping expired entries, so the
  share works.
- `app_state` goes only to the client that asked, also after a helper restart. `emit()` sends only to
  `self.desktop` today.
- The checks are not weakened:
  - the peer is still checked (`SO_PEERCRED`), the socket is 0600, and there are at most 8 connections (the desktop
    and up to four views fit);
  - a view gets no new operation that runs a command or opens a path, and `world_ready`, `heartbeat` and
    `publish_home` are refused;
  - the page never sees the socket, the token or the nonce.
- What was missed is in findings 1, 4 and 5.

**4. Past 16 apps.** The street slides; section 3 and the report state the limit (16 a group, about 45 apps in
HUB's mix). The two fallbacks review 1 offered are rejected with reasons (section 8).

**5. From the world.** Esc, E or T is described in sections 1, 2.2 and 6 and in the report. JUDGMENT-CALL 5 now
gives the stronger reason for the key.

**6. Search.**
- Seven kinds of hits, with generic name and keywords after every kind of name hit. `score()` matches the list.
- `generic_name` and `keywords` are what `app_row(details=True)` already sends to a 1.1-or-later client.
- The finder shows the generic name and never a group. This agrees with HUB's own note that the Apps screen shows no
  group.
- `pdf` finds "Test Viewer" by its keyword (picture street-3).

**7. Motion.** Measured with the tool and the prototype as described:
- `?sprite=1` walks a figure on a full-screen see-through canvas (80 x 80 pixels, the runtime's default size 5) that
  is cleared every frame;
- processor time per process over 60 seconds;
- memory from `smaps_rollup` with `Pss_File` and `Pss_Shmem`.

The conclusion and the new build rule are stated in sections 4, 7 and 9 and in the report. The basis needs writing
down (finding 3).

**8. JUDGMENT-CALL 3 and section 10.**
- Picture street-10 shows full colour, and question 3 is worded "slightly dimmed" against "full colour" (62 % and
  82 % are both stated).
- Section 10 and the report ask the same six questions in the same order, each with a recommendation.

**9. The memory split.** 127 MiB working memory, 208 MiB mapped files, under 1 MiB shared memory. It is now
measured (`Pss_File`, `Pss_Shmem`).

**10. Motion at rest.**
- The caret runs 5 blinks and restarts on each key.
- Typed text clears when the page loses the focus.
- The clock ticks once a minute.

**11. Logos.** Each logo comes from an FNV hash of the app's ID. "Test Game 1" is the same in street-1 and street-8.

**12. Long names.** Signs wrap to two lines, and "Test Media Workbench" shows it in street-1, 8 and 10. Two lines
still fit under the street above at `CELL` 10.

**13. Build notes.** All four are in sections 4, 6 and 9:
- `LD_PRELOAD` for the layer library;
- the scheme registered as secure and CORS-enabled, with its MIME types;
- `fullscreen_on_monitor` on the `eDP` screen for the fallback;
- the environment cleaned before WebKit starts.

### The new pieces

**The sliding street.**
- It stays in the middle at rest. End signs sit over a fade.
- The gold frame's street slides as little as shows the whole house.
- A click on an end sign slides to that side's last house.
- A slide by hand ends on Escape, a click on the group's name, or the loss of the keyboard.
- Ledges and boxes slide with the street (but see finding 7).

I recomputed the 45-app town:
- System & Tools needs slots 0 to 9 a side, so `CELL` is held at 7.
- Slots 8 and 9 are out of sight on each side, so the signs read "‹ 2" and "2 ›" (street-8).
- `tool19` is `S3L3`, slot 9 on the left. Sliding it into view moves the street 182 pixels, so the right sign reads
  "4 ›" (street-9).

Both pictures show this. Every other street keeps its place.

**Full colour.** Street-10 against street-1 is a fair comparison of question 3.

**Search and the way from the world.** Both hold up, apart from findings 2 and 8. The reserved key is untried and
marked so, and nothing else binds Super alone in `rc.xml`.

### The measurement

- The method is sound for what it measures:
  - a headless `cage` with his display variables removed;
  - a refusal on `wayland-0` or without the tool's marker;
  - processor seconds of the program and the engine's processes over 60 seconds;
  - PSS from `smaps_rollup`.
- The per-process split (window program 240 % in the two-chip case) supports the diagnosis, and the contrast of 22 %
  against 248 % supports the build rule.
- The risk for the companions version is stated plainly in section 7: a fifth of a core, a budget of their own, the
  two-chip trap checked before anything moves. What is missing is the record of the set-ups and the scope of the
  numbers (finding 3).

### The JUDGMENT-CALLs

Six questions, the same in the report and in section 10, each with a recommendation. Each is answerable from what he
will see or imagine:
- the pictures, for the direction and for dimmed against full colour;
- plain choices, for one look, what else is shown, and pins;
- the key, once finding 2's line is added.

### Hygiene

- No file under `os/` or `mod/` changed on the branch.
- REVIEW-1.md was not edited.
- No names of his installed programs are in the draft, the report or the prototypes. Notepad is the image's own
  starter app, as in HUB.md.
- The logos come from hand-made test signs: no app icons, no game textures.
- The pictures are page renders of test towns, not his screen.
- No personal data.
