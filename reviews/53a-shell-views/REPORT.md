# 53a report

## Done

- The OS helper speaks `aresos-shell/1.2`. Views authenticate with a separate session token, can list and open
  apps, and get their own launch events. The helper filters private variables from app and scope-tool processes.
- Pending and recorded launches use a client and request ID. Desktop replay history retains its existing disk
  format and quota. Named view histories survive helper restarts within their own quotas.
- Minor-2 desktops can publish a bounded multipart home. Views receive completed revisions, page through the home
  with its palette, and get the sorted IDs of running apps. The views' window ownership includes discovered apps
  independently of the desktop's rules.
- With a view connected, the helper preserves the compositor's focus when an app's last window closes on a known
  separate output. The known same-screen and unknown-output cases use the existing return.
- Restart reconciliation waits for discovery before settling a discovered launch's window. View-only metadata
  retained after uninstall stays out of the desktop's ownership rules. Views receive a new event when the first
  scan removes unknown houses from a home they could have already read.
- Section 5 of the laptop home design records the protocol and the package 23c handoff. The new shell 1.2
  fixtures are the shared examples for the next packages.

## Verified

Ran `python3 -m unittest discover -s os/tests -p '<module>.py'` for each module separately. Each printed `OK`.

| Module | Tests |
|---|---:|
| `test_aresos_shell` | 74 |
| `test_aresos_shell_discovery` | 36 |
| `test_aresos_shell_hardening` | 26 |
| `test_aresos_shell_home` | 13 |
| `test_aresos_shell_icons` | 43 |
| `test_aresos_shell_launch_hints` | 13 |
| `test_aresos_shell_protocol` | 21 |
| `test_aresos_shell_review_fixes` | 31 |
| `test_aresos_shell_review_fixes_2` | 16 |
| `test_aresos_shell_review_fixes_3` | 12 |
| `test_aresos_shell_review_fixes_4` | 11 |
| `test_aresos_shell_views` | 23 |
| `test_aresos_shell_windows` | 33 |
| **Total** | **352** |

`python3 -m py_compile os/config/usr/libexec/aresos-shell` and `git diff --check origin/main...HEAD` both exited 0 with no
output. The local shell suite also printed Python 3.14 resource warnings from the test harness.

`gh workflow run "OS image" --ref pkg/53a-shell-views -f checks_only=true` started the hosted checks at
`69ee2f4f`. `gh run watch 44324248782 --exit-status --interval 60` exited 0. The regression job printed
`Ran 1795 tests in 1578.765s` and `OK (skipped=4)`. The four existing cover tests require GTK 4 or the
headless labwc setup, which the hosted runner lacks. The live system manager check reported 437 unit files
and 478 unit names. The earlier run at `a83dc2e3` was canceled after the review fix landed.
[Hosted regression run](https://github.com/Ares-Empire/AresOS/actions/runs/44324248782).

The independent code and credential review found a blocking restart bug and two additional catalogue issues.
The targeted recheck of the fixes returned `SAFE`. [Code review](REVIEW-1.md) · [Targeted recheck](RECHECK-1.md).

The PR's Mod build, tests and JAR reproducibility check passed at `69ee2f4f`, as did the repo privacy check.
[Mod](https://github.com/Ares-Empire/AresOS/actions/runs/44324224132) ·
[Repo privacy](https://github.com/Ares-Empire/AresOS/actions/runs/44324224157).

No files over 500 MB were present in `.work/`.

## Not verified

The owner’s two-screen session needs a trial with the 23c supervisor, 53b mod publisher and 53c laptop home
running together. This helper-only package has no game tests, Gradle runs or screenshots.

## JUDGMENT-CALL

- The fifth concurrent view receives `busy`. Replacing a view with the same name is allowed at capacity. The
  desktop has 256 journal entries. Each view history has 32, and the four most recently used histories are kept
  with recency updated on recorded launches and replays. Eviction forgets replay history for that name.
- A home revision is nonempty text of at most 128 characters with no control characters. The 1.1 catalogue
  client only checks for a nonempty string. This cap leaves room for the complete palette and page data under
  the 64 KiB limit. Changing it would require updating the shared protocol and its validation.
- The helper starts a multipart upload over when the desktop reconnects, and keeps the last complete home
  until another completes. The publisher starts again with part 0, which keeps parts from different desktop
  connections from being combined.
- View events are sent by role. The view hello advertises catalogue, launch and 1.2 capabilities, while the
  desktop advertises and subscribes to its existing window and readiness capabilities. A home cursor has the
  same byte and shape limits as a list cursor and is issued for `get_home`.

## Known limit

The compositor does not identify a window's launch process. For overlapping starts of the same reviewed app,
the helper assigns the first matching window to the earliest launch still waiting. If the windows arrive out of order,
an affected opener can get the wrong window state or a timeout. Serializing those launches would add waits and
change launch timing for existing clients. The review recorded this as a should-fix, and it remains a
low-harm follow-up under decision 24.

## View errors on the wire

| Code | When |
|---|---|
| `malformed` | Invalid framing or fields, including the view name, capability lists and cursor shape |
| `message_too_large` | The input exceeds the line limit |
| `incompatible_version` | Incompatible major or hello capability requirements, or a view hello below minor 2 |
| `hello_required` | A known operation arrives before hello |
| `unknown_operation` | An unrecognized operation arrives before the connection has a role |
| `not_authorized` | Instance or credential checks fail |
| `busy` | A fifth distinct view connects |
| `invalid_state` | A repeated hello or an operation outside the view's allowlist |
| `invalid_cursor` | The cursor was issued for a different stream or helper, or its signature is invalid |
| `request_id_reused` | The view reuses a request ID for another app |
| `journal_full` | The view's replay quota has no reclaimable entry |
| `unknown_app`, `unavailable` | The app has no launch definition or its launch check failed |
| `launch_failed`, `no_window`, `launch_uncertain` | Starting failed, a matching window failed to appear, or a restart could not confirm launch |

## PLAN-GAP

- 23c passes the token to the helper and laptop home. Before saving `view_token`, 23c also needs to redact it
  from the runtime-field export in `os/ci/overlay/checks.py`. The task is recorded beside the handoff in the design.
- Section 5 now gives the home revision bound and asks views to refresh a home when catalogue changes affect
  visibility, since catalogue filtering can also change a page.

## Open questions

None for 53a. The physical 23c screen and focus trial remains.
