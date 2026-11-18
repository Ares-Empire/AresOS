# 311 progress

## Done
- Patch `os/labwc/0001-allow-constraints-for-layer-surfaces.patch`: upstream b7820667a2 adapted to 0.9.6 (37 insertions, 8 deletions, the same as upstream).

## Left, in order
1. Build the patched RPM in fedora:44, compare with Fedora's.
2. Headless proof (patched passes, Fedora's fails, normal window still locks).
3. Lock, build stage, final stage, signature exception, resolve, image checks, tests.
