# VM screenshots

`03b-attempt3-diagnostic.png` is the unedited last framebuffer from
[run 39698003724](https://github.com/carlsenares/AresOS/actions/runs/39698003724),
source `5991246e5bbd5db52248432cbccff26ac1ff999b`, downloaded and visually
inspected. It shows the AresOS foot terminal in labwc. That run failed parsing
the runtime inventory export before reaching recovery/power tests, so this is
boot/session evidence only; there is no 03b successful TTY screenshot.

`initial-boot.png` is the unedited QEMU framebuffer from
[run 39671066887](https://github.com/carlsenares/AresOS/actions/runs/39671066887).
It shows greetd's `ares` session running labwc and foot on the pinned image.
That run's automated guest checks were blocked by a serial-shell prompt matching
bug in the test harness; the picture is boot/session evidence only.

`aresos-labwc.png` and `tty3-authenticated-diagnostic.png` are unedited QEMU
framebuffers downloaded from [run 39685234531](https://github.com/carlsenares/AresOS/actions/runs/39685234531),
source `ee9ee390031bfa2d20a32129aeb0715a6af700f3`.
The first follows a successful recovery-shortcut assertion (two foot processes).
The second visibly shows the root shell on tty3 after credential entry. The
automated wait expected a bracketed prompt and rejected the themed prompt, so
the root-owned proof-file and clean-shutdown checks were not reached. This
diagnostic screenshot does not turn that run into a passing recovery test.
