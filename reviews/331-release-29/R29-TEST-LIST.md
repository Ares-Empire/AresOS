# R29 on the laptop

## How to run this

Use this after the owner has installed R29. Work alongside normal use. Start with the quiet checks and collect the visible ones together when the owner is free. The owner's own observations and this pass both feed R30.

- Keep findings only in `~/AresOS-R29-FINDINGS.md`, local and uncommitted. Fix nothing. Use one line per test with **pass**, **fail**, **skipped (why)** or **needs the owner**. Add one entry per finding: test ID, what you did, what you expected, what you saw, **blocks / annoying / cosmetic**, and an evidence path or a few lines of output. Link an observation from a second test rather than counting it twice.
- Budget about **1–3% of the Claude week**. One short pass, bounded output, `grep` or `tail` for logs. Use no subagents except for the local agent discovery/message tests. When something fails, stop that test and ask before investigating. A config match is evidence for a config test. A visual or hardware test needs an observation.
- **must** covers an R29 change or release promise. **should** covers everyday use. **could** is optional. **the owner** means wait for the indicated action or OK. **outside** means an external service, account or device is involved. Use Bash as the daily user. Paths starting with `~` refer to that user's home.
- At the end, count the four statuses (their sum should equal the number of IDs) and findings by severity. With the owner's in-session OK for the messages, send **linux-hub** and **mac-capacity** the local path and counts only. If OK is pending, record the unsent handoff locally. Keep screenshots, credentials, pairing codes, account names and page contents out of messages.

## Guardrails

- Anything that sends, deletes or changes something outside the laptop needs a test target or the owner's OK **in this session**. This includes Mail, Chrome on the owner's accounts, git pushes, GitHub writes, messages to people, the Mac and the server. Use local fixtures and blank test windows wherever possible. Keep pending work belonging to other sessions untouched.
- Never use sudo, rpm-ostree deploy/rebase/rollback, bootc switch, disk tools, firmware or the owner tools' write actions without the owner's explicit OK. Read-only status is fine. If status needs privileges, mark it **needs the owner**. There is no install, rollback or repair exercise in this pass.
- Never touch `~/.minecraft`, `~/.lunarclient` or Lunar Client. Check the Lunar **launcher name** on PATH only.
- Don't stop or restart the desktop game or session while the owner uses it. Any test that needs a stop waits for the owner's OK. Never inject input into the owner's seat. Let the owner press the key, choose the target window and enter any password. Keep the original sound, brightness, mode and sharing settings to return to after a trial.
- Never push to main. The privacy test branch is local and never pushed anywhere. Write **the owner** in anything that could be committed.

## Installed system and release

- **R29-T01 · must.** Run `bootc status --json | jq -r '.status.booted.image.imageDigest'`. Compare the full digest with the owner's signed R29 announcement and the `reference` in `~/AresOS/os/manifest/releases/29.json` at the announced commit. All must agree. Stop the release pass on a different running image.
- **R29-T02 · must.** Run `bootc status --json | jq -r '.status.rollback.image.imageDigest'`. Expect the R28 digest, `sha256:aa97b2d506a4b48e24869902d78adb7700482a068d9bb5dc371e886a76e5f15d`.
- **R29-T03 · must.** Run `rpm-ostree status --json | jq -c '[.deployments[] | {booted,pinned,digest:."container-image-reference-digest"}]'`. After confirmation expect R29 running, R28 retained and corrected stock still pinned. Checking this never requires booting another entry.
- **R29-T04 · must.** Run `cat /etc/hostname && hostnamectl --static && hostnamectl --transient`. Expect the laptop's existing static name in all three places. Record “match” or “differ”. The rehearsal guest's name is specific to that guest.
- **R29-T05 · should.** In the daily terminal run `printf '%s\n' "$PATH" | tr : '\n' | grep -Fx "$HOME/.local/bin"`. Expect one or more exact matches.
- **R29-T06 · must.** Run `systemctl is-active aresos-guardian.service && systemctl is-enabled aresos-guardian.service`. Expect `active` and `enabled`.
- **R29-T07 · must.** Run `grep -Fx 'Before=aresos-guardian.service' /usr/lib/systemd/system/session-.scope.d/50-aresos-guardian.conf`. Expect the matching line. It keeps the login session available while the guard saves.
- **R29-T08 · should.** Run `systemctl --user list-timers --all --no-pager '*aresync*'`. Expect the aresync timer, a next run and its service. For a first login a previous run may still be blank. Don't start a sync.
- **R29-T09 · must.** Run `rpm -q labwc && jq -r .result.nevra /usr/share/aresos/manifest/labwc.lock.json`. Expect matching builds (the lock includes the architecture). R29 uses `0.9.6-1.fc44.aresos2` with Deskflow, `0.9.6-1.fc44.aresos1` without.
- **R29-T10 · must.** Run `rpm -V labwc`. Expect exit 0 and no changed files.
- **R29-T11 · must.** Run `sha256sum /usr/share/aresos/minecraft/mods/aresos.jar && jq -r '.sha256,.pinned_sha256' /usr/share/aresos/manifest/aresos-mod.json`. Expect three equal hashes. The B333/B343 handoff gives `4846c24fbdd5fd69000bd68a4bac26a011aba6e3c6c8f8324852978aba00ab5f`. Use the final signed cut record if it supersedes that pin.
- **R29-T12 · must.** Run `for f in 'Jersey 10' 'JetBrains Mono'; do fc-match -f '%{family}\n' "$f"; done`. Each must select the named family.
- **R29-T13 · must.** Run `rpm -q gtk4-layer-shell && test -x /usr/libexec/aresos-laptop-home`. Expect the library and exit 0. The executable is staged for later launch wiring.
- **R29-T14 · must.** Read `grep -nE 'ADMISSION_SCOPE_TIMEOUT =|home cursor is stale|focused = not launch.ambiguous' /usr/libexec/aresos-shell`. Expect the one-second admission limit, stale app-list rejection and a focus check after uncertain restarts. This checks the installed helper without stalling or restarting it.
- **R29-T15 · must · the owner.** Read the owner's R29 confirmation from the installed tools' **check** output. Expect `PASS check` and confirmation that the announced R29 runs and starts next. Compare the tools fingerprint in the saved **install** output with the announced guide. Use the saved confirmation if available. If a fresh check is wanted, the owner opens Terminal and uses the guide's `sudo /var/lib/ares/at check` with explicit OK, keeping Terminal open through PASS. The check can settle interrupted work and write local records. Don't run it as an unattended read-only probe.

## Claude Code and the session tools

Use two disposable local sessions for the messaging tests. Read the installed usage in `~/aresync/TOOLS.md` for laptop tools whose arguments follow the user's tool version. Use the test sessions' own labels for messages, never a similarly named working session.

- **R29-T16 · should · the owner · outside.** In a fresh foot Terminal, run `claude` from the daily shell. Expect the interactive prompt without a command or terminal error. Keep this test session for the next checks.
- **R29-T17 · should · the owner · outside.** In a fresh Konsole window run `claude`. Expect a usable prompt in this second local session. If Konsole is unavailable, record where it was missing.
- **R29-T18 · should · the owner.** In each prompt type `one`, press Shift+Enter, type `two` and clear the draft with Ctrl+C. Both lines should be editable together, with no submission on Shift+Enter. Record each terminal's result.
- **R29-T19 · should · the owner · outside.** In the test session use `/status` and ask “Reply R29-OK only.” Expect the existing sign-in to handle the request without a login loop. If sign-in is needed, the owner handles it. Record only the result.
- **R29-T20 · should · outside.** In each test session look up the installed name-me invocation with `grep -in -m3 'name-me' ~/aresync/TOOLS.md`. Run it in that session's own context. Assign each test a distinct unused name if the tool asks. Use the names in T23 to check which session each one identifies.
- **R29-T21 · should · outside.** Run `board --help`. Use the displayed read-only commands to list topics and read one item by its ID. Expect the same ID and topic. Record neither private text nor unrelated items.
- **R29-T22 · should · outside.** Use `board leave` once with the installed usage, addressed to a fresh topic owned only by this test session, with text `R29 loopback`. Read it back, then use the board's documented drop command on the returned test ID or topic. If cleanup is ambiguous, stop before dropping anything. Expect the note to arrive and leave the active list. Never drop an existing topic.
- **R29-T23 · should.** In one test session call **ListAgents**. Look for the exact name of the second local test session. Expect it to be distinguishable from the working sessions.
- **R29-T24 · should.** Use **SendMessage** to send `R29 ping` to that second session. Have it return `R29 pong` to the first. Expect one matching round trip. Only these two tests may use test agents.
- **R29-T25 · should · the owner · outside.** In the test Claude session use `/remote-control`. Have the owner open its connection from the usual remote client and send `R29 remote` to that test session. Expect the same conversation to receive it. Keep the connection URL out of findings.
- **R29-T26 · should.** Open `/hooks` in the test session. Compare the enabled hook events and commands with the aresync installer's hook entries in `~/aresync` (locate them with `git -C ~/aresync grep -il 'UserPromptSubmit\|SessionStart\|PreToolUse' | head -15`). Expect installed aresync entries to match their event and target and any referenced scripts to exist. Use a normal test prompt to check for hook errors. Don't edit or reinstall hooks.
- **R29-T27 · should · outside.** Run `(cd ~/AresOS && timeout 90 codex exec --sandbox read-only 'Reply R29-OK only. Use no tools.' </dev/null) 2>&1 | tail -6` with `set -o pipefail`. Expect exit 0 and the reply without waiting for stdin. A timeout is a finding.
- **R29-T28 · should · outside.** Run `gh auth status --hostname github.com >/dev/null 2>&1; echo "$?"`. Expect 0. Never print the token or change login.
- **R29-T29 · should.** Run `gitleaks version`. Expect a version and exit 0. T30 exercises the installed checker on one local commit.
- **R29-T30 · should.** Run the aresync pre-push privacy check on one clean commit on a throwaway local branch. Supply the two commit IDs directly as Git would. The remote is a local test path. There is no push.

  ```bash
  (
    set -eu -o pipefail
    fixture=$(mktemp -d)
    git init -q -b r29-privacy "$fixture/repo"
    cd "$fixture/repo"
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

  Expect exit 0 for the clean range, with the scanner actually run. Record any skipped terms check by name without reading or copying the terms.

## Installed commands, Chrome and Control

- **R29-T31 · must.** Run `/usr/bin/aresos --help | head -12`. Expect the image's command to give usage. Run `/usr/bin/aresos chrome do --help | head -4` to see the multi-step action and `/usr/bin/aresos chrome read --help | head -4` for the compact outline. Help works while the gate is closed.
- **R29-T32 · must.** Run `systemctl is-active aresos-toold.service`, then `aresos control pending | jq '{ok, error: .error.code}'`. Expect `active` and `ok: true`. Leave any pending requests alone.
- **R29-T33 · must.** Run `/usr/bin/gh --version | head -1` and `~/.local/bin/gh --version | head -1`. Both should run. The image lock (`jq -r .nevra /usr/share/aresos/manifest/gh.lock.json`) names the image version. The local version can differ.
- **R29-T34 · should.** Run `type -a chrome lunar discord localsend` in the daily shell. Expect each launcher on PATH. Record any missing name without launching it.
- **R29-T35 · must · the owner.** In Chrome's toolbar look for the **A**, in `chrome://extensions` for the AresOS extension, and in Chrome's menu for **Managed by your organization**. Use a blank test window with the owner. Don't change policy or open account pages.
- **R29-T36 · must · the owner.** Run `stat -c '%U:%G %a' /var/lib/aresos-control/chrome-excluded-sites.json`. Expect `root:aresos-tools 640`. Confirm with the owner that the never-list is still unwritten before T37–T40. Only run these during the owner's first-use sitting or with the owner's in-session OK. Don't read its hosts, write a list or change permissions.
- **R29-T37 · must · the owner.** With OK to test the closed gate, run `aresos chrome tabs | jq -r '.error.code'`. Expect exactly `chrome_settings_unavailable`. If the list exists, skip T37–T40. If any reply differs, stop the remaining gate tests without reading page data.
- **R29-T38 · must · the owner.** Run `aresos chrome read --input '{"tab":2147483647}' | jq -r '.error.code'`. This unused test ID should get `chrome_settings_unavailable` before any tab lookup.
- **R29-T39 · must · the owner.** Run `aresos chrome open --input '{"url":"https://r29-test.invalid/"}' | jq -r '.error.code'`. Expect `chrome_settings_unavailable` and no new tab. Only the reserved test address is in scope.
- **R29-T40 · must · the owner.** Run `aresos chrome take --input '{"tab":2147483647}' | jq -r '.error.code'`. Expect `chrome_settings_unavailable` before the tool can take a tab.
- **R29-T41 · must.** In an AresOS desktop terminal run `xdg-mime query default x-scheme-handler/prismlauncher`. Expect `org.prismlauncher.PrismLauncher.desktop`. From a shell lacking the desktop name, use `XDG_CURRENT_DESKTOP=AresOS xdg-mime query default x-scheme-handler/prismlauncher`.
- **R29-T42 · should · the owner · outside.** At the next genuine Prism Microsoft sign-in, let the owner finish in the browser. The browser should hand control to the waiting Prism window and sign-in should finish. If already signed in, skip. Keep the account signed in.

## Windows, keys and indicators

For visual evidence use the physical observation or an owner-approved capture of a harmless screen. For keys use an isolated test compositor if available. A remote Claude prompt alone cannot judge pointer feel or press a laptop key.

- **R29-T43 · should.** Run `grep -E '^(grim|ydotool|wtype)-' /usr/share/aresos/manifest/packages.txt; type -P grim ydotool wtype`. The repo's full inventory (`os/manifest/ci/packages.txt`) lists grim and ydotool. The add-on lock (`os/packages.lock.json`) pins grim. Neither lists wtype. Use the installed result for this cut. ydotool targets an input device: use it only with a verified isolated test seat, never the daily seat.
- **R29-T44 · could · the owner.** With permission to capture what is visible, use the block below in the daily user's shell. The first foot must belong to the desktop the owner wants captured. Check that every visible output is safe to include. Expect a nonempty PNG of the agreed screen. Record its path locally. If the socket is unavailable or the screen has private content, use the owner's observation.

  ```bash
  (
    set -eu
    foot_pid=$(pgrep -o -u "$(id -u)" -x foot)
    display=$(tr '\0' '\n' < "/proc/$foot_pid/environ" | sed -n 's/^WAYLAND_DISPLAY=//p')
    test -n "$display"
    umask 077
    shot=$(mktemp --suffix=.png "${XDG_RUNTIME_DIR:?}/r29-screen.XXXXXX")
    WAYLAND_DISPLAY="$display" grim "$shot"
    test -s "$shot" && printf '%s\n' "$shot"
  )
  ```

- **R29-T45 · must.** Run `grep -E '<name>AresOS|A-S-Tab|thumbnailLabelFormat|name="TitleBar"|direction="(Up|Down)"' /usr/share/aresos/labwc/rc.xml`. Expect the AresOS theme, reverse switcher, thumbnails and two title-bar scroll actions set to None.
- **R29-T46 · must · the owner.** Put two blank, framed windows side by side. Click each title bar. Expect pixel edges and readable lettering, with the active frame moving to the selected window.
- **R29-T47 · must · the owner.** With three test windows open, hold Alt, tap Tab twice, then release Alt. Expect labelled thumbnails on the focused screen and the selected window to take focus.
- **R29-T48 · must · the owner.** Hold Alt, tap Tab, then hold Shift and tap Tab. Expect the selection to move back one place. Release Alt to choose it.
- **R29-T49 · must · the owner.** Roll the wheel up and down over a floating test window's title bar. Its size should stay the same and its content should stay visible.
- **R29-T50 · must.** Read `grep -A4 '<context name="Root">' /usr/share/aresos/labwc/rc.xml`. Expect Left, Right and Middle Press all set to None. If bare desktop is visible in a test session, the owner can confirm a click there shows no Exit menu.
- **R29-T51 · must.** Run `/usr/libexec/aresos-settings get` and `grep -c 'command="/usr/libexec/aresos-level ' /usr/share/aresos/labwc/rc.xml`. Expect place and size (top, medium by default), a look setting and six key bindings. For the available choices read `grep -E "^    'indicator-(place|size)'" /usr/libexec/aresos-settings`. Expect top/bottom and small/medium/large. T52 checks what is actually drawn.
- **R29-T52 · must · the owner.** Press volume down once while a blank test window has focus. Expect a game-style panel at the configured position, the new level, then a clear screen. Compare with `wpctl get-volume @DEFAULT_AUDIO_SINK@`.
- **R29-T53 · must · the owner.** Mute the speakers, then press volume up. Expect the mute indication first, then a higher level (unless already at maximum) and an unmuted sink in `wpctl get-volume @DEFAULT_AUDIO_SINK@`.
- **R29-T54 · must · the owner.** Toggle microphone mute twice. Each time compare the panel with `wpctl get-volume @DEFAULT_AUDIO_SOURCE@`. Expect opposite mute states and a return to the original.
- **R29-T55 · must · the owner.** Press brightness up, then down. Expect the laptop panel and the brightness indicator to change in the matching direction. Read the backlight with `brightnessctl --class=backlight get`.
- **R29-T56 · must · the owner.** Record the starting brightness. Hold brightness down to the floor, then press it again. Compare `brightnessctl --class=backlight get` with `echo $(( ($(brightnessctl --class=backlight max) + 99) / 100 ))`. They should match and the panel should stay lit. Let the owner restore a comfortable level.
- **R29-T57 · must · the owner.** While looking around in the world, tap a volume key and keep turning. Expect one panel that disappears, with mouse and keyboard still controlling the world.
- **R29-T58 · could · the owner.** With a test app beside the world, hold Alt, tap Tab and cancel with Escape. Try a movement key. Record whether the known loss of keyboard input occurs and whether switching away and back restores it (T486).

## The home, apps and the R28 findings

Use Terminal and blank test windows. For Chrome use only owner-approved harmless tabs. The checks of the marks need the hotbar visible beside a floating window. Use the owner's existing pins or the disposable preview. Leave the owner's layout intact.

- **R29-T59 · must · the owner.** During ordinary arrival and movement in the home, watch the toast area. Expect no “punch a tree”, recipe or advancement prompts. Record what the owner actually did and how long they watched.
- **R29-T60 · must · the owner.** In Esc, hover “Start a new home…”, open its confirmation, then cancel. Expect both screens to explain that the present home is kept. You should be back in the same home.
- **R29-T61 · must · the owner.** In a disposable home in Live mode, try mining ordinary ground, then a logo. Expect the blocks to stay put and the action bar to explain protection. Don't risk an edit in the owner's town.
- **R29-T62 · must · the owner.** In that disposable home toggle Build mode in Esc, mine a throwaway block, then press G and reopen Esc. Expect the edit in Build and the label back at Off after G.
- **R29-T63 · must · the owner.** Look at Terminal's pinned item and its loaded town gate. Expect a black block in the slot and a light prompt on a dark gate without the pale rim. Record an old gate that persists without rebuilding it.
- **R29-T64 · must · the owner.** In Live mode double-tap Space and fly a familiar route. Expect faster flight across town than on R28. Note the owner's verdict on speed separately from whether flight worked.
- **R29-T65 · must · the owner.** Focus a part-screen Terminal and move the pointer over the visible world without clicking. Expect a free pointer and a still camera. Hovering over a pinned app slot should show its name.
- **R29-T66 · must · the owner.** Place a harmless local test page in a floating Chrome window over the middle of the game window, leaving world visible beside it. Use a scrollable test page with no account or form. Click exposed world to steer, then turn, left-click the sky and scroll. Expect world input and no click, focus or scroll in the test page. Record separately if the app disappears (the R28 stacking issue).
- **R29-T67 · must · the owner.** With the pointer free, left-click Terminal's visible slot when it has no window. Expect Terminal to open. Minimize that test window and bring it back by using the held Terminal item in the world. Its shell should be the same one (compare `echo $$`).
- **R29-T68 · must · the owner.** Focus, switch away from, then minimize all windows of one pinned test app. Expect a long bright mark while active, a shorter mark while open behind another app, and a dim one while minimized. Closing its last test window clears the mark.
- **R29-T69 · must · the owner.** Minimize a Chrome test window showing a harmless distinctive tab. With the pointer free, left-click Chrome's slot. Repeat using `/chrome` in the world. Expect that last window and tab back both times, with no extra window.
- **R29-T70 · must · the owner.** Walk into Terminal's gate with the test Terminal already open. Expect the same shell to return. Note whether the view behind a part-screen window looks black at the gate (an open R28 finding).
- **R29-T71 · must · the owner.** With one Terminal test window open and the pointer free, right-click its slot. Expect another Terminal window with a different `echo $$`. Right-click requests an ordinary launch. A single-instance app may handle it differently.
- **R29-T72 · must · the owner.** Run `command -v hub-try`. For a preview, confirm the trial checkout includes B343 with `git -C ~/AresOS-try merge-base --is-ancestor 70364fa9 HEAD` (exit 0). Run `hub-try --outputs 2` **only at a time the owner approves, especially if the desktop game is running**. If that checkout is older, mark the preview checks skipped. Expect two movable preview windows and a disposable world. On a busy/refused run, skip. Never force it, update its checkout or stop the desktop game for it.
- **R29-T73 · must · the owner.** In the preview with classic look (the default), move the mouse to steer, then press Esc. Expect ordinary captured movement, then a free pointer in the menu.
- **R29-T74 · must · the owner.** Close only the disposable preview between trials. Have the owner try `look = click` in the **preview's** `~/AresOS-try/mod/run/config/aresos/settings.properties`. Start the preview with that setting. Click open world, turn, then rest the mouse and movement keys for about a second. Expect the first click to start looking and the pause to release the pointer. Ask how crossing feels.
- **R29-T75 · must · the owner.** With `look = edge` in that same preview file, start the two-output preview. Align the two windows side by side. At an outer left or right edge the camera should turn. At the shared edge the pointer should cross without turning. This tests the prototype, not automatic placement of the home on a plugged-in monitor.
- **R29-T76 · must · the owner.** In edge look point at the top band until looking up. Keep the pointer there and hold Down past level, then press Up. Expect to look back down, then up. Try Left and Right for sideways turns. Restore the previous preview setting after the trial.
- **R29-T77 · must · the owner.** Use an ordinary **planned system shutdown** the owner already wants, with the R29 world running and other work saved. Record the time and ask whether the black save screen appeared with only the world open. At the next login inspect `grep -F 'stop (shutdown)' ~/.local/state/aresos/desktop.log | tail -15`. For that stop expect a confirmed save of the running home **before** “SIGTERM sent to Java”, then an exited game. The same home should reopen. If there is no matching stop, mark **needs the owner** and wait for the next normal shutdown. Don't simulate a timeout, kill the game or request a reboot.

- **R29-T78 · must.** Run `grep -F 'restart()' /usr/share/aresos/desktop-view.bashrc`. Expect the message window's command to call `/usr/libexec/aresos-desktop restart`. Leave live restarts to the owner.

## Deskflow and the Mac, conditional on the cut

- **R29-T79 · must.** Check the signed release announcement, then run `rpm -q deskflow; command -v aresos-input-sharing`. With B321, expect `deskflow-1.27.0-1.fc44` and the switch. Without B321, expect both absent and mark T80–T89 **skipped (deferred to R30)**. Missing parts on a cut that promises them are a failure.
- **R29-T80 · must.** Run `cat /usr/share/dbus-1/services/org.freedesktop.impl.portal.desktop.aresos-input.service && cat /usr/share/aresos/input-portal/allowed-apps`. Expect activation of `/usr/libexec/aresos-input-portal` on demand and only Deskflow's app ID on the allow-list. A constantly running system service is unnecessary.
- **R29-T81 · must.** Run `aresos-input-sharing status`. Expect `off` on first use, or the owner's last choice on a later login. Record the original setting before touching it.
- **R29-T82 · must · the owner · outside.** With the Mac available and work saved, have the owner open **Mouse and keyboard sharing** and turn it on. Expect a password prompt. Open Deskflow from the hub for this login. For a new pairing, use the Mac's exact screen name in the layout, point its client at the laptop and keep TLS on. The owner confirms only matching fingerprints. If already paired, keep the trust record and skip the first-pair observation.
- **R29-T83 · must · the owner · outside.** With both devices ready, run `/usr/libexec/aresos-input-portal --status` in the desktop session. Expect an enabled Deskflow session with a barrier. Cross the edge and type a test word in a scratch window on the Mac. Move back and type locally. Each word should reach its intended device.
- **R29-T84 · must · the owner · outside.** With both clipboards available for testing, copy `R29-laptop` to a scratch Mac document and `R29-Mac` back. Expect exactly those strings. Use only new test text.
- **R29-T85 · must · the owner · outside.** On the Mac side use a harmless shortcut in a test window and press volume or brightness. Expect the Mac to receive them and the laptop level to stay put. Microphone mute is a known exception and should affect neither device while captured.
- **R29-T86 · must · the owner · outside.** While across the edge press Super+Shift+Escape, then type a test word in a local scratch window. Expect local input and no stuck modifier on the Mac. Cross again and try Super+Ctrl+Escape. Expect local input and the recovery terminal.
- **R29-T87 · should · the owner · outside.** While sharing is armed, have the owner unplug and replug the external monitor when convenient. Compare `pgrep -u "$(id -u)" -x labwc` before and after, then try crossing again. Expect the same desktop process, recovered displays and working crossing.
- **R29-T88 · must · the owner · outside.** With the Mac connected, turn sharing off. Expect no password, immediate local input, and no new clipboard transfer or crossing. The owner chooses whether to leave it off or restore the original setting.
- **R29-T89 · must · the owner · outside.** At the next normal login with sharing left on by choice, check `aresos-input-sharing status` and try crossing without opening Deskflow. Expect `on` and a working connection. If left off, expect `off` and local input only. Record which case you observed. Don't log the owner out to manufacture the other case.
