# Review 12: before the publish (f77273b7, 9393cbcb)

Codex gpt-6.2-sol, effort high, read-only, on a detached checkout at 9393cbcb (2026-11-19, before the one release_28 dispatch). The lead's prompt stated the safety bar and asked four questions: the source stop's build.sh allowance, setpriv's user switch, at most one publish only after build, image checks, first VM pass and diff, and the signature identity. Verbatim:

SAFE

No findings in `f77273b7` or `9393cbcb`.

**Review checks**

- `os/ci/release_diff.py:707` produces one accepted byte sequence from the merge-base blob. At `fba94b25`, each of the five old lines occurs once, and applying those replacements reproduces `HEAD:os/build.sh` byte for byte. The caller also requires a `100644` blob on both sides. Only this fix and the existing jar-pin renewal pass the source stop.
- `os/build.sh:275` runs the CLI as `nobody` with real, effective, and saved UID/GID switched and supplementary groups cleared. The reviewed invocation hands it a writable stdout under `/tmp` and exposes no inherited access that would let it write into `/usr`. A failed privilege drop, CLI exit, or usage check stops the build. [util-linux implementation](https://github.com/util-linux/util-linux/blob/v2.41.5/sys-utils/setpriv.c)
- `.github/workflows/os-image.yml:525` requires `release_28` on `pkg/42-release-28` with the other job selectors off. Ref concurrency serializes runs. `os/ci/rehearsal_guard.py:361` counts the current dispatch, rejects reruns and excess dispatches, and checks for prior publish attempts again before upload. With both caps at one and retained run history, at most one upload can proceed. [GitHub Actions concurrency](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency)
- `.github/workflows/os-image.yml:571` requires the build, image checks, first VM pass, and complete diff against verified release 27 before publication. `os/ci/publish.sh:19` independently requires the diff result to be `passed`.
- `os/ci/publish.sh:58` verifies and records the workflow identity ending in `os-image.yml@refs/heads/pkg/42-release-28`. It matches `os/ci/release28_walk.py:62` and `os/ci/verify_release.py:53` exactly. [Sigstore’s GitHub Actions identity format](https://docs.sigstore.dev/certificate_authority/oidc-in-fulcio/)

Seventeen focused tests, four shell syntax checks, and the in-memory publish-guard simulation passed. The live build, VM, and registry signing were outside this read-only review. No files changed and no workflow was dispatched.
## The lead's handling

No findings. The branch is pushed and release_28 dispatched once (publish-28, cap 1).
