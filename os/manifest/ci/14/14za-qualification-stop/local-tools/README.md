# Local watcher evidence; never a workflow component

`executed-sources.zip` preserves exact executed source/log bytes, including
original line endings. `source-archive.json` binds every member and archive hash.
The pre-dispatch control test is under `pre-dispatch/`; its bytes match the
pre-dispatch replay receipt. The repeatable three-test version was a later
isolation fix only. Python and txt files here are LF-normalized reading copies.
No watcher/controller executable changed after dispatch. No push occurred.

For replay, restore the archive files under `.work/14/` from the repo root and
copy `probe-run-identity.json` to `.work/14/run-40560134727/run.json`. No actor,
credential or private console is required. Run
`python -B .work/14/test_14za_watcher.py` and
`python -B .work/14/test_14za_control.py`. Controller tests stub every API/POST and
write boundary and prove an existing nonce prevents another POST. These files
are local-tool provenance, never scripts imported by the Actions workflow.
