Reviewed `6aa4961`, including the retained CI artifacts. The brief permits the disclosed standalone-runtime reproduction; native-runtime uncertainty alone is not a finding.

1. **blocking — Network tests can pass when domain enforcement is broken.**  
   Where: [hostile.py:90](/Users/pab/AresOS-18b-control-boundary/control/boundary/hostile.py:90), [workflow:42](/Users/pab/AresOS-18b-control-boundary/.github/workflows/control-boundary.yml:42).

   Every nonzero curl exit counts as containment. But Docker runs with `--network none`, `blocked.boundary.test` has no configured destination, and the loopback receiver is never addressed by either hostname probe. Allowing every domain could therefore produce DNS/routing failures and still pass. The retained runs show HTTP 403, but CI does not require that result.

   **Fix:** use a deterministic, live destination reachable by the outside proxy. Prove the identical request reaches its receiver when allowed, then require a policy refusal and zero arrivals when denied. Confirm that disabling the restriction makes the test fail.

2. **should-fix — “No IDE integration” is assumed rather than enforced.**  
   Where: [launcher.c:13](/Users/pab/AresOS-18b-control-boundary/control/boundary/launcher.c:13), [launch.py:49](/Users/pab/AresOS-18b-control-boundary/control/boundary/launch.py:49).

   Starting the CLI directly does not establish isolation from IDE integrations. Anthropic documents that `autoConnectIde` in `~/.claude.json` can make an external-terminal session connect automatically; `CLAUDE_CODE_AUTO_CONNECT_IDE` overrides it. The launcher supplies no disabling value, and tests replace global configuration with harmless fixtures. Nothing demonstrates that `--setting-sources ''` excludes this separate global setting. This leaves an integration route outside the shell sandbox unqualified. [Anthropic reference](https://code.claude.com/docs/en/settings-reference#autoconnectide).

   **Fix:** force IDE auto-connection off in the fixed environment and test with `autoConnectIde: true` plus a discoverable fake IDE listener. Require a working positive control and zero launched-session connections.

3. **should-fix — Replacement probes often fail before testing destination protection.**  
   Where: [hostile.py:57](/Users/pab/AresOS-18b-control-boundary/control/boundary/hostile.py:57), [REPORT.md:74](/Users/pab/AresOS-18b-control-boundary/reviews/18b-control-boundary/REPORT.md:74).

   All replacements use a source inside the read-only work mount. In each retained mode, **16 of 32** replacement attempts return `EXDEV`; another seven return `ENOENT`. Cross-mount rename failure would occur even with a writable destination. Unchanged hashes establish that these attempts caused no damage, but do not establish the claimed replacement protection.

   **Fix:** prepare independent replacement sources beside their targets, verify the same operations succeed outside containment, and distinguish hidden targets from permission refusals. Do not count `EXDEV` as evidence that destination writes are blocked.

4. **nit — The settings table attributes a Linux result to an ineffective key.**  
   Where: [managed-settings.draft.comments.md:35](/Users/pab/AresOS-18b-control-boundary/control/settings/managed-settings.draft.comments.md:35).

   The table credits `allowLocalBinding: false` with keeping host-local services inaccessible and calls it checked by `network:direct`. Anthropic documents that this key has no effect on Linux; the separate network namespace explains that result. [Anthropic reference](https://code.claude.com/docs/en/settings-reference#sandbox-network-allowlocalbinding).

   **Fix:** mark the key inapplicable on Linux and attribute the observed refusal to network-namespace isolation.

I inspected code and saved evidence; I did not rerun Linux CI or independently verify the final-head GitHub checks.

CHANGES-NEEDED