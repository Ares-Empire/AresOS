# Checks-only: new Cockpit fixture fails on an empty user-unit tree

[Run 39755103185](https://github.com/carlsenares/AresOS/actions/runs/39755103185),
source `59253df`, printed `Ran 39 tests in 0.842s`, `FAILED (errors=1)`.
The new fixture left its user-unit tree empty, so real
`systemctl --root=... --global list-unit-files` returned 1. This is a fixture
error, not evidence against the mask or permission to skip the user audit.
Add a harmless user unit while retaining every assertion; the next
[checks-only run](../checks-3/README.md) passes. The image job was skipped.

[Exact selected output](verification-output.txt), [run](run.json),
[jobs](jobs.json), [original workflow ZIP](workflow-logs.zip).
