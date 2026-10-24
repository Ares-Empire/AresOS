| Run / order / stage | Protected bytes / final writes | Firmware and Linux position events |
|---|---|---|
| b-1 / protected-second / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| b-1 / protected-second / protected-second-install | MATCH; 0 bytes / 0 operations | Linux Boot000A: index None → 0 |
| b-1 / protected-second / boot-3-pre-login-reset | MATCH; 0 bytes / 0 operations | pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
| b-1 / protected-second / stock-before-windows | MATCH; 0 bytes / 0 operations | None |
| b-1 / protected-second / after-first-login-default-windows | MATCH; 0 bytes / 0 operations | Linux Boot000A: index 0 → 1 |
| b-1 / protected-second / after-install-without-linux | MATCH; 0 bytes / 0 operations | pci:00:02.0: Boot0003 → absent<br>pci:00:03.0: Boot0004 → Boot0002; relabel |
| b-1 / protected-second / b-switch | MATCH; 0 bytes / 0 operations | pci:00:02.0: absent → Boot0002<br>pci:00:03.0: Boot0002 → Boot0003; relabel |
| b-1 / protected-second / b-menu-preparation | MATCH; 0 bytes / 0 operations | None |
| b-1 / protected-second / b-recovered-stock | MATCH; 0 bytes / 0 operations | None |
| b-1 / protected-second / b-unattended-stock | MATCH; 0 bytes / 0 operations | None |
| probe-1 / protected-first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-1 / protected-first / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-1 / protected-first / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0004 → absent<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
| probe-1 / protected-second / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-1 / protected-second / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-1 / protected-second / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:02.0: Boot0003 → absent<br>pci:00:03.0: Boot0004 → Boot0002; relabel<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
