# 38: The mod jar builds the same everywhere

Empire board brief 285. Build plumbing for `mod/`, asked for by the OS lead (`linux-aresos`, 2026-11-13).

**Builder:** Codex (gpt-6.1-sol, xhigh): build configuration and a CI job, nothing about looks. **Review:** a fresh reviewer that isn't the builder.

## Why

The AresOS image carries the mod as a jar, and a release pins that jar's hash. The same `mod/` source (commit `953bf892`) built `8b04c511…` on 2026-11-10 and builds `8f505f26…` now; only the machine that built it changed. The OS lead's unproven guess: one line in the jar's manifest lists the client classes in file-system order instead of sorted. A release cannot pin a jar that differs from build to build.

Also, the mod's tests have only ever run on a developer's machine. Since package 29 they pass on Linux, so they can run on GitHub for every change to `mod/`, as the Empire's other repos do.

**Goal:** the same commit gives a byte-identical `aresos` jar on the owner's laptop and on a GitHub runner, proven by its hash, and every pull request that touches `mod/` builds the mod and runs its unit tests and server game tests on GitHub.

## Build

1. **Find the cause, don't guess.** Build the jar twice on the laptop in two different folders (two clones, different paths, different file order if you can force it) and compare: `sha256sum`, then the archives' listings (`unzip -lv`, entry order, times, modes) and the files that differ (`META-INF/MANIFEST.MF`, the refmap, the mixin and mod json files, classes). Name every difference and its cause in the report. The image builds the jar in `eclipse-temurin:25.0.5_8-jdk-noble` (see `git show origin/pkg/23-minecraft-starts:os/Containerfile` and `os/build.sh` there, mode `mod`; read-only, do not touch that branch): build the same way.
2. **Make it reproducible** in `mod/build.gradle` (and `gradle.properties` if needed): fixed file order and no file times in every archive task (`preserveFileTimestamps = false`, `reproducibleFileOrder = true`, fixed file modes), a sorted and stable manifest (if Loom writes a client-entries line in file-system order, sort it or have Loom do so; say which and why it is safe), nothing in the jar that depends on the build's path, user, host, time zone, locale or date. No change to what the mod does. Keep the jar's name and where the image's build expects it.
3. **A CI workflow `.github/workflows/mod.yml`**, on pull requests and pushes that touch `mod/**` or the workflow itself, and by hand (`workflow_dispatch`):
   - builds in the same JDK the image uses (the same Temurin 25 build; pin it the way the image does or as a pinned setup step, and say which), with Gradle's caches cached;
   - runs `./gradlew build` (unit tests and server game tests; no client tests, they need a display and a GPU);
   - prints the jar's SHA-256 in the job summary and uploads the jar as an artifact;
   - builds a second time from a clean checkout in another path in the same job and fails if the two hashes differ.
   Standard free runners only; no secrets; minimal permissions (`contents: read`).
4. **Prove it across machines:** the hash from `mod/dev/build.sh` on the laptop (this worktree, a clean tree at your head commit) equals the hash of the workflow run on the same commit. Put both hashes, the commit and the run's URL in the report. If they differ, find out why (JDK build, Gradle version, line endings, the environment) and fix or pin it; do not stop at "close".
5. **Docs:** `mod/README.md` gets a short "The same jar everywhere" paragraph (what is pinned, how to check). Do not edit `os/`, `STATE.md`, `HANDOFF.md` or `CLAUDE.md`.

## Acceptance

- Two builds in different folders on the laptop: identical hash, with the commands and output in the report.
- The workflow is green on the PR, its own double build agrees, and its hash equals the laptop's for the same commit.
- `mod/dev/build.sh` passes. The client tests are not needed for this package unless a source set or a resource changed; if one did, `mod/dev/client-test.sh` passes once.
- `reviews/38-reproducible-jar/REPORT.md` in the AGENTS.md format, with the cause of the old difference stated plainly, and the hash the OS lead can expect for your head commit.

## Out of scope

Any change to the mod's behaviour, the image, its pins or its build script. Client tests on GitHub.

## Already decided

- The jar is built by Gradle as today; reproducibility is configuration, not a post-processing script, unless Loom leaves no other way (then say so and keep it small).
- `mod/build.gradle` is also edited by packages 32, 33 and 34 (each adds a system property line for its screenshot folder): keep your change in a block of its own so merges stay easy.

## If unsure

Pin more rather than less, and say what you pinned.

## Rules

- `AGENTS.md` applies. Worktree `/var/home/ares/AresOS-38-reproducible-jar`, branch `pkg/38-reproducible-jar` (it has package 29's dev scripts merged in; do not edit `mod/dev/`). Push it and open a PR against `main` with `~/.local/bin/gh pr create`. Never merge, never push to `main`, never `--no-verify`.
- On the laptop build only through `mod/dev/build.sh`, or, for the extra clone in another folder, with the same environment (`source mod/dev/env.sh` style: Java 25 from `~/.local/opt/jdk-25`, `--no-daemon`). While the script refuses (exit 75: the owner's game runs, or under 6 GiB available), wait with a blocking sleep of several minutes. Never `--force`. Delete extra clones when done.
- No sudo, no system installs. Don't touch other worktrees, `~/AresOS` itself, `~/.minecraft` or `~/.lunarclient`.
- The repo is public: no personal data.
- Commit messages end with a trailer naming the model.
