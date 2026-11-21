# Review 11: the cut's bytecode fix (69a553e1)

Codex gpt-6.2-sol, effort high, read-only, on a detached checkout at 69a553e1 (2026-11-19). The lead's prompt stated the safety bar. Verbatim:

SAFE

1. **NIT** `os/tests/test_release28_control.py:294` — The static test catches a missing `-B` on all five current direct `python3` calls. It misses the Chrome build-ID subprocess at `os/build.sh:139`, so removing that child’s `-B` would still pass. It also misses other interpreter spellings such as `python3.14`. The launcher assertion at `os/tests/test_release28_control.py:301` catches the old bare root command but would miss one prefixed with `env`. These are coverage gaps. The current calls are safe.
2. **NIT** `os/tests/test_release28_control.py:279` — `unittest.main()` runs before the new class is defined when the file is executed directly. I confirmed that direct execution with the class filter ran zero tests. CI uses discovery, which found and passed both tests.

**Review checks**

- **Root imports.** All five direct Python calls use `-B`, and the Chrome build-ID child passes its own `-B`. The pinned wheel-only pip install skips source builds and pip’s byte compilation. The CLI wrapper starts Python with `-I -S`, so startup imports can occur before `sys.dont_write_bytecode` is set. In this branch that interpreter runs as `nobody` and lacks write access to the base Python directories. `os/build.sh:68`, `os/build.sh:139`, `os/build.sh:274`, `control/packaging/aresos:3`, `control/launch.py:38`. [Python command-line reference](https://docs.python.org/3.14/using/cmdline.html#cmdoption-B) · [pip install reference](https://pip.pypa.io/en/stable/cli/pip_install/)
- **Shipped files and records.** `compileall` explicitly writes checked-hash bytecode under the vendor tree. A read-only probe captured identical checked-hash bytes with import caching enabled and disabled. The install map, modes, hashes, wheel records and Chrome build-ID inputs are unchanged. `control.json` still records the build’s source revision, so that field reflects the new commit as usual. The dry-run cap rises to six and the publish cap remains zero. `os/build.sh:75`, `os/build.sh:213`, `os/build.sh:230`, `os/build.sh:249`, `os/ci/rehearsal-packages.json:183`. [Python `compileall` reference](https://docs.python.org/3.14/library/compileall.html)
- **Help as `nobody`.** Root can mask a missing read or traverse permission. Failing the build for such a permission regression is correct because ordinary users need to run the CLI. The installer gives the wrapper and directories `0755` and the Python files, `proxy.json` and generated help `0644`. The launcher checks the files’ ownership, and its owner-UID check applies only to proxy mode. CLI help exits during argument parsing before it opens a service connection or accesses the owner’s home. `runuser` also needs the base account and a working PAM session. `os/build.sh:93`, `os/build.sh:185`, `os/build.sh:220`, `os/build.sh:274`, `control/launch.py:16`, `control/launch.py:44`, `control/aresos_control/cli.py:11`, `control/aresos_control/cli.py:33`. [util-linux `runuser` manual](https://man7.org/linux/man-pages/man1/runuser.1.html)

Shell syntax, both discovered bytecode tests, and the dispatch-cap test passed. The image build and release diff remain unverified. No files were edited.
## The lead's handling

- NIT 2 fixed: the unittest.main() guard moves to the end of test_release28_control.py, so a direct run finds the new class.
- NIT 1 stays a known limit: the static test covers the Control branch's direct `python3` calls; the Chrome build-ID child passes its own `-B` (build.sh), other interpreter spellings and an `env`-prefixed launcher call are not matched. The release diff itself is the real guard: any rewritten base bytecode is an unexplained difference that stops the dry run and the publish.
