# Package 43, review 10: fix check of review 9 (Codex gpt-6-astra, high, read-only, on 6662c152)

Two should-fix findings remain:

- **Environment precedence changes** — [aresos:78](/var/home/ares/AresOS-43-aresos-command/os/config/usr/bin/aresos:78). The dictionary construction keeps the **last** duplicate name; `os.environ` keeps the **first**. Reproduced with raw `execve` environment entries `DISPLAY=` followed by `DISPLAY=:2`: previously `check` refused; now it selects sudo and passes `DISPLAY=:2` into the clean environment. Control handover also collapses duplicates, so it is not literally byte-exact. Preserve the existing effective-value semantics and add a duplicate-name regression.

- **Caught audit exceptions let refusal probes pass** — [image-checks.sh:818](/var/home/ares/AresOS-43-aresos-command/os/ci/image-checks.sh:818). Injecting an exec attempt inside `try/except Exception: pass` makes the complete Bash refusal block exit **0** and print its PASS marker. The hook blocks execution during testing, but the dispatcher swallows the evidence and prints its normal refusal. Without instrumentation, that exec would run. Record attempts independently and fail after dispatcher termination, even when its code catches the exception; add this mutation to the tests.

The archive comparison passed targeted checks: it rejects changed bytes—including review 9’s mutated update mapping—incorrect ownership/modes, link members, missing/extra/duplicate members, and reordered members. Removing the byte assertion accepts the mutation.

Real-shebang probes using memory-backed files preserved empty, `LANG=C`, ordinary, and non-UTF-8 environments. Reverting to `os.environ` failed the locale regressions. Ordinary exec, shell, and subprocess mutations were rejected by the refusal checks.

No finding in `6e2b03d4`: installation, wrapper header, and integration invocation consistently use `/usr/libexec/aresos-control/cli`.

Verification: command tests reported 12 passes, the intentional word-set failure, and two environmental errors; diff tests had two environmental errors; image tests had two passes and 16 environmental errors. Temporary-directory restrictions caused those errors. Shell syntax and whitespace checks passed. No image/container integration ran; no files changed.

CHANGES-NEEDED