1. **Blocking — The config move requires forbidden test edits.** Agreed change 7 ([brief:181](/var/home/ares/AresOS-18c-image-test/briefs/18c-image-test.md:181)) requires updating the config paths and their tests, but the amended protected-path list still forbids editing existing `control/tests/` files ([brief:456](/var/home/ares/AresOS-18c-image-test/briefs/18c-image-test.md:456)). In both this checkout and the supplied Chrome branch, `test_integration.py` uses `/etc/aresos-control` at lines 55, 56, 276, 390 and 535. Updating `setup.sh` and the launcher without those replacements breaks the integration suite. The precedence rule covers proposal text, while this prohibition sits outside the proposal. **Fix:** explicitly permit these five path replacements in the existing test, alongside the two production constants and `setup.sh`.

2. **Should-fix — The dependency ban conflicts with enabling the shipped unit.** Agreed change 6 ([brief:176](/var/home/ares/AresOS-18c-image-test/briefs/18c-image-test.md:176)) requires an enabled service while forbidding any boot unit from depending on or ordering after it. The unit has `WantedBy=multi-user.target`; enabling it creates that target’s `Wants` dependency and automatic `After` ordering. [Systemd documents this behavior](https://www.freedesktop.org/software/systemd/man/latest/systemd.target.html). These requirements cannot both hold literally. **Fix:** explicitly allow normal target activation dependencies, and prohibit login, session and recovery services from requiring or waiting for Control. Keep `Type=simple`, and arm the failure before testing a fresh session startup.

The remaining amendment is implementable on inspection:

- CI identities are independent fixtures: integration tests use service UID/GID 23102, the boundary container creates UID 10002, and Chrome’s container creates UID 1001. None consumes the production sysusers declaration.
- `aresos.conf` supplies both the owner UID and canonical home. The generic CI hook and reusable rehearsal checks fit the existing harness.
- The CLI’s actual special top-level words are `admin` and `log`, plus served apps, on both branches. The reserved-word test can inspect or exercise that behavior.
- A CI-only runtime unit override can produce a stable failed service without modifying immutable `/usr/share` config. Chrome’s additional old-path occurrence is an unused directory creation in its CI Dockerfile.

No additional harm to normal use found within the amendment. The owner approval gate appropriately covers the measured hook interruption and idle footprint.

No files modified; this was a static review.

CHANGES-NEEDED