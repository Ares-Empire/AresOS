# 22d design note: the owner tools without the stick, from Claude's terminal

Empire brief 291. Written 2026-11-14 on main `44ddfd16` by a Claude agent on Fable 5.2 (the integrator's choice: a new, not fully scoped design for a tool that decides what the laptop trusts). A design note only: it changes no tool, test, guide or workflow.

Made by reading the code and running pure-Python and git snippets on repository files. No owner tool, `sudo`, ostree, bootc or rpm-ostree command ran. **(live)** marks a read-only look at the laptop under R27 on 2026-11-14; those are not repository facts and no test pins them.

Words: **v2, v3, v4** are tools versions (v2 `851eb742…` is on the laptop, v3 `2084c786…` on main, v4 is 22d's). The **fingerprint** is the SHA-256 of a bundle's `SHA256SUMS`. The **block** is the start block the guide quotes. The **routine route** is Claude's terminal plus his password; the **emergency route** is the stick and the tty3 console.

## The answers in short

1. **Approval:** the password prompt and nothing else. On R27 a program of `ares` becomes root only with his password typed at that moment; the image enforces and tests that. It proves he approved a root command now, not which one, and no dialog on R27 can prove which. 22d adds one fixed generated command and a label in the prompt, and builds no new mechanism.
2. **Identity:** the fingerprint, as today, taken from the reviewed commit on GitHub's main with `git archive`. He can compare eight characters with one line on GitHub on his phone. No signed tag, no bundle signature.
3. **Records** stay where they are. `export` without a stick writes a copy his account can read, and the current title reaches his phone after every change.
4. **First install:** the block runs the new bundle's code, so v4 decides for itself; v2 and v3 never run. Their recovery code must still read v4's journal.
5. **Emergency route:** unchanged, rule for rule. Which block ran decides the route.
6. **Rehearsal:** package 27's route, then v4 installed from his desktop session with no terminal and the password typed into the dialog. One stick install stays in the walk.
7. **Size:** about a third of 22c: five or six agent steps and one VM rehearsal.

## What today's checks prove

| Check | Where | Proves | Does not prove |
|---|---|---|---|
| stdin is a terminal | `os/owner-tools/owner.py:2503` (tools update), `:2658` (first install) | Some terminal is on stdin | That it is tty3: a pseudo-terminal passes (measured in `reviews/14-owner-tools/REPORT.md:4365`). Only `Tools.session()` (`owner.py:1999-2031`), used by the layout commands, checks a physical console |
| The labelled stick | `owner.py:2223-2237`, called at `:2504` and `:2663`; `os/owner-tools/media.py:45-62` | A removable exFAT USB labelled ARESTOOLS, mounted once, holds the same bundle as the private copy. Someone plugged it in since the last restart (`at reboot` refuses while it is attached, `owner.py:1913`) | That the bundle is the right one |
| Line 8 | `docs/INSTALL.md:95`, `:248`; `os/owner-tools/bootstrap.py:47` | System tools checked the private copy against the block's fingerprint before any bundle code ran | Where that fingerprint came from: that is the owner comparing with the guide (`docs/INSTALL.md:103`, `:238`) |
| Root | `owner.py:2785` | sudo accepted a password | Whose session it was |

With v3 the human acts are: plug in the stick, type or compare line 8, type the password. "Only from the physical recovery console" is a message, not a check.

Claude's shell has no terminal: stdin is `/dev/null` and there is no controlling terminal **(live)**. From there v3 stops at `owner.py:2503` with **Tools update runs only from the physical recovery console**, before the stick check. From a terminal the STOP is **Tools USB label not found**, as 22c's PLAN-GAP 1 says (`reviews/22c-ways-back-after-update/REPORT.md:1784-1796`). Nothing changes either way. This is read from the order of the two lines, not run.

## 1. What proves that the owner approved

**Facts**

- **No cached sudo credential.** `Defaults:ares timestamp_timeout=0` (`os/config/etc/sudoers.d/aresos-everyday:5`). The image build requires it (`os/ci/image-checks.sh:31`), refuses `sudo -n` (`:44`) and proves that a child of a shell that just authenticated is refused (`:48-80`); the update rehearsal checks it again on the updated system (`os/ci/owner_vm.py:1439-1443`, `:904-905`). The file is root-owned (`os/ci/image-checks.sh:41-42`). polkit keeps no authorization either and denies rpm-ostree's actions to `ares` even with the password (`os/config/usr/share/polkit-1/rules.d/00-aresos-maintenance.rules:68-74`). The one standing credential the image cannot prevent is a root shell he leaves open in a desktop terminal; the routine route never needs one.
- **The dialog.** Without a terminal sudo can ask only through an askpass helper. `SUDO_ASKPASS` is `/usr/bin/ksshaskpass`, set by `/etc/profile.d/askpass.sh`, which the image inherits from Bazzite **(live)**; nothing under `os/config` sets it. `sudo -A` has not been tried on the laptop (`STATE.md:162`).
- **What it shows.** Only the prompt text. The caller sets the text (`sudo -p`), picks the helper (`SUDO_ASKPASS` wins over `sudo.conf`) and picks the command, which the dialog never shows. So he cannot see which bundle he approves: the window says what the caller says.
- **The helper can remember.** ksshaskpass 6.7.5 is made for SSH. It links keyring read and write and a "keep password" option, and recognises prompts such as `^Password for '(.*)': $` **(live, from the binary's strings; its source was not read)**. sudo's default prompt matches none, but the caller chooses the prompt. An answer kept in the keyring would be a cached credential outside sudo.
- **An agent with his shell, without his password,** cannot become root. It can write the bundle folder, the checkout, his dotfiles and `~/.local/bin` (first on his PATH, **live**), open a password window at any time with any text, and choose what runs behind it. The helper runs as `ares` and `kernel.yama.ptrace_scope` is 0 **(live)**, so a hostile program running as him could read what he types. **With one accepted prompt** the caller is root for that command, whatever it is.

A fresh prompt therefore proves that he approved *a* root command at that moment, not *which*. On the stick route the command is his, because he types the block at tty3. On the routine route it is Claude's.

**Options**

| | Option | Verdict |
|---|---|---|
| A | The password prompt is the approval: `sudo -A`, one fixed generated command, a label in the prompt | **Recommended.** What he asked for; already enforced by the image; nothing new to trust or build |
| B | Keep a physical act: the tty3 console without the stick | That is the emergency route minus the stick, not "Claude runs it" |
| C | A root-owned prompt: a polkit action with its own message, or a root-owned `aresos` entry | Needs an image change, so it cannot serve this install. The window is still drawn by a program in his session (`os/ci/image-checks.sh:489`): better words, same proof. Step 2's, if anywhere |
| D | A second channel: a tap on his phone, a code on the console | New machinery that step 2 replaces |

**Why A.** It is the line that already guards every other administrator action on R27 (his decision "Like Windows", `docs/design/OS-BASE.md:14`; Control relies on it, `STATE.md:42`). 22d adds no new trusted party.

**Its limit.** A protects against an agent acting unasked and against mistakes. It does not protect against an agent that shows one thing and runs another. Nothing at this layer can: once he accepts the prompt, the caller is root. Control draws the same line (decision 24, `STATE.md:232-234`).

**How it is enforced**

- **The sudoers rule in the image is the enforcement.** No new rule: `ares` already has `(ALL) ALL`, so a narrower one adds nothing, and the image refuses passwordless rules (`os/ci/image-checks.sh:32-39`). polkit is not used.
- **`sudo -k` goes into the generated line.** With a command it makes sudo ignore any ticket for that call. It covers a laptop whose sudoers were changed by hand, but it is the caller's flag, not the enforcement.
- **No check inside the tools.** Root cannot prove how it became root, and a root caller bypasses any such check. The tools record who called: login uid, terminal or not, source.
- **One fixed line:** `SUDO_ASKPASS=/usr/bin/ksshaskpass sudo -k -A -p '<label>' bash -c '<the 12-line folder block>'`. `bootstrap.py` generates it, `commands.json` holds it as `install-folder`, the guide quotes it and the tests compare them (`os/tests/test_owner_equality.py:47-54` already does this for the folder block, which starts `sudo bash -c` today, `bootstrap.py:57`). Naming the helper makes the route independent of the inherited profile script.
- **The label** names the action and the fingerprint's first eight characters, for example `AresOS owner tools 2084c786: password for ares`. It must match none of the helper's remembered-prompt patterns; the rehearsal shows the window and that nothing is stored.
- **The other owner commands** get the same prefix and their own label. They need no tools change: only `login`, the layout commands, the tools update and the first install look at the terminal (`owner.py:1660`, `:2000`, `:2503`, `:2658`).
- **His rule, in the guide:** type the password only right after telling Claude to go, and only into a window with that label. Cancel changes nothing. He must be at the laptop: the window is on its screen, not on his phone.

## 2. What replaces the stick as the bundle's identity

**Today** the identity is the fingerprint (`os/owner-tools/bundle.py:27-32`, `:47`; `owner.py:197-231`), a literal on line 8 that he types or compares. The stick only carries the bundle: `tools_stick` ties the private copy to it (`owner.py:2236`) and its volume UUID goes into the journal so a resume needs the same stick (`:2567`, `:2570-2571`).

**The problem.** When Claude types everything, bundle and fingerprint come from the same hands. Checking one against the other proves only that the copy is undamaged.

| | Anchor | Verdict |
|---|---|---|
| a | The checkout as it stands | No: a working tree can be dirty, stale or on a branch |
| b | The reviewed commit on GitHub's main: fetch, require the announced commit on `origin/main`, take the payload with `git archive`, pin its fingerprint in the fixed block | **The anchor** |
| c | The block, as root, fetches main's `SHA256SUMS` and compares | No: it guards the same mistakes as b and puts network and TLS into the trusted start |
| d | A signed tag or a signed bundle | Not now |
| e | He compares eight characters with one line on GitHub on his phone | **His optional check** |

**Why b and e**

- **b removes the failures that really happen:** a bundle from a dirty tree, an unmerged branch or a stale checkout. Claude runs its lines as `ares` before the prompt (22c wrote them, `reviews/22c-ways-back-after-update/REPORT.md:1826-1833`; the on-main check is one more line). `git archive` takes the committed payload whatever the working tree holds; on `44ddfd16` it reproduces `2084c786…` (checked for this note). The tests hold guide, `commands.json` and payload to one fingerprint (`os/tests/test_owner_equality.py`). The tools themselves refuse older tools and a foreign release history (`owner.py:2559-2561`).
- **Why not d.** A key on the laptop can be used by the agent. A key he holds means he signs every bundle: more ceremony than the stick, for something he cannot review. A keyless signature by the workflow (cosign, as `os/release/verify.sh:5-8` does for the image) is step 2's anchor; there the tools travel inside the signed image, so a bundle signature built now would be thrown away.
- **What he can realistically check:** that a window appears when he expects one, its label, and eight characters, once per new tools, against a line he can find on his phone: the tools row of `docs/INSTALL-STATUS.md` (line 27 today) and the pull request's title. Not a 12-line block or 64 hex digits.
- **Its limit.** Main is the anchor because it is public, reviewed, tested and logged, not because the laptop's agent cannot reach it: `gh` is logged in on the laptop (`AGENTS.md:67`) and main has no branch protection (GitHub API, **live**). The phone check shows "what is installed is what is public on main", not that main is good.

**What changes in v4** (`update_tools`, `owner.py:2503-2504` and the journal lines)

- **Which block ran decides the route,** never whether a stick happens to be plugged in. The stick block leaves its mount at `m` beside the private copy (`bootstrap.py:25-27`); the folder block has none (`:29-30`). With the mount: today's rules, all of them. Without: no terminal test, no stick, and an attached stick is not consulted. A new command word was considered and dropped: it would change the block 22c built and the words Control reserves (`STATE.md:157`) for no added safety.
- **The journal** keeps its schema name `tools-update1` and gains a `source` (the stick with its volume UUID, or the folder). The receipt records source and caller.
- **Resume** needs the same fingerprint. An update started from the stick resumes only from that stick, as today. One started from the folder resumes from either route, so the emergency route can finish what the routine route began.
- **The first installation** (`owner.py:2658-2663`: typed disk serials, stick, terminal) stays as it is; on the folder route it refuses before any prompt.

## 3. Records and diagnostics without the stick

**Today.** Records are root-only in `/var/lib/ares/records`, STOP diagnostics in `/var/lib/ares/diagnostics` (`owner.py:32-34`, `:2752-2780`). `export` copies both to the stick and nowhere else (`media.py:65-122`). Without a stick it passes with **Tools stick absent; full records remain internal** (`media.py:66-68`). With a stick whose bundle differs from the installed one it STOPs (`media.py:74`, `:102`, `:108`), so after a stick-free update the old stick is refused.

1. **The tools' own records: no change.** They stay root-only and remain the one truth; the receipt gains source and caller. sudo's journal entry names the command each prompt approved (to confirm in the rehearsal).
2. **Help after a STOP.** The printed lines usually name the cause. For the file behind them the options are a free-form `sudo cat` (a prompt for an arbitrary root command, the habit to avoid), the stick, or `export`. **Recommended:** with no stick plugged in, `export` writes its checked copy to a root-owned folder outside any home that only the calling account can read. One fixed command, one prompt, a known place. Records hold no secrets by design (`owner.py:3-5`, `:2790-2791`) but they hold disk serials and firmware entries: never into the repository, a pull request or the board.
3. **The title off the laptop.** The failed-update card works from the last title he saved (`docs/INSTALL.md:289`, `:297`; `docs/EMERGENCY.md:18`). If Claude runs the commands and the title stays on the laptop, he has none when the laptop does not start. **Recommended:** after every command that changes what starts next, Claude puts the title's lines where he reads them on his phone (a title names systems and boot-menu rows, no disk serials). A guide rule, no tool change; where exactly is his choice (section 7).
4. **An off-device copy.** The stick stays the way. To keep it working after stick-free updates, `export` should also accept a stick whose bundle this laptop installed before (the verified copies in `retired-tools`, `owner.py:2618-2630`). This loosens a check on the emergency route: open question 4.

## 4. The first install of v4, over v3 or v2

The block ends in `bash ./at install` from the private copy (`bootstrap.py:56`), so **v4's own code decides** and the installed tools are not run. v4 reads the old bundle's history as data (`owner.py:163-164`) and checks today's state:

- the installation is complete, its files are the known ones and the disks are the recorded ones (`owner.py:2505-2516`);
- v4 is newer than what is installed and its release history extends the installed one (`:2559-2561`). v3 → v4 and v2 → v4 both pass: if the stick session for v3 has not happened by then, v4 goes straight over v2;
- no installed owner command is running (`:2537-2541`);
- no unfinished layout trial, no deployment transaction or client running, and a deployment list v4's rules qualify (`:2521-2535`).

**The one check in the installed tools that could refuse** is their recovery code. Until publication the old toolset stays the current one, and after a cut its `settle_tools` reads the journal v4 wrote. v3 accepts schema `tools-update1` with `phase`, `previous`, `manifest` and `previous_directory` (`owner.py:2428-2433`); v2 has the same check (`41b06513:os/owner-tools/owner.py:2075-2079`). Neither reads `tools_volume_uuid`. So v4 keeps the schema name and those fields and adds `source` beside them; a renamed schema would make every command of the old tools refuse after a cut. A test runs v2's and v3's `settle_tools`, loaded from their commits, over v4's journal at every cut before publication.

**Where the routine route exists.** `ares` has sudo only on a release whose record says he is an administrator: R27 yes, R13 no (`os/owner-tools/history.json:7`, `:12`); plain Bazzite has only `ares-recovery` (`docs/INSTALL.md:147`). As a by-product the folder block also works at tty3 as `ares-recovery` on any system, typed by hand: a console route when the stick is lost. The guide need not offer it.

## 5. The emergency route

**What stays on the stick and the console:** the first installation (`owner.py:2658-2663`); a tools update when the desktop or Claude is unavailable, or when he wants a route that does not pass through Claude; the layout commands (`owner.py:1999-2031`); `login`, whose hidden prompt takes his registry token (`owner.py:1660`), typed by him and never through Claude; `export` to the stick.

**How the two routes coexist**

1. **The stick route's rules do not change.** v4 runs today's lines when the stick block ran, and that block stays as generated (`bootstrap.py:24-27`) apart from v4's fingerprint. Its terminal test is not strengthened either: that would change a rehearsed route.
2. **Neither route reads what the other trusts.** The stick block never reads the folder `/var/home/ares/ares-tools` (`bootstrap.py:18`).
3. **One journal, one set of records and one version rule** for both, with the source recorded.
4. **The stick may fall behind.** After a stick-free update it carries an older bundle. Installing from it is refused as a downgrade with nothing changed (`owner.py:2559-2560`), which is right; `export` to it needs section 3, point 4. A current stick matters only when new tools are needed while the desktop is down, so refreshing it about once per release is enough.
5. **Refreshing the stick without Windows is not in the repository.** The guide's way is the Windows box (`docs/INSTALL.md:228-236`); the lead's Linux script lives in the home folder (`HANDOFF.md:34`) and needs a small package of its own. Not 22d.
6. **The guide** puts the routine route first and the stick second (`briefs/22c-stage-1b-additions.md:25`). `docs/EMERGENCY.md` keeps its steps.

## 6. The VM rehearsal

**Reused from 22c's harness:** package 27's route up to R27 with v2 (`os/ci/owner_vm.py:1527`, `:1591`); setting his password and proving sudo keeps no ticket (`:873-908`); typing into foot in his desktop session as `ares` (`:1400-1430`); screenshots (`:112`); reading the tools' records through the root serial shell (`:377`); older bundles built from their commits (`:1336`); the stick (`os/ci/owner_media.py:113`, `:183`, `:212`); the cut watcher (`owner_vm.py:2092`).

**New:** a mode (say `tools-local`) with its ledger entry (22c's is at `os/ci/rehearsal-packages.json:120-149`), the workflow option and the mode lists 22c names (`reviews/22c-ways-back-after-update/REPORT.md:2982-2986`); a driver for the dialog (wait for the helper's process, screenshot, type, Enter or Escape); 22d's own host-walk receipt and record step, because 22c's receipt stays frozen (`reviews/22c-ways-back-after-update/REVIEW-8.md:24`; `STATE.md:30`).

**The walk,** after package 27's route:

| Stage | What happens | Proves |
|---|---|---|
| Stick, v2 → v3 | As 22c's E1 (`owner_vm.py:2130-2150`). Skipped if the laptop still has v2 when 22d is ready, so the VM walks what the laptop will | One stick install stays in the walk |
| v3 refuses | From his desktop session with no terminal: the folder block with v3's own bundle. The console STOP; the installed tools untouched | The gate is in the bundle being installed |
| Cancel | tty3 logged out. In foot as `ares`: the guide's lines, then the generated line with stdin from `/dev/null` and no controlling terminal. Screenshot of the dialog (the label, no "remember" option), then Escape | Refusing changes nothing |
| Cut | The line again, the password typed into the dialog, a hard reset between copy and publication. After the restart the old tools' `check` passes | The old tools' recovery reads v4's journal on a real system |
| Install | The line once more: it resumes. `PASS install`, **Tools updated from version**; the receipt names the folder, uid 1001 and no terminal; `sudo -n true` is refused; then `check` and `title`, each with its dialog | The stick-free install: no console, no ticket left behind |
| Tamper | One byte changed in the folder: STOP before any bundle code | The local suite covers every tamper case for both sources (`os/tests/test_owner_bootstrap.py`) |
| Stick with v4 | v4 on the stick, tty3, the stick block: **Tools already installed; nothing changed** (`owner.py:2556-2557`); `export` passes | v4's stick rules still pass, without a second bundle |
| End | Restart, `check`, `title`; every protected-disk audit unchanged | |

**What the VM cannot show:** Claude Code itself (the stand-in is a shell in his session without a terminal) and where the window appears over the hub. The first real proof is the laptop session. The walk should be shorter than 22c's, which used 216 minutes (`HANDOFF.md:33`).

## 7. Size, steps, and what goes to the owner

**Size:** about a third of 22c. The tools change is small (the route decision, the journal's source, the resume rule, `export`: perhaps 150 lines in `owner.py` and `media.py`). Most of the work is tests (the refusal table's rows for both sources, the old recovery code over the new journal), the guides (one new box first in the update route, the fingerprint's pins, the status row), the harness mode and one rehearsal. The model test reruns in full, as for any change under `os/owner-tools`, but does not change unless finding 2 rides along.

**Steps,** one fresh agent each:

0. With his OK, one harmless try on the laptop: `sudo -k -A true`. He sees the window, where it appears over the hub and what it says. It answers open questions 2 and 6 before anything is built.
1. A fresh review of this note (Fable: it decides what the laptop trusts).
2. The tools and their tests, against a tight brief (Codex while it lasts, else Opus).
3. The bundle, the pins, `commands.json` and the guides.
4. A fresh review of steps 2 and 3 (Fable).
5. The harness mode, the local walk, hosted checks with the full model, the VM run.
6. The record step, the final review before the laptop (Fable), the merge, the laptop session.

**To the owner.** Told, no answer needed: how it will look (Claude says what it installs; a window named "AresOS owner tools" appears; he types his password; Cancel changes nothing), that he must be at the laptop, and his rule from section 1. Asked:

- **A. How many password windows.** One per command: three for new tools (install, check, title), about seven for a full update with its restart. Or one for a whole box. *Recommended: one per command for now.* Each window names one command, each line is the reviewed command behind one fixed prefix, and `aresos update` brings it down to one or two in step 2. If three in a row annoy him, grouping is a small change.
- **B. The stick.** It stays in the drawer as the emergency route. *Recommended: Claude asks for it about once per release to refresh it.* Otherwise never, and in an emergency it can take records but not bring new tools.
- **C. The boot-menu map on his phone.** After each change Claude sends the three lines he needs if the laptop does not start. *Recommended: a note that reaches his phone through the board.* Otherwise a photo he takes himself.
- **D. v3 by stick now, or wait** for 22d and never plug the stick in for these tools. The integrator can settle this by timing.

## What carries over to step 2

- **Carries over:** the source in `update_tools` (step 2's tools inside the image are a third source, a root-owned signed folder, on the same code path and journal field); the approval rule (his password, fresh each time, for one fixed command, which becomes the root-owned `/usr/bin/aresos`); the readable export and the title on his phone; the harness's no-terminal caller and dialog driver; the guide's shape, routine route first.
- **Deliberately not built:** a bundle signature, a key, a sudoers or polkit rule, a helper program, a service, an online check in the block.
- **Thrown away in step 2, and small:** the folder in his home with the `git archive` lines, the `install-folder` box and the on-main check. The signature and the signed release list replace them.

## Follow-ups from review 8, candidates for v4

Named, not designed (`reviews/22c-ways-back-after-update/REVIEW-8.md`; `REPORT.md:3781-3804`):

- **Finding 2:** a cleanly stopped `update` leaves its record open, so the other commands refuse in the same start. It matters from the first tools whose `update` can really stage: the next release's.
- **Finding 5:** the layout-trial refusal should name `layout abandon` after a restart. A wording change.
- **Finding 8:** one name for the same system across an update. It changes title lines that the guides quote and the harness holds exactly (`os/ci/owner_vm.py:1930`), so it costs more than the other two.
- **Finding 3** (a test that keeps tool and guide files off the waiting list) fits 22d's record step.

If they ride with 22d, build them as their own step after the trust change is reviewed, so that review stays about one thing.

## Open questions

**For the owner:** A to D in section 7.

**For a reviewer or a council**

1. **Review or council?** This note claims that 22d trusts nothing new: his password already means root on R27, and the fingerprint stays the identity. If the reviewer agrees, a fresh Fable review is enough and the council is step 2's. If not, a council before any build.
2. **The askpass helper.** Confirm from ksshaskpass's source at the image's version, and in the VM, that the fixed label can never be remembered or answered from the keyring. If it can, use `/usr/libexec/openssh/gnome-ssh-askpass` (on R27 **live**; its package is in `os/manifest/ci/packages.txt:1787`) or ship a helper of our own with the next image. Should the next image set `SUDO_ASKPASS` itself and test it?
3. **The gap that stays.** Nothing here stops an agent that shows one thing and runs another. Is that acceptable for step 1, as the same line as every other administrator action on R27? Step 2's council should decide whether updates need an approval outside the laptop: a protected main, a signed list, a tap on his phone.
4. **`export` accepting an older bundle on the stick** (section 3, point 4). The bundles are public, so that check never authenticated a stick; it catches a wrong stick, and still would.
5. **Which review-8 follow-ups ride with 22d.**

**Only the laptop can answer**

6. **Where the window appears over the hub** and whether it takes the keyboard (step 0). A Claude session without his desktop's display, started from a console or remotely, cannot open the window; sudo then fails and nothing changes.
