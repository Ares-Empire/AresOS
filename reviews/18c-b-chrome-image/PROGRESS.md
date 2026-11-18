# 18c-b progress

Brief: `briefs/18c-b-chrome-image.md` (on `main` since PR #73).
Branch `pkg/18c-b-chrome`, one builder at a time. Each step is a fresh agent; this file is the handoff.

## Step 3b: the lead's runs on 5a027074 (2026-11-19)

The lead dispatched and watched these from the shell (the builder pushes and stops):
- checks_only 44397757752: **success**; "Ran 1805 tests", "OK (skipped=4)" (log 3595/3597); CONTROL_GH_PAYLOAD_PASS 240 paths, CONTROL_GH_RPM_PASS, CONTROL_GH_INSTALL_PASS (2371-2379); CONTROL_CHROME_CHECKOUT_PASS and CONTROL_CHROME_BUILD_LOG_PASS (2108-2109, 2380).
- check_build=build 44409288317: **success**. CONTROL_GH_PAYLOAD_PASS 240 paths (1561), CONTROL_GH_RPM_PASS (1562), CONTROL_GH_INSTALL_PASS (1563), CONTROL_GH_KEYRING_PASS (1564), CONTROL_GH_IMAGE_PASS 2.103.3 (2336), CONTROL_CHROME_BUNDLE_PASS (2928), CONTROL_CHROME_KEY_SCAN_PASS (2929), CONTROL_GH_CHECKOUT_PASS (3586), CONTROL_CHROME_CHECKOUT_PASS (3587), CHECK_BUILD_PASSED (3590), CONTROL_CHROME_BUILD_LOG_PASS (3591), CHECK_BUILD_VM_PASSED (4284).
- The old name check's diagnostic (2335): `INFO gh legacy name matches=["/usr/share/bash-completion/completions/_gh", "/usr/share/fish/completions/gh.fish"]`. Both are base-image files, not paths of the pinned gh RPM's payload, so the payload-bound check is right to pass them.
- check_build=resolve 44344811923 (on 6b80a139): "INFO gh newest=v2.105.0 pinned=gh-2.103.3" (1397).

**3b is green.** Next: `linux-aresos` reads 3b's `os/` diff; then step 4 (the VM's first half), on a Claude Opus agent (Codex is kept for reviews until about 2026-11-25).

## Step 3b (2026-11-18, gpt-6-astra)

### Done

- `61644462`: pins GitHub CLI **2.103.3**, its one exported 2026 public key and the tag's licence.
  No patch upgrade: GitHub CLI's published advisories inspected on this date did not require a newer
  2.103 patch. The RPM is `gh-2.103.3-1.x86_64` from
  `https://github.com/cli/cli/releases/download/v2.103.3/gh_2.103.3_linux_amd64.rpm`.
- `b3e0c0e5`: packages verifies HTTPS-only download/redirects, RPM hash and NEVRA, no scripts or triggers
  (file triggers included), one committed primary key, and the pinned header signature with every result
  line OK. It deletes all newly imported keys even when signature checking raises, then requires the key
  list equal to its previous value. Chrome's cleanup also removes every added key; a second comparison
  spans the first Chrome import through the last gh deletion.
- Only `./usr/bin/gh` is read from `rpm2cpio` by `cpio --extract --to-stdout`; both processes must succeed.
  The binary hash is checked before copying and afterwards, mode 0755, root:root. The licence is committed
  once and installed by the existing config copy. No gh RPM install, git dependency, repository, completion
  or man page. The lock goes to `usr/share/aresos/manifest/gh.lock.json`, 0644 root:root.
- The existing Control map records `gh: {version, binary_sha256}`; the actual build checks the installed
  binary against that record. The image check runs `--version` as root and the daily account, requires
  at least 2.102.0 and exact lock version, checks the binary/licence hashes and all three files' modes,
  owners and parents, absence of a gh RPM, repository, trusted key and every other path in gh's own RPM.
  The runner requires the reviewed lock byte for byte and `control.json.gh` equal to the checkout's.
- Resolve prints `INFO gh newest=... pinned=...` to the console and `resolve/gh.txt`. Network errors,
  nonzero curl, timeouts and malformed responses produce `unavailable (lookup failed)` without failing.
- `git fetch origin` completed. Main changed no file this step changes, so no merge. The starting head was
  `f96ca4aa`. `pending-rebind.json` was regenerated only by
  `python3 -B reviews/27-first-update-release/rebind.py pending "18c-b step 3b: pin and verify GitHub CLI 2.103.3, extract only gh, restore RPM trust, bind lock and binary to image checks, add informational resolve and failure fixtures."`:
  `pending: 10 bound files differ from the active bindings, 0 removed`.
  No workflow, runtime Control code, release pin or laptop deployment changed.

`6b80a139`: the first hosted checks-only run exposed an older-lock fixture in
`test_aresos_desktop` that supplies only the existing locks. Removed the redundant gh entry from that
JSON comparison, keeping the already present, stronger byte-for-byte `cmp` outside it. The existing
fixture and its assertions are unchanged. The gh test now executes that exact shell comparison against
equal, changed-but-JSON-equivalent, and missing locks; only the equal one passes. The 43-test touched
module passes again (5.894s); pending bindings were regenerated with the follow-up note. The second
checks-only dispatch was the final round authorized at that point. No infrastructure rerun was used. The
lead later authorized this one check fix and assigned the next checks-only/build dispatches to its shell.

### The lock and key provenance

`os/gh.lock.json` preserves Chrome's field names/order, then adds `binary_sha256`, `license_sha256`
and (in the check follow-up) `payload_paths`. The signing-key object extends the same first four fields with `source_sha256` and the provenance record.

| Input | SHA-256 |
|---|---|
| RPM | `65d55875faa3281959676d91da15a9380583281586ac31bbd3d32b7924a9f4d2` |
| Extracted binary | `b768184570b12536be4ac1528893f6340d1c6a7b40b56ad45bca9cd0e87ad34d` |
| Published ASCII keyring | `cec6e9ed82d3949ca5f4428cc968b41ef5e7416cb3653cdfc2a421977663bbfd` |
| Committed exported key | `5cf71eb7df215f2dd79b8eb7cfbb069bd62458d8be8d64c141c02945838e754f` |
| Tag's LICENSE | `6da4adc42392c8485e40b4251c7e332fc3352df1947c9ffade71dd60b14a7a4f` |

Fetched `https://cli.github.com/packages/githubcli-archive-keyring.asc` over HTTPS with HTTPS-only redirects.
Its checksum and both primary fingerprints match GitHub CLI's own
[installation documentation](https://github.com/cli/cli/blob/trunk/docs/install_linux.md):
`2C6106201985B60E6C7AC87323F3D4EA75716059` (expired 2026-09-05) and
`7F38BBB59D064DBCB3D84D725612B36462313325`. Imported the bundle with `gpg --no-options --batch
--no-autostart --no-auto-key-retrieve --auto-key-locate clear` into the temporary home
`.work/18c-b-3b/gnupg`, then used `--armor --export 7F38BBB59D064DBCB3D84D725612B36462313325`.
These import/export operations use the downloaded file only, without network or a keyserver.
Only the exported key is committed. `gpg --import-options show-only --with-colons` counts primary keys
in the actual committed file; its test refuses a second primary key or another fingerprint.

The licence was fetched once from `https://raw.githubusercontent.com/cli/cli/v2.103.3/LICENSE`.
The pinned RPM matched the brief's hash, and the signature check printed:

```text
Header OpenPGP V4 RSA/SHA512 signature, key fingerprint: 7f38bbb59d064dbcb3d84d725612b36462313325: OK
Header SHA256 digest: OK
Payload SHA256 digest: OK
```

`rpm -qp --scripts --triggers --filetriggers` printed nothing; NEVRA was `gh-2.103.3-1.x86_64`.
`file` reports the extracted binary is a statically linked x86-64 ELF. The actual `verify_rpm` code also ran
with every rpm/rpmkeys command scoped to a fresh `.work/18c-b-3b/verification-rpmdb` and `_keyring rpmdb`:
`CONTROL_GH_RPM_PASS ...` then `REAL_GH_RPM_AND_KEY_CLEANUP_PASS isolated scratch RPM database`.
The key list started and ended empty. The laptop's RPM database/keyring was never changed.

### Local tests and named scratch mutations (initial implementation)

`TMPDIR` for local tests and scratch scripts was `.work/18c-b-3b/tmp`.
`python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'`: **43 tests, OK**, 5.704s,
no skips. This includes the 32 existing image tests and 11 gh cases. No owner test module or full local
OS suite was run. `for script in os/build.sh os/ci/check-image.sh os/ci/image-checks.sh os/ci/check-resolve.sh; do bash -n "$script" || exit; done`
and `git diff --check`: exit 0. No Gradle process was started locally.

`python3 -B .work/18c-b-3b/mutations.py` executed the following against the actual packages-step
functions extracted from `build.sh`, in disposable scratch fixtures. RPM query/import/delete commands
are stand-ins in these adversarial cases; the two-key case invokes real GnuPG over the changed file.

| Mutation | Actual result |
|---|---|
| `wrong-binary-hash`: change the fixture lock's binary hash to 64 zeros | `MUTATION_KILLED wrong-binary-hash: gh binary differs from its pin`; no image binary written |
| `second-key-in-committed-file`: append a different committed public key to a scratch copy | `MUTATION_KILLED second-key-in-committed-file: gh key file must hold exactly the pinned primary key` |
| `leftover-imported-key`: deletion returns success but leaves its key | `MUTATION_KILLED leftover-imported-key: gh import left a changed RPM keyring` |
| `rpm-with-script`: RPM query reports a postinstall shell script | `MUTATION_KILLED rpm-with-script: gh RPM carries scripts or triggers`; import not reached |

Additional regressions refuse wrong RPM/key/licence hashes, NEVRA, a bad signature/digest line, another
signer, missing header signature and nonzero verifier exit; cleanup removes multiple additions and also
runs after verification failure. Fixtures assert the one cpio member, file modes, root ownership request,
key cleanup before extraction, and scratch removal. Checkout comparison rejects a changed `gh` record;
resolve handles success, lookup failure and malformed replies in one informational line.

### Check fix follow-up (2026-11-18)

Commit `689d8a48`, **Bind gh image exclusions to the pinned RPM payload**, completes the requested check
fix. No extraction, signature policy, version, installed payload or workflow changed.

- `os/gh.lock.json` now records `payload_paths`, the **240** filenames returned by
  `rpm -qp --nosignature --qf '[%{FILENAMES}\n]' .work/18c-b-3b/downloads/gh_2.103.3_linux_amd64.rpm`.
  The cached RPM's SHA-256 was checked first and equals the existing pin. Nothing was downloaded again.
- `os/build.sh` re-queries that list from the downloaded RPM after its existing hash, signature, script
  and key-cleanup checks. Exact list equality is required before extraction; success prints
  `CONTROL_GH_PAYLOAD_PASS 240 paths`. The existing lock copy carries that same list into the image and
  `check-image.sh` already compares the complete lock byte for byte against the checkout.
- `os/ci/image-checks.sh` checks all **239** other pinned paths, allowing only `/usr/bin/gh` from the
  RPM. Existing files, directories and symlinks (including dangling links) fail with
  `Unexpected gh RPM payload paths: <all offending paths>`. Unrelated base files do not fail it.
- Five added tests in `os/tests/test_control_image.py` exercise the actual checker code and the packages
  verifier: RPM/list disagreement, binary-only success, man-page and all three completion paths rejected
  individually and together with their names, a dangling payload link rejected, and an unrelated
  `gh-base-tool` completion accepted. The existing 43 tests remain.

**Verified locally in this follow-up:**

- `TMPDIR="$PWD/.work/18c-b-3b-check-fix/tmp" python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'`:
  `Ran 48 tests in 6.448s`, `OK`, no skips. Only this touched OS test module was run; no owner module.
- `for script in os/build.sh os/ci/check-image.sh os/ci/image-checks.sh os/ci/check-resolve.sh; do bash -n "$script" || exit; done`:
  exit 0, no output. `git diff --check`: exit 0, no output.
- `python3 -B reviews/27-first-update-release/rebind.py pending "18c-b step 3b check fix: record gh RPM payload paths in its lock, verify them against the pinned RPM, and reject only those paths in the image while printing legacy name matches."`:
  `pending: 10 bound files differ from the active bindings, 0 removed`. The pending file was generated,
  never edited by hand.
- The exact Repo privacy workflow shell, extracted to `.work/18c-b-3b-check-fix/privacy-check.sh`, ran with
  `RUNNER_TEMP` under the same scratch folder: exit 0, `No file holds a home path with a real user name.`
- `TMPDIR="$PWD/.work/18c-b-3b-check-fix/tmp" python3 -B .work/18c-b-3b-check-fix/mutation.py`:
  put the original name-based assertion back in a scratch copy of `image-checks.sh`, then ran the new
  unrelated-base-file test against that copy. It printed
  `MUTATION_KILLED name-based-check: Ran 1 test; FAILED (failures=1)` and
  `AssertionError: gh documentation or completions were installed`. The fixture path is
  `/usr/share/bash-completion/completions/gh-base-tool`, absent from the pinned payload. The working
  checker was never replaced by the mutant.

**Old pattern diagnostic:** the old name search runs as a diagnostic before the new assertion. In the
new base-file test it lists the synthetic `gh-base-tool` path above and the new check passes. That is a
fixture, not an observation of the real base image. The supplied failing build log names no matched
paths; no real base-image match is claimed here. The lead's next `check_build=build` on the pushed head
will print `INFO gh legacy name matches=<sorted JSON array of full paths>` for every match under the
same four man/completion folders. This supplies the missing base-image path evidence without failing
on unrelated names. Any actual gh payload path still fails and is named separately.

**Not verified here:** the corrected checker in a built image. No workflow was dispatched or watched in
this follow-up, and no laptop RPM keyring was changed. The lead's shell owns the next two runs.
No new owner-facing JUDGMENT-CALL; the PLAN-GAP was the old assertion's assumption that a matching name
belongs to gh. Open questions: none for this fix.

### Runs

The original builder ran checks-only, build, then resolve, one at a time. The completed results for
`44329677029`, `44339552024` and `44344811923` below are from the lead's shell, supplied with this
follow-up; they were not re-watched here. Other rows retain the draft's historical evidence. Full-log
line numbers are used below; unit-test fixture PASS markers are not image proof.

| Run | Mode/workflow | Result / full log lines |
|---|---|---|
| 44323572283 | checks-only round 1, `b3e0c0e5` | FAIL; one failure in 1800 tests (3819–3821), four existing GUI skips. The older-lock fixture has no gh lock: failure/trace 3802–3815. This is our integration failure, not infrastructure. |
| 44329677029 | checks-only round 2, `6b80a139` | PASS (lead's shell). |
| 44339552024 | `check_build=build`, `6b80a139` | FAIL; `CONTROL_GH_RPM_PASS`, `CONTROL_GH_INSTALL_PASS`, `CONTROL_GH_KEYRING_PASS` at 1561–1563, then root and daily-account `gh --version` lines; `AssertionError: gh documentation or completions were installed` in `image-checks.sh` 339–341. Fixed by `689d8a48`; no image-check PASS claimed for this run. |
| 44344811923 | `check_build=resolve`, `6b80a139` | PASS; `INFO gh newest=v2.105.0 pinned=gh-2.103.3` at 1397 (lead's shell). |
| 44323585982 | PR Control Chrome install | PASS; 28 tests 2229, node:crypto cross-check 2235; five cases PASS 2307–2311; `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2312 |
| 44323586219 | PR Chrome records | PASS; 21 tests 216; `record_build check passed` 227 |
| 44323586423 | PR Control boundary | PASS; `PRECEDENCE_OK cases=24` 2060; `CONTROL_INTERACTIVE_ASK_PASS cases=17` 2732 |
| 44323586285 | PR Control base | PASS; `Control base suite PASS` 715 |
| 44323586189 | PR Repo privacy | PASS |
| 44323586012 / 44323587243 / 44323586057 | Superseded PR qualification / Chrome / Mail | Qualification and Chrome cancelled after the fix push to unblock its checks; Mail cancelled automatically. No PASS claim. |

Fixed-head PR evidence (`6b80a139`):

| Run | Workflow | Result / full log lines |
|---|---|---|
| 44329692789 | Control Chrome install | PASS; 28 tests 2228, node:crypto 2234; cases 1–5 PASS 2306–2310; `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2311 |
| 44329693134 | Chrome records | PASS; 21 tests 199; `record_build check passed` 210 |
| 44329692739 | Control boundary | PASS; `PRECEDENCE_OK cases=24` 2059; `CONTROL_INTERACTIVE_ASK_PASS cases=17` 2731 |
| 44329692726 | Control base | PASS; `Control base suite PASS` 699 |
| 44329692951 | Repo privacy | PASS |
| 44329692733 / 44329692894 / 44329693644 | Chrome / qualification / Mail | Pending in the original draft; not rechecked in this follow-up, no PASS claim. |

The first push's five completed PR workflows passed. Its still-queued qualification and Chrome runs
received `gh run cancel` after the fix push; because the queued qualification run remained active,
`gh run cancel --force` was used for these two superseded runs. The qualification concurrency group
otherwise blocks the new head. Mail was cancelled by its own concurrency rule. Those workflow notes are
historical; no cancellation is counted as a passing check, and this follow-up watches no runs.

The build's three gh package markers and both version lines establish installation and execution before
its checker failure; they do not establish a passing image check. On the pushed follow-up head the lead's
**checks-only must pass**, then **one `check_build=build` must pass completely**, including
`CONTROL_GH_PAYLOAD_PASS 240 paths`, `CONTROL_GH_RPM_PASS`, `CONTROL_GH_INSTALL_PASS`,
`CONTROL_GH_KEYRING_PASS`, both exact-version lines, the legacy-match diagnostic,
`CONTROL_GH_IMAGE_PASS` and `CONTROL_GH_CHECKOUT_PASS`. The diagnostic's actual matched base paths belong
in that run's evidence. Resolve is already green; no new resolve run is requested by this fix.

### Left, in order

1. **Lead (`linux-tools`):** dispatch checks-only and then one `check_build=build` on this pushed head;
   the lead's shell watches both and records the markers and actual legacy-pattern matches above.
2. **4:** real-session polkit probe, then Chrome VM first half. Tell the lead before committing any
   `os-image.yml` change so linux-aresos hears first.
3. **4b:** C3, remaining C6, C10 and C11 if step 4 reaches its budget. C10 still must run gh as the service
   user under the real unit sandbox and establish no verifier login/token.
4. **5:** update/rollback, broken/missing bundles, store requests and password/cancel/ask-again flows.
   With 28b integrated, prove the in-session profile ask and durable pin continuity too.
5. **6:** rehearsal checks, final-head runs, guides and final report; distinguish installation from profile
   continuity. No release containing 28b before the combined proof.

### JUDGMENT-CALLs

No new owner-facing choice and no version upgrade. For implementation review: cpio streams the one member
instead of recreating RPM paths; script refusal includes ordinary, transaction and file triggers; key cleanup
checks the full key listing and deletes every addition, including Chrome's. Replacing this with a private
verification database in the image was rejected because the brief explicitly requires import/delete and
before/after proof in the image's keyring. None of these changes expands installed content or privileges.

### PLAN-GAPs

The first checks-only run exposed a fixture boundary: the existing lock-loop test builds only its three older manifests. The gh lock is checked separately, byte for byte, without changing that test. No supply-chain stop condition was encountered. The existing Step 3a storage/profile boundaries remain.
This step proves supply-chain installation and image execution; it does not establish C10's sandboxed service
execution or any later Chrome VM flow. Open questions: none for 3b.

### The os/ diff for linux-aresos

Net from `f96ca4aa`:

- `os/gh.lock.json`: new reviewed RPM/binary/licence/key pins, provenance and 240 RPM payload paths.
- `os/keys/github-cli-rpm.pub`: new, exactly the 2026 public key.
- `os/config/usr/share/licenses/gh/LICENSE`: new, exact tag licence.
- `os/build.sh`: verify/extract gh, restore full key list, record/check gh in the existing Control map.
- `os/ci/check-image.sh`: reviewed gh lock and checkout-record equality, `CONTROL_GH_CHECKOUT_PASS`.
- `os/ci/image-checks.sh`: installed gh version/hash/metadata and absence checks, `CONTROL_GH_IMAGE_PASS`.
- `os/ci/check-resolve.sh`: non-failing newest-versus-pin info and evidence line.
- `os/tests/test_control_image.py`: sixteen gh tests, gh record expectations and fixture lock.
- `os/README.md`: gh install and verification description.
- `os/manifest/ci/16/pending-rebind.json`: generated pending note; no table rebound.

`.github/workflows/os-image.yml` is unchanged. The closing `.work/` audit printed
`Files over 500 MB in .work/:` followed by `Total: 0`. No large download, extracted image or partial
file needed removal. Scratch for this follow-up is `.work/18c-b-3b-check-fix/`; the prior cached RPM is
reused. No Gradle process was started.

## Step 3a fix (2026-11-18, gpt-6-astra)

**The complete 3a image proof is green on `2e2516b1`.** The earlier two-build stop below stays
as history. This step permits one checks-only run, then two build rounds, with one whole-run rerun only for an
infrastructure failure. No workflow edit, storage exception or server-instruction text is part of this fix.

### Merge and facts before the fix

- `405f6fe3`: separate merge of `origin/main` at `7417c19a` (PR #106). Git reported
  `Automatic merge went well`; no conflict resolution was needed. Main's brief/design and mod development
  work remain alongside the branch's Chrome install work. For `pending-rebind.json`, main's complete file was
  selected, the four branch-only notes re-added through `rebind.py pending`, and a merge note added through
  the same tool. All 13 main notes and the rebound history were checked equal word for word. The regenerated
  record has ten changed bound files and no removed files. No workflow changed in this merge.
- The downloaded `check-build-evidence` artifact and full log of 44247363499 show only the unresolved path:
  log 2902–2914, artifact `image/checks.txt` 1203–1215. Neither records the link type or target. The lead's
  revised brief supplied the expected `root` → `var/roothome` layout; the new run below establishes it.
- `32f38e36`: temporary CI-only `lstat` diagnostic for `root`, `var`, and `var/roothome` in the non-recursive
  image view, before the unchanged failing scanner. It records link text without following `root`, checks that
  `var` is a directory, and prints the target's presence. The first authorized build round established the
  actual layout; the second is reserved for the corrected scan. No laptop container or system path is inspected.

- **Observed in the image, run 44286574648:** `root` is `lrwxrwxrwx`, with link text `var/roothome`
  (log 2867); `var` is a real `drwxr-xr-x` directory (2868); `var/roothome` is missing (2869).
  The unchanged checker then fails with `FileNotFoundError` (2871–2883). This is the known checker defect,
  not infrastructure; there is no blind rerun. This observation consumed the first of the two authorized
  build rounds. Nothing was inspected on the laptop's own system.

### Fix and verification

Fix commit `2e2516b1`: `os/ci/control/chrome_image.py` now resolves each selected name component by component using `lstat`.
Absolute link targets start at the scan root, and `..` stops there. Existing targets are traversed and their
regular files checked; a missing link target returns no content and produces a `CONTROL_CHROME_SCAN_LINK`
JSON row with the link, target, resolved image-relative path and `status: missing`. The function returns the
same rows as evidence, and `check-image.sh` retains the printed rows in `image/checks.txt`. The same traversal
handles `tmp`, `var/tmp`, `root`, nested links and linked parent directories. Only `FileNotFoundError` while
resolving a link target is treated as empty. Missing ordinary names (including a missing child after an
existing parent-link target), unreadable metadata/folders/files, non-directory parents and cycles fail.
The whole-image modulus walk now also calls `lstat` on every visited entry; it still does not follow links.
No read/list error is ignored. The temporary shell diagnostic is removed; `image-checks.sh` returns to its
pre-step bytes. No workflow, installed file, control code, storage policy or instruction text changes.

The added `ChromePrivateScanTest` cases cover all three scan names for an existing folder containing a PEM
marker and for a missing target with exact printed/returned evidence. Other cases cover absolute links with
opposite host/image contents, unreadable folders (an injected `PermissionError`, effective even when CI is
root), file-read and metadata errors, nested and parent links, `..` containment, missing ordinary children,
link/directory cycles and non-directory parents. The absolute-link fixture's two views are both artificial
scratch folders within this worktree.

| Command (scratch `TMPDIR` under `.work/18c-b-3a-fix/tmp`) | Actual result |
|---|---|
| `python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'` after the fix | 32 tests, `OK`; nine new regression cases, no skips |
| `python3 -B .work/18c-b-3a-fix/host-view-mutation.py` | `follow-image-links-in-host-view` replaces the image-relative scan with host `Path.resolve()` plus the regular-file walk. `test_absolute_link_uses_image_contents_never_the_host_view` fails with `AssertionError not raised`; one failure, no errors, followed by `MUTATION_KILLED follow-image-links-in-host-view: image PEM was missed`. The mutation is only in a disposable imported module, never the source file. |

Local pre-fix check:
`TMPDIR="$PWD/.work/18c-b-3a-fix/tmp" python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'`:
23 tests, `OK`. `bash -n os/ci/image-checks.sh` and `git diff --check`: exit 0.
`PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_extension_stores_nothing`: 3 tests, `OK`.
`python3 -B -m unittest discover -s control/chrome/ci/install -p 'test_*.py'`: 28 tests, `OK`.
Both use the same scratch `TMPDIR`. `python3 -B control/chrome/build.py` still prints
`c689b9c8f7d748c137dd5f64b0a317368a13f5b781ce0d17a21b199b03c4eaa9`.
The exact privacy workflow shell body, with scratch `RUNNER_TEMP`, prints
`No file holds a home path with a real user name.` and exits 0.

Before changing the scanner, the new regressions were also run against its existing loop in a disposable
module: the missing-target test produced `FileNotFoundError` for all three names, and the absolute-link test
failed with `AssertionError not raised` because the old loop read the clean host decoy and missed the image PEM.
Only artificial scratch trees were used.

The first push of the fix was blocked by the privacy hook's private-key rule on literal synthetic PEM headers
in the new tests. There was no key material. The fixture now constructs the identical header bytes from two
pieces, like the existing marker tests. The unpushed fix commit was amended after rerunning the suite and
mutation; no allowlist, bypass or force-push is used.

### Runs

The exact dispatches are `gh workflow run os-image.yml --ref pkg/18c-b-chrome -f checks_only=true` once,
then `gh workflow run os-image.yml --ref pkg/18c-b-chrome -f check_build=build` twice, one at a time.
Each uses `gh run watch <id> --exit-status --interval 60`; PR checks use
`gh pr checks 76 --watch --interval 60`. No other workflow was dispatched and no infrastructure rerun used.

| Run | Head | Result / full `gh run view --log` line numbers |
|---|---|---|
| 44280758650, checks-only | `32f38e36` | PASS; 1780 tests at 3776, `OK (skipped=4)` 3778; tools-manifest PASS 3779; 17 destination refusals PASS 3780. Regression job 30m30s. Four existing GTK/labwc environment skips at 524–527; no Chrome test skipped. |
| 44286574648, build round 1 (layout observation) | `32f38e36` | FAIL as expected at the unchanged scan, in 8m2s. Layout 2867–2869; trace 2871–2883. Extension ID/CRX hash 1597; Chrome polkit PASS 1825. BUNDLE, KEY_SCAN, CHECKOUT and BUILD_LOG were not reached. |
| 44288748140, build round 2 (fixed scanner) | `2e2516b1` | PASS in 40m2s, including the complete image checks and VM pass. Every Chrome image PASS is listed below; no rerun used. |
| 44280744725, PR Control Chrome install | `32f38e36` | PASS; case 1–5 at 2295–2299; `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2300. |
| 44280744759, PR Chrome records | `32f38e36` | PASS; 21 tests 194, `OK` 196; `record_build check passed` 205. |
| 44280744560 / 44280744736 / 44280744399 / 44280744700, PR boundary / base / Mail / privacy | `32f38e36` | All PASS. |
| 44280744308 / 44280744312, PR Chrome qualification / Chrome | `32f38e36` | Both PASS; every workflow on this push completed successfully. |
| 44288754083, PR Control Chrome install | `2e2516b1` | PASS; 28 unit tests at 2213, node:crypto cross-check 2219; cases 1–5 PASS 2291–2295; `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2296. |
| 44288754676, PR Chrome records | `2e2516b1` | PASS; 21 tests 195, `OK` 197; `record_build check passed` 206. |
| 44288754410 / 44288754273 / 44288754854, PR boundary / base / privacy | `2e2516b1` | All PASS. |
| 44288754707, PR Mail | `2e2516b1` | PASS. |
| 44288754376 / 44288754297, PR Chrome / qualification | `2e2516b1` | Still in progress at the evidence-only report commit; last check snapshot 45 passed, two core browser jobs running, no failures. These are not complete-workflow PASS claims. |

The final commit changes this progress file only. Its PR workflows are watched separately through completion;
the exact manual runs and their source head remain those above. No pending workflow is counted as passed.

### Image evidence from the green build

These are full `gh run view 44288748140 --log` line numbers, not the unit-test stand-ins in checks-only:

| Evidence | Log line | Result |
|---|---|---|
| `CONTROL_CHROME_EXTENSION` | 1640 | `fiacjggnpbfbgiaiaanigeddhgnegmfe`, CRX SHA-256 `4459d94d7d9029a111226946f2ac1ea5d9ee85c07bb829b0e477bbb7813b4004` |
| `CONTROL_CHROME_BUILD` | 1641 | `c689b9c8f7d748c137dd5f64b0a317368a13f5b781ce0d17a21b199b03c4eaa9`, unchanged runtime |
| Chrome polkit action PASS | 1868 | no/no/auth_admin, never kept, owner is the service user; no rule names it; pkcheck and agent present |
| Existing uncached-polkit PASS | 1909 | The same process is asked again; the cached control action is reused |
| `CONTROL_CHROME_SCAN_LINK` | 2910 | `root` → `var/roothome`, target missing, no content |
| `CONTROL_CHROME_PUBLIC_MODULUS` | 2911 | Public modulus printed for the runner's build-log scan |
| `CONTROL_CHROME_BUNDLE_PASS` | 2912 | Same ID and CRX hash as 1640 |
| `CONTROL_CHROME_KEY_SCAN_PASS` | 2913 | Complete image scan passed |
| Chrome excluded-sites PASS | 3520 | Absent in image; tmpfiles creates refused placeholder, preserves changed content, restores mode/group; installed validator refuses format 0 and accepts empty format 1; unit cannot write the folder |
| `IMAGE_CHECKS_PASSED` | 3549 | Complete image checks |
| `CONTROL_CHROME_CHECKOUT_PASS` | 3570 | Same runtime hash and ID; image bound to checkout |
| `CHECK_BUILD_PASSED` | 3573 | Complete runner comparison, including the installed vendor tree |
| `CONTROL_CHROME_BUILD_LOG_PASS` | 3574 | No modulus or PEM private-key marker in the image build log |
| `CHECK_BUILD_VM_PASSED` | 4267 | Existing general image VM pass; not the later Chrome-specific VM pass |

The downloaded `check-build-evidence` artifact independently retains the same link row at
`image/checks.txt` line 1203 and BUNDLE/KEY_SCAN at 1205/1206. Its `image/control-chrome-checkout.txt` and
`image/control-chrome-build-log.txt` contain their corresponding PASS lines. The link row is:

```json
{"path": "root", "resolved": "var/roothome", "status": "missing", "target": "var/roothome"}
```

The one hosted checks-only run covers the merged baseline and diagnostic. The later scanner change is
covered by the final 32 local image tests (all the touched module), the killed host-view mutation, and this
complete built-image run. No second checks-only dispatch is claimed. Its unit-test stand-in PASS lines
(2556–2557 and 2561) are not image proof.

### Not verified

The Chrome-specific VM flows, real-session rule-loosening dialog, browser update/rollback and profile
continuity remain for steps 4–6 and the 28b integration. No `gh` installation is built by this step. No owner
profile, hosts or laptop deployment was used. No local Gradle process was started.

### Left, in order

After the lead accepts this 3a fix:

1. **3b — `gh`:** pinned RPM, key and licence; extraction/signature checks, lock/record/resolve line, tests,
   then another green `check_build=build`.
2. **4:** real-session polkit probe for rule loosening, then the Chrome VM pass. Tell the lead before committing
   any `os-image.yml` change so linux-aresos hears first.
3. **4b:** the brief's split for C3, remaining C6, C10 and C11 if step 4 reaches its budget.
4. **5:** update/rollback, missing/broken bundles, store requests, and F7's password/cancel/ask-again checks.
   When 28b is integrated, case 3/C4 also proves the in-session profile ask and durable pin continuity.
5. **6:** rehearsal checks, final-head runs, guides and final report, with installation and profile continuity
   reported separately.

### JUDGMENT-CALLs

No new owner-facing decision. The profile decision in PR #106 is settled: a managed yes/no ask in the session,
with no profile password dialog. The existing polkit dialog still belongs to F7 rule loosening.

### PLAN-GAPs

The older Step 3a entry's claim that the storage exception is undecided is superseded by PR #106. The narrow
installation-ID exception and its runtime pin/handshake implementation belong to 28b. That module is absent
here; 3a keeps the complete storage ban. Installation evidence does not prove profile continuity, and the
combined proof remains required before a release containing 28b ships. There is no outstanding scanner gap
from this step. Open questions for 3a fix: none.

### The os/ diff for linux-aresos

Net changes from the starting head `91ad33d6`:

- `os/ci/control/chrome_image.py`: image-relative link traversal, missing-target evidence, strict `lstat`
  walks; no installed/runtime change.
- `os/tests/test_control_image.py`: nine scanner regressions and the image-to-helper wiring assertion.
- `os/manifest/ci/16/pending-rebind.json`: generated pending record; main's notes/history and branch notes
  retained, with this step's merge/diagnostic/fix notes. No rehearsal table is rebound.

`os/ci/image-checks.sh` has a temporary diagnostic in `32f38e36`, removed by the fix; its net step diff is empty.
`.github/workflows/os-image.yml` is unchanged. The earlier Step 3a section below lists the full installation diff.

Scratch audit: no file over 500 MB remains in `.work/`. No image layer, ISO or extracted disk was downloaded
to the laptop. Retained scratch holds small logs, test scripts and the CI evidence artifact.

## Step 3a (2026-11-18, gpt-6-astra)

**Stopped incomplete after the two allowed image-build rounds.** Both builds failed in the new CI checker,
not on infrastructure. The first defect (requiring 0755 on the image's 0555 root) is fixed; the second remains:
the PEM scan assumes `<scan-root>/root` resolves to a directory. Run 44247363499 reports `FileNotFoundError`
there. No third run or post-limit code fix was made. The image/key/placeholder/checkout proof is not green;
3b must wait for the lead's disposition of this 3a finding.

### Done

Chrome's image files are installed by 18c's existing map. No `gh` installation, service/extension change, instruction
text or storage exception is included. `build.py` on this head prints
`c689b9c8f7d748c137dd5f64b0a317368a13f5b781ce0d17a21b199b03c4eaa9`.

| Installed path | Mode | Binding/check |
|---|---|---|
| `/usr/libexec/aresos-control/chrome/host` | 0755 | `FILES`, recorded source/SHA-256/mode, image ownership and checkout comparison |
| `/usr/libexec/aresos-control/chrome/native_host.py` | 0644 | same; unchanged native relay |
| `/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy` | 0644 | same; XML and real `pkaction` defaults no/no/auth_admin, owner annotation equals unit user, no rule names it, existing uncached test remains |
| `/usr/lib/tmpfiles.d/aresos-control-chrome.conf` | 0644 | same; exact two lines, boot placeholder, content preserved and group/mode restored on second invocation, installed `owner_hosts` as service user |
| `/usr/share/aresos/chrome/extension.crx` | 0644 | one `pack.py` invocation per image, public record, independent CRX3 reader/signature/key-derived ID, exact zip payload hashes, checkout payload |
| `/usr/share/aresos/chrome/update.xml` | 0644 | recorded SHA-256, exact XML ID/version and fixed file URL, checkout template rendered for recorded ID |
| `/usr/share/aresos/chrome/policy.json` | 0644 | recorded SHA-256, exactly one force-installed/force-pinned entry with override, checkout template |
| `/usr/share/aresos/chrome/native-host.json` | 0644 | recorded SHA-256, exact manifest and one allowed origin, checkout template |
| `/etc/opt/chrome/policies/managed/aresos.json` | symlink | record's `links`, exact target `/usr/share/aresos/chrome/policy.json`, root-owned 0755 parents under `/etc` and the base's 0555 `/`, only entry in managed folder |
| `/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json` | symlink | record's `links`, exact target `/usr/share/aresos/chrome/native-host.json`, same parent checks, base host retained |
| `/usr/share/aresos/manifest/control.json` | 0644 | gains `chrome_build`, `chrome_extension` (public packer fields plus four file modes/hashes) and the two links |

The bundle folder is 0755; every installed file above is root:root. The map now records 78 deterministic
files, nine directories and three links, plus the four per-build files. `control-tree` installs the same
deterministic map and an empty bundle folder, without signing. The real image build hashes untouched `control/`
before generating settings or invoking the packer. No generated output goes back into `control/`.
The existing `chrome/build-id.json` must contain exactly the new `chrome_build` value; the existing wheel and
vendor checks remain in place.

The install map writes neither `/var/lib/aresos-control` nor the old `/etc/aresos/control/chrome-excluded-sites.json`.
The tmpfiles configuration makes the root:root 0755 folder and root:aresos-tools 0640 regular placeholder at boot:
`{"format":0,"hosts":[]}`. The installed validator refuses it and accepts an empty format-1 list; the service
unit cannot write this folder. Only made-up `.invalid` hosts are used in checks. The new image-side tmpfiles
and installed-validator checks were not reached in either build; the local source tests are separate evidence.

The new checker is CI-only: `check-image.sh` mounts `os/ci/control/chrome_image.py` read-only in the check
container; it is not copied into the image. A non-recursive bind of `/` inside the CI container exposes the image files
under the helper and Podman metadata mounts for the key scans. It checks bundle contents, metadata and identity independently of
the packer, scans every regular image file outside `/proc`, `/sys`, `/dev` for the build's modulus (raw, hex,
base64 and base64url with all three alignments, wrapped forms included), and requires the sole raw occurrence
in the CRX. It scans recorded files, the bundle and temporary/root folders for PEM private-key markers.
The runner is wired to repeat the modulus scan over `evidence/build.log` after `check-image.sh`. Only the public modulus,
ID and hashes are printed. Negative checks reject another bundle, policy, AresOS host or unrecorded Chrome
startup file. The checker's compare command uses only stdlib and the packer's payload/template readers.
These describe the implemented checks: the failed PEM-directory traversal prevents the full scan, its PASS
markers, the build-log scan and checkout comparison from completing in a built image.

### The merge and its resolutions

- `a5e91c5c`: `git fetch origin`, then `git merge --no-commit origin/main`, committed separately. Parent
  `ce3d01e2`; main `774d7954` includes PR #58 (`beb42ec8`), #98 and the later packages. Git reported
  `Automatic merge went well`; there were no conflicts or hand resolutions. The branch's earlier Chrome work
  and main's service/qualification changes both remain.
- `pending-rebind.json` was exactly main's after the merge. Later `rebind.py pending` calls recalculated the
  pending record and added four notes for 3a. Its ten existing rows stayed the same; all of main's notes and
  rebound history were checked equal word for word. This records pending work, not a new rehearsal rebind.
- Main already has the correct workflow sum `tools 20 + build 80 + Control VM pass 16 + 15` and limit 131.
  There is no step-3a workflow edit or commit requiring a notice to linux-aresos.
- The merge-only `git diff --cached --check` reported existing trailing Markdown whitespace from main's
  historical reviews. Those files were retained unchanged; the step-3a diff check passes.
- `74de4a19`: the install and checks. `7fb12b0e`: scan the non-recursive image view so container mounts cannot
  hide image files. `bb2af7f4`: pin the manifest
  metadata and test unsafe owners, modes and parents. Every commit ends with `Built-by: gpt-6-astra`; normal push to the existing
  draft PR #76, no merge or ready conversion.

- `a7e66405`: merge follow-up in the existing install proof. 18e's `daemon.listen` binds
  `.chrome.sock.new` and renames it to `chrome.sock`; the kernel's `ss` address retains the bind name. The old
  proof counted zero connected peers despite successful tool calls. `service_peers` now counts exact established
  server endpoints at both bind names (not peer addresses, prefix matches or listeners). The lead's decision 3
  is applied: failure to ask a hand-loaded extension fails case 1. No runtime file or Chrome build hash changes.
- `c1110036`: the placeholder sweep imports `Engine` through `test_engine`, as main's qualification fixture
  requires, so it uses the fixture baseline rather than the source tree's shipped qualification history.
  The refusal assertions, production engine and runtime hash are unchanged.
- `10ba0470`: the first image build found that my link checker expected 0755 even for `/`; the pinned image
  keeps `/` at 0555. The check now pins that read-only root and retains 0755 for all `/etc` parents. Link metadata
  uses one `lstat`, and a new regression rejects wrong owners, groups, types, targets and modes. No image
  permission, policy or workflow changes; the same runtime hash remains.

### Tests and what they catch

All local scratch stayed under `.work/`: 3a's logs and mutation copies in `.work/18c-b-3a/`, and the existing
suites' fixtures in `.work/18c-b-chrome/` and `.work/20-chrome/`. No local container, VM, Chrome, privileged
command, owner-test module or Gradle process was started.
Closing scratch audit: no file over 500 MB; 11,999,363 regular-file bytes at the audit. No large download or
extracted image remains. The quick tests did not cover an absent or dangling root-home path in the scan view;
that gap is the second build's finding, not a passing test.

| Command (with `TMPDIR` under `.work/18c-b-3a/tmp`) | Actual result | What it catches |
|---|---|---|
| `python3 -B -m unittest discover -s os/tests -p 'test_control_image.py'` after merge | 15 tests, OK | 18c's install map, wheels/vendor and account declarations remain intact |
| same after 3a | 22 tests before the first build; 23 after its root-mode finding, all OK | new fixed files/links, source byte identity, hash-before-generation, exactly one pack call, independent CRX checks, checkout comparison, streaming key scans and both links beneath the read-only root |
| `PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_excluded_sites_placeholder test_exclusions test_build test_extension_stores_nothing test_unit` | 19 tests, OK | current tool sweep, refused placeholder, excluded path, unchanged storage ban, hash and sandbox |
| `python3 -B -m unittest discover -s control/chrome/ci/install -p 'test_*.py'` | 25 tests after merge; 28 after proof correction, all OK | packer, key disposal, network log reader, DevTools pipe, exact server endpoint counting and refused unasked case |
| `python3 -B -m unittest discover -s control/chrome/ci/records -p 'test_*.py'` | 21 tests, OK | archived-commit build records and release-manifest checks |
| `PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_excluded_sites_placeholder test_qualification_fixture` | 17 tests, OK | placeholder sweep uses the isolated qualification baseline; shipped-history guard and fixture regressions pass. Python 3.14 prints a ResourceWarning while cleaning a synthetic HTTPError used by a test. |
| `python3 -B control/chrome/record_build.py check` | `record_build check passed` | current manifests have no control object; registry unchanged |
| `bash -n` separately for each of `os/build.sh`, `os/ci/check-image.sh`, `os/ci/image-checks.sh`, `os/ci/check-build.sh`; `git diff --check` | four syntax PASS lines; diff check exit 0 | shell syntax and patch whitespace |
| Exact `Repo privacy` workflow shell body extracted into scratch and run with scratch `RUNNER_TEMP` | `No file holds a home path with a real user name.`; exit 0 | final tracked files, including this handoff, contain no disallowed home-path username |

The new suite mutates signed bytes with the record updated too, a foreign CRX, recorded ID/payload/version,
wildcard policy, missing override, a second origin, network update/CRX URLs, leftover template token and an extra
bundle. Separate comparisons mutate build, link, payload, version, mode and template hashes. The scanner tests
raw newlines across chunks, both hex cases, base64/base64url at three alignments, wrapped encodings, private-key
marker variants and build-log leakage. These are executed tests, not assertions inferred from code.

Eight additional source mutations were run in a disposable scratch copy, each with its catching test, then removed:

| Mutation | Result |
|---|---|
| Require 0755 on the image root again | FAILED: the valid 0555 root rejected, reproducing the first build's exact finding |
| Remove image ownership/group check | FAILED: wrong-owner metadata unexpectedly accepted |
| Remove CRX signature verification | FAILED: broken-signature mutation unexpectedly accepted |
| Remove CRX payload comparison | FAILED: recorded-payload mutation unexpectedly accepted |
| Remove checkout template/mode comparison | FAILED: mode mutation unexpectedly accepted |
| Remove streaming overlap | FAILED: newline-containing raw modulus crossing the chunk missed |
| Replace build hash with 64 zeros | FAILED: installed hash differs from the untouched source's hash |
| Call pack.py twice | FAILED: call sequence is build.py, pack.py, pack.py |

The proof correction adds three tests: exact `ss` endpoint/state parsing, the real current daemon's extracted
`listen` function with zero/one/two/disconnected scratch peers, and load failures that must fail case 1.
Only the tested functions are extracted from AST; the proof's root/container guard stays intact and no Chrome or
service is started locally. Both behavioral regressions fail on `bb2af7f4`'s proof (two failures, no errors).
The qualification fixture's existing module-import guard was also run before its correction: one failure naming
`test_excluded_sites_placeholder`. The same guard and both whole modules pass after the one-line import change.

### Runs

Dispatched with `gh workflow run os-image.yml --ref pkg/18c-b-chrome -f checks_only=true` (twice, sequentially),
then `gh workflow run os-image.yml --ref pkg/18c-b-chrome -f check_build=build` (two sequential rounds).

| Run | Head | Result / full `gh run view --log` line numbers |
|---|---|---|
| 44227811908, checks-only | `74de4a19` | PASS; 1778 tests at 3546, `OK (skipped=4)` at 3548; tools-manifest PASS 3549; 17 destination refusals PASS 3550. Four existing GTK/labwc tests are skipped by their environment guards (293–296); none is a Chrome test. |
| 44232510221, checks-only | `bb2af7f4` | PASS; 1779 tests at 3760, `OK (skipped=4)` at 3762; tools-manifest PASS 3763; 17 destination refusals PASS 3764. Same four existing GUI skips. Second and final checks round; regression job 22m25s after waiting about 52 minutes for a runner. |
| 44241272420, `check_build=build` | `c1110036` | FAIL in 19m5s: the link-parent checker expected 0755 on `/`, whose actual mode is 0555 (trace 2924–2934). Our checker error, not infrastructure. Chrome polkit PASS at 1882. Bundle identity printed at 1654 (below), but the full image/key/checkout checks were not reached. Fixed by `10ba0470`; no blind rerun. |
| 44247363499, `check_build=build` | `10ba0470` | FAIL in 16m3s: PEM scan raises `FileNotFoundError` for `<scan-root>/root` (trace 2902–2914, checker line 237). Our directory-traversal assumption, not infrastructure. Chrome polkit PASS 1860; existing uncached polkit PASS 1901. Bundle identity 1632 and build hash 1633. The root-mode check was passed on the way to this later failure. Second and final allowed build round; no rerun or further source fix. |
| 44239451590, PR Control Chrome install | `c1110036` | PASS in 3m11s; 28 unit tests at 2218 (`OK` 2220), node:crypto cross-check at 2224; `CONTROL_CHROME_INSTALL_CASE_1_PASS` through `_5_PASS` at 2296–2300, `CONTROL_CHROME_INSTALL_PROOF_PASSED` at 2301. The downloaded 1,282,344-byte artifact has all five verdicts true and case `1-ordinary` explicitly `asked: true`. |
| 44239451427, PR Control base | `c1110036` | PASS; `Control base suite PASS` at 684. |
| 44239451552, PR Control boundary | `c1110036` | PASS; `PRECEDENCE_OK cases=24` at 2050, `CONTROL_PERMISSION_REQUEST_RECORDED` at 2721, `CONTROL_INTERACTIVE_ASK_PASS cases=17` at 2722. |
| 44239451516, PR Chrome records | `c1110036` | PASS; 21 tests at 187, `OK` at 189. |
| 44239451435, PR Repo privacy | `c1110036` | PASS (16s). |
| 44247360319, PR Control Chrome install | `10ba0470` | PASS; 28 tests at 2221 (`OK` 2223), node:crypto cross-check 2227; five case PASS lines 2299–2303, `CONTROL_CHROME_INSTALL_PROOF_PASSED` 2304. |
| 44247360306, PR Control base | `10ba0470` | PASS; `Control base suite PASS` 693. |
| 44247360506, PR Control boundary | `10ba0470` | PASS; `PRECEDENCE_OK cases=24` 2061, `CONTROL_PERMISSION_REQUEST_RECORDED` 2732, `CONTROL_INTERACTIVE_ASK_PASS cases=17` 2733. |
| 44247360328, PR Chrome records | `10ba0470` | PASS; 21 tests at 199, `OK` 201. |
| 44247360400, PR Repo privacy | `10ba0470` | PASS. |
| 44247360331 / 44247360457 / 44247360354, PR Chrome / Mail / qualification | `10ba0470` | Still queued or running at the stop. Last check snapshot: 18 passed, 4 running, 25 queued; no reported current-head PR failure. These are not complete-suite PASS claims. The report-only push may supersede these checks. |

The first run's `CONTROL_CHROME_*` lines 2326–2331 are unit-test stand-ins, not an image bundle's evidence.
The first failed image build printed at line 1654:

```text
CONTROL_CHROME_EXTENSION hlohdejcdlkcapgadfbliibpkcchhlho 0f788c247fe8f0f3b6b2cecf3feb59d4983321bbecf28580a7b268fbb2aae5af
```

The second failed image build printed at line 1632:

```text
CONTROL_CHROME_EXTENSION gcibdegialobgchchpfljagigklhcgmd 4a77bc474f5f7fb338eab80e9f63b51f9af4651c29d373c8d8ae7fe6407a2370
```

Neither run printed `CONTROL_CHROME_BUNDLE_PASS`, `CONTROL_CHROME_KEY_SCAN_PASS`,
`CONTROL_CHROME_CHECKOUT_PASS` or `CONTROL_CHROME_BUILD_LOG_PASS`. The log proves that `<scan-root>/root`
does not resolve; it does not establish whether the image entry is absent or a dangling link. The next fix
must inspect that layout and cover it without ignoring read failures or letting a symlink escape the image
view. I have left the failing check intact for the lead rather than suppressing the error.

The first `check_build=build` dispatch followed the second OS checks run. The checks-only runs cover the final
install map and the checkers before the root-mode correction. The later `a7e66405` and `c1110036` change only test
harnesses; `10ba0470` changes the CI link checker, covered by the 23 local image tests, the scratch mutation and
the second build run up to its later failure. No third checks-only or build round is dispatched: the user
limited each mode to two. Neither failure was infrastructure, and no whole-run infrastructure rerun was used.

PR install run **44229730715** on `bb2af7f4` failed cases 2 and 3 at log lines 2357–2358: the old socket-path
counter saw zero peers (trace 2245–2255 and 2295–2305). Cases 1, 4 and 5 passed at 2356, 2359 and 2360. This is
an integration failure from merging 18e, not infrastructure; no blind rerun was used. `a7e66405` corrects the
observation without changing the one-peer assertions. Run 44239451590 now passes all five cases on `c1110036`.
Earlier PR runs 44227807617 (Control Chrome, Python shard 3) and 44227807705 (qualification, both Python shard-3
repeats) also found the missing isolated-fixture import. Jobs 134545193405, 134551231548 and 134551231722 all
reported only `test_excluded_sites_placeholder` in that guard's missing-module list (per-job log lines 312, 450
and 450, respectively). This is another merge
integration failure, corrected by `c1110036`, not an infrastructure rerun or a relaxed guard.
Superseded Control Chrome runs 44235110518 (`a7e66405`) and 44229730688 (`bb2af7f4`) were cancelled from the
queue after `c1110036` was pushed. Later, runs 44227807705 (`74de4a19`, qualification) and 44228697962
(`7fb12b0e`, Chrome) were cancelled while awaiting aggregation, to release the remaining backlog and the
qualification concurrency group. Run 44227807617 had already finished with failure. The failed guard logs were
read and retained in scratch. After the root-mode fix, cancellation was also requested for superseded
`c1110036` runs 44239451436 (Chrome) and 44239451508 (qualification). Those runs and 44228697962 still had
aggregation queued after ordinary cancellation, so `gh run cancel <id> --force` was used for these three obsolete
runs. The current
head's complete suites and both OS checks runs were kept; no test or assertion was disabled.
Each OS run is watched with `gh run watch <id> --exit-status --interval 60`, never concurrent on this ref.
PR checks are watched with `gh pr checks 76 --watch --interval 60`.

### Left, in order

First resolve the incomplete 3a image proof above with the lead; the code remains at `10ba0470` and the final
commit adds this report only. After 3a is accepted, the brief's remaining order is:

1. **3b — `gh`:** pinned RPM/key/licence, extraction and signature checks, lock/record/resolve line, its tests,
   then `check_build=build` green once more.
2. **4:** start with the real-session polkit probe; then the Chrome VM pass and first checks. Tell the lead before
   committing any `os-image.yml` change. The current Control limit is 131, so account for that when adding the
   Chrome pass.
3. **4b:** the documented split if step 4 reaches its budget; C3, remaining C6, C10 and C11.
4. **5:** update/rollback and broken/missing bundle, store-request proof, password dialog/cancel/ask-again checks.
5. **6:** rehearsal checks, final-head runs, guides and final report.

### What the code doesn't show

- This does not yet prove the complete image installation: both built-image checks failed as recorded above.
  No image-side key-scan, placeholder, checkout or build-log PASS is claimed. The owner has not used this
  image. No release was built for publication, signed, pinned or deployed. Booted Chrome/polkit flows, browser
  VM cases and real update / `previous` preservation remain for the later steps.
- The randomized bundle is intentionally absent from `control-tree`; comparing a second CRX's bytes would be
  wrong. The image's independent reader binds the actual CRX to its record, and the runner binds that record's
  payload/rendered templates/build/links to the checkout. The known per-image-identity consequences stay.
- The PEM scan excludes vendored packages and the rest of `/usr`, whose legitimate crypto code contains key
  markers; the unique-modulus scan covers those paths. It counts paths without following symlinks, fails on
  read/list errors, and handles line-wrapped encoded keys as well as raw binary.
- The host and polkit action are installed byte for byte; there is no change to service policy, unit sandbox or
  Chrome launch flags. No instruction text was added. Decision 3's case-1 `asked:false` rule is applied in the
  proof correction; inability to load/ask now fails. Decisions 4–8 and 10 remain instructions for steps 4–6.

### JUDGMENT-CALLs

- No new owner-facing choice. The install follows the agreed paths, modes, policy shape and placeholder exactly.
- The independent checker lives under `os/ci/control/`, is mounted only in the check container, and also provides
  the runner's comparison/log scan. This avoids shipping test code and keeps the two modulus scans identical. The non-recursive view prevents
  those check-only mounts from hiding image files.
- The modulus scan additionally removes ASCII whitespace for encoded forms, so wrapped PEM/base64 cannot evade
  it. The raw stream is still checked with overlap, without line splitting.

### PLAN-GAPs

- **Open dependency, PR #106:** 28b's proposed profile pin may require a storage exception. It is undecided.
  3a preserves the brief's complete storage ban; no exception or profile pin is implemented here.
- The old timeout note in decision 11 is already resolved by main; no workflow edit is necessary.
- Main's 18e atomically published socket retains `.chrome.sock.new` in kernel observations. The old step-2
  proof's literal `chrome.sock` observation was stale after this required merge. Corrected in the test harness,
  with no service or extension change; future VM peer checks must account for the original bind name too.
- Main's qualification fixtures require every test that constructs an engine/Chrome adapter to import
  `test_engine`. The earlier placeholder sweep missed that new convention; its import now installs the shared
  isolated baseline, preserving both sides' test intent.

### The os/ diff for linux-aresos

Every path below is relative to this repository; this list covers step 3a's changes after the merge:

- `os/build.sh`: four deterministic FILES entries, two links, hash-before-generation comment, one per-image pack
  call, `chrome_build`/`chrome_extension` and `CONTROL_CHROME_EXTENSION`.
- `os/ci/image-checks.sh`: real pkaction/annotation and no-rule check; stronger policy-folder/bundle check;
  boot-only placeholder, second tmpfiles invocation and installed-validator checks.
- `os/ci/control/chrome_image.py` (new): independent CRX/policy/host/XML/metadata checker, full-image key scans,
  stdlib checkout comparison and build-log scan; never shipped.
- `os/ci/check-image.sh`: read-only checker mount, deterministic build comparison and per-build payload/template
  comparison, preserving the existing wheel and vendor checks.
- `os/ci/check-build.sh`: scan the runner's build log with the checked public modulus before disk/VM work.
- `os/tests/test_control_image.py`: extended install expectations and eight new tests described above.
- `os/README.md`: browser-side install, per-build identity and refused placeholder; `gh` left for 3b.
- `os/manifest/ci/16/pending-rebind.json`: four generated pending notes; main's rows/notes/history unchanged.


## Where it stands

**Step 3b's check fix is implemented in `689d8a48`; the lead's new-head CI proof is left.** The gh
2.103.3 RPM, 2026 key and licence remain pinned. Its exact RPM payload list now replaces the name-only
exclusion; all 48 local image tests pass and the restored name check fails the new base-file regression.
The lead reports checks-only `44329677029` and resolve `44344811923` green on `6b80a139`; build
`44339552024` reached the gh install/keyring/version proof, then failed the old name check. No passing
3b image check is claimed. The lead's shell dispatches and watches checks-only and one build on the
pushed follow-up head; this builder commits, pushes normally and stops.

The complete step 3a image proof remains green on `2e2516b1`. After 3b, the order remains **4, 4b, 5, 6**.
The approved profile ask is in-session; 28b owns its pin and narrow installation-ID storage exception.
No workflow file, release pin or laptop deployment has changed.

## The lead's decisions after step 2b (2026-11-15)

1. **JUDGMENT-CALL 1 (the DevTools pipe) is accepted**, for the proof's own Chrome starts only. The image's Chrome
   start and policy never carry a `--remote-debugging-*` flag; step 4's image check asserts that (keep or add it).
2. **JUDGMENT-CALLs 2 to 5 are accepted** as written.
3. **JUDGMENT-CALL 6 changes:** on the pinned Chrome, a hand-loaded extension that could not be asked fails case 1
   instead of passing with `asked: false`. A check that quietly stops running must not look green; if a later
   Chrome can't load one, that is a finding for the lead. The next step that touches `proof.py` makes the change.
4. **C9 in the VM (step 5) may use case 5's trigger:** one test-only Chrome start in the guest with
   `--remote-debugging-pipe` and `cdp.py`, its own throw-away profile, run by the test; it checks that nothing
   listens, and the positive control (the probe's requests, log count equal to the server's count) is required.
   `cdp.py` goes into the guest with the test's files, never into the image. This amends the brief's C9.
5. **C2 in the VM (step 4)** asks an extension loaded by hand over the pipe, as `case_ordinary` does.
6. **PLAN-GAP 2:** both of the brief's assertions stay. The brief's sentence that the IDs go in a body the log
   doesn't record is outdated for Chrome 157; the header makes the ID assertion a real one.
7. **PLAN-GAP 3:** nothing to change; case 5 compares against the probe alone, so Chrome's own start-up requests
   cancel out.
8. **The three known-limit lines are accepted**; step 6 places them in `KNOWN-LIMITS.md` and the report.
9. **3a waits for PR #58 on `main`.** Claude reviewed #58 on 2026-11-16, and its fix round is running. Codex astra
   reviews #58 before it merges. Then the lead's go.
10. **The never-list guide text** (brief review 5 of PR #48, S6, 2026-11-16): the step that writes his guide says the
    list is empty only when he has no site to exclude. His dashboard's host goes on it first, as CONTROL.md section 6
    says. PR #48 corrects brief 18c-b's lines 24 and 423 to match.

11. **From #58's fix round 1, part 2 (2026-11-16):**
    - Control's Chrome build hash in the image is now `91cdfeb6291380ffd8cf271a77e5baef8a6abd5aaa2c4ea504b69ff866969ae5`
      (was `ccd0fd79…`, the one the brief names). Use the hash the build makes at 3a's head; don't copy either
      literally.
    - `os-image.yml`'s Control job keeps `timeout-minutes: 127` while the pass step went 12 → 16 minutes; the job's
      comment still adds up with 12. 3a's first `os-image.yml` commit fixes the comment's sum (or the job's limit,
      131), runs `rebind.py pending`, and `linux-aresos` is told before it, as for every `os-image.yml` change.

## Step 2b (2026-11-15, Claude Fable 5.2)

### The lead's decisions on step 2's findings

1. **`setEnabled(false)` from another policy-installed extension** is accepted as Chrome's behaviour. Case 1 as
   step 2 changed it stands (the `uninstall` refusal; ours enabled and connected again at the next start).
2. **Chrome's own update-service requests** for its own extensions are accepted. Case 5's rule is the brief's
   fallback: against a run of the probe alone, ours adds no address and no ID.
3. **Case 5's trigger:** make the update check deterministic instead of waiting for the schedule; first try
   `chrome.developerPrivate.autoUpdate()` in `chrome://extensions` over the DevTools protocol.
4. **Case 3's record of the previous ID:** look at what it holds; a check if it grants the old ID anything,
   otherwise a line under "what the code doesn't show".

### Done

- **`cdp.py`** (new, standard library, 4 tests in `test_cdp.py`): the DevTools protocol over
  `--remote-debugging-pipe`. Only the Chrome starts that name it get the pipe (case 5's three, and the one below);
  every other start still refuses the `NEVER` flags. A pipe, not a port: each of those starts checks that Chrome
  listens on nothing.
- **Case 5** asks Chrome for each update check. Per run (ours; the probe alone; the policy without
  `override_update_url`): Chrome starts with the network log, `--disable-component-update` and the pipe; once the
  extensions are in, `chrome://extensions` is opened and `chrome.developerPrivate.autoUpdate()` is called twice,
  3 s apart (what the page's "Update" button calls: `ExtensionUpdater::CheckNow` with no IDs, so every extension;
  read in Chrome 157's `developer_private_functions.cc` and `extension_updater.cc`). After each call the proof waits
  for the probe's request at the test's own server. Required of every run: the probe's ID is in two update requests
  in the log, **and the log holds exactly as many as the server answered**.
- **`netlog.py`** (11 tests): a request's start is the event the log's own constants call `URL_REQUEST_START_JOB`
  (a log without constants is read as before); `added` counts a mention of the update service that the events
  don't account for (a line cut off mid-write) as added, also when the baseline has one.
- **Case 3** writes what the preference files keep under the previous ID to
  `case3-<n>-previous-record.json` and requires that it holds none of `manifest`, `path`, `location`,
  `active_permissions`, `granted_permissions`, `runtime_granted_permissions`.
- **Case 1, an extension loaded by hand** (`case_ordinary`, counted in case 1's verdict): a Chrome start of its own
  (own profile, the pipe, `--enable-unsafe-extension-debugging`), developer mode on, `Extensions.loadUnpacked` of a
  two-file extension with the `management` permission, then its page calls `management.setEnabled(<ours>, false)`.
  Chrome must refuse, and ours must still be enabled and connected. If this Chrome won't load one that way, the
  result says `asked: false` with the reason and case 1 doesn't fail for it.

### Runs

| Run | Head | Result |
|---|---|---|
| 43729218613 | `c4514015` | `pack` green (`Ran 25 tests`, `OK`, `# pass 1`). Proof: `CONTROL_CHROME_INSTALL_CASE_1_PASS` to `_5_PASS`, `CONTROL_CHROME_INSTALL_PROOF_PASSED`. The job took 3 minutes, after 56 in the queue |

Three of the 40 runs of this workflow are used. Cases 1 to 4 repeat step 2's numbers (install 0.8 s, pin 0 and
819 pixels, both switches of case 3 done 0.89 s after Chrome's start, case 4 held 20 s).

**Other runs, looked at once and not waited for.** On `c4514015`: records 43729218607, base 43729218627 and
boundary 43729218628 green; Control Chrome 43729218606, Mail 43729218574 and qualification 43729218660 still
queued. **Control Chrome 43726164356 on `9ac6c8cb` never started** (queued since 14:46 UTC, at both looks); that
head's Mail and qualification runs were cancelled by this step's push. So the whole matrix has no result on any
head of this branch since step 2: read 43729218606.

### Case 5 on run 43729218613 (all **run**)

| Run of Chrome | Update checks asked (s after start) | Probe's requests: log / server | Update-service addresses and IDs | Our ID outside a `file:` address |
|---|---|---|---|---|
| ours | 1.1, 4.3 | 2 / 2 | `https://clients2.google.com/service/update2/crx`, Chrome's own two IDs | none |
| the probe alone | 1.07, 4.27 | 2 / 2 | the same | none (it doesn't have it) |
| without `override_update_url` | 1.12, 4.32 | 2 / 2 | the same, **plus `POST https://update.googleapis.com/service/update2/json`** at each of the two checks | **`X-Goog-Update-AppId: <our ID>`**, twice |

- **Ours adds nothing:** `added_by_our_policy` is empty, and the two runs name the same five hosts.
- **The negative control fails the scan both ways:** an added address, and our ID named. The POSTs are in the log
  at the same instant as the probe's two requests (+0.71 s and +3.91 s), so each asked check did take ours in, and
  with `override_update_url` the same two checks leave nothing.
- What Chrome asks by itself in every run, all ending in `ERR_INTERNET_DISCONNECTED`: its time service
  (`clients2.google.com/time/1/current`), a spelling dictionary (`redirector.gvt1.com`), `www.google.com/async/…`,
  a key list at `www.gstatic.com`, and the store's update address for its own two extensions at 0.2, 2.2 and 6.1 s.
- Each run lasts about 7 s. `autoUpdate()`'s own answer never came within it (`checks_ended` 0): the check ends
  only when Chrome gives up on its own store requests.

### Case 3's record of the previous ID (**run**)

After A to B and after B to A, `Default/Preferences` keeps **an empty object, `{}`**, under the previous ID;
`Secure Preferences` has no entry for it. Nothing Chrome could load, no permission, no host access: bookkeeping
only. The check above stays as a guard, and the files are in the artifact.

### Case 1, who can switch ours off (**run**)

- An extension installed by policy can (step 2; `after_it`: `enabled` false, the tools `chrome_unavailable`; back
  0.61 s after the next start).
- **An extension loaded by hand can't:** `installType` `development`; `setEnabled(false)` answers
  "Extension … cannot be modified by user."; ours stays enabled and connected. This was read in step 2 and is run
  now. Chrome's rule: `AdminPolicyIsModifiable` in `standard_management_policy_provider.cc`.
- He himself in Chrome's own pages: `mayDisable` false (run); the switch on `chrome://extensions` was not clicked.

### Known-limit lines (for the report and `KNOWN-LIMITS.md`; the lead places them)

- An extension installed by policy can switch ours off until the next start of Chrome. Adding one needs root, so
  that is he himself or whoever has his password. While it is off the tools answer `chrome_unavailable` (fails
  closed). An extension he loads by hand can't do it.
- On a fresh profile Chrome asks Google's update service about two extensions of its own, whatever our policy
  says. Ours adds no address and no ID to that.
- After an update the profile's `Preferences` keeps an empty record under the previous ID.

### Left, in order

1. **3a**, when PR #58 is on `main` and the lead says go. Then 3b, 4 (4b), 5, 6 as before.
2. **For step 5 (C9 in the VM):** no scheduled update check comes within a VM run either. C9 needs case 5's
   trigger in the guest: a Chrome start with `--remote-debugging-pipe` and `cdp.py` (standard library, like
   `netlog.py`), which the brief's C9 doesn't allow yet. The lead decides; the other way, a policy change (below),
   is read and not run.
3. **For step 4 (C2):** the probe can't be refused `setEnabled` (it is policy-installed). With the pipe, C2 can ask
   an extension loaded by hand, as `case_ordinary` does.

### What the code doesn't show (2b)

- With `override_update_url` the update check of ours leaves **no line in the network log**: Chrome doesn't load a
  `file:` address through its network stack. That ours is in each check is shown by the negative control (the same
  two calls give two POSTs) and by Chrome's log having no "can not be updated" line (`chrome_could_not_update`
  empty in all three runs).
- Chrome doesn't close the log's JSON on SIGTERM: all three logs end mid-list. The constants are read from the
  file's first line.
- The pipe's ends: Chrome's two are passed as descriptors 10 and up and moved to 3 and 4 by a one-line `bash`
  `exec`, so Chrome keeps its PID. Our reading end is closed by its own thread at the pipe's end.
- Developer mode is switched on in the profile `ordinary` alone. No other profile sees the pipe except case 5's
  three.
- The network logs in the artifact hold Chrome's own built-in API key and request keys in Chrome's addresses.
  They are Chrome's, the same in every copy; nothing of ours or of the owner's.
- Step 2's two other ideas (a run with a network; a policy change adding a pending forced ID) were not tried:
  the first one worked. Read only: a changed policy with at least one `update_url` extension ends in
  `CheckNow` for every extension (`external_provider_manager.cc`).

### JUDGMENT-CALL (2b)

1. **A DevTools pipe in four Chrome starts**, against the brief's "never `--remote-debugging-*`", on the lead's
   decision 3. The pipe instead of a port, so nothing listens; cases 1 to 4's own starts are unchanged.
2. **`--extensions-update-frequency` is no longer passed.** Chrome 157 has no such switch: `extension_service.cc`
   gives the updater a fixed `kDefaultUpdateFrequency` and `extensions/common/switches.cc` doesn't list it.
3. **The proof doesn't wait for `autoUpdate()`'s answer**; it waits for the probe's request (the positive
   control) after each call. Two checks, 3 s apart.
4. **The positive control is stricter than the brief:** the log's count of the probe's update requests must equal
   what the test's server answered, not only be at least two.
5. **Case 3's check names what must not be there** instead of requiring an empty record, so a timestamp Chrome
   might add later doesn't fail it. Today's record is empty.
6. **The hand-loaded extension is asked where Chrome can load one**, and reported as not asked otherwise, because
   the brief requires the question of the probe alone. On the pinned Chrome it was asked.

### PLAN-GAP (2b)

- **No short update schedule exists** in Chrome 157 (JUDGMENT-CALL 2), so "across at least two update checks" can
  only be had by asking for them. The same holds for C9.
- **The log does show the IDs sent to the update service.** The brief says they go in a body the log doesn't
  record; Chrome 157's log has the request's headers (`CORS_REQUEST`), among them `X-Goog-Update-AppId` with every
  ID asked about. So both of the brief's assertions see the leak, not only the address.
- **Chrome asks more than the update service by itself** (the four addresses above). They are the same with and
  without ours and name no extension of ours.
- Step 2's three points stand.

## Step 2 (2026-11-15, Claude Fable 5.2)

### Done: the install proof in a container (item 2)

- `.github/workflows/control-chrome-install.yml` ("Control Chrome install"): pull requests touching
  `control/chrome/packaging/**`, `control/chrome/extension/**`, `control/chrome/ci/install/**`, the container's
  `Dockerfile`, `service.py`, `native_host.py` or the workflow. `contents: read`, no secrets. It builds the container
  of `control/chrome/ci/Dockerfile` with the pinned Chrome, adds `python3-cryptography` in a layer of its own
  (`control/chrome/ci/install/Dockerfile`), runs `run.sh pack` and then `run.sh proof`, both with `--network none`.
- `control/chrome/ci/install/chrome.lock.json`: Chrome **157.0.8103.50**, the image's pinned version, as Google's
  `.deb` by URL and SHA-256 (`92148bd1…3f79`, 147674220 bytes; Google still serves it). A workflow step compares it
  with `os/google-chrome.lock.json`: another major fails, another patch version warns.
- `proof.py` (root, in the container only): the image's layout (four files in `/usr/share/aresos/chrome/`, the two
  links in `/etc`, `packaging/host` 0755 and `native_host.py` in `/usr/libexec/aresos-control/chrome/`), a made-up
  `format` 1 list at `exclusions.SETTING`, CI's `service.py` as it is, one Xvfb session, Chrome with `browser.mjs`'s
  flags. Bundles A, B and C each come from one call of `pack.py -I -B`. Evidence in the artifact
  `control-chrome-install-<run>-<attempt>` (`result.json`, Chrome's logs, `probe.jsonl`, `tool.jsonl`, screenshots,
  network logs).
- The probe: `probe/` (extension: `management`, `nativeMessaging`; its manifest's `update_url` is
  `http://localhost:18766/probe/update.xml`), `probe_host.py` (its test-only host: writes down every message and
  relays it to the check's socket). Installed by `ExtensionInstallForcelist` alone, in `aresos-install-probe.json`,
  from its own `file:` address, packed with `pack.pack` under its own key.
- `netlog.py` with `test_netlog.py` (9 tests): the scan of `--log-net-log` for case 5, standard library only, so
  the VM pass can use it in the guest. `tool_call.py`: one tool call as the owner over `act.sock`.

### Runs

| Run | Head | Result |
|---|---|---|
| 43724239061 | `faa7e340` | `pack` green: Python 3.11.2, `cryptography` 38.0.4, `Ran 17 tests`, `OK`; node v22.23.5, `pack-crosscheck.test.mjs` `# pass 1` (**its first run ever**). Proof: case 4 PASS; 1, 2, 3, 5 FAIL (the three findings below) |
| 43726164336 | `9ac6c8cb` | `pack` green (`Ran 19 tests`, `OK`, `# pass 1`). Proof: `CONTROL_CHROME_INSTALL_CASE_1_PASS` to `_4_PASS`, `_5_FAIL` |

Two of the 40 runs of this workflow are used. Every push also started Control Chrome, base, Mail, boundary,
qualification and records (their paths); nobody waited for them: on `9ac6c8cb` base 43726164318, boundary
43726164304 and records 43726164298 are green, Control Chrome 43726164356, Mail 43726164371 and qualification
43726164312 were still queued. The lead's rerun of 43716630045: `fixtures (external, word-1)` passed on attempt 2;
the run's conclusion still read `failure` when looked at once.

### What run 43726164336 shows, case by case (all **run**)

1. **Install: PASS.** Fresh profile, no address but loopback's, no default route. Chrome installs ours from
   `file:///usr/share/aresos/chrome/update.xml` through the two links: installed 0.6 s and connected 0.64 s after
   Chrome's start. `management.get`: `installType` `admin`, `enabled` true, `mayDisable` false. `uninstall` is
   refused: "Extension … cannot be modified by user." No forbidden flag in any Chrome process, no listening port.
   **The pin:** in the right half of the top strip, 0 pixels differ between two pinned starts and 819 between
   pinned and the same policy without `toolbar_pin`. `setEnabled(false)`: see "wrong against real Chrome", 1.
2. **One origin: PASS.** The host manifest behind the link equals the rendered template; the host runs as the
   owner, started by Chrome, with exactly `PATH=/usr/bin:/bin` and `LANG=C.UTF-8`. The probe's
   `connectNative('org.aresos.chrome')` answers "Access to the specified native messaging host is forbidden."; over
   28 samples while it tried there was one host process and one connection on `chrome.sock`; ours still answered.
3. **Update and back: PASS.** A to B, then B to A, one profile, Chrome restarted. Both times, after Chrome's
   start: old ID gone 0.41 s, new installed 0.41 s, new connected 0.67 s, old folder gone from
   `Default/Extensions` 0.67 s. Only the current ID is listed beside the probe; the probe is refused again; the
   manifest's bytes hold the current origin and not the previous ID.
4. **A broken package: PASS (both runs).** On a profile that never held C: with one byte of the signed archive
   changed (Chrome logs `Package is invalid: 'CRX_SIGNATURE_VERIFICATION_FAILED'`) and with the file missing, C
   is not installed over 20 s (20 samples each), the tools answer `chrome_unavailable`, Chrome and the service stay
   up, the start page and a typed address both load. Restored: installed 0.41 s, connected 0.44 s. Installed, then
   changed or missing: still enabled and connected after 8 s.
5. **Nothing asks the store: FAIL, unfinished.** See "Left".

### The brief against real Chrome (157.0.8103.50)

1. **`setEnabled(false)` is not refused to the probe.** Chrome lets one policy-installed extension switch another
   off, and the brief requires the probe to be policy-installed. Run 43724239061: the call answered `ok`, ours showed
   `enabled: false`, the tools `chrome_unavailable`, for the 120 s watched. Case 1 now requires the `uninstall`
   refusal and that **the next start of Chrome has ours enabled and connected again** (run 43726164336: 0.4 s and
   0.43 s), and records what Chrome answered. Not exercised: an extension that is not policy-installed (read, not
   run: Chrome refuses those as it refuses the user). Whoever can add a policy file can already replace ours, so
   this adds no new party; it does mean C2 in the VM can't require the refusal either.
2. **"No request at all to the update service" doesn't hold for Chrome itself.** On a fresh profile, with
   `--disable-component-update` and no network, Chrome asks
   `https://clients2.google.com/service/update2/crx` for two extensions of its own
   (`ghbmnnjooekpmoecnnnilnnbdlolhkhi`, `nmmhkkegccagdldgiimedpiccmgmieda`, both `v=0.0.0.0`), retrying at 0, 2, 6,
   13, 29, 60, 120 and 236 s (run 43724239061's log). **Neither our ID nor the probe's appears anywhere in that
   236 s log.** So the brief's fallback is the rule now: case 5 always runs the probe alone as the baseline, and ours
   must add no address and no ID (`netlog.added`); the control without `override_update_url` must add one.
3. **`--extensions-update-frequency` gave no scheduled check.** With `=30`, no update check of the probe reached
   the test's server in 240 s (run 1) or 600 s (run 2). The probe's own `chrome.runtime.requestUpdateCheck()` then
   answered `no_update` and its request did arrive at `localhost`, so the address works and the schedule doesn't.
   Not a "Stop and report" case: nothing names our ID.

### Left, in order

(1 and 2 are closed in step 2b, above.)

1. **Case 5.** The baseline, the comparison and the negative control are written but have never run: the case
   stops at "two scheduled update checks". Find what makes Chrome 157 check all extensions. Untried ideas: the
   two store installs that never finish without a network may hold the schedule back (a run with a network, or a
   longer one); a policy change that adds a pending forced ID starts a check of everything (read, not run). The
   probe's `requestUpdateCheck` is ready as a positive control for the probe alone, but it doesn't check ours.
   Chrome doesn't close the log's JSON on SIGTERM; `netlog.events` reads the cut-off file line by line.
2. **Case 3's preference record.** After each switch the profile's preference files still list the previous ID
   (`"previous": true`, 7 entries) although the management API and the folder say it is gone. Recorded, not
   required; look at what the entry holds before turning it into a check.
3. Then 3a, 3b, 4 (4b), 5, 6 as before.

### What the code doesn't show (2)

- The artifact's files are public by design (`bundles.json` holds IDs and hashes only). No key is written; the
  probe's key is made in `proof.py`'s own process by `pack.pack` and dropped.
- `proof.py` runs as root because it swaps files under `/usr/share`; Chrome, the tool calls and the session run as
  `owner`, the service as `aresos-tools`. Chrome is ended with SIGTERM by its PID.
- The "one host" check reads the kernel's view (`ss -x`) and the process list, sampled every 50 ms, plus Chrome's
  own refusal text. `service.py` has no line for an accepted or refused host.
- Cases are independent where they can be: each has its own profile except 1 and 3, which share one on purpose.

### JUDGMENT-CALL (2)

1. **The policy form stays `ExtensionSettings` alone**: the pinned Chrome installs from it. The fallback isn't needed.
2. **Case 1's `setEnabled` check changed** as described above instead of installing a second, non-policy probe.
3. **The pin is asserted by pixels** (pinned twice against pinned and unpinned), since nothing but our own
   extension can ask Chrome about its pin. Thresholds: at least 150 pixels and four times the same-start difference.
4. **The harness is Python, not node**, so steps 4 and 5 can reuse `netlog.py`, the probe and its host in the guest.
5. **The Chrome pin is a file** (`chrome.lock.json`) whose hash has no second source; a patch-level difference to
   the image's lock warns instead of failing, as the brief allows the same major.
6. **Case 5 runs without a network** like the other cases; `--extensions-update-frequency=30` because release
   builds are said to enforce 30 s (read, not confirmed: no check ran at all).

### PLAN-GAP (2)

- The three points under "The brief against real Chrome".
- A change of `os/google-chrome.lock.json` doesn't start this workflow (its paths are the brief's plus its own
  files); the version step only speaks on the next run.
- Every push to this branch starts the whole Control Chrome matrix, because the new files live under `control/`.

## Step 1b

### Part A: the latency pair after 1a (run 43705955018)

**Cause (read from the run, not assumed).** Every job of `Control Chrome` on `265caa52` was green except
`latency (plain)` and `latency (audit)`, both in "Paired current and historical measurements on the same runner"
(`control/chrome/ci/latency-pair.sh`). The pair runs two legs: `current`, then `ab7aba92` (main's older runtime,
with the current `control/chrome/ci/` and `control/chrome_tests/` copied over it). The `current` leg finished and
printed its results (`"runtime": "current"`, build `2acd63cb…`); the `ab7aba92` leg failed in `browser.mjs` line 40
with `extension native connection: undefined`. Its artifact (`chrome-latency-43705955018-1-ab7aba92-plain`,
`tool.jsonl`) holds 296 `tabs` answers: 5 `chrome_unavailable` (before the extension connected), then 291
`chrome_settings_unavailable`. So the extension did connect; the tools refused because the list wasn't where that
runtime reads it. `ab7aba92`'s `exclusions.py` has `SETTING = '/etc/aresos/control/chrome-excluded-sites.json'`,
and the current `prepare.mjs` (copied into that leg) wrote only `/var/lib/aresos-control/…`. `rpc('tabs')` answers
`ok: false` without throwing, which is why the message says `undefined`. The lead's guess was right.

**Fix** (`32f1126c`): `prepare.mjs` no longer names a path for the list. It asks the tree under test,
`python3 -B -c 'from aresos_control.chrome.exclusions import SETTING;print(SETTING)'` with
`PYTHONPATH=/workspace/control`, refuses an answer that isn't an absolute path ending in
`/chrome-excluded-sites.json`, and writes the same content, mode (0640) and owner (`root:1001`) there. The
`current` leg and every other Control Chrome job get `/var/lib/aresos-control/…` as before; the `ab7aba92` leg
gets `/etc/aresos/control/…`, as main's harness gave it. Ceilings, sample counts, `latency-targets.json`,
`latency-reference.json`, `latency-pair.sh` and the comparison are unchanged. Checked locally: the command prints
the old path over `git archive ab7aba92 control/aresos_control` and the new one over the checkout.

**Its test:** `CiInstall` in `control/chrome_tests/test_excluded_sites_placeholder.py` (3 tests): `prepare.mjs`
holds neither path nor the file name as a literal, and writes and chowns `excludedSites`; the exact command taken
from `prepare.mjs` prints `exclusions.SETTING` over the checkout and the old path over a copy of
`aresos_control` whose `SETTING` is the old one; the guard accepts both and refuses others. All three fail on
`prepare.mjs` before the fix.

### 1b done: `record_build.py` (item 4)

- `control/chrome/record_build.py` (stdlib only; not one of `build.py`'s inputs, the hash stays `2acd63cb…`):
  - `add --commit <40 hex> --shipped-at <YYYY-MM-DDTHH:MM:SSZ> [--expect <64 hex>] [--registry PATH] [--repo PATH]`:
    `git archive <commit> -- control` into a temporary folder (extracted with tarfile's `data` filter), runs that
    commit's `control/chrome/build.py` with `-I -B`, refuses a wrong `--expect` or an existing row for the commit
    with another hash, adds the row, keeps the newest three by `shipped_at` and writes atomically. `--registry`
    defaults to the repository's `builds.json`; the recorded run below used a scratch copy.
  - `check [--root PATH]`: validates `builds.json` (the planner's rules plus unique commits), then
    `os/manifest/release.json` and every `os/manifest/releases/**/*.json`. No `control` object: an info line. A
    `control` object must be exactly `{"source_revision": <40 hex>, "chrome_build": <64 hex>}` with
    `source_revision` equal to the manifest's `source_commit`; `release.json` needs an equal row; a release under
    `releases/` needs an equal row only if one is kept. Exit 1 with `FAIL:` lines, else `record_build check passed`.
- `control/chrome/ci/records/test_record_build.py` (21 tests, synthetic repositories and checkouts in temporary
  folders): `add` records what that commit's own `build.py` prints over its archived tree (the test archives and
  runs it itself); a commit with another `build.py` keeps its own algorithm, not the checkout's, and uncommitted
  changes don't count; wrong `--expect`; a repeated commit (unchanged file) and a conflicting row (refused); pruning
  to three, added out of order; a later commit with the same build; bad commits, times, `--expect`, a commit
  without `control/`; invalid registries; what `add` writes passes `qualify.plan`; the command line. `check`: with
  a row, without one, with an unequal one, no `control` object, malformed objects (in `release.json` and in
  `releases/`), `source_revision` against `source_commit`, `releases/**` (kept equal, kept unequal, missing,
  a subfolder), an invalid registry, a missing or non-object `release.json`, exit codes, and this checkout.
- `.github/workflows/control-chrome-records.yml`: pull requests touching `os/manifest/release.json`,
  `os/manifest/releases/**`, `control/chrome/builds.json`, `record_build.py`, `control/chrome/ci/records/**` or the
  workflow itself; `contents: read`, no secrets, `persist-credentials: false`, ubuntu-24.04's own `python3`; the
  tests, then `record_build.py check` on the checkout.
- `builds.json` is unchanged (`{"format":1,"builds":[]}`).

**The recorded run (run, on the laptop, into a scratch copy of `builds.json`):** 18c's head is reachable
(`origin/pkg/18c-image`).
```
$ python3 control/chrome/record_build.py add --commit 84f45c28fc20a21bf4882de8eb9fe83b94414798 \
    --shipped-at 2026-11-15T12:00:00Z --expect ccd0fd79190f492dbb0ca9889a288c0c004e0d46da3458e0f4446c80b5f5ce15 \
    --registry <scratch>/builds.json
{"commit":"84f45c28fc20a21bf4882de8eb9fe83b94414798","build":"ccd0fd79190f492dbb0ca9889a288c0c004e0d46da3458e0f4446c80b5f5ce15","shipped_at":"2026-11-15T12:00:00Z"}
record_build: recorded
```
exit 0. The same commit again: `already recorded; builds.json unchanged`, exit 0; with `--expect aaaa…`:
`refused: commit 84f45c28… hashes to ccd0fd79…, not the expected aaaa…`, exit 1. `qualify.plan` accepts the
scratch file. `check` on the checkout prints an info line for `release.json` and `releases/06.json`, `13.json`,
`27.json` (none has a `control` object yet) and `record_build check passed`.

### Local tests (laptop, Python 3.14.8)

- `python3 -B -m unittest discover -s control/chrome/ci/records -p 'test_*.py'`: `Ran 21 tests`, `OK`.
- `PYTHONPATH=control:control/chrome_tests python3 -B -m unittest test_excluded_sites_placeholder test_exclusions
  test_build test_extension_stores_nothing test_unit`: `Ran 19 tests`, `OK`.
- `CiInstall` on the `prepare.mjs` before the fix: `FAILED (failures=3)`.
- Three mutants of `record_build.py` (the checkout's `build.py` instead of the commit's; no pruning; `check` not
  comparing the build) each fail tests; not committed.
- `python3 -B control/chrome/build.py`: `2acd63cbc4ae0ec273e82f700a4a8afdfa7288f191706a848c9091b64636c6ec`
  (unchanged by 1b).
- **Not run locally:** `prepare.mjs` itself (no node, no container): the Control Chrome run below is its proof.

### CI runs (started by the push of `9302528d`; nobody waited for them)

1a's other runs on `265caa52` were green: Control Chrome qualification 43705955046, Control base 43705955015,
Control Mail 43705954960, Control boundary 43705954998.

| Run | Workflow | What to look for |
|---|---|---|
| 43716630045 | Control Chrome | `latency (plain)` and `latency (audit)` green (Part A); the 3 `CiInstall` tests in the python shards |
| 43716630095 | Control Chrome records | first run of the 21 tests and `check` on GitHub |
| 43716630048 | Control Chrome qualification | |
| 43716630066 | Control base | |
| 43716630101 | Control Mail | |
| 43716630097 | Control boundary | |

### What the code doesn't show (1b)

- `record_build.py` needs Python 3.12 or later (tarfile's `data` filter) and `git` on `PATH`. The commit must be
  in the clone: a release job with `actions/checkout`'s default depth of 1 has its own commit, so
  `add --commit "$GITHUB_SHA"` works there without fetching history.
- `add` runs the archived `build.py` as a script with `-I -B` in a temporary folder that is removed afterwards;
  nothing is written into the repository but `--registry`.
- The python shards of `Control Chrome` pick up `CiInstall` (every `control/chrome_tests/test_*.py`); nothing but the
  records workflow runs `control/chrome/ci/records/`.

### Left, in order

1. **Read the runs above.** If a latency leg still fails, its `tool.jsonl` artifact names the refusal.
2. **2** the install proof in the container. First thing: run `test_pack.py` and `pack-crosscheck.test.mjs` there.
   They have run nowhere on GitHub yet, and the node test has never run at all.
3. **3a, 3b, 4 (4b), 5, 6** as the brief's "Steps" lists them. 3a waits for PR #58 on `main`, the lead's go and
   the owner's answer to question 5.

### JUDGMENT-CALL (1b)

1. **Part A asks the runtime for its path** instead of writing the list at both paths. Two paths would leave a
   list at the old `/etc` path in every container of current code, so a `SETTING` moved back to `/etc` would
   still pass every browser run. Cost: `prepare.mjs` (an existing file under `control/chrome/ci/`, which the brief
   lets this package change only on item 1's path lines) changed on those three lines plus two imports, on the
   lead's instruction. The test went into this package's new `test_excluded_sites_placeholder.py`, not the existing
   `test_latency.py`, for the same rule.
2. **`add` archives `control/` only**, not the whole tree (about 980 MB at HEAD). Every version of `build.py` so
   far hashes only paths under `control/` (`ROOT/'control'`). A later `build.py` that reads outside `control/`
   would need the archived paths widened (one line).
3. **A repeated commit with an equal hash is a no-op** (exit 0, the first `shipped_at` stays), so a rerun release
   job passes; with another hash it is refused.
4. **A later commit with the same build takes over that build's row** (with its own commit and time). The planner
   (`qualify.plan`) refuses a build named twice, and a release that changed nothing under `control/` hashes the
   same as the one before. Refusing would fail every such release; two rows would break qualification. The older
   release then has no row, which `check` allows for `releases/`.
5. **A row older than the three newest is refused**, not added and pruned at once in silence.
6. **`--shipped-at` is strictly `YYYY-MM-DDTHH:MM:SSZ`** (no fractions, no offsets), and must be a real time.
7. **`check` is a little wider than item 4:** `source_revision` must equal `source_commit` in `releases/` too; it
   reads `releases/` recursively; a missing or non-object `release.json` and an invalid `builds.json` fail.
8. **The workflow** runs on pull requests against any base (no branch filter) and on its own path too;
   `pull_request` only, as item 4 says.
9. **`builds.json` layout:** one row per line, newest first, so the pinning pull request shows its row as one
   line; the empty file stays byte for byte as it is.

### PLAN-GAP (1b)

- **The latency pair wasn't in the brief's picture.** It runs the current harness over main's runtime
  (`ab7aba92`), so a path the harness writes and the runtime reads can't simply move in the harness. 1a moved the
  list as the brief said and the historical leg broke. Any later change of that kind (the policy or host paths in
  steps 2 and 3a, if CI's install follows them) meets the same.
- **"That commit's tree"** in item 4 would be about a gigabyte per `add`; see JUDGMENT-CALL 2.
- **Item 4 leaves open** a repeated commit and the same build under a new commit; decided in JUDGMENT-CALLs 3 and 4.
  `linux-aresos`'s release job should run `add` once per release and may rerun it.

## Step 1a

### Done

**1a. Packer, templates, pins** (item 1; `control/` only, nothing under `os/` or `docs/design/`)

- `control/chrome/packaging/pack.py`: `python3 pack.py EXTENSION_FOLDER OUTPUT_FOLDER` writes `extension.crx`,
  `update.xml`, `policy.json`, `native-host.json` (each 0644) and prints the public record as one JSON line
  (`id`, `version`, `public_key_sha256`, `crx_sha256`, `payload`). As a module: `pack.pack(folder)` returns
  `(files, record)`, `pack.write(folder, output)` returns the record; `pack.payload(folder)`,
  `pack.version(folder)` and `pack.render(id, version)` need only the standard library (for `check-image.sh`).
- Templates: `policy.json` is `ExtensionSettings` alone with the four keys; `update.xml` has the placeholder
  `EXTENSION_VERSION`; `native-host.json` is unchanged (it already had one origin and the fixed launcher).
- `control/chrome/ci/install/test_pack.py` (10 tests) and `pack-crosscheck.test.mjs` (the node cross-check).
- `control/chrome_tests/test_extension_stores_nothing.py`: the storage pin.
- `exclusions.py`: `SETTING` is `/var/lib/aresos-control/chrome-excluded-sites.json`, and the refusal has the
  brief's exact text. `prepare.mjs` lines 32 to 34 and `test_exclusions.py` line 13 follow the path. Nothing
  else in the service changed.
- `control/chrome/packaging/aresos-control-chrome.tmpfiles`: the two agreed lines with a comment.
- `control/chrome_tests/test_excluded_sites_placeholder.py`: the tmpfiles lines, the placeholder refused, the
  empty list accepted, the unit unable to write the folder, and the sweep over the 31 Chrome tools.
- `control/chrome/packaging/README.md`: the paragraphs item 1 names.

`python3 control/chrome/build.py` prints `2acd63cbc4ae0ec273e82f700a4a8afdfa7288f191706a848c9091b64636c6ec` at
`0fc242e7` (the brief expected it to change: `packaging/` and `exclusions.py` are hashed).

### What the code doesn't show

- **Signing uses Python's `cryptography`**, imported inside `_sign_with_fresh_key` only. The container of
  `control/chrome/ci/Dockerfile` (Debian bookworm) has `python3` without it: step 2's workflow installs the
  distribution package `python3-cryptography` (no pip). The calls used exist since `cryptography` 3.1.
- **Run `pack.py` without `-S`**: `-S` hides site-packages and with it `cryptography`. 18c's `os/build.sh` runs
  `build.py` with `-I -B`, which is fine for `pack.py` too.
- **`pack.py` never overwrites.** It refuses an output folder that already holds one of the four files. Bundles
  A, B and C each go into a folder of their own and are copied from there.
- **The image check needs a reader of its own** for `extension.crx` (the installed tree has no `pack.py`, and a
  packer shouldn't be checked with itself). `test_pack.py` has one (`fields`, `read_crx`) and the key-scan forms
  (`forms`: raw, hex, base64 and base64url at three alignments) for whoever writes the modulus scan in step 3a.
- **`os/tests` in step 3a** ("no installed file contains `EXTENSION_ID`, `UPDATE_URL` or `CRX_URL`") should also
  name `EXTENSION_VERSION`. `pack.render` already refuses to return a file with any of the four left in it.
- **How the key test works:** it wraps `rsa.generate_private_key` to see the keys the packer makes, then looks
  for p, q, d and the CRT numbers in everything returned, written or left behind. No key is a fixture anywhere.
- **The sweep's prepared operations** are written through the engine's own `reserve`, with the adapter's
  `prepare` replaced (it reads the page, which the gate never allows). The record has the engine's shape that way.
- In today's code the swept tools make **no** bridge call at all; the test allows `ack_steps` and `queued_steps`
  as the brief says and fails on any other, `configure` included.

### Local tests (laptop, 2026-11-15, Python 3.14.8, `cryptography` 50.0.0)

- `python3 -m unittest discover -s control/chrome/ci/install -p 'test_*.py'`: `Ran 10 tests`, `OK`.
- `PYTHONPATH=control:control/chrome_tests python3 -m unittest test_extension_stores_nothing
  test_excluded_sites_placeholder test_exclusions test_build test_unit`: `Ran 16 tests`, `OK`.
- `… -m unittest test_owner_confirm.Policy` (it reads the README): `Ran 7 tests`, `OK`.
- `test_excluded_sites_placeholder` on the code before the change: `FAILED (failures=29)`, as required.
- A packer changed to leave its key as a file in the temporary folder fails
  `test_no_private_key_in_what_is_returned_written_or_left_behind` (tried once, not committed).
- **Not run:** `pack-crosscheck.test.mjs` and every other `*.mjs` (no node on the laptop); the container; the
  full Chrome and Control suites (GitHub runs them). `test_committed`, `test_fault_surface`, `test_sites` and
  `control/tests`' `test_policy_sources`, `test_slim_policy`, `test_unit` were started locally and stopped
  unfinished (slow suites; the laptop is shared): take their result from the GitHub runs below.

### CI runs

Draft pull request **#76**. Started by its first push, on head `265caa52` (queued when this was written; nobody
waited for them, so the next agent reads the results first):

| Run | Workflow |
|---|---|
| 43705955018 | Control Chrome (runs the two new `control/chrome_tests` files and CI's install with the list at its new path) |
| 43705955046 | Control Chrome qualification |
| 43705955015 | Control base |
| 43705954960 | Control Mail |
| 43705954998 | Control boundary |

Nothing on GitHub runs `control/chrome/ci/install/` yet (step 2).

### JUDGMENT-CALL

1. **`cryptography` in the process, not OpenSSL through pipes.** The key lives only in the crypto library's
   memory, is never serialized and is freed after one signature. The pipe route would carry the key's PEM
   through a pipe and into Python bytes that can't be wiped. Cost: the container needs a distribution package
   (above). Changing it later touches one function and changes the build hash.
2. **The policy form** is `ExtensionSettings` alone, as the brief and the lead's answer 7 say. Whether the
   pinned Chrome installs from it is step 2's first case; the fallback in the brief stays open until then.
3. **The placeholder gate and its message** are the brief's, word for word.
4. **The named tools are called too.** The brief only names them. The test also requires each to answer `ok`
   and to reach no page, and requires the two tables to cover the tool list and `chrome_sites`' commands
   exactly, so the list can't go stale in either direction. Stricter than asked; easy to loosen.
5. **The storage pin is a little wider** than the four names: it also catches `navigator.storage`,
   `chrome['storage']` and a `storage` permission in the manifest.
6. **`pack.py`'s refusals beyond the brief:** an output folder that already holds a bundle file; a manifest
   version that isn't one to four numbers (it goes into `update.xml` as it stands); a file name that isn't
   UTF-8. The command also sets the core-file limit to zero, so a crash can't write the key to disk.
7. **The zip** is deflated as `install.mjs`'s is (what CI's Chrome has unpacked since package 17), with the
   time fixed at 1980-01-01 and mode 0644.

### PLAN-GAP

- **Branch name.** The brief's "Rules" say `pkg/18c-b-chrome-image`; the lead's handoff gave
  `pkg/18c-b-chrome`, which is what exists.
- **No runner for `control/chrome/ci/install/` until step 2.** The brief places the tests there so no existing
  suite picks them up, so on GitHub they first run in step 2's workflow.
- **The README names `record_build.py`** one step before it exists (item 1 asks for the sentence now).
- **Other texts still name the old `/etc` path:** `docs/control/TOOLS-HANDOFF.md`, `STATE.md`,
  `briefs/18c-image-test.md`, `reviews/20-chrome/` (history). All outside this package's paths; the lead's.
- **CI's list in the container** now goes to `/var/lib/aresos-control/`, which `prepare.mjs` makes as root
  (0755 by default). `Boundary.read` needs that; only the `control-chrome.yml` run shows it.

### The brief against the code

Nothing in item 1 turned out wrong. Checked: `exclusions.py` lines 8 and 23, `prepare.mjs` lines 32 to 34,
`test_exclusions.py` line 13 and `background.js` lines 869 to 875 are where the brief says; the extension uses
no browser storage; `python-shard.py` picks up every `control/chrome_tests/test_*.py`, so the two new test
files run in `control-chrome.yml` without a workflow change.
