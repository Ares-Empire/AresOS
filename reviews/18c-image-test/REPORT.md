# 18c: unit network lines and B1 only

**run — PermissionRequest result:** an allow hook approves the managed ask interactively at both user and managed level, in normal and skip-permissions mode, without an owner answer. Each of the four cases called its hook once and produced one receiver arrival. This matches 18d's print-mode approval result on native Claude Code **2.1.319**. Evidence: [run 43444623151, attempt 1](https://github.com/Ares-Empire/AresOS/actions/runs/43444623151), `interactive-console.txt` lines 9, 10, 17–19; unchanged print checks printed `PRECEDENCE_OK cases=24` at 14:39:37.6118819Z.

**run — observed screens in that run:** normal/user, normal/managed and skip/managed briefly displayed the permission prompt while the hook ran; skip/user had no captured prompt frame. None required an answer. Full request, screen, hook and receiver evidence is in artifact `control-boundary-43444623151-1`, under `terminal/`; [one completed managed-hook screen](screens/permission-managed-approved.txt) is retained here.

**read — pin:** `control/boundary/interactive-permission-request-expected.json` pins each case to `hook_calls: 1`, `send_arrivals: 1`, `owner_answers: 0`. `interactive_suite.py` records the actual `prompt_shown` boolean separately. A brief asynchronous render is timing dependent: in [run 43444128696](https://github.com/Ares-Empire/AresOS/actions/runs/43444128696), normal/user had no captured prompt, whereas it did in 43444623151. Pinning that frame observation would make the same approval outcome flaky. The original print-mode pin is unchanged.

## Done

- **read — `control/packaging/aresos-toold.service`, `control/tests/test_unit.py`:** the approved comment and `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6` replace the former two network directives; no `IPAddressDeny` remains. Every non-comment `[Service]` directive is pinned, including order and the other sandbox properties. Both files compare byte for byte with the read-only PR #27 service and its `chrome_tests/test_unit.py`.
- **read — `interactive_driver.py`:** reusable 120x40 tmux terminal control with rendered captures, named conditions, deadlines, text-matched answers, and a continuously visible dialog before input. Numeric shortcuts may submit immediately or only select; the driver observes that distinction. The bypass warning uses its observed unnumbered options. Each action has a saved screen and JSON record.
- **read — `interactive_model.py`:** scripted streaming Messages double, separate from `native.py`. A step either uses a fixed fixture approval or prepares and copies `data.approval` unchanged. Only a new scripted owner marker selects another send. Stop continuations get plain text and are recorded with their complete requests.
- **read — `interactive_suite.py`, Dockerfile, workflow:** all 17 B1 cases run in a separate networkless container on GitHub's runner using the existing locked native binary. Every case allows preparation at user scope. DAA retains settings for send 2 and the fresh CLI for send 3. The fixture receiver, hook events, native transcripts, per-turn settings and model requests are saved. The new step also runs after an independent sandbox failure; that failure still fails the job. No workflow permission was added.
- **read — `test_interactive.py`, boundary README, this review folder:** six quick parser/model/input-guard regressions, driver documentation, representative rendered screens, and `verify-evidence.py` for independent artifact checks.
- **run — scope audit:** `git diff 2558e25a -- os control/boundary/native.py control/boundary/precedence.py control/boundary/permission-request-expected.json` printed nothing. No Part A, B2 or C was built. No production Control Python code, existing tests, generated files, settings or Python/npm dependency locks were edited.

## Verified

**run — local, unprivileged, no containers or VMs:**

| Command | Result |
| --- | --- |
| `python3 -m unittest discover -s control/tests -p test_unit.py -v` | One test, `OK` |
| `python3 -m unittest discover -s control/boundary -p test_interactive.py -v` | Six tests in 0.003s, `OK` |
| `python3 -m py_compile control/boundary/interactive_model.py control/boundary/interactive_driver.py control/boundary/interactive_suite.py` | Exit 0, no output |
| `git diff --check` | Exit 0, no output |
| `cmp` of the service and unit test against the authorized read-only Chrome worktree | Both exit 0, no output |
| `git hook run pre-push -- origin https://github.com/Ares-Empire/AresOS.git </dev/null` | Exit 0, no output; pushes also succeeded without bypassing hooks |
| `python3 reviews/18c-image-test/verify-evidence.py .work/18c/green-artifacts/control-boundary-43444623151-1` | `EVIDENCE_CHECK_PASS cases=17 arrivals=7 hooks=6 bytes=26417301`; also checked 21 native tool results, saved choices, question ordering and persisted DAA settings |

**run — Control base:** [43440235125](https://github.com/Ares-Empire/AresOS/actions/runs/43440235125) passed. Its log printed `test_service_sandbox_and_launch_are_exact (test_unit.InstalledUnit.test_service_sandbox_and_launch_are_exact) ... ok`, `Ran 305 tests in 191.953s`, and `Control base suite PASS` at 14:14:38Z. These are lines 575, 578 and 587 of `.work/18c/base-43440235125.txt` downloaded with `gh run view --log`.

**run — complete boundary development head `1e856ed3`:** [43444623151/1](https://github.com/Ares-Empire/AresOS/actions/runs/43444623151) was green, including the unchanged sandbox and print suites. Interactive step: 57 seconds; whole job: 152 seconds. All entries below are exact `INTERACTIVE_CASE_PASS` lines in its `interactive-console.txt`:

| Case | Lines | Prompts observed | Arrivals | Hook calls |
| --- | --- | --- | ---: | ---: |
| Normal Yes | 2 | Yes; question first | 1 | 0 |
| Normal / skip No | 3 / 11 | Yes | 0 each | 0 |
| User / project / local allow, normal | 4–6 | Yes | 0 each | 0 |
| User / project / local allow, skip | 12–14 | Yes | 0 each | 0 |
| PreToolUse allow, normal / skip | 7 / 15 | Yes | 0 each | 1 each |
| DAA, normal / skip | 8 / 16 | All three sends, including restart | 1 each, only send 1 | 0 |
| PermissionRequest user, normal / skip | 9 / 17 | Flash / no captured frame; no answer | 1 each | 1 each |
| PermissionRequest managed, normal / skip | 10 / 18 | Flash; no answer | 1 each | 1 each |

**run — required PASS lines:** line 19 printed `CONTROL_PERMISSION_REQUEST_RECORDED` with all four outcomes; line 20 printed `CONTROL_INTERACTIVE_ASK_PASS cases=17`. In the full `gh run view --log` capture those are lines 2528 and 2529, at 14:40:48.2845077Z and 14:40:48.2846424Z. Artifact size was 26,417,301 extracted bytes, below 180 MB. [Yes](screens/normal-yes.txt), [DAA send 2](screens/daa-second-send.txt), and [warning](screens/bypass-warning.txt) captures are retained here.

**read — final-head verification procedure:** this report is committed before the final-head runs. The exact final SHA, both boundary attempts, their PASS lines, artifact cross-checks and final Control base result are recorded in the [PR #43 acceptance addendum](https://github.com/Ares-Empire/AresOS/pull/43). This avoids changing the tested head just to append run IDs. The development run above is evidence for the measured behavior, not a substitute for those two final-head executions.

**run — failed development attempts, never counted as passing:**

| Run | Failure / discovery |
| --- | --- |
| 43438859926 | Existing helper-absent VSOCK mutation got `ECONNRESET`; interactive step had not run |
| 43439542838 | Native No interrupted instead of requesting the model again |
| 43440234513 | DAA send 2 showed the ask; input confirmation did not complete |
| 43440947883 | No's numeric shortcut submitted before a selected frame could be captured |
| 43441617939, 43442384540 | DAA send 2 still showed the ask; immediate confirmation was refused; literal return alone did not fix it |
| 43443214193 | Stable input fixed DAA; a managed PermissionRequest hook approved while its transient prompt was being observed; existing VSOCK failure also occurred |
| 43444128696 | All normal cases passed; skip warning had unnumbered choices |

## Not verified

- **read — scope, brief B2:** real systemd networking, installed launchers/files, Mail, password privacy, service-down reminders, `gh`, SELinux, the image and VM cases remain for Part A/B2. VM steps and measured VM times: **not run**. The update from release 27 and live laptop/phone/Remote Control tests remain unverified. No real model or account was used here.
- **read — fixture limitation:** the boundary MCP app has no preparation and the notification stand-in reports empty pending work. B1 exercises fixed approvals and prompt precedence. It does not prove the real service's approval binding or Stop reminder. The model supports preparation and Stop continuations; the former's unchanged-copy path and continuation distinction were unit tested.
- **assumed — future guest:** the installed-file cases should match these container outcomes, but only B2 can establish that. A different guest result remains the brief's stop condition.

## JUDGMENT-CALL

- **read — product:** no new owner-facing choice. The only product change is H1's already agreed network directive, copied exactly. Image defaults, accounts, folders, enabled units and release choices were not made in this run.
- **read — test choice:** normal means explicit `--permission-mode default`, because discovery on this pinned binary displayed auto mode when no mode flag was given. This matches 18d's observed normal print mode. Auto mode is outside this table; changing that coverage later requires another case, not a product change.

## PLAN-GAP

- **run — asynchronous PermissionRequest UI:** a prompt frame can appear before an allow hook completes. The four stable approval outcomes are pinned; actual frame observations remain recorded per run. Treating every frame as a prompt needing an answer races the hook. Evidence: 43443214193, 43444128696 and 43444623151.
- **run — No ends the interactive turn:** an owner continuation is needed before the model receives the denied tool result. The driver records `Interrupted · What should Claude do instead?`, then types `INTERACTIVE_RESUME_CURRENT_TURN`; it does not prepare or send again. Evidence: 43439542838 and the green run's refusal rows.
- **run / read — input guard:** immediate input after an owner prompt can select No without completing it. The binary excerpts collected in development run 43443214193 show an answer-admission guard; a one-second continuously visible named dialog resolved the DAA flow. Screens and receiver counts still prove each outcome. No fixed sleep is used as passing evidence.
- **run — existing runner-dependent VSOCK failure:** 43438859926 and 43443214193 reported `['connect:vsock', 'network:proxy-http', 'network:proxy-connect']` where the unchanged mutation expects the two proxy routes. Other runs, including 43444623151, passed. No sandbox assertion or classification was changed, and neither failure was retried in a loop.

## Open questions

- **read — remaining work:** no blocking question within these two parts. The intermittent VSOCK classification needs a separate investigation if it recurs. Part A/B2 still needs the image agreement and the Chrome merge described in the brief.
- **run — workspace closing check:** `.work/` contains **no file over 500 MB**. Only runner logs/artifacts and small scratch files were downloaded; no image, extracted image, ISO, container or VM was created locally. No Gradle daemon was started.

## For the builder of Part A and B2

**read — call the driver:** import `Terminal` from `interactive_driver.py` and `Model` from `interactive_model.py` in the CI guest supervisor. Supply `run(argv, env=..., required=...)` returning a captured `CompletedProcess` as `ares`, a writable owner tmux socket path, canonical workspace/home, evidence directory, Claude argv and a synthetic environment. `Terminal.wait(label, predicate)` saves rendered screens; `choose(screen, 'Yes'/'No'/'DAA')` uses text; `prompt(marker)` submits the next owner prompt. The container-only `interactive_suite.main()` creates fixtures and must not be called on the laptop or used as the VM installer.

**read — model script:** use one unique `prompt` marker per intended send; set `prepare={'name': 'mcp__testapp__prepare_send', 'input': message}` and `send='mcp__testapp__send'`. `message` is exactly `control/tests/support.py::message()`: fixture account, `to` alpha/beta, empty cc, bcc hidden, subject `Fixture message`, text `Written in full`, empty attachments. The double reads the preparation result and copies its approval unchanged. Without preparation, `approval` supplies the fixed container input. For an ordinary-session tool, the same step can name that tool and its fixed arguments. Run `Model(steps, evidence, port=18081)` beside the CLI in the guest; configure the loopback URL and synthetic key in the CI environment, keeping shipped managed files unchanged. `INTERACTIVE_DONE_1` marks the first model completion; a Stop continuation produces `INTERACTIVE_CONTINUATION_DONE_1` and is separately recorded.

**run — warning setup on 2.1.319:** seed onboarding, synthetic-key approval and workspace trust as in `precedence.py`. Do not guess a warning key. The first skip CLI shows the unnumbered `No, exit` / `Yes, I accept` dialog. The driver matches the latter, observes the former's focus, sends Down and confirms. The binary writes **`skipDangerousModePermissionPrompt: true` to `~/.claude/settings.json`**. All eight fresh skip cases accepted it; the DAA restart retained that setting and did not show it again. Evidence: green run lines 11–18, `skip-no/session-1/actions.jsonl` and its before/after settings snapshots.

**run / read — VM prompt details:** normal argv must explicitly select default mode; skip argv uses `--dangerously-skip-permissions`. Wait for named rendered states, including the input guard interval. A selected numeric option can submit without Enter. No interrupts; resume with the non-step marker before expecting the next model request or its pending reminder. DAA writes `mcp__testapp__send` into the workspace's `.claude/settings.local.json`; preserve that file for sends 2 and 3, and still require all three prompts. PermissionRequest hooks may flash a question and then approve without any answer; do not race them with No. Keep hook counts, actual frame observations and independent arrival counts separate. Save the real service's pending/reminder evidence before the brief's cancel/notice-ack cleanup, and assert a clean baseline before every next case.
