Reviewed **5335f8a4**, read-only. I found one blocking cleanup issue and one nonblocking harness issue.

1. **Blocking — the automatic timeout bypasses finalizer restoration.**  
   [update.sh:47](C:/Users/pab/AresOS-27-review/os/release/update.sh:47) relies on its Bash `EXIT` trap. But [owner.py:250](C:/Users/pab/AresOS-27-review/os/owner-tools/owner.py:250) runs that shell through `subprocess.run(..., timeout=1800)`. On timeout, Python kills the shell with SIGKILL; its trap cannot run, and the separate `bootc` process is not necessarily terminated. [CPython implementation](https://github.com/python/cpython/blob/v3.14.0/Lib/subprocess.py).

   A slow or stuck laptop update can therefore return STOP with both finalizers still unmasked and staging potentially continuing. This is an explicit application timeout, not an unavoidable power-loss scenario. It breaks the accepted all-or-nothing failure behavior; I am **not** claiming it necessarily destroys R13.

   **Fix:** keep a supervisor alive through timeout/cancellation, terminate and reap the transaction, reconcile whether staging completed, and restore the removed masks when staging failed. Test timeout and interruption through the real runner, then regenerate the bundle and fingerprint pins. Merely adding a TERM trap does not fix Python’s SIGKILL path.

2. **Should-fix — the util-linux check accepts unreviewed version suffixes.**  
   [owner_login.py:41](C:/Users/pab/AresOS-27-review/os/ci/owner_login.py:41) accepts `2.41.6-rc1` and `2.41.6-custom` as `2.41.6`: its boundary excludes only digits and dots.

   This cannot change the laptop’s pinned image, so it is **not blocking for laptop safety**, but it weakens the harness’s claimed exact-version qualification.

   **Fix:** match the complete version token, allowing only the documented trailing feature-list format, and add suffix rejection tests. Upstream `login.c` and `agetty.c` are unchanged between the two approved releases. [Upstream comparison](https://github.com/util-linux/util-linux/compare/v2.41.5...v2.41.6).

The other targeted checks look sound:

- The bundle fingerprint is **`daa31228…`**. All 15 payload files match their sources and hashes; the release copies and ten recorded source bindings agree.
- Verification uses the exact image digest, exact workflow identity and GitHub OIDC issuer. The history prevents an older bundle from updating a newer, unknown release.
- Staging uses `--retain`; subsequent checks require the running deployment and retained deployments to remain unchanged. Pinned stock remains separately protected.
- Disk checks require Windows to be unmounted and Linux’s root, boot and EFI mounts to belong to the selected AresOS disk. I found no new Windows-disk write path.
- No apparent secrets or owner-specific serials, GUIDs or personal email addresses appeared in the added file content.
- `terminal_path`’s bounded retry still requires an actual result from the daily user with the correct PATH. It records the retry and preserves a screenshot; it does not manufacture success.

**Run 6 is plausibly a VM artefact, but the precise cause remains unproved.** The harness adds `console=ttyS0`; the laptop does not have that console, and R27 changes neither the kernel nor systemd package. Earlier runs also booted this same R27 image. However, systemd’s terminal-size probe normally times out after **333 ms**, so the last `ESC[6n` alone does not explain a five-minute stall. The watchdog warning makes VM timing trouble plausible; the evidence establishes a serial-login timeout, not conclusively a whole-system hang. [systemd source](https://github.com/systemd/systemd/blob/v259/src/basic/terminal-util.c).

Hash/source checks and `git diff --check` passed; the worktree remains unchanged. I did not rerun builds or VM tests. Run 7 remains in progress; the later evidence/rebind/report check remains separate as requested.

CHANGES-NEEDED