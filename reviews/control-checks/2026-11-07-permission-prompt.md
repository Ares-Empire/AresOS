# Check: what Claude Code's approval prompt shows (2026-11-07)

**Question:** when an AresOS tool is marked "asks first", does Claude Code still ask in skip-permissions mode, and
does the prompt show everything the owner needs to judge a send?

**Setup (on the MacBook, throwaway folder, nothing real):** Claude Code 2.1.319, interactive, started with
`--dangerously-skip-permissions --strict-mcp-config`, one fake MCP server `testmail` whose `send_mail` tool only
logs the call, and a settings file with one rule: `{"permissions": {"ask": ["mcp__testmail__send_mail"]}}`. Claude
was asked to call `send_mail` once with to, cc, bcc, a subject, a 25-line body and one attachment (path + sha256).
The screen was captured through a pseudo-terminal.

**Result:**

- The prompt appeared although the session ran in skip-permissions mode ("bypass permissions on"), naming the rule:
  "Permission rule mcp__testmail__send_mail requires confirmation for this tool."
- Every input field was shown in full: to, cc, **bcc**, subject, all 25 body lines, and the attachment's path and
  hash.
- Refusing (Esc) meant the tool was never called: the fake server logged `initialize` and `tools/list`, and no
  `tools/call`.
- The prompt also offers "2. Yes, and don't ask again for testmail — Send Mail commands in <folder>". That option
  must not be able to switch the rule off in AresOS; check it with the managed settings
  (`allowManagedPermissionRulesOnly`) when the real settings are written.

**Not checked here:** a much longer body (does the prompt cut it off?), approving through remote control (the owner
confirmed on 2026-11-07 that he approves pushes through it), and managed (system-wide) settings on Linux.

**What it means for the tools:** an action that asks must carry everything the owner needs to decide in its own
input (full recipients, text, attachment paths and hashes; for Chrome the site, the address and the data being
sent), and the tool must refuse if the input does not match what would actually happen.

## The captured prompt

```text
❯ This is a permission-prompt test with a fake tool; nothing is really sent. Do not run any other tool and do not name the session. Call
  mcp__testmail__send_mail exactly once with: to ["anna@example.com"], cc ["ben@example.com"], bcc ["hidden-copy@example.com"], subject
  "Offer for the flat, second version", body = 25 numbered lines "Line N: the quick brown fox jumps over the lazy dog." (N from 1 to 25,
  joined with newlines), attachments [{"path": "/home/ares/Documents/offer.pdf", "sha256": "9f2c0e1d"}]. Then stop.
⏺ I'll load the mail tool's schema first (it's deferred, so the call won't work without it), then send the one test mail.
  Calling testmail…
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
 Tool use
 testmail — Send Mail Tool: (MCP)
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 to: ["anna@example.com"]
 cc: ["ben@example.com"]
 bcc: ["hidden-copy@example.com"]
 subject: "Offer for the flat, second version"
 body:
   │ Line 1: the quick brown fox jumps over the lazy dog.
   │ Line 2: the quick brown fox jumps over the lazy dog.
   │ Line 3: the quick brown fox jumps over the lazy dog.
   │ Line 4: the quick brown fox jumps over the lazy dog.
   │ Line 5: the quick brown fox jumps over the lazy dog.
   │ Line 6: the quick brown fox jumps over the lazy dog.
   │ Line 7: the quick brown fox jumps over the lazy dog.
   │ Line 8: the quick brown fox jumps over the lazy dog.
   │ Line 9: the quick brown fox jumps over the lazy dog.
   │ Line 10: the quick brown fox jumps over the lazy dog.
   │ Line 11: the quick brown fox jumps over the lazy dog.
   │ Line 12: the quick brown fox jumps over the lazy dog.
   │ Line 13: the quick brown fox jumps over the lazy dog.
   │ Line 14: the quick brown fox jumps over the lazy dog.
   │ Line 15: the quick brown fox jumps over the lazy dog.
   │ Line 16: the quick brown fox jumps over the lazy dog.
   │ Line 17: the quick brown fox jumps over the lazy dog.
   │ Line 18: the quick brown fox jumps over the lazy dog.
   │ Line 19: the quick brown fox jumps over the lazy dog.
   │ Line 20: the quick brown fox jumps over the lazy dog.
   │ Line 21: the quick brown fox jumps over the lazy dog.
   │ Line 22: the quick brown fox jumps over the lazy dog.
   │ Line 23: the quick brown fox jumps over the lazy dog.
   │ Line 24: the quick brown fox jumps over the lazy dog.
   │ Line 25: the quick brown fox jumps over the lazy dog.
 attachments: [{ path: "/home/ares/Documents/offer.pdf", sha256: "9f2c0e1d" }]
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 About the testmail — Send Mail Tool:
 │ Send an email (TEST FAKE: nothing is sent).
 Permission rule mcp__testmail__send_mail requires confirmation for this tool.
 /permissions to update rules
 Do you want to proceed?
 ❯ 1. Yes
   3. No
 Esc to cancel · Tab to amend
```
