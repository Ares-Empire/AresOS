# Package 334c network levels and egress gate

## Done

- Bench scripts accept `none`, `fake` and hosted `internet`. They default to `none`, use `net up/down` only at `fake`, and record the selected level in `run.json`. Hosted internet runs carry a nonrepeatable flag.
- The offline desk command fixes the Podman network to `none`, disables pulls and proxy inheritance, drops capabilities, and adds the fake fixture name to `/etc/hosts` only for `fake`. The shared stub code generates a disposable CA and serves normal, slow and wrong responses. Stopping the stub closes its listener.
- The hosted driver starts the offline QEMU runs in a private network namespace with only loopback. The `none` VM uses `-nic none`. The `fake` VM uses a user-mode NIC with its fixture name in guest `/etc/hosts`, verifies TLS with the fixture CA, and uses QMP to pull and restore the guest link. The guest probe runs under an unprivileged UID with a fresh profile and no inherited proxy configuration or capabilities.
- The laptop policy compiler denies laptop addresses, home routes, the reflected address, and reserved ranges. It drops IPv6, restricts DNS to a configured IPv4 resolver, and permits outbound IPv4 TCP and UDP with replies. The scoped launch API refuses laptop internet with the bench's exit-75 reason. The proof format requires all endpoint and clean-setting checks on every entry, and stores only a keyed binding to the code version and in-memory network facts.

## Verified

| Local command | Result |
| --- | --- |
| `python3 -B -m unittest discover -s os/tests -p 'test_bench_net_levels.py' -v` | After the HTTPS response fix, `Ran 4 tests in 0.661s`, `OK`. A second run printed `Ran 4 tests in 0.710s`, `OK`. |
| `python3 -B -m unittest discover -s os/tests -p 'test_bench_net_egress.py' -v` | `Ran 8 tests in 2.141s`, `OK`. |
| `python3 -B -m unittest discover -s os/tests -p 'test_bench_script.py' -v` | `Ran 3 tests in 0.026s`, `OK`. |
| `python3 -B -m unittest discover -s os/tests -p 'test_bench_dispatch.py' -v` | `Ran 7 tests in 0.202s`, `OK`. |
| `python3 -B -m unittest discover -s os/tests -p 'test_bench_agent.py' -v` | `Ran 4 tests in 0.023s`, `OK`. |
| `python3 -B -m unittest discover -s os/tests -p 'test_bench_laptop_store.py' -v` | `Ran 19 tests in 0.800s`, `OK`. |
| `python3 -B -m unittest discover -s os/tests -p 'test_bench_laptop_gates.py'` | `Ran 14 tests in 0.036s`, `OK`. |
| `python3 -B -m unittest discover -s os/tests -p 'test_checkout_sources.py' -k test_every_active_source_binding_replays_checkout_including_crlf -v` | `Ran 1 test in 0.419s`, `OK` after restoring the workflow. |
| `python3 -B -m unittest discover -s os/tests -p 'test_ways_back_probe.py' -k test_the_probe_reads_package_22cs_host_walk_and_refuses_a_stale_one -v` | `Ran 1 test in 0.020s`, `OK` after restoring the workflow. |
| `bash -n os/ci/bench/build.sh` and `git diff --check` | Both exited zero. |
| Forked stand-in with `restrict_writes((), 0)` | Printed `new socket denied by the scoped command contract` and `new directory denied by the scoped command contract`. |
| `unshare --user --map-current-user --keep-caps --mount --net` with a read-only synthetic hosts file and the TLS stub | Printed `PASS fixture resolved via /etc/hosts, served verified TLS, and refused after net down`. |
| `find .work -type f -size +500M -print` | No files. |

The two new modules also passed a repeat run with the same counts. The local network tests used a private namespace and owned listeners. The nftables fixture placed the listeners in a second private namespace. It confirmed that each listener was reachable before applying the policy, then checked that three blocked listeners received no connections and the allowed listener received one. The test workload ran with a non-root UID and all capability sets empty. The local fake fixture tested TLS, rejection without its CA, the slow and wrong responses, up/down/up, and an untouched outside listener after its positive control. These tests exercised synthetic addresses only.

| Hosted command and run | Result |
| --- | --- |
| `gh workflow run 'OS image' --ref pkg/334c-bench-network -f checks_only=true`, [45127091541](https://github.com/Ares-Empire/AresOS/actions/runs/45127091541) | Superseded after making IPv4 reflection mandatory for the IPv4 policy. |
| Same checks-only command for `d562bbec`, [45127402154](https://github.com/Ares-Empire/AresOS/actions/runs/45127402154) | All 12 network tests passed. The full suite printed `Ran 2655 tests in 2882.351s` and `FAILED (failures=3, skipped=24)`. The shared workflow edit invalidated the existing source binding and two host-walk checks. |
| Same checks-only command for `23d87547`, [45129960398](https://github.com/Ares-Empire/AresOS/actions/runs/45129960398) | Superseded by the source-binding fix. |
| Same checks-only command for `dbd87a1e`, [45133636787](https://github.com/Ares-Empire/AresOS/actions/runs/45133636787) | Passed. The regression job took 31m05s and printed `Ran 2655 tests in 1795.112s`, `OK (skipped=24)` and `Live hosted system manager passed: 434 unit files, 421 unit names`. Both new network modules passed, including the curl regression. |
| `python3 -B os/ci/bench/dispatch.py --ref pkg/334c-bench-network reviews/334c-bench-network/bench/fake-network.json`, [45127096186](https://github.com/Ares-Empire/AresOS/actions/runs/45127096186) | Built the image and booted with KVM. Evidence printed `PASS 001 status` and `FAIL 002 net (guest fake network behavior differed from the fixture)`. The VM took 34.5 seconds and the workflow returned exit 1. |
| `python3 -B os/ci/bench/dispatch.py --ref pkg/334c-bench-network reviews/334a-bench-hosted/bench/session-health.json`, [45127100053](https://github.com/Ares-Empire/AresOS/actions/runs/45127100053) | Passed all six steps. Both boot records had `no_nic: true`. The VM took 73.7 seconds with KVM. The job printed `PASS outside listener positive control and no guest traffic` and `Bench evidence safe: 3 files, 65682 bytes`. |

Watched each dispatch with `gh run watch <id> --exit-status --interval 60`.

The guest's curl command reproduced the fake VM's failure mode in the isolated local fixture. It received the expected body and exited 56 because the stub closed the TLS stream without specifying the body length. The stub now sets `Content-Length`, and the regression requires curl to return zero and the expected body. Both allowed VM dispatches had already been used when this fix was pushed.

The no-NIC run's `bench-evidence` artifact includes the session screenshot from step 3, the two boot records, and the six assertion results. [Hosted run artifact](https://github.com/Ares-Empire/AresOS/actions/runs/45127100053)

The shared OS workflow was restored byte for byte. The bench-only build script now configures user namespaces on its disposable runner before the VM step. The hosted regression log confirmed the Ubuntu image already supplies nftables. The two targeted tests above passed locally after restoring the workflow.

## Endpoints and entry paths

| Controlled endpoint | Fixture exercised | Live laptop paths required for a pass |
| --- | --- | --- |
| Fake HTTPS stub and outer loopback listener | Desk network namespace fixture, and hosted VM fake script. The outer listener has a positive control. | Desk startup, step loop, each `podman exec`, VM. |
| Host loopback port | Outside listener in the offline namespace fixture. | Desk startup, step loop, each `podman exec`, VM, fetch, build. |
| Laptop address | Bench-owned listener at a synthetic host-address alias. | Desk startup, step loop, each `podman exec`, VM, fetch, build. |
| Home route | Bench-owned listener under a synthetic routed public prefix. | Desk startup, step loop, each `podman exec`, VM, fetch, build. |
| Reflected public address | Bench-owned listener at a synthetic reflected-address alias. | Desk startup, step loop, each `podman exec`, VM, fetch, build. |
| Allowed public destination | Bench-owned listener in the private peer namespace. | Desk startup, step loop, each `podman exec`, VM, fetch, build. |

## Not verified

- A live rootless desk container through the step-2 launch contract, and the laptop egress policy applied through real pasta and Podman. No laptop pass was recorded.
- A hosted fake VM pass with the fixed HTTPS response framing.
- Runtime checks of the user, capabilities, fresh profile, credential store, proxy and DNS settings across the laptop entry paths. The record validates matrix completeness using fixture inputs.
- The package changes OS bench code. No mod build, client game tests, in-game verification or new client screenshots were run for it.

## JUDGMENT-CALL

- The candidate policy uses IPv4 for egress and drops the entire IPv6 family. The equivalent IPv6 proof needs its own host, route, reflection, resolver and relay cases before enabling that family. It would change the policy and invalidate existing pass records through the code binding.
- The hosted proof uses an unprivileged network namespace around the existing QEMU driver. The namespace takes no Podman storage and provides an independent loopback boundary. The laptop desk still needs its bounded Podman runtime.

## PLAN-GAP

- The step-2 launcher admits pre-created regular output files. It denies new sockets and file and directory creation in the workload. Rootless Podman needs sockets, runtime directories and mutable metadata. A later scoped launcher contract needs an independently bounded runtime and storage backend before it can run even an offline desk container. The laptop gate stays closed while that contract is missing.
- The brief requires observing the actual home routes and reflected public address while keeping the data in memory and probing only controlled endpoints. The checkout supplies no approved way to observe that reflection or establish that a port behind it belongs to a bench-controlled listener. Synthetic reflection covers the policy compiler only. A live pass needs an observation source and a controlled endpoint for that case.

## Known limits

- The kernel fixture covers the generated rules and its own topology. Route changes, actual pasta behavior, and every real entry path still need qualification. The bench does not use fixture records to authorize live laptop traffic.
- The hosted fake VM pulls the virtual link. The desk fixture stops the service, so it models availability rather than a guest link change.

## Open questions

- Which bounded rootless runtime will step 2 admit for the desk, image fetches and builds?
- Which controlled endpoint will establish reflection and its positive control without sending private network facts into evidence?
- The pull request remains unopened because the live laptop proof and the hosted fake VM replay are open.
