# 03c CI evidence

**No green 03c run exists.** All three full attempts are counted and the budget
is exhausted. `attempt1/` contains the small artifact from the cancelled build;
it did not reach image completion or VM checks.

`attempt2/` is the unmodified small evidence artifact from failed run
[39703243372](https://github.com/carlsenares/AresOS/actions/runs/39703243372),
checkout `05e8f7e79f4766f05b356cafd9bb9b6016809007`, except screenshots and
console logs are retained separately under `reviews/03-os-image/`.
It is not a green result. Its first VM passed policy, raw exports, ignored power
events and recovery authentication; the final journal-record assertion failed
after guest poweroff. There was no second VM pass.

`attempt3/` is the corresponding artifact from final run
[39707546339](https://github.com/carlsenares/AresOS/actions/runs/39707546339),
checkout `70b632f2a74b085ff9c1af3566d121d2b53d61f1`. The same preceding checks
passed, along with the cursor-based journal follower's readiness proof. QMP
recorded guest-initiated shutdown and the console reached `poweroff.target`,
but the enforced logind button-record assertion failed again. There was no
second VM pass and no successful poweroff-result file. No source fix was added
after that final run.

`image-oci-manifest.json` / `image-digest.txt` describe the release candidate.
`vm-image-oci-manifest.json` / `vm-image-digest.txt` describe a separate CI-only
layer containing the verification service. The live guest's raw `backend.json`
identifies this test image, not the release tag. Neither image was published.

Guest `backend.json` and `runtime-updaters.json` are byte-preserved exports with
guest SHA-256 values in `export-result.json`. No kernel record was removed and
no JSON was reconstructed or reformatted. `power-events.json`, check responses
and QMP events retain the live assertions and observations. Screenshots are
QEMU framebuffer captures; tty3 images show the getty, while password
authentication is proved separately by `recovery-result.json`.

The [03c report](../../../../reviews/03-os-image/REPORT.md#03c-robust-vm-channels-for-recovery-and-power)
records source commits, workflow outcomes, the complete run budget, measurements
and remaining hardware/interactive-login qualification. Both completed VM
captures are diagnostics from failed workflows, not release promotion evidence.
