# Checks-only: static fallback and retained graph regressions pass

[Run 39748939881](https://github.com/carlsenares/AresOS/actions/runs/39748939881),
source `c547325`, passed **38 tests**, syntax checks and the real hosted manager
query (**437 unit files / 475 live unit names**). The image job was skipped:
no image, container, disk or VM ran. This is not VM acceptance.

The suite retains all earlier graph/parser assertions against the deferred
prototype and adds checks for static/generated content in both scopes,
active/running masked updaters, missing user managers and malformed live rows.
All offline-reader, channel and serial regressions remain enabled.

[Exact selected output](verification-output.txt), [run](run.json),
[jobs](jobs.json), [original workflow ZIP](workflow-logs.zip).
