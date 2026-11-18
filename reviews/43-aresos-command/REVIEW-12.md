# Package 43, review 12: step 4, the guides (Codex gpt-6-astra, high, read-only, on ee738d1d)

No must-fix findings. Two should-fix findings:

- **Should-fix — [docs/EMERGENCY.md:67](/var/home/ares/AresOS-43-aresos-command/docs/EMERGENCY.md:67):** Extending this paragraph to all `aresos` STOPs conflicts with INSTALL’s exceptions. **Another owner command is running** means wait, ask and retry without export; a stale-title refusal permits `aresos title`, then renewed restart approval. The card instead directs export and forbids any other command or second try. Name these exceptions or link them before the general STOP rule.

- **Should-fix — [docs/EMERGENCY.md:26](/var/home/ares/AresOS-43-aresos-command/docs/EMERGENCY.md:26):** The new **was not applied** warning renders inside the preceding **Any other result** bullet because no blank line ends the list. I confirmed this with the installed Markdown renderer. Someone following the dedicated **was not applied** branch could miss the immediate-repeat warning. Put it in that branch or make it a separate paragraph outside the list.

- **Note — [docs/INSTALL.md:286](/var/home/ares/AresOS-43-aresos-command/docs/INSTALL.md:286):** Section 6’s required content is present, including the owner’s restart and rollback approvals, console-only login/layout, and N4/N7 decisions. The console portion is unchanged after accounting for the obsolete Windows-box position wording and moved newest-command sentence.

- **Note — [os/tests/test_aresos_command.py:129](/var/home/ares/AresOS-43-aresos-command/os/tests/test_aresos_command.py:129):** Guide/TABLE equality passes. In-memory mutations of labels, missing rows, duplicates, refused commands and ordering all fail. The inline-command rules remain intact. All four refreshed binding hashes match.

- **Note — [reviews/43-aresos-command/PROGRESS.md:870](/var/home/ares/AresOS-43-aresos-command/reviews/43-aresos-command/PROGRESS.md:870):** One-page/phone fit remains unverified. The card grew from 2,279 to 2,411 whitespace-delimited words; almost unchanged source-line count does not establish rendered fit.

Verification: `test_owner_equality` ran 12 tests with 3 environmental errors; `test_owner_path` ran 48 with 14 environmental errors; `test_aresos_command` ran 17 with 3 environmental errors and the expected word-set failure. Temporary-file errors are sandbox limitations. The intentional CLI gap and step-5a bridge placeholder are not findings. No files changed.

CHANGES-NEEDED