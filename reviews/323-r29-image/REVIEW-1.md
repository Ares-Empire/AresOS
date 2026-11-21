**Must-fixes**

- None found at `0c9df244`. The stage order satisfies every `COPY --from` dependency. Fedora’s labwc install and the swap share one `RUN`, and the offline check verifies the rebuilt NEVRA and runs `rpm -V labwc` against the committed image. `os/Containerfile:7`, `os/Containerfile:34`, `os/ci/check-image.sh:13`, `os/ci/image-checks.sh:596`
- The new checks fit strict Bash and the offline root runner. The preload reaches Python after `runuser` switches to `ares`. Fedora ships the expected typelib and library, and the upstream version getters need no display. The original 53f block is byte-identical. `os/ci/image-checks.sh:738`, `os/ci/image-checks.sh:772` · [Fedora package](https://packages.fedoraproject.org/pkgs/gtk4-layer-shell/gtk4-layer-shell/fedora-44.html) · [Upstream implementation](https://raw.githubusercontent.com/wmww/gtk4-layer-shell/v1.3.0/src/gtk4-layer-shell.c)
- The release tests recover the same lock bytes they used before this patch. The smoke test substitutes only its source-lock input and still exercises the production comparisons. Release 28’s published tools and records are untouched. `os/tests/test_release27.py:33`, `os/tests/test_release28.py:135`, `os/tests/test_release28.py:2098`

**Should-fixes**

- Match the transaction preview’s package spec to the candidate download by using `gtk4-layer-shell.x86_64` in both. This keeps the preview aligned with the reviewed architecture. `os/ci/check-resolve.sh:163`, `os/ci/check-resolve.sh:235`

**Known limits**

- Bash syntax, both font copies, 18 targeted tests, and the driver probe against local manifests passed. Four driver unit tests could not create fixtures in the read-only sandbox. The committed image and VM results remain unverified here.

SAFE