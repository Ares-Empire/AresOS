**4. Daily use — cross-check**

**1. Claims needing correction or qualification**

- **Security’s opening is too broad:** real-account *reading* need not wait for a transaction-approval device. **Checked:** Gmail, for example, offers separate `gmail.readonly` and `gmail.send` scopes. [Google’s scope reference](https://developers.google.com/workspace/gmail/api/auth/scopes) **Inference:** qualified read-only access can precede phone pairing, provided alternate write routes are blocked and the owner approves the data/model scope. This does not establish compatibility with the owner’s unknown provider.
- **Skeptic’s Claude authentication caveat checks out:** API keys and `setup-token` credentials do not enable Chrome integration; interactive `/login` is required. An unattended-startup brief cannot assume otherwise. [Claude documentation](https://code.claude.com/docs/en/chrome)

**2. Where I disagree**

**Assumed judgment:** Security’s separate browser profile is a sensible laboratory default, but it does not satisfy “help with this already-open form.” Existing-tab handoff should be an early synthetic acceptance test unless the owner explicitly accepts a separate working profile.

I also would not settle phone-only confirmation before the owner tries the workflow. Independent authorization is necessary for automated writes; the phone is a proposed implementation. Keep sending manual while that choice remains unresolved.

**3. What changes my findings**

- **Security changes my entry-point recommendation:** I withdraw the implication that recovery help and the daily companion should reuse one unrestricted Claude session. They can share presentation, but not authority. Otherwise mail content can reach a session capable of bypassing the broker. The existing design explicitly says its same-user socket is not that security boundary. [OS-BASE §B1](../../../docs/design/OS-BASE.md:236)
- **System moves browser packaging earlier:** I checked that the build makes the installed `flatpak` executable root-only. Choosing and qualifying the browser package belongs before promising week-one integration, not merely in first-boot troubleshooting. [build.sh](../../../os/build.sh:93)
- **Assumed revision:** add System’s explicit “outcome unknown” state to the user-facing task lifecycle. After an uncertain send, “Retry” must not silently mean “send another copy.”

**4. What everyone missed**

**Assumed gap: we never completed the manual-send handoff.** A local reply draft can still leave the owner finding the original message, selecting the correct sending account, copying text and restoring attachments. That may consume the time supposedly saved.

The acceptance test should continue through the owner’s mail client: open the intended conversation, prepare the correct reply, let the owner edit it, then manually send to the fixture mailbox. Verify recipients, attachments and reply ancestry, and count the required handoffs. **Checked:** reply ancestry has defined `In-Reply-To` and `References` headers; matching the subject alone is insufficient evidence. [RFC 5322 §3.6.4](https://www.rfc-editor.org/rfc/rfc5322.html#section-3.6.4)

**Assumed verdict:** build the synthetic prototype and qualified read/prepare workflows now; retain the separate gate for real automated writes.

BUILD