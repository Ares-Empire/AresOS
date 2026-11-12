- **Medium — [os/ci/journal_ready.py:14](/C:/Users/pab/AresOS-21-everyday-account/os/ci/journal_ready.py:14):** `\s*` includes newlines and carriage returns, so `[\n 1.0] host aresos-ci[7]: ARESOS_JOURNAL_READY\n` still matches. This violates the single-complete-line requirement. **Fix:** use `[ \t]*` and add regressions rejecting line breaks inside the timestamp.

- **Medium — [os/config/etc/profile.d/aresos.sh:9](/C:/Users/pab/AresOS-21-everyday-account/os/config/etc/profile.d/aresos.sh:9):** Prepending `~/.local/bin` also affects session startup: `aresos-session` resolves `dbus-run-session` and `labwc` through PATH, and `aresos-keyboard` resolves `busctl`. A broken shadowing executable prevents the desktop—and its recovery shortcut—from starting. **Fix:** use absolute system paths throughout startup; test with shadowing executables.

The Flatpak before/after guard is correct, and `vm.py`’s pending hash matches exactly. No additional passwordless root/image/boot/kernel-argument/firmware bypass found in source and supplied CI evidence. Native tests and the image were not rerun; Python was unavailable and WSL access denied.

CHANGES-NEEDED