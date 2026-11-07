# 17c Chrome pages — feasibility check only

Run exclusively in GitHub Actions on Linux, headed branded Chrome with its sandbox enabled. The runner refuses every other platform. No browser/profile is accessed by local syntax checks.

Extends 17/17b's signed policy install, native transport and fixture approach. `wrap.js` provides cooperative call queues, `background.js` fails HTTP fallbacks immediately, and `fixture.mjs` logs independent receiver arrivals. Raw RPC, origin-only fixture guards, a globally exposed test queue and synthetic adapter evidence are intentional experimental shortcuts, never product security claims. Negative coverage results are recorded as findings; receiver expectations are asserted through browser shutdown.

Phases: `pages`, `guards`, `public`. Evidence includes exact version/head, server log, summary, final delivery audit, initiator stacks, worker events, public traffic, screenshots. Public checks block non-reading HTTP, Fetch/XHR/Ping, new sockets and live transport constructors, and bypass service workers; they cannot establish normal signed-in site behavior.
