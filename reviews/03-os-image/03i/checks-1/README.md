# 03i checks-only: 39 regressions pass before full attempt 1

[Run 39756899131](https://github.com/carlsenares/AresOS/actions/runs/39756899131),
source **`a4eaca14b2b7c8aaef8dd4b815b2abe73fce47e5`**, passed:

```text
Ran 39 tests in 0.783s
OK
Live hosted system manager passed: 437 unit files, 466 unit names
```

The workflow also passed Python compilation and Bash syntax checks without error
output. It skipped the image job; no image, container, disk or VM ran. The
suite's mocked offline-journal success/contingency messages are regression
output, not guest or hardware evidence.

[Selected output](verification-output.txt), [run metadata](run.json),
[job metadata](jobs.json), [artifact metadata (none)](artifacts.json),
[workflow logs](workflow-logs.zip), [redaction record](log-redaction.txt).
The original downloaded archive is retained byte-for-byte; no credential hash
was present, so no redaction was needed.
