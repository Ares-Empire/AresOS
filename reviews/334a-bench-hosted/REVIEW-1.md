# Review 1: 334a, the bench's hosted pass

**Verdict:** CHANGES-NEEDED

## Must fix

1. **Guest launch credentials can reach the artifact.** `os/ci/bench/agent.py:148` runs `exec` as the desktop user, who can read the runtime file containing the launch nonce. The driver writes the command output into evidence, and the filter at `os/ci/bench/evidence.py:12` accepts both a bare nonce and the `ARESOS_LAUNCH_NONCE=…` form. I confirmed both misses with a synthetic value. Keep the actual credential out of exported guest output and add regression cases for both forms.
2. **The health probe can take over the desktop connection.** The `hello` at `os/ci/bench/agent.py:134` authenticates as the desktop. The real helper installs that connection as its desktop, clears publishing state, and closes any previous desktop connection at `os/config/usr/libexec/aresos-shell:3446`. The first-start fixture has no game connection to displace, so the hosted pass misses this. Use a bench-provisioned, non-displacing authenticated identity for `list_apps` and verify that an existing desktop connection survives the probe.
3. **A bench dispatch can block later releases on a guarded ref.** The workflow names a plain bench dispatch `OS image check build (bench, never published)`. Package 42’s resolve preflight rejects that title, and subsequent guards also reject it when scanning branch history. I reproduced the stop with a completed bench run in a mocked history. This applies when a ledger-managed ref carries the new workflow. Keep bench dispatches off those refs or account for their rejected runs separately, preserving the existing mode caps and B331 authorization. A job guard alone leaves the run in history.

## Should fix

- Give `qemu-img` and QEMU an explicit environment allow-list. Both inherit the runner environment at `os/ci/bench/driver.py:39` and `:48`, contrary to the design. The reviewed VM path does not pass an Actions token into the guest.
- Strengthen `os/tests/test_bench_dispatch.py:37` to check the effective job conditions and the condition on the specific bench upload step. The current substring checks can pass with a bypassing `||` or with the upload gate attached to the wrong step.

## Known limits

- Ref plus SHA is a sound concurrency key for disposable development runs. It isolates the clean and negative commits and preserves the existing groups for non-bench modes. Same-ref, same-SHA dispatches share one pending slot, so a newer pending run can replace an older one. [GitHub Actions concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
- The screenshot gate checks file type, size, and bytes. It has no OCR.

## Checked

- Traced the release build contexts and publish tags. The bench layer has a separate local tag, and `os/.containerignore` keeps the new bench sources, tests, and generated test bytecode out of release layers. The installed audit script remains available. Package 13 and the other release, rehearsal, and switch jobs exclude bench; the workflow runs the dispatch validator before image tools. Both hosted bench runs scanned 134 plain-image layers and refused the planted file hidden by a later layer. [Clean run](https://github.com/Ares-Empire/AresOS/actions/runs/45080827587)
- Traced the upload gate and VM output. The gate requires allowlisted regular files within the size caps and a successful token scan. QEMU serial output is discarded, and job logs receive structured step results. The guest boots with `-nic none`; the driver checks loopback-only status and a new boot ID. `run.json` binds the dispatched SHA, committed script digest, image label, and guest revision. Existing logs confirm health on both boots and that the negative run passed image checks before failing at helper health. [Clean run](https://github.com/Ares-Empire/AresOS/actions/runs/45080827587) · [Negative run](https://github.com/Ares-Empire/AresOS/actions/runs/45080853329)
- The German keyboard profile is a sound bench-only choice. It supplies the layout the launcher requires and matches the installer’s `de` settings. The pending-rebind workflow row matches the checkout bytes; `check-build.sh` is outside the active bindings. The diff leaves `rehearsal_guard.py` alone and contains no R29 job edits.
- The tests exercise the production parser, evidence checker, and layer scanner. All four dispatch tests passed locally. Seven cases across the other three modules hit the read-only filesystem when creating fixtures. Existing hosted logs show all 14 bench tests and the normal regression job passing. Shell syntax and `git diff --check` passed locally. I ran no workflow, VM, container, or sudo command. [Hosted regressions](https://github.com/Ares-Empire/AresOS/actions/runs/45080899317)
