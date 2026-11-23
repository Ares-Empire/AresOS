# 334c: the bench's network levels and the egress gate (test bench, steps 3 and 4)

**Goal:** the bench's per-test network option (`docs/design/TEST-BENCH.md`, section 6, "Network: a per-test
option, off by default"; build plan steps 3 and 4). The owner asked for it on board T499: "for things requiring
network, doesn't it make sense to include functions like that?"

A test names one level:
- `none` (default): loopback only.
- `fake`: stub servers on the container's own loopback, which can be up, down, slow or wrong, and nothing leaves.
- `internet`: real internet, outbound only.

This package builds `none` and `fake`, and the **egress gate** that must pass before `internet` may ever run on the
laptop. Until that gate passes, `internet` stays hosted-only, and a laptop run that asks for it exits 75.

Model: Codex `gpt-6.2-sol`, effort `xhigh` (a network boundary on the owner's home network).

## Read first

- `AGENTS.md` (rule 1's bench-store exception included).
- `docs/design/TEST-BENCH.md`:
  - section 6 in full (the network table, "Level `fake`", "Level `internet`");
  - section 7, steps 3 and 4 and "Carried into the step briefs", Step 4 (part of this brief);
  - section 9 ("Network" known limits).
- `reviews/334-test-bench/REVIEW-3.md` blocking 1, for why the gate looks the way it does.
- `os/input-portal/harness/run.sh` and `in-container.sh` (`--network=none`, `only_loopback`, `no_host_mount`): the
  rootless container patterns to reuse.
- `os/ci/bench/` (steps 1 and 2 on `main`): the gates, the capped scope, the store and its budget. Every container
  this package starts goes through step 2's launcher and budget, and its exit codes.

## In scope

1. **`none` and `fake`** for the desk container, plus the VM's user-mode NIC inside a network-less container, as
   section 6 describes: stub servers by name through the container's `/etc/hosts`, a per-run CA, and `net up/down` as
   a step. Acceptance:
   - `none` has only loopback and no guest NIC;
   - at `fake`, a test reaches a stub by name and observes `net down`;
   - **no traffic leaves**, checked against a controlled listener outside the container that must see nothing.
2. **The egress gate for `internet` on the laptop:**
   - the policy (outbound only, through rootless pasta with no access to the host's own ports);
   - every entry path guarded, including `podman exec`, fetches and build steps;
   - each path checked against controlled listening endpoints before any real workload uses it.
   Carried into this brief from the note:
   - name each controlled endpoint and the entry paths it checks;
   - cover the laptop's own addresses, the home network's routes, and the home's public address reflected by the
     router;
   - verify the unprivileged user, the dropped capabilities (no `CAP_NET_ADMIN` on any entry) and clean profile,
     credential store, proxy and DNS settings on every entry.
   A missing or unverifiable policy fails closed (exit 75). Record a pass in the store so later runs can check it,
   tied to the bench code version and the network it was verified on. A change of either sends `internet` back to
   refused.
3. **Tests** in `os/tests/test_bench_net_*.py` for the level parser, the policy builder, fail-closed behaviour and the
   record. They run on the hosted checks.

## Rules

- `AGENTS.md` holds. The owner allowed rootless, throwaway containers on the laptop (T499). Every container goes
  through step 2's gates, scope and budget, with `--network=none` unless this package's verified policy applies. No
  sudo. No host mounts other than read-only inputs the design names. Nothing in the owner's session.
- **The owner's network stays private.** Never commit, print into evidence, or send anywhere the laptop's addresses,
  the router's address, the home's public address, network names or MAC addresses. Tests and evidence use
  placeholders. The gate finds these addresses at run time and keeps them in memory only.
- The egress probes go only to **listeners the bench itself starts** (on the laptop or in a container) and to the
  reflected public address. Never scan or probe other devices on the home network. Keep every probe to a few packets.
- Write "the owner", never a person's name. Repo-relative paths in everything committed.
- Hosted: `gh workflow run "OS image" --ref <branch> -f checks_only=true`, watched with
  `gh run watch <id> --exit-status --interval 60`. A bench dispatch is allowed only if a level needs the VM proof; at
  most 2.
- Commit and push on `pkg/334c-bench-network`, open a PR into `main`, never merge. Name the model in commit trailers.
  Keep `reviews/334c-bench-network/PROGRESS.md` while you work. At the end, write `REPORT.md` there (what was built,
  the endpoints and paths table, the run IDs, PLAN-GAP, Known limits) and delete `PROGRESS.md`.
