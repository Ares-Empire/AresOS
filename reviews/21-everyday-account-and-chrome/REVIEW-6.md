- **Low, nonblocking — [os/ci/overlay/checks.py:89](/C:/Users/pab/AresOS-21-everyday-account/os/ci/overlay/checks.py:89):** The profile assertion passes if the probe is missing or records no matching wrapper. **Fix:** require at least one noninteractive, non-login wrapper record before checking its PATH. Run 42743949300 contains that record, so this doesn’t invalidate its evidence.

Both Medium findings are fixed correctly, including the helper commands. The VM verifies both terminals have live system Bash children and none of the 17 shadows ran.

JUDGMENT-CALL 9 is sound: reliable startup/recovery outweighs requiring future GUI launchers to configure user-tool paths explicitly. The whole-PR pass found no remaining privilege, boot, firmware or session blocker.

Shell/JavaScript syntax checks passed. Python tests weren’t rerun: Python is absent and WSL access denied. Image/VM conclusions rely on supplied CI evidence.

SAFE