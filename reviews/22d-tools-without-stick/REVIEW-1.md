Reviewed the 22d design note at `1afd1f6f` (PR #66).

Reviewer: a fresh Claude agent on Fable 5.2, read-only. No owner tool, sudo, ostree, bootc or rpm-ostree ran, and the askpass helper was not started. I read the code and the running image's files, extracted both bundles with `git archive` into a scratch folder, made read-only GitHub API reads, and read ksshaskpass's source at tag v6.7.5 from KDE's GitHub mirror.

**In short:** nothing is blocking. The note's facts hold, and so does its main claim: 22d moves no trust line, because on R27 his password already means root. The findings that matter most before the brief:
- The owner text leaves out the limit of the password window (F1).
- His rule contradicts three windows in a row (F2).
- The emergency route after 22d is never walked with v4's own code (F13).
- Owner question D is already answered on main (F5).

## 1. Are the facts true?

| Claim | Verdict |
|---|---|
| `timestamp_timeout=0` for `ares` | True in the repository. Set in `os/config/etc/sudoers.d/aresos-everyday:5`; tested in `os/ci/image-checks.sh:31`, `:44`, `:48-80` and in the VM (`os/ci/owner_vm.py:904-905`, `:1441-1443`). Not confirmed on the running laptop: `/etc/sudoers.d` is closed to `ares`. |
| `SUDO_ASKPASS` is ksshaskpass | True (live, in my own shell). `/etc/profile.d/askpass.sh` sets it only when `image-info.json` says `kinoite` (it does). Nothing in `os/config` or the image checks pins it. |
| The helper can remember | True, and open question 2 is now answered from source. Keyring read, the "keep" box and keyring write happen only when the prompt matches one of 16 patterns that yield an identifier. The proposed label matches none. Two patterns are not anchored at the start (`Enter PIN for '(.*)': $`, `Verification code: $`). I read the source through a summarising fetch; it agrees with the binary's strings. |
| Order of the terminal and stick checks | True: `owner.py:2503` then `:2504`; first install `:2658`, the serial prompts, then `:2663`. Claude's shell has stdin `/dev/null` and no controlling terminal (live). |
| `tools-update1` compatibility | True. v3 `owner.py:2428-2433` and v2 `41b06513:os/owner-tools/owner.py:2075-2079` are the same check. The volume UUID is read only inside `update_tools` and `install`. |
| `export` refuses an out-of-date stick | True: `media.py:74`, `:102`, `:108`; without a stick `:66-68`. |
| main has no branch protection | True, and more: no rulesets, and the laptop's token has admin rights on the repository with scopes `repo` and `workflow`. |
| Fingerprints | True: `44ddfd16` gives `2084c786…`, `41b06513` gives `851eb742…`, every file checks. |

Small corrections (all nit):
- **Note:37.** sudo can also read the password from stdin (`-S`). That is how a program that has the password gets in without any window.
- **Note:86.** "Reviewed, tested" is a habit, not enforced: State and Handoff commits go straight to main. Say "public and logged".
- **Note:119.** `login` needs a terminal, not the console (`owner.py:1660`).
- **Note:36.** The running PAM stack lists `pam_fprintd` as sufficient before the password. This laptop has no reader, so "only his password" holds here, but nothing pins it.

## 2. The threat model

| Against | Protected? |
|---|---|
| Mistakes: dirty tree, stale checkout, unmerged branch, damaged copy, older tools | Yes: `git archive`, the on-main check, the pinned fingerprint, the version rule. |
| A program of his using root unasked | Yes: no ticket, a password every time. |
| An honest but confused agent | Partly. The label does not help by itself, because the same agent writes it. A generated line and the phone compare do. |
| A hijacked agent, or any hostile program running as him | No. It can open a look-alike window or watch the real one (`ptrace_scope` is 0). |
| A compromised GitHub account or laptop token | No for the anchor itself. Partly, if the laptop installs only the commit the integrator announced. |

So the window is a meaningful approval of "an administrator action happens now", and theatre as proof of which one. The note says this honestly.

**No cheap design makes the window unforgeable.** I checked the three candidates:
- **A root-owned wrapper in the installed tools** runs only after the password, cannot serve v4's own install, and prints into Claude's pipe or a window any program of his can cover.
- **A polkit action** gives the honest path root-owned words, but its window is still a program in his session, and it needs an image change.
- **An independent fetch as root** catches the same mistakes as the on-main check, and a hostile agent simply runs something else.

The one place on this laptop where a program of his can neither draw nor type is tty3 under `ares-recovery`, which is the emergency route. Option A is right for step 1.

**F1, should-fix (note:40, :55, :165).** "Root for that command" undersells the risk. A password typed into a hostile window is captured. After that the program is root whenever it likes, with no window, and `timestamp_timeout=0` no longer matters. The owner text must say this in plain words: the window stops accidents, not a tricked Claude. He should be able to say no to that.

**F2, should-fix (note:65 against :167).** His rule is "type only right after telling Claude to go". Three windows in a row break it on the first day and train the habit the rule forbids. Use one window per "go": one generated line for the tools-only box (install, check, title). Otherwise the rule must say how many windows to expect and with which labels. I advise one per go.

**F3, should-fix (note:79, :85).** The eight characters mean something only when he compares them with a source the agent did not just write. Make the compare part of his rule for new tools, not optional.
- Give him one short line at a fixed address on main, held by the fingerprint test.
- The status table row is too long to read on a phone, and a pull request title is not pinned.
- A test must also hold the label's eight characters equal to the block's literal.

**F4, should-fix (note:76).** Define "the announced commit": the integrator's board note carries the full commit hash and the fingerprint, and the laptop session installs only that. Otherwise a confused agent installs main's head.

Nit (note:62): name `/usr/bin/sudo` in the generated line. `~/.local/bin` is first on his PATH.

## 3. The bundle identity

It is sound against mistakes and not an anchor against the laptop's agent, as the note says.
- **A protected branch or ruleset** can be removed with the laptop's token, so it is a tripwire with a log entry. Optional and free: a ruleset that blocks force pushes and deletion of main, so the log stays complete (nit, integrator's call).
- **A required review** needs a second account, since an author cannot approve their own pull request.
- **A key he holds** signs as blindly as the password approves.
- **The real fix** is that the agent stops holding his own GitHub identity with admin rights. That is step 2's council.

**F6, should-fix (note:174-176).** Tell step 2's council that the workflow signature is reachable with the same token. The token can push workflows, and the identities in `history.json` are branch refs.

**F7, should-fix (note:83).** The lines Claude runs as `ares` (fetch, on-main check, `git archive`) exist only as prose in 22c's report.
- Generate, pin and test them like the block, including the refusal for a commit that is not on `origin/main`.
- Chain them so a failed fetch stops.
- Take the block from the commit, not from the working tree.

## 4. The first install over v2

Yes, v4's install should run. The VM route already has the laptop's shape: 15f, then v2 as an update with a completed journal. The installed v2 is read as data only (`owner.py:2553`, `:2558`). The one v2 code path that can run is recovery after a cut, and it accepts v4's journal as the note says.

**F8, should-fix, for the brief.**
- Before publication, v4 writes nothing new under `/var/lib/ares` except the journal's extra key.
- The readable export copy lives outside `/var/lib/ares`: older tools require `records` and `diagnostics` to be root-only (`private_tree`).
- Local tests cover both v2 to v4 and v3 to v4.

**F5, should-fix (note:109, :140, :170).** Main moved after the note (`ba4591cc`, board #265): v3 never goes on the laptop. Drop question D and make v2 to v4 the only walked case.

Nit (note:93): on the folder route the first installation refuses "before any prompt" only without a terminal. Refuse by route. Also say what `at install` through the installed entry does in v4.

## 5. The emergency route

Nothing weakens it in substance. An interrupted tools install always leaves working tools.

**F9, should-fix (note:100).** `export` without a stick changes meaning on the emergency route too.
- The message must say the copy is on this laptop, not off it.
- "SAFE TO REMOVE ARESTOOLS" stays the only proof of an off-laptop copy.
- A folder under `/run` avoids leftovers.

**F10 (note:102, open question 4).** Yes, accept a stick that holds a bundle from `retired-tools`. Without it a stale stick, the normal state after 22d, cannot take records in an emergency.

**F11, should-fix (note:127, :168).** Question B promises a stick refresh that has no reviewed route on Linux. Name the small package, or say the refresh uses the Windows box until then.

**F12, should-fix (note:128).** A STOP on the routine route has no card. Add what Claude does: report the line, run `export`, never retry something else.

## 6. Size and order

A third of 22c is plausible. The dialog driver and the receipt work are the unknowns.

**F13, should-fix (note:16, :140, :146).** The promise "one stick install stays in the walk" is not kept.
- v4's stick route is only walked as "already installed".
- The dropped v2 to v3 stage ran v3's code anyway.
- Fix: install a harness-built next-version bundle from the stick at tty3, or state that local tests carry it and why.

**F14, should-fix (note:157).** Step 0 gates the brief.
- Use the real generated prefix and label.
- Record the window's text, focus over the hub, Cancel, a wrong password and the journal line.
- Say what happens if the window cannot take the keyboard, since 22d cannot change the image.

**F15, should-fix (note:64, :182).** The caller can end.
- An unanswered window stays open; I believe sudo's password timeout does not cover a helper, but I did not verify that.
- Claude's foreground commands are limited to ten minutes, while an `update` step may take thirty (`owner.py:70`).
- Say how long Claude waits and how it closes the window, and rehearse it.
- A stopped `update` is exactly review 8's finding 2, so finding 2 must be in the tools that carry the next release.

**F16, should-fix (note:155-163, :187).** Any follow-up changes the fingerprint, so its step and review come before the VM run.

**F17, should-fix (note:62).** `test_owner_equality.py:49` finds blocks that start with `sudo bash -c `. A block with the new prefix would go unpinned without any failure.

**F18, should-fix (note:63, :196).**
- With the next image, check every generated label against the patterns in the image's own helper, and that the helper exists.
- In the VM, assert the helper's argument equals the label and that no keyring process starts.

Nits:
- Other sessions on the laptop must be quiet during the install (`owner.py:553`).
- The stand-in must assert it has no controlling terminal.
- The routine route exists only on R27 and later.

## 7. Who decides

- **Owner:** step 0's OK; windows per go (F2); the phone compare as his habit (F3); the limit in plain words (F1); B once F11 is settled; C. D is closed.
- **Integrator:** open questions 2, 4 and 5. For 5: finding 5 rides, finding 2 as in F15, finding 8 waits, finding 3 goes with the record step. Also every other finding here.
- **Council:** none for 22d (open question 1: a review is enough). Step 2's council takes open question 3 and F6.

READY
