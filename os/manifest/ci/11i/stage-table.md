| Run / order / stage | Protected bytes / final writes | Firmware and Linux position events |
|---|---|---|
| full-4 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| full-4 / first / protected-first-install | MATCH; 0 bytes / 0 operations | Linux Boot000A: index None → 0 |
| full-4 / first / boot-3-pre-login-reset | MATCH; 0 bytes / 0 operations | pci:00:1f.2/sata:0:65535:0: Boot0002 → absent<br>Linux Boot000A: index 0 → 1 |
| full-4 / first / stock-before-windows | MATCH; 0 bytes / 0 operations; failure path recorded | None |
| probe-3 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-3 / first / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-3 / first / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0004 → absent<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
| probe-3 / reverse / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-3 / reverse / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-3 / reverse / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:02.0: Boot0003 → absent<br>pci:00:03.0: Boot0004 → Boot0002; relabel<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
