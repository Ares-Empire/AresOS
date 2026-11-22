# Package 334a progress

## Done

- Added the bench-only image layer, passwordless disk recipe, offline VM script runner, and authenticated helper probe.
- Added dispatch exclusions, raw-layer inspection with a masked-file fixture, and a separate evidence gate.
- Local bench unit modules passed individually (13 tests). The shell refuses local and self-hosted invocations before calling any tools.
- Passing-case dispatch queued on the implementation commit at run 45072067558. It passed dispatch validation and evidence refusal tests.
- Negative-case dispatch 45072177942 captured the temporary helper change. The branch now has the explicit revert.
- The separate hosted Mod build was dispatched as 45072215651.

## Left

- Wait for the bench runs, verify evidence and timings, and run the standard hosted OS checks on the restored branch.
- Replace this file with the closing report and open the PR after acceptance.

## Runtime details

- The disk is built from the plain CI image. The negative change affects only the protocol handler for `list_apps`, so static helper imports and the standalone `--list` remain available.
- The runner uses the guest's installed source revision as an independent comparison to the bench image label and the dispatch SHA.
