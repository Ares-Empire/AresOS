# Package 06 image evidence

`image-6/` preserves evidence from the successful image job in
[run 39796347427](https://github.com/carlsenares/AresOS/actions/runs/39796347427),
source `01aae1e38ec11356677f526692783c14b89a1d4d`. Both fresh VM passes succeeded,
including the daily account's locked password and fixed UID/GID, strict
audit/canaries, recovery/power checks and actual offline logind proof. The
corrected release was published privately and signed with GitHub OIDC.

`image/` is historical evidence from the earlier successful image job in
[run 39774351695](https://github.com/carlsenares/AresOS/actions/runs/39774351695),
source `3cc9df51bc528c9683696098023486d49a5832c1`. Both fresh VM passes succeeded,
including the strict audit/canaries, recovery/power checks and offline logind
proof. That image lacks the later native sysusers fix and is superseded; its
failed switch attempts do not qualify a handoff.

`preflight/` records the final runtime source's successful 50-test checks-only
run and official ISO checksums. Original final-image artifact bytes and GitHub
digest/size metadata are retained under `reviews/06-image-release/artifacts/`.
Expanded `.txt` display copies remove trailing whitespace and normalize line
endings; the ZIP preserves the original bytes, including raw console logs.

The current registry reference is in [release.json](../../release.json). Its
`switch_qualification` is failed. Historical `switch-6/` records successful stock
login, private signature/pull/staging followed by the stock reboot timeout.
[06b evidence](../06b/README.md) supersedes that failure point: reboot into the
published digest passed, then Homebrew remained executable by the daily user.
Qualification stopped on that product failure before tty3 recovery or rollback.
In each image directory, `image-oci-manifest.json` is the local
release manifest; `published-manifest.json` and `published-digest.txt` identify the actual GHCR
manifest. The VM overlay has its own manifest/digest and was never published.

Screenshots and passive console logs are preserved under
`reviews/06-image-release/`. No disk, credential file, builder configuration,
raw authentication transcript or binary journal is retained.
