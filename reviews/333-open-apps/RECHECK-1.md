### Blocking finding

1. **View-history eviction can still cause a second launch.** A desktop activation waits for its executable check. Before the helper handles that completion, a 1.2 view deliberately opens the same app. If three other view histories are protected, the next new view’s recorded request evicts the deliberate open’s history and moves its live process to `reaping`. With no window mapped yet, the activation recheck sees neither a window nor a starting launch and spawns again. The new deliberate-open test keeps the launch history intact, so it misses this sequence. `os/config/usr/libexec/aresos-shell:2276`, `os/config/usr/libexec/aresos-shell:2312`, `os/config/usr/libexec/aresos-shell:3881`, `os/config/usr/libexec/aresos-shell:3982`, `os/config/usr/libexec/aresos-shell:4077`, `os/tests/test_aresos_shell_open_apps.py:284`

### Checks that passed by inspection

2. **Queued windows are restored before fallback can spawn.** Both immediate and deferred check completion drain the compositor socket and recheck windows and launch state. The new test queues actual Wayland messages before marking the check complete and asserts activation with zero spawns. Deliberate `open_app` still starts independently. `os/config/usr/libexec/aresos-shell:3849`, `os/config/usr/libexec/aresos-shell:3982`, `os/tests/test_aresos_shell_open_apps.py:240`
3. **Recorded refusals and unjoined fallback starts survive view churn within the retry window.** The eviction rule protects both records and replay returns the saved result before launch handling. The tests force eviction pressure and retry the same ID. The refusal test also closes the target window and reloads the journal. `os/config/usr/libexec/aresos-shell:2312`, `os/config/usr/libexec/aresos-shell:3817`, `os/tests/test_aresos_shell_open_apps.py:324`
4. **Log cleanup failures are contained.** `ShellLog` detaches before cleanup, contains flush and close failures, and reports the original error through stderr. The test forces `ENOSPC` on flush and `EIO` on close, verifies detachment at close, and checks that later records still reach stderr. `os/config/usr/libexec/aresos-shell:286`, `os/tests/test_aresos_shell_open_apps.py:447`

### Known limits / nits

5. **Four protected histories can temporarily deny launch requests from a fifth view name.** That can include the 1.2 laptop home if its name has no retained history. Its `apps_running` feed and 1.2 negotiation still work, and the desktop quota remains independent. `os/config/usr/libexec/aresos-shell:2295`, `os/config/usr/libexec/aresos-shell:2327`, `os/config/usr/libexec/aresos-shell:3510`, `os/tests/test_aresos_shell_open_apps.py:40`

Read-only review. No files changed and no builds or tests ran.

NOT SAFE