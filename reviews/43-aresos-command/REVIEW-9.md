# Package 43, review 9: step 3 (Codex gpt-6-astra, high, read-only, on 82bd71bd)

- **should-fix — [os/ci/image-checks.sh:805](/var/home/ares/AresOS-43-aresos-command/os/ci/image-checks.sh:805): The image checks can accept a broken desktop update branch.** They check the dispatcher’s shebang and two refusal paths, but neither its complete installed bytes nor its offered-command argv. An in-memory mutation making the desktop command `/var/lib/ares/at update` leaves both refusal probes unchanged; Control’s help checks also bypass that branch. Compare the installed dispatcher against the tested checkout source, or test its offered plans and intercept exec inside the image. The refusal probes also infer “nothing ran” from output/status rather than observing execution.

- **note — [os/config/usr/bin/aresos:1](/var/home/ares/AresOS-43-aresos-command/os/config/usr/bin/aresos:1): Environment preservation has a Python-startup exception.** With an empty environment or `LANG=C`, Python adds `LC_CTYPE=C.UTF-8` before `main()`. I reproduced this through the real handover with `/usr/bin/env` as the target. The tests compare supplied dictionaries or one marker, so miss it. Control subsequently clears its environment, making this a contract/documentation discrepancy rather than an observed Control failure.

No must-fix defect found in the dispatcher or helper. The nine commands, `update` → `newest`, refusals, sudo environment, quoted askpass arguments, and wrapper installation match the design. No password logging or storage was introduced.

Verification: command tests ran **14: 12 passed, one expected word-set failure, one environmental temporary-directory error**. Both diff tests encountered environmental temporary-directory errors. Seven in-memory regressions were caught by the existing unit tests. Shell syntax and whitespace checks passed. No files changed; no sudo, window, image build, or deployment ran. The two documented PLAN-GAPs are not findings.

CHANGES-NEEDED