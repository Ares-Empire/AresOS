# R29 on the laptop

## How to run this

Use this after the owner has installed R29. Work alongside normal use. Start with the quiet checks and collect the visible ones together when the owner is free. The owner's own observations and this pass both feed R30.

- Keep findings only in `~/AresOS-R29-FINDINGS.md`, local and uncommitted. Fix nothing. Use one line per test with **pass**, **fail**, **skipped (why)** or **needs the owner**. Add one entry per finding: test ID, what you did, what you expected, what you saw, **blocks / annoying / cosmetic**, and an evidence path or a few lines of output. Link an observation from a second test rather than counting it twice.
- Budget about **1–3% of the Claude week**. One short pass, bounded output, `grep` or `tail` for logs. Use no subagents except for the local agent discovery/message tests. Stop a failed test after recording the evidence. Mark tests awaiting a normal login, shutdown or the owner’s time and finish the handoff in this sitting. A config match is evidence for a config test. A visual or hardware test needs an observation.
- **must** covers an R29 change or release promise. **should** covers everyday use. **could** is optional. **the owner** means wait for the indicated action or OK. **outside** means an external service, account or device is involved. Use Bash as the daily user with `set -o pipefail`. Mark missing evidence explicitly. For grouped checks, record each case and count the ID once. An observed mismatch fails. Pass only when all required cases were observed. Paths starting with `~` refer to that user's home.
- At the end, count the four statuses (their sum should equal the number of IDs) and findings by severity. Send **linux-hub** and **mac-capacity** the local findings path and counts only. These are the owner’s own Claude sessions. This handoff and discovery/messages between the two disposable sessions are internal and need no OK. Keep screenshots, credentials, pairing codes, account names and page contents out of messages.

## Guardrails

- Anything that sends, deletes or changes something outside the laptop needs a test target or the owner's OK **in this session**. This includes Mail, Chrome on the owner's accounts, git pushes, GitHub writes, messages to people, the Mac and the server. Use local fixtures and blank test windows wherever possible. Keep pending work belonging to other sessions untouched. The fresh Board topic in T22 is a test target. Never use `board ask` during this pass (it reaches the owner’s phone).
- Never use sudo, rpm-ostree deploy/rebase/rollback, bootc switch, disk tools, firmware or the owner tools' write actions without the owner's explicit OK. Read-only status is fine. If status needs privileges, mark it **needs the owner**. There is no install, rollback or repair exercise in this pass.
- Never touch `~/.minecraft`, `~/.lunarclient` or Lunar Client. Check the Lunar **launcher name** on PATH only.
- Don't stop or restart the desktop game or session while the owner uses it. Any test that needs a stop waits for the owner's OK. Never inject input into the owner's seat. Let the owner press the key, choose the target window and enter any password. Record the original sound, brightness, mode and sharing settings before a trial and restore them afterwards.
- Never push to main. The privacy test branch is local and never pushed anywhere. Write **the owner** in anything that could be committed.

## Installed system and release

- **R29-T01 · must.** Set `announced_commit` to the pinning commit in the signed announcement. Compare its full R29 digest with both `git -C ~/AresOS show "$announced_commit:os/manifest/releases/29.json" | jq -er '.reference | split("@") | .[1]'` and `bootc status --json | jq -er '.status.booted.image.imageDigest'`. Proceed only on three equal digests. On missing evidence or denied access, pause unverified. A confirmed mismatch fails.
- **R29-T02 · must.** Run `bootc status --json | jq -er '.status.rollback.image.imageDigest'`. Expect the R28 digest, `sha256:aa97b2d506a4b48e24869902d78adb7700482a068d9bb5dc371e886a76e5f15d`.
- **R29-T03 · must.** Run `rpm-ostree status --json | jq -ec '[.deployments[] | {booted,pinned,checksum,serial,osname,digest:."container-image-reference-digest"}]'`. After confirmation expect R29 booted, R28 retained and a pinned stock row whose checksum, serial and osname match the saved corrected-stock deployment. If its saved identity is unavailable, record that gap.
- **R29-T04 · must.** Run `cat /etc/hostname && hostnamectl --static && hostnamectl --transient`. Expect the laptop's existing static name in all three places. Record “match” or “differ”. The rehearsal guest's name is specific to that guest.
- **R29-T05 · should.** In the daily terminal run `printf '%s\n' "$PATH" | tr : '\n' | grep -Fx "$HOME/.local/bin"`. Expect one or more exact matches.
- **R29-T06 · must.** Run `systemctl is-active aresos-guardian.service && systemctl is-enabled aresos-guardian.service`. Expect `active` and `enabled`.
- **R29-T07 · must.** Run `grep -Fx 'Before=aresos-guardian.service' /usr/lib/systemd/system/session-.scope.d/50-aresos-guardian.conf`. Expect the matching line. It keeps the login session available while the guard saves.
- **R29-T08 · should.** Run `systemctl --user list-timers --all --no-pager '*aresync*'`. Expect the aresync timer, a next run and its service. For a first login a previous run may still be blank. Don't start a sync.
- **R29-T09 · must.** Run `rpm -q labwc && jq -r .result.nevra /usr/share/aresos/manifest/labwc.lock.json`. Expect matching builds (the lock includes the architecture). R29 uses `0.9.6-1.fc44.aresos2` with Deskflow, `0.9.6-1.fc44.aresos1` without.
- **R29-T10 · must.** Run `rpm -V labwc`. Expect exit 0 and no changed files.
- **R29-T11 · must.** `readlink -f ~/.local/share/PrismLauncher/instances/AresDesktop/minecraft/mods/aresos.jar` must resolve to `/usr/share/aresos/minecraft/mods/aresos.jar`. Compare its `sha256sum` with both `.sha256` and `.pinned_sha256` in `/usr/share/aresos/manifest/aresos-mod.json` and the final cut pin (handoff `4846c24fbdd5fd69000bd68a4bac26a011aba6e3c6c8f8324852978aba00ab5f`). The installed `.source_revision` must equal `.source_commit` in T01’s release record.
- **R29-T12 · must.** Run `for f in 'Jersey 10' 'JetBrains Mono'; do fc-match -f '%{family}\n' "$f"; done`. Each must select the named family.
- **R29-T13 · must.** Run `rpm -q gtk4-layer-shell && test -x /usr/libexec/aresos-laptop-home`. Expect the library and exit 0. The executable is staged for later launch wiring.
- **R29-T14 · must.** Check each string separately with `grep -F` in `/usr/libexec/aresos-shell`. Require all three: `ADMISSION_SCOPE_TIMEOUT = 1.0`, `home cursor is stale` and `focused = not launch.ambiguous`.
- **R29-T15 · must · the owner.** Read the owner's R29 confirmation from the installed tools' **check** output. Expect `PASS check` and confirmation that the announced R29 runs and starts next. Compare the tools fingerprint in the saved **install** output with the announced guide. Use the saved confirmation if available. If a fresh check is wanted, the owner opens Terminal and uses the guide's `sudo /var/lib/ares/at check` with explicit OK, keeping Terminal open through PASS. The check can settle interrupted work and write local records. Don't run it as an unattended read-only probe.

## Claude Code and the session tools

Use two disposable local sessions for the messaging tests. Read the installed usage in `~/aresync/TOOLS.md` for laptop tools whose arguments follow the user's tool version. Use the test sessions' own labels for messages, never a similarly named working session.

- **R29-T16 · should · the owner · outside.** In a fresh foot Terminal, run `claude` from the daily shell. Expect the interactive prompt without a command or terminal error. Keep this test session for the next checks.
- **R29-T17 · should · the owner · outside.** In a fresh Konsole window run `claude`. Expect a usable prompt in this second local session. If Konsole is unavailable, record where it was missing.
- **R29-T18 · should · the owner.** In each prompt type `one`, press Shift+Enter, type `two` and clear the draft with Ctrl+C. Both lines should be editable together, with no submission on Shift+Enter. Record each terminal's result.
- **R29-T19 · should · the owner · outside.** In the test session use `/status` and ask “Reply R29-OK only.” Expect the existing sign-in to handle the request without a login loop. If sign-in is needed, the owner handles it. Record only the result.
- **R29-T20 · should.** In each disposable session set `topic` to a fresh `r29-test-<unique>-a` or `r29-test-<unique>-b` (substitute a short unused suffix). Run `name-me "$topic"`, then submit a harmless prompt in each. Verify both applied `linux-<topic>` names before using Board or messaging.
- **R29-T21 · should · outside.** Inspect `board --help`. Run plain `board` inside the named session to read its own topic. Continue to T22 only if that fresh topic is empty. Keep unrelated Board text out of findings.
- **R29-T22 · should · outside.** From the session that owns the fresh topic, run `board leave "$topic" 'R29 loopback'`. Find the returned `T<number>` and text on that topic in plain `board`. Set `item_id` to that exact ID, run `board drop "$item_id"`, then verify it left the active list. No OK needed. If ownership or ID is unclear, leave the item untouched and record the ID for follow-up.
- **R29-T23 · should.** In one test session call **ListAgents**. Look for the exact name of the second local test session. Expect it to be distinguishable from the working sessions.
- **R29-T24 · should.** Use **SendMessage** to send `R29 ping` to that second session. Have it return `R29 pong` to the first. Expect one matching round trip. Address only the verified test names.
- **R29-T25 · should · the owner · outside.** In the test Claude session use `/remote-control`. Have the owner open its connection from the usual remote client and send `R29 remote` to that test session. Expect the same conversation to receive it. Keep the connection URL out of findings.
- **R29-T26 · should.** In the approved disposable session compare `/hooks` with `WANTED` in `~/aresync/claude/install-hooks`, including commands and script paths. Check UserPromptSubmit, SessionStart’s `resume` and `startup|resume` matchers, and Stop. Both `hook-watch` entries need `asyncRewake: true`. Submit one harmless prompt and check for hook errors. Startup can contact Board.
- **R29-T27 · should.** From `~/AresOS`, run the block below. This trivial read-only prompt needs no OK. Expect exit 0 and `R29-OK`. A timeout is a finding.

  ```bash
  (
    cd ~/AresOS || exit 1
    set -o pipefail
    unset_args=()
    while IFS= read -r v; do unset_args+=(-u "$v"); done < <(compgen -e CLAUDE)
    env "${unset_args[@]}" timeout --kill-after=5s 90s ~/.local/bin/codex exec -s read-only \
      'Reply R29-OK only. Use no tools.' </dev/null 2>&1 | tail -6
  )
  ```

- **R29-T28 · should · outside.** Run `gh auth status --hostname github.com >/dev/null 2>&1; echo "$?"`. Expect 0. Never print the token or change login.
- **R29-T29 · should.** Run `gitleaks version`. Expect a version and exit 0. T30 exercises the installed checker on one local commit.
- **R29-T30 · should.** Run the aresync pre-push privacy check on one clean commit on a throwaway local branch. Supply the two commit IDs directly as Git would. The remote is a local test path. There is no push.

  ```bash
  (
    set -eu -o pipefail
    export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
    fixture=$(mktemp -d)
    trap 'rm -rf -- "$fixture"' EXIT
    git init -q --template= -b r29-privacy "$fixture/repo"
    cd "$fixture/repo"
    git config --local core.hooksPath /dev/null
    git config user.name 'the owner'
    git config user.email 'r29-fixture@users.noreply.github.com'
    git commit -q --allow-empty -m baseline
    printf '%s\n' 'the owner' > check.txt
    git add check.txt
    git commit -qm 'R29 local privacy check'
    ref=$(git symbolic-ref HEAD)
    printf '%s %s %s %s\n' "$ref" "$(git rev-parse HEAD)" "$ref" "$(git rev-parse HEAD^)" |
      bash ~/aresync/privacy-check.sh pre-push origin "$fixture/repo" 2>&1 | tail -6
  )
  ```

  Expect exit 0 for the clean range. Successful scanner output is suppressed. Record any skipped terms check by name without reading or copying the terms.

## Installed commands, Chrome and Control

- **R29-T31 · must.** Check `/usr/bin/aresos --help`, `chrome do --help` and `chrome read --help` through that same binary. Expect usage even with the gate closed. For quiet service readiness, `systemctl is-active aresos-toold.service && test -S /run/aresos-tools/act.sock` must print `active` and exit 0.
- **R29-T32 · must · the owner · outside.** Only with explicit OK, run `/usr/bin/aresos control pending | jq '{ok, error: .error.code}'`. It can reconcile Chrome operations, query Mail’s Sent folder and record results. Expect `ok: true`. Leave pending requests alone and keep their contents out of findings.
- **R29-T33 · must.** Run `/usr/bin/gh --version` and `~/.local/bin/gh --version`. Compare the hash from `sha256sum /usr/bin/gh` with `jq -er '.binary_sha256' /usr/share/aresos/manifest/gh.lock.json`. Require equality and the image version named by `.nevra`. The personal copy may differ.
- **R29-T34 · should.** Run `type -a chrome lunar discord localsend` in the daily shell. Expect each launcher on PATH. Record any missing name without launching it.
- **R29-T35 · must · the owner.** In Chrome's toolbar look for the **A**, in `chrome://extensions` for the AresOS extension, and in Chrome's menu for **Managed by your organization**. Use a blank test window with the owner. Don't change policy or open account pages.
- **R29-T36 · must · the owner.** For `/var/lib/aresos-control/chrome-excluded-sites.json`, `stat -c '%U:%G %a'` must give `root:aresos-tools 640`. Missing file fails. With explicit OK, the owner can verify untouched bytes silently with `printf '%s' '{"format":0,"hosts":[]}' | sudo cmp -s - /var/lib/aresos-control/chrome-excluded-sites.json` (exit 0). Never print hosts or edit the file. Skip T37–T39 for an owner-written list. An unexplained difference is a finding.
- **R29-T37 · must · the owner.** With the placeholder confirmed and OK for a blank test profile, run `/usr/bin/aresos chrome tabs`. For T37–T39 capture the CLI status before filtering its JSON. Require CLI exit 1 and `jq -e '.ok == false and .error.code == "chrome_settings_unavailable"'`. Allow only `chrome_unavailable` with exit 1 briefly while the native host connects. Retry only that pre-connection response for up to 150 seconds, as in the release probe. Stop gate tests on an unexpected reply. Never log raw replies.
- **R29-T38 · must · the owner.** Through the same CLI run `chrome read --input '{"tab":2147483647}'` and `chrome take --input '{"tab":2147483647}'` in turn. Require T37’s closed-gate refusal for each before proceeding.
- **R29-T39 · must · the owner.** Use an owner-approved HTTP fixture bound to `127.0.0.1` on a free port. Prove its request counter with one local GET, then reset it. Call `chrome open --input` with the fixture URL. Require T37’s refusal, zero requests after two seconds and no new tab. See `os/ci/release29_chrome_probe.py` for the counter.
- **R29-T40 · must · the owner.** Mark **needs the owner** until the separately approved first-use sitting, after the owner opens the gate. Use `chrome open` on a disposable loopback page with two labelled, unchecked boxes outside any form. Require `chrome read` to return a compact outline with both refs. In one `chrome do`, check each by ref. Expect two completed steps, a reported change and both boxes visibly checked. Use no account page or submission.
- **R29-T41 · must.** In an AresOS desktop terminal run `xdg-mime query default x-scheme-handler/prismlauncher`. Expect `org.prismlauncher.PrismLauncher.desktop`. From a shell lacking the desktop name, use `XDG_CURRENT_DESKTOP=AresOS xdg-mime query default x-scheme-handler/prismlauncher`.
- **R29-T42 · should · the owner · outside.** At the next genuine Prism Microsoft sign-in, let the owner finish in the browser. The browser should hand control to the waiting Prism window and sign-in should finish. If already signed in, skip. Keep the account signed in.

## Windows, keys and indicators

For visual evidence use the physical observation or an owner-approved capture of a harmless screen. A remote Claude prompt alone cannot judge pointer feel or press a laptop key.

- **R29-T43 · should.** Check command presence with `type -P grim`, `type -P ydotool` and `type -P wtype`. The image inventory lists the first two. Record what is installed. Never run input injection in this pass.
- **R29-T44 · could · the owner.** From the intended desktop terminal, use its own `WAYLAND_DISPLAY`. Have the owner choose a harmless output (`wlr-randr` lists names) and approve its capture. Set `output` to that exact name and run the block there. Record only the private PNG path. Use the owner’s observation if capture is unavailable.

  ```bash
  (
    set -eu
    : "${WAYLAND_DISPLAY:?}" "${output:?}"
    umask 077
    shot=$(mktemp --suffix=.png "${XDG_RUNTIME_DIR:?}/r29-screen.XXXXXX")
    grim -o "$output" "$shot"
    test -s "$shot" && printf '%s\n' "$shot"
  )
  ```

- **R29-T45 · must.** Run `grep -E '<name>AresOS|A-S-Tab|thumbnailLabelFormat|name="TitleBar"|direction="(Up|Down)"' /usr/share/aresos/labwc/rc.xml`. Expect the AresOS theme, reverse switcher, thumbnails and two title-bar scroll actions set to None.
- **R29-T46 · must · the owner.** Put two blank framed windows side by side and select each. Check pixel edges, readable lettering and the active frame. Open the title-bar menu, dismiss it, then drag a test window to a screen edge. Expect the menu and snap preview to share the frame’s pixel style.
- **R29-T47 · must · the owner.** With three test windows open, hold Alt, tap Tab twice, then release Alt. Expect labelled thumbnails on the focused screen and the selected window to take focus.
- **R29-T48 · must · the owner.** Hold Alt, tap Tab, then hold Shift and tap Tab. Expect the selection to move back one place. Release Alt to choose it.
- **R29-T49 · must · the owner.** Roll the wheel up and down over a floating test window's title bar. Its size should stay the same and its content should stay visible.
- **R29-T50 · must.** Read `grep -A4 '<context name="Root">' /usr/share/aresos/labwc/rc.xml`. Expect Left, Right and Middle Press all set to None. If bare desktop is visible in a test session, the owner can confirm a click there shows no Exit menu.
- **R29-T51 · must.** Read `/usr/libexec/aresos-settings get` and count the six `aresos-level` key bindings in `/usr/share/aresos/labwc/rc.xml`. Place defaults to top, size to medium. Desktop `look` defaults to `B` and draws the pixel artwork even for other choices. The game’s `look` is separate.
- **R29-T52 · must · the owner.** With OK, preserve the original desktop settings file (or its absence) under `${XDG_CONFIG_HOME:-$HOME/.config}/aresos/settings.json`. Use `/usr/libexec/aresos-settings set indicator-place bottom` and `/usr/libexec/aresos-settings set indicator-size large`. Start from top/medium for the comparison. Expect the first preview to move down and the second to grow. Restore the original settings even on failure.
- **R29-T53 · must · the owner.** Start unmuted, press volume down, mute, then volume up. Check the level rises on the last press (unless at maximum), the panel fades and `wpctl get-volume @DEFAULT_AUDIO_SINK@` agrees each time, ending unmuted. With two outputs, put the pointer on the external screen and expect the sound panel there.
- **R29-T54 · must · the owner.** Toggle microphone mute twice. Each time compare the panel with `wpctl get-volume @DEFAULT_AUDIO_SOURCE@`. Expect opposite mute states and a return to the original. With two outputs expect the panel on the pointer’s screen.
- **R29-T55 · must · the owner.** Press brightness up, then down. Expect the laptop panel and the brightness indicator to change in the matching direction. Check `brightnessctl --class=backlight get`. With the pointer on an external screen, expect the indicator on the laptop panel.
- **R29-T56 · must · the owner.** Record the starting brightness. Hold brightness down to the floor, then press it again. Compare `brightnessctl --class=backlight get` with `echo $(( ($(brightnessctl --class=backlight max) + 99) / 100 ))`. They should match and the panel should stay lit. Let the owner restore a comfortable level.
- **R29-T57 · must · the owner.** While looking around in the world, tap a volume key and keep turning. Expect one panel that disappears, with mouse and keyboard still controlling the world.
- **R29-T58 · could · the owner.** With a test app beside the world, hold Alt, tap Tab and cancel with Escape. Try a movement key. Record whether the known loss of keyboard input occurs and whether switching away and back restores it (T486).

## The home, apps and the R28 findings

Use Terminal and blank test windows. For Chrome use only owner-approved harmless tabs. The checks of the marks need the hotbar visible beside a floating window. Use the owner’s existing pins and leave the layout intact. Group classic-look checks at the same installed-game start. T72 covers permission and restoration for every look change, including T66.

- **R29-T59 · must · the owner.** Watch for tutorial hints during arrival. In a disposable home where a new recipe or advancement can be earned, note the actual trigger and watch its toast area. Expect no corresponding Minecraft pop-up. Record each trigger observed and mark unexercised cases skipped.
- **R29-T60 · must · the owner.** In Esc, hover “Start a new home…”, open its confirmation, then cancel. Expect both screens to explain that the present home is kept. You should be back in the same home.
- **R29-T61 · must · the owner.** For T61–T62 verify a disposable session home running B327 or later on the installed game. Skip both if none is ready. In Live mode try mining ordinary ground, then a logo. Expect protection feedback and both blocks intact.
- **R29-T62 · must · the owner.** In that disposable home toggle Build mode in Esc, mine a throwaway block, then press G and reopen Esc. Expect the edit in Build and the label back at Off after G.
- **R29-T63 · must · the owner.** Look at Terminal's pinned item and its loaded town gate. Expect a black block in the slot and a light prompt on a dark gate without the pale rim. Record an old gate that persists without rebuilding it.
- **R29-T64 · must · the owner.** In Live mode double-tap Space and fly a familiar route. Expect faster flight across town than on R28. Note the owner's verdict on speed separately from whether flight worked.
- **R29-T65 · must · the owner.** Focus a part-screen Terminal and move the pointer over the visible world without clicking. Expect a free pointer and a still camera. Hovering over a pinned app slot should show its name.
- **R29-T66 · must · the owner.** In classic look, centre a small Chrome test window over the game. On a local page, prove its visible press, click and wheel counters work. Note their values. Click exposed world to capture, turn, click the sky and scroll. Expect camera motion, a hand swing and a changed hotbar slot. All page counters must stay put. Record separately if Chrome disappears.
- **R29-T67 · must · the owner.** Left-click Terminal’s slot with the pointer free and no Terminal window. Expect it to open. Minimize it and use the held item to recover the same shell (`echo $$`). After launch, `stat -c '%a' "${XDG_STATE_HOME:-$HOME/.local/state}/aresos/shell.log"` must give `600`. Leave log contents private.
- **R29-T68 · must · the owner.** Focus, switch away from, then minimize all windows of one pinned test app. Expect a long bright mark while active, a shorter mark while open behind another app, and a dim one while minimized. Closing its last test window clears the mark.
- **R29-T69 · must · the owner.** Open two disposable Chrome windows with distinct harmless tabs. Focus one and minimize it, returning focus to the world without selecting the other. Left-click Chrome’s slot. Repeat with the other window using `/chrome`. Each time expect the last focused window and its tab, with the window count unchanged.
- **R29-T70 · must · the owner.** Walk into Terminal's gate with the test Terminal already open. Expect the same shell to return. Note whether the view behind a part-screen window looks black at the gate (an open R28 finding).
- **R29-T71 · must · the owner.** With one Terminal test window open and the pointer free, right-click its slot. Expect another Terminal window with a different `echo $$`. Right-click requests an ordinary launch. A single-instance app may handle it differently.
- **R29-T72 · must · the owner.** Verify the R29 AresDesktop instance (T11). Its game setting is `~/.local/share/PrismLauncher/instances/AresDesktop/minecraft/config/aresos/settings.properties`. Missing file or key means classic. Get explicit OK before changing it because Minecraft reads it at the next start. Save the exact original file privately or note its absence. Change only `look`, for game starts the owner approves. If any trial is cut short, restore the original as in T76 before handing off.
- **R29-T73 · must · the owner.** In the installed home with `look = classic` (or the default), move the mouse over the focused world to steer, then press Esc. Expect capture first and a free menu pointer after Esc.
- **R29-T74 · must · the owner.** At an approved start with `look = click`, click exposed world to enter look without acting. Turn, then rest mouse and movement keys for about 800 ms. Expect a free pointer. Repeat from rest using a movement key to enter, turn and pause again. Check release both times.
- **R29-T75 · must · the owner.** Start with `look = edge`. Rest the free pointer at an outer side edge and expect the camera to turn. With a real adjacent output, cross the shared edge. Expect the pointer to cross without turning there. Record the shared-edge case separately if no second screen is available.
- **R29-T76 · must · the owner.** In edge look, hold the pointer in the top band and press Down past level, then Up. Expect down then up, and sideways turns with Left and Right. After any trials, even if interrupted, restore the exact original file or remove only the file created for the test. Verify restoration. The owner chooses when to restart. Mark unavailable startups **needs the owner**.
- **R29-T77 · must · the owner.** Wait for an ordinary planned shutdown with work saved and the world running. Note time and whether the screen went black with only the world open. At next login check matching `stop (shutdown)` lines in `~/.local/state/aresos/desktop.log` and `.1` if rotated. Require `the save is confirmed (saved)`, then `SIGTERM sent to Java`, then `confirmed, close exited`, and the same home back.
- **R29-T78 · must · the owner.** Check `restart()` in `/usr/share/aresos/desktop-view.bashrc` calls `/usr/libexec/aresos-desktop restart`. When the owner initiates that restart with the world running, check T77’s sequence for `stop (restart)` and the same home returning. For either stop, mark **needs the owner** while waiting. After a witnessed stop, missing or unconfirmed evidence fails. Use signed rehearsal evidence for lid inhibition and hung saves.

## Deskflow and the Mac, conditional on the cut

- **R29-T79 · must.** Follow the signed cut. Use `rpm -q --qf '%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}\n' deskflow` and `test -x /usr/bin/aresos-input-sharing`. Expect `deskflow-0:1.27.0-1.fc44.x86_64` (or the superseding signed pin) and the executable. On the fallback require an uninstalled RPM and an absent image path, then skip T80–T89 as deferred. Missing promised parts fail.
- **R29-T80 · must.** Require `Exec=/usr/libexec/aresos-input-portal` in `/usr/share/dbus-1/services/org.freedesktop.impl.portal.desktop.aresos-input.service` and `org.deskflow.deskflow` as the sole ID in `/usr/share/aresos/input-portal/allowed-apps`. Expect on-demand activation.
- **R29-T81 · must.** Run `/usr/bin/aresos-input-sharing status`. Expect `off` at first use or the owner’s last choice. Record it. Schedule T87’s Off hotplug while already Off, before enabling if possible.
- **R29-T82 · must · the owner · outside.** Get OK for the specific Mac and both clipboard changes. Save work and put harmless text on both clipboards before enabling. Turn on **Mouse and keyboard sharing** with the password and open Deskflow from the hub. Use the Mac’s exact screen name and TLS. Compare the Mac’s own fingerprint in the laptop dialog and the laptop’s on the Mac if prompted. Accept only matches. Preserve existing pairings.
- **R29-T83 · must · the owner · outside.** On the AresOS desktop’s session bus run `/usr/libexec/aresos-input-portal --status`. Require exactly one row with `app="org.deskflow.deskflow"`, `enabled=true` and a positive `barriers` count. Cross to a Mac scratch window, idle at least 20 seconds, then type. Return and type locally. The idle key must arrive on the Mac and the return key on the laptop.
- **R29-T84 · must · the owner · outside.** Paste fresh `R29-laptop` text on the Mac and `R29-Mac` back on the laptop in scratch windows. With Minecraft holding the pointer locally in classic look, try the same edge. Expect game steering to stay local.
- **R29-T85 · must · the owner · outside.** While controlling the Mac, try Alt+Tab and Alt+F4 using disposable windows, then a Mac shortcut, volume and brightness. Expect forwarding with no laptop switch, close or level change. Microphone mute should affect neither device. Restore levels.
- **R29-T86 · must · the owner · outside.** Across the edge, press Super+Shift+Escape and type locally. Check for stuck Mac modifiers. Cross again and try Super+Ctrl+Escape. Expect local input and a usable recovery terminal. Use hosted evidence for the stopped-backend fallback.
- **R29-T87 · should · the owner · outside.** In an ordinary listed display mode, unplug and replug the external monitor once with sharing Off and once On with T83’s barrier armed. Compare `pgrep -u "$(id -u)" -x labwc` before and after each. Expect unchanged PID, working screens, and crossing again only when On. Skip custom modes.
- **R29-T88 · must · the owner · outside.** With the Mac connected, turn sharing Off. Expect no password and immediate local input. Try crossing and copying a fresh marker: the pointer stays local and pasting on the Mac yields no new marker. With OK, turn On again and expect a password prompt. Restore the original choice unless the owner chooses otherwise.
- **R29-T89 · must · the owner · outside.** At normal logins, observe both saved states when available. With On, expect `aresos-input-sharing status` to say `on` and crossing to work without opening Deskflow. With Off, expect `off` and keep input local. Record each state seen and defer the other if necessary. Leave the owner logged in.
