| Run / order / stage | Protected bytes / final writes | Firmware and Linux position events |
|---|---|---|
| full-2 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| full-2 / first / protected-first-install | MATCH; 0 bytes / 0 operations | Linux Boot000A: index None → 0 |
| full-2 / first / after-install-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0004 → absent<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent<br>Linux Boot000A: index 0 → 1 |
| full-2 / first / boot-4-pre-login-reset | MATCH; 0 bytes / 0 operations | pci:00:03.0: absent → Boot0002 |
| full-2 / first / switch-sequence-stock | MATCH; missing counter | None |
| probe-1 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-1 / first / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-1 / first / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0004 → absent<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
| probe-1 / reverse / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-1 / reverse / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-1 / reverse / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:02.0: Boot0003 → absent<br>pci:00:03.0: Boot0004 → Boot0002; relabel<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
