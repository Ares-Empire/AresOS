# Evidence: the owner update test leak

WSL (Ubuntu), 2026-11-10. Fresh clones of `main` (`6978dc3c`) and `fix/owner-update-test-leak` (`eee46789`). Run from the repo root:

```
python3 -m unittest discover -s os/tests -p test_owner_update.py
```

"Without namespaces" puts a stub `unshare` first in PATH. The stub prints the runner's message (`unshare: write failed /proc/self/uid_map: Operation not permitted`) and exits 1, as on GitHub's hosted runner.

| Branch | Namespaces | Result |
|---|---|---|
| main `6978dc3c` | without | `Ran 59`, `FAILED (failures=7, errors=111, skipped=27)`: exactly the hosted run 42815704308 |
| fix `eee46789` | without | `Ran 59`, `OK (skipped=136)` |
| fix `eee46789` | with (real `unshare`) | `Ran 59 tests in 306.337s`, `OK` |
| fix `698a6302` | hosted runner, run 42819274873 | `Ran 853 tests in 179.513s`, `OK (skipped=136)` |
