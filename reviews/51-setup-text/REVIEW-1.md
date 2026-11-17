# 51: review 1 (Codex gpt-6-astra high, 2026-11-17)

Reviews `70219407`. Its should-fix and nit are fixed by the lead in the next commit.

- **should-fix — [os/config/usr/libexec/aresos-desktop:977](os/config/usr/libexec/aresos-desktop:977):** “click AresOS, then Create” is not valid for every creation failure. `HomeButton.createWorld()` creates AresHub before writing its contents; a later failure can leave an incomplete folder. Clicking AresOS then reports an error instead of offering Create. Fix: qualify the instruction: “Click AresOS. If Create is offered, click it; otherwise follow the error shown.” Update the assertion at `os/tests/test_aresos_desktop.py:2931` accordingly. Package 48’s report overlooks this distinction.

- **nit — [os/config/usr/libexec/aresos-desktop:883](os/config/usr/libexec/aresos-desktop:883), also line 1358:** The comment still says “title screen, the owner creates AresHub,” and the log says “title screen for setup.” Fix both to describe automatic first-start creation, with the title screen as a fallback.

The normal-path wording and forget-hub reply are correct and plain. The message assertions pass in memory and reject the old SETUP and forget-hub text. Full-suite evidence remains the lead’s reported **189 OK**; I did not rerun it. No files changed.

CHANGES-NEEDED