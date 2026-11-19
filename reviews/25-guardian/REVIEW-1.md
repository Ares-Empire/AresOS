### Blocking findings

1. `os/config/usr/libexec/aresos-desktop:3212` — A replacement supervisor that cannot identify the running JVM asks `jvm_lock_held()` whether a writer exists. That function returns `False` if opening the lock fails (`:3846`). The supervisor then reports a confirmed “nothing to stop,” and the guard accepts it without checking the lock itself. An inaccessible lock can therefore let shutdown proceed without a save request or an `unsaved` warning.

2. `os/config/usr/libexec/aresos-desktop:3402` — The final logout check rereads a cached window count. `app_windows()` only checks that the helper process is alive (`:2090`). If the helper stalls after reporting zero, an app can open and accumulate unsaved work. Logout still signals labwc and closes the session. A fresh zero-window report before that signal would protect the open app.

3. `os/config/usr/libexec/aresos-desktop:2649` — During first setup, a heartbeat or the launch’s exit can overwrite the remembered inode. If the owner replaces the half-made `AresHub` with a different damaged home before setup ends, the supervisor remembers the replacement. The next recovery `retry` moves that home aside as unfinished. The no-overwrite rename preserves its files, but it moves the wrong world.

4. `os/config/usr/libexec/aresos-desktop:2985` — Save validation compares the active folder name at request and reply. If the helper reports a different ready world and then the original name again before a delayed answer is processed, the old answer passes. Section 1.3 requires the world to stay unchanged throughout the request. Tracking a world-change counter would distinguish those cases.

### Release proof

`reviews/25-guardian/REPORT.md:38` records both boots passing in run `44603436437` on `35ce377e`. Only the report changed through `6b5e461e`. Boot 1 requires the fixture’s matching answer after it writes the reply, followed by Java’s exit and guard completion. The guest powered itself off in 9 s. Boot 2 received the request, stayed silent, ignored SIGTERM and powered itself off in 78 s. `save=timeout` is the recorded reason for the `unsaved` result alongside `close=overrun`. Both boots require polkit and tty3’s getty to begin stopping after the guard. Boot 2 also requires a tty3 sample during the black stop. `os/ci/guardian_host.py:208`, `os/ci/vm.py:159`, `os/config/usr/libexec/aresos-desktop:3527`.

### Known limits

- `os/ci/guardian_host.py:234` accepts a guard duration of 55–85 s. The measured 60.632 s supports the supervisor’s 60 s deadline, though the assertion permits a longer wait. The unit has the requested dependencies and 85 s limit. Neither boot reported an ordering cycle. The home mount was writable during saving, but its unmount timestamp was unavailable.
- `os/ci/image-checks.sh:851` catches literal desktop and Prism names in executable directives. A unit that supplies the program name through `Environment=` and invokes it through `env` escapes the narrowed check.
- `os/config/usr/libexec/aresos-shell:3943` preserves the existing search and covering paths. I found no regression in 53c, 53d or 56 from excluding the laptop home. Local `test_guardian_vm.py` stopped in setup because the read-only sandbox had no writable temporary directory.

CHANGES-NEEDED