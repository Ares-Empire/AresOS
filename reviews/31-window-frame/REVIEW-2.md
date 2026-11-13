No remaining or new findings in `a07a3852..1535a3f8`.

- Both helpers are deleted. Only historical references remain in the report and first review; no executable dependency remains. All six pictures are unchanged, and the report documents their capture method and the scripts’ removal.
- The checksum correctly hashes all 37 files in filename order: each file’s byte SHA-256, two spaces, filename; entries joined with LF, without a trailing LF, then hashed again. Independently computed from committed blobs: `cf01b9b105fc38847e6bf6382056862f3c460d8fc6864cc6d0932794fbd2153e`, matching the pin. In-memory empty-`themerc` and invisible-button substitutions both fail it. `bash -n os/ci/image-checks.sh` passes.
- Check build 43520195380 succeeded, as supplied. Nothing in this diff is expected to change hosted regression results: regression code and bound sources are unchanged, the removed helpers have no callers, and the modified image-check section is outside the sections exercised by regressions. Pending regressions are not claimed green.

Read-only; no files changed.

SAFE