# Local watcher evidence; never a workflow component

These are the exact local files and test logs. No push occurred in14za.
Original paths were `.work/14/<filename>`; replay uses that location from the
repo root, with the retained `.work/14/run-40560134727/run.json` fixture. The
seven watcher tests use only its public run identity fields. Controller tests
stub every API/POST/file-write boundary; the repeatable three-test version
isolates the actual nonce and proves an existing nonce prevents a second POST.
The original two-test version executed before dispatch is preserved separately
and matches the pre-dispatch local-replay hash. The later repeatability change
changes test isolation only. No controller, watcher, runtime or workflow change
after dispatch. Archives are provenance, not scripts the workflow executes.

For an isolated replay, restore these filenames under `.work/14/` and place
`probe-run-identity.json` at `.work/14/run-40560134727/run.json`. The minimal
identity fixture suffices; no actor metadata, credential or private console is
needed. Run `python -B .work/14/test_14za_watcher.py` and
`python -B .work/14/test_14za_control.py`. API/POST boundaries stay stubbed.
