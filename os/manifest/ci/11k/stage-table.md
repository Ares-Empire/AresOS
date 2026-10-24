| Run / order / stage | Protected bytes / final writes | Firmware and Linux position events |
|---|---|---|
| full-5 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| full-5 / first / protected-first-install | MATCH; 0 bytes / 0 operations | Linux Boot000A: index None → 0 |
| full-5 / first / boot-3-pre-login-reset | MATCH; 0 bytes / 0 operations | pci:00:1f.2/sata:0:65535:0: Boot0002 → absent<br>Linux Boot000A: index 0 → 1 |
| full-5 / first / stock-before-windows | MATCH; 0 bytes / 0 operations | None |
| full-5 / first / after-install-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0004 → absent |
| full-5 / first / switch-sequence-stock | MATCH; 0 bytes / 0 operations | pci:00:03.0: absent → Boot0002 |
| full-5 / first / switch-sequence-aresos | MATCH; 0 bytes / 0 operations | None |
| full-5 / first / switch-sequence-rollback | MATCH; 0 bytes / 0 operations | None |
| full-5 / first / switch-sequence-persistent-stock | MATCH; 0 bytes / 0 operations | None |
| full-5 / first / before-undo-windows | MATCH; 0 bytes / 0 operations | None |
| full-5 / first / after-undo-default-windows | MATCH; 0 bytes / 0 operations | None |
| full-5 / first / after-undo-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0002 → absent |
| full-5 / reverse / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| full-5 / reverse / protected-second-install | MATCH; 0 bytes / 0 operations | Linux Boot000A: index None → 0 |
| full-5 / reverse / boot-15-pre-login-reset | MATCH; 0 bytes / 0 operations | pci:00:1f.2/sata:0:65535:0: Boot0002 → absent<br>Linux Boot000A: index 0 → 1 |
| full-5 / reverse / stock-before-windows | MATCH; 0 bytes / 0 operations | None |
| full-5 / reverse / after-install-without-linux | MATCH; 0 bytes / 0 operations | pci:00:02.0: Boot0003 → absent<br>pci:00:03.0: Boot0004 → Boot0002; relabel |
| full-5 / reverse / switch-sequence-stock | MATCH; 0 bytes / 0 operations | pci:00:02.0: absent → Boot0002<br>pci:00:03.0: Boot0002 → Boot0003; relabel |
| full-5 / reverse / switch-sequence-aresos | MATCH; 0 bytes / 0 operations | None |
| full-5 / reverse / switch-sequence-rollback | MATCH; 0 bytes / 0 operations | None |
| full-5 / reverse / switch-sequence-persistent-stock | MATCH; 0 bytes / 0 operations | None |
| full-5 / reverse / before-undo-windows | MATCH; 0 bytes / 0 operations | None |
| full-5 / reverse / after-undo-default-windows | MATCH; 0 bytes / 0 operations | None |
| full-5 / reverse / after-undo-without-linux | MATCH; 0 bytes / 0 operations | pci:00:02.0: Boot0002 → absent<br>pci:00:03.0: Boot0003 → Boot0002; relabel |
| full-5 / reverse / b-switch | MATCH; 0 bytes / 0 operations | pci:00:02.0: absent → Boot0002<br>pci:00:03.0: Boot0002 → Boot0003; relabel |
| full-5 / reverse / b-menu-preparation | MATCH; 0 bytes / 0 operations | None |
| probe-1 / first / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-1 / first / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-1 / first / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:03.0: Boot0004 → absent<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
| probe-1 / reverse / baseline-firmware | MATCH; 0 bytes / 0 operations | Baseline ownership |
| probe-1 / reverse / live-ui-probe | MATCH; 0 bytes / 0 operations | None |
| probe-1 / reverse / probe-windows-without-linux | MATCH; 0 bytes / 0 operations | pci:00:02.0: Boot0003 → absent<br>pci:00:03.0: Boot0004 → Boot0002; relabel<br>pci:00:1f.2/sata:0:65535:0: Boot0002 → absent |
