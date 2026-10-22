# Full attempt 1: failed before disk build

[Run 39736454217](https://github.com/carlsenares/AresOS/actions/runs/39736454217)
on `21d64fdc07db5c1b7b665652cd7203569fa5bee5` passed 34 regressions,
syntax/signature/tool/package checks, release build and the 817-unit build audit.
The new preflight's `/opt/parser_preflight.py` bind mount failed because its
parent path did not exist in this Bazzite container. No systemd inventory,
overlay/isolation check, disk or VM ran. Counted as full attempt 1.

[Exact selected output](verification-output.txt), [original workflow ZIP](workflow-logs.zip),
[original evidence ZIP](evidence.zip), [run](run.json), [jobs](jobs.json),
[artifact metadata](artifacts.json), [metrics](metrics.json), [provenance](provenance.json).
The ZIP retains all 31 evidence files unchanged, including the empty console.
