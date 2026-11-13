# Package 38: reproducible mod jar

## Done

- `mod/build.gradle`: a separate reproducibility block fixes file order, timestamps and archive permissions (0644 files / 0755 directories), Java source encoding and resource filtering encoding. After Loom finishes, it sorts the client-only manifest list, main attributes and named sections. The normal jar name remains `mod/build/libs/aresos-0.1.0.jar`.
- `mod/gradle.properties`: fixes the Gradle JVM's encoding to UTF-8, language/country to en/US and time zone to UTC. Existing dependency versions are unchanged.
- `.github/workflows/mod.yml`: runs on mod/workflow pull requests and pushes, and manual dispatch; `contents: read` only, standard `ubuntu-24.04` runner. Uses the exact package 23 builder container, caches Gradle dependencies/wrapper, builds/tests two clean checkouts at the same commit in different paths, compares bytes, writes SHA-256s to the summary, and uploads the verified jar with its hashes. No client tests. Test-result XML is retained even when tests fail; the second checkout and byte comparison also finish after a test failure, without changing the failing job status.
- `mod/README.md`: documents the pins and laptop/CI hash comparison.
- `archive-comparison.txt`: complete manifest diffs and archive metadata comparisons before/after normalization and reversed client-class creation order.

## Cause of the old difference

Loom **1.19.2**, on the non-remapped Minecraft 26.2 jar path, takes the client output file tree in filesystem order. `NonRemappedJarTaskConfiguration.getClientOnlyEntries()` returns that list without sorting; `ManifestModificationAction` joins it into **`Fabric-Loom-Client-Only-Entries`**. Archive entry sorting does not sort a list *inside* a manifest value. In this path Loom does not expose a sorting setting. Its remapped-jar implementation does sort, but this mod uses the non-remapped path.

This is demonstrated, not just inferred from code: recreating the 23 generated client class files in reverse creation order (unchanged contents and restored mtimes) changed the original jar hash from `c0e5cf1e1b0dfb8eead4586665c38de844be41bae7edc74d460276a2a69d70fc` to `7e65724c9956bf9812455a9479fb0b691a8683b52b44a0ee2451e577719ad049`. **Only the manifest changed**, and only that attribute's item order changed. All 121 entries, their archive order, timestamps, modes, compression method, flags, extra fields and comments agree. All classes, mod/mixin JSON, language JSON and license bytes agree; this jar has no refmap. Changed manifest CRC, compressed bytes and downstream ZIP offsets are consequences of that content difference.

The production sources/resources and Loom/Gradle versions are unchanged from `953bf8928ac780b2c7a922b4e2a8ddf05b87e96d`: package 29 changed only development/test plumbing. The historical `8b04c511…` and `8f505f26…` binary pair was not available in the downloaded old run evidence; the reproduced pair above isolates the defect on the same production inputs. The two historical binaries were not compared directly.

The fix uses Loom's own `ZipReprocessorUtil.transformZipEntry` in a final jar action, registered after Loom's configuration. Gradle's manifest writer handles UTF-8 encoding, required first `Manifest-Version` and line folding. Every original attribute/section is retained; list membership is unchanged. The same reversed-file experiment after the fix is byte-identical. No class/resource payload or runtime behavior changes. This small postprocessing step is necessary because Loom adds the unsorted list after Gradle writes the jar, with no configuration hook for its ordering.

Sources inspected: [Loom 1.19.2 source archive](https://maven.fabricmc.net/net/fabricmc/fabric-loom/1.19.2/fabric-loom-1.19.2-sources.jar), specifically `NonRemappedJarTaskConfiguration`, `ManifestModificationAction`, `ClientEntriesService`, `JarManifestService` and `ZipReprocessorUtil`; [Gradle archive options](https://docs.gradle.org/9.8.0/dsl/org.gradle.api.tasks.bundling.AbstractArchiveTask.html).

## Verified

All local builds ran serially after `free -g`, with the dev scripts' memory/game checks intact. No `--force`, system installation or sudo. Available memory before the builds was 6–8 GiB. The scripts use owned systemd scopes and `--no-daemon`; each printed `Daemon will be stopped at the end of the build` and cleaned up its scope. No persistent daemon was started, and no global daemon stop was used against other builders.

### Laptop diagnosis and regression

Starting commit: `64611f33` (clean worktree, before package 38 changes).

```text
mod/dev/build.sh --console=plain
BUILD SUCCESSFUL in 39s
17 actionable tasks: 16 executed, 1 up-to-date
All 38 required tests passed :)

sha256sum .work/repro/baseline-first.jar
c0e5cf1e1b0dfb8eead4586665c38de844be41bae7edc74d460276a2a69d70fc
```

The second checkout was created inside this worktree with:

```bash
git clone --quiet --no-checkout --depth=1 "file://$PWD" .work/second-checkout
git -C .work/second-checkout sparse-checkout set mod
git -C .work/second-checkout checkout --quiet
.work/second-checkout/mod/dev/build.sh --console=plain
```

That build produced the identical jar but exited 1: `62 tests completed, 17 failed, 6 skipped`, all 17 fake-helper failures were `java.net.SocketException: Unix domain path too long`. The existing tests put their socket under `build/tmp/unit-tests`. Renamed the checkout to `.work/b`; no test or assertion was changed. Rebuilt there through `source .work/b/mod/dev/env.sh`, `aresos_find_java`, `aresos_check_room 0` and `aresos_scoped ... -- "${ARESOS_GRADLE[@]}" jar --console=plain` (the image's `--no-daemon jar` task). It passed in 7s.

For the filesystem-order experiment the following code recreated compiled outputs, then the same scoped `jar` command ran again. It printed `compileClientJava UP-TO-DATE`, `Task :jar`, `BUILD SUCCESSFUL in 4s`, so compilation did not undo the perturbation:

```python
root = Path('.work/b/mod/build/classes/java/client')
files = [(p.relative_to(root), p.read_bytes(), p.stat())
         for p in root.rglob('*') if p.is_file()]
shutil.rmtree(root)
for rel, data, stat in sorted(files, reverse=True):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
Path('.work/b/mod/build/libs/aresos-0.1.0.jar').unlink()
```

Ran `sha256sum`, `unzip -lv` on both archives, and compared entry order, contents and metadata using Python `zipfile`. Listings have the same order/times/modes; the manifest's CRC/compressed data differ. Full comparisons are in [archive-comparison.txt](archive-comparison.txt).

### Fixed builds in different laptop folders

At build-source commit **`0dc3959dbcd62e4ed4a9d1289a0d719ed1580b57`**, fetched that commit into the second checkout and deleted only its generated `mod/build/` before rebuilding:

```text
mod/dev/build.sh --console=plain
BUILD SUCCESSFUL in 32s
17 actionable tasks: 6 executed, 11 up-to-date

(umask 077; export TZ=Pacific/Honolulu LC_ALL=C; .work/b/mod/dev/build.sh --console=plain)
BUILD SUCCESSFUL in 40s
17 actionable tasks: 15 executed, 2 up-to-date

sha256sum mod/build/libs/aresos-0.1.0.jar .work/b/mod/build/libs/aresos-0.1.0.jar
dacae565e4f837faf5323d6cc8fb1efce1acc03577fcb904a2c0fa1a8f5a63be  mod/build/libs/aresos-0.1.0.jar
dacae565e4f837faf5323d6cc8fb1efce1acc03577fcb904a2c0fa1a8f5a63be  .work/b/mod/build/libs/aresos-0.1.0.jar
cmp: exit 0
```

Both full builds passed **38/38 server game tests** and **56 unit tests**, with **6 Windows-only skips**, zero failures/errors. Repeated the class-output reversal and `dev/build.sh`: `BUILD SUCCESSFUL in 20s`; both jars still had the hash above (`cmp`: exit 0). Server game tests passed again; unit tests were up-to-date on this repeat.

The first implementation attempt failed in 6s because Gradle 9.8 no longer exposes `project.manifest()`; corrected it to the public `JavaPluginExtension.manifest()` factory before the passing builds. No checks were weakened.

The final archive has fixed DOS timestamps: 1980-02-01 for ordinary entries and 1980-01-01 for the manifest, whose timestamp Loom's rewriter fixes separately. Ordinary file/directory modes are 0644/0755; the rewritten manifest has fixed DOS creator/zero external attributes. These metadata are identical before/after the patch and in the perturbed build.

### Image-style cold-cache build

Deleted the second checkout's generated `mod/build/`, set an empty `GRADLE_USER_HOME` under `.work/repro/gradle-clean`, sourced `mod/dev/env.sh`, checked Java/memory/game state, and ran `aresos_scoped repro-image -- "${ARESOS_GRADLE[@]}" jar --console=plain`. This matches the image's Gradle invocation (`--no-daemon jar`) and cold cache, with the same Temurin release:

```text
BUILD SUCCESSFUL in 1m 3s
6 actionable tasks: 6 executed
sha256sum .work/b/mod/build/libs/aresos-0.1.0.jar
dacae565e4f837faf5323d6cc8fb1efce1acc03577fcb904a2c0fa1a8f5a63be
```

The cache, extra checkout and downloaded old-run evidence were deleted after this comparison.

### GitHub and laptop proof

Build commit **`cea4b73bd2e03b89e60fb86c2faacf14b6e86481`**, [run **43480222519**](https://github.com/Ares-Empire/AresOS/actions/runs/43480222519):

```text
Laptop SHA-256:
dacae565e4f837faf5323d6cc8fb1efce1acc03577fcb904a2c0fa1a8f5a63be
GitHub first checkout SHA-256:
dacae565e4f837faf5323d6cc8fb1efce1acc03577fcb904a2c0fa1a8f5a63be
GitHub second checkout SHA-256:
dacae565e4f837faf5323d6cc8fb1efce1acc03577fcb904a2c0fa1a8f5a63be
```

The laptop's local full/cold builds above used exactly the same `mod/` tree as this commit, **`23bef44dd2e8b718e8eee525ecb92b28cfc8c007`**. The follow-up changed only the workflow, and the final report commit changes only review artifacts; **the expected hash for this branch's head is the hash above**. A clean laptop build and the automatic PR run are repeated on the final report commit before handoff; their exact head/run are recorded in the PR description.

Started with `~/.local/bin/gh workflow run mod.yml --ref pkg/38-reproducible-jar`, waited with one blocking `gh run watch 43480222519 --exit-status` (exit 1; no polling loop), and read `gh run view 43480222519`, its complete logs and the uploaded hash file. `gh run download 43480222519 -D .work/repro/ci-code` downloaded both artifacts. Independently hashed the uploaded jar and compared its complete bytes with the laptop jar: identical. The summary/hash step and artifact upload passed. Both server test runs passed all 38 required tests. First full build: `BUILD SUCCESSFUL in 1m 14s`, 56 unit tests passed / 6 Windows-only skips. Second full build: `BUILD FAILED in 37s`, 55 unit tests passed / 1 failed / 6 skipped.

**The workflow is red, so the green-CI acceptance is not met.** It detected the pre-existing startup replay race described below. The second checkout's retained XML shows the exact wire-ID mismatch: expected `[first, second]`, received `[first, first, second]`. The independent two-build byte comparison and cross-machine equality both passed. This is not reported as a fully green package and the test has not been weakened or retried automatically.

### Existing test failure exposed by GitHub

The first hosted run, [43479256953](https://github.com/Ares-Empire/AresOS/actions/runs/43479256953), at `0dc3959dbcd62e4ed4a9d1289a0d719ed1580b57`, failed: `BUILD FAILED in 1m 18s`; `62 tests completed, 1 failed, 6 skipped`. All 38 server game tests passed. The failing assertion was `ShellClientTest.eachOpenIsOneRequestWithItsOwnId`, line 194, which compares the exact list of wire request IDs. It was not skipped or weakened, and this failed run is not counted as passing evidence.

`ShellClient.session()` publishes the connection and completes readiness before it queues replay of pending requests. A caller can add its first open in that interval; both the original send and startup replay then carry the same ID. The helper's journal prevents a second actual launch, but this violates the existing exact-request-count assertion. This is a pre-existing race in unchanged production code, not jar serialization. A controlled probe using the actual compiled `ShellClient` and existing `FakeHelper`, with an open from the first apps listener, reproduced it deterministically:

```text
connections=1
open_app wire requests=2
unique request IDs=1
actual launches=1
```

[StartupReplayProbe.java](StartupReplayProbe.java) is the diagnostic source, outside all mod source sets. It was compiled/run under the same Java 25 dev environment and owned scopes, with `javac -cp <main classes>:<test classes>:<cached gson jar> -d .work/repro/probe-classes ...` and `java -cp <probe classes>:<same classpath> dev.aresos.shell.StartupReplayProbe <absolute .work/repro path>`; exit 0. The apps-listener barrier forces the existing race instead of depending on CPU scheduling. The test's failure and the startup replay ordering still need a separate runtime fix; this brief explicitly forbids changing mod behavior. A later successful build cannot establish that this pre-existing test is stable.

Workflow follow-up commit `cea4b73bd2e03b89e60fb86c2faacf14b6e86481` preserves both checkouts' test-result XML and completes the independent jar comparison even after a test failure. No `continue-on-error`, test filter, automatic test retry or assertion change was added. All failing test outcomes remain failures.

### Pins and final housekeeping

- JDK: **Eclipse Temurin 25.0.5+8**, exactly the package 23 image `docker.io/library/eclipse-temurin:25.0.5_8-jdk-noble@sha256:95e350ad1eb738f943e141640f7e3d797e483359a3b33c3864255bfd1ad71f8a`. Laptop `~/.local/opt/jdk-25/bin/java -version` prints `Temurin-25.0.5+8` / `build 25.0.5+8-LTS`.
- Existing pins retained: wrapper **9.8.0** with distribution SHA-256 `bafd5ce9cfaea0fbccfdc8439a1ac42fbd4cd9c89dc9a988228d8a2639a58e6c`; Loom **1.19.2**; Minecraft **26.2**; Loader **0.19.5**; Fabric API **0.161.0+26.2**. No dependency upgrades.
- Added explicit UTF-8, en/US, UTC, archive order/timestamps/modes, and sorted manifest serialization. Workflow actions are pinned to full commits (checkout, cache, artifact upload).
- `git diff --check`: exit 0. Workflow YAML parsed successfully with PyYAML; checked read-only permissions, standard runner and absence of `continue-on-error`. A jar byte scan found no absolute build-path strings. `git diff 64611f33 HEAD -- mod/src mod/dev os STATE.md HANDOFF.md CLAUDE.md` was empty. Local diagnostic jars and logs stay ignored under `.work/`; no game assets were committed.
- Removed `.work/b`, the cold Gradle cache and downloaded old-run evidence. Final `.work/` listing for files over **500 MB**: **none**. Only small diagnostic jars/logs remain ignored.

## Not verified

- No client game tests or manual play: the brief explicitly exempts this package when no source set/resource changes. None changed. No screenshots are needed.
- No OS image rebuild or pin update: forbidden by this brief. The OS lead can pin the jar hash above in their separate package.
- No direct binary comparison of the two historical jars (see cause section).
- CI stability of `ShellClientTest.eachOpenIsOneRequestWithItsOwnId`: a real startup replay race was exposed and deterministically reproduced; its runtime fix is outside this brief.
- No claim of identical output from other JDK builds or future tool/dependency versions: use the documented pins.

## JUDGMENT-CALL

None affecting the desktop feel or hard to undo. The manifest normalization is confined to build configuration, keeps all values/membership, and uses the already pinned Loom implementation rather than changing plugin versions or runtime code.

## PLAN-GAP

The brief assumes the existing unit suite is stable on GitHub. The first hosted run exposed the startup replay race described above. Reliable green checks need a separate authorized runtime fix; hiding the failure or relaxing the assertion would violate the brief and AGENTS.md.

The original partial archive-order/timestamp configuration could not fix an unsorted string inside the manifest. Loom provides no sorting switch on this path, so the brief's explicitly permitted small final action is used. A deeply nested extra checkout also exceeds the existing fake-helper Unix socket path limit; the shorter `.work/b` path solves this verification issue without modifying tests.

## Open questions

The existing startup replay race needs a separate runtime-fix package before CI stability can be claimed. The OS jar-pin update remains with the OS lead. Fresh independent package review remains the normal next workflow step; the builder did not review their own PR.
