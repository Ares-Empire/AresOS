# Scoped security re-check — aaf3d4b1

Reviewer: gpt-6-astra (xhigh), read-only.

**FIX — native DOM method clobbering.** The animation scan called
`root.querySelectorAll` on watched receivers. A form's input named querySelectorAll
shadows that method. A production-guard probe returned activation_unknown with
raw href/blank-target authority intact, and left an earlier animation permanently
changed. Save native query methods, collect before mutation and cover the watched
clobbering form in receiver and restoration probes.

**FIX — lost restoration records.** Retargeting or detaching an animation between
two native activations removes it from the second scan. That scan replaced the
old record and invalidated its timer, leaving the quarantine property name
permanent. Preserve outstanding earlier records; restore only unchanged markers.
Production-guard probes reproduced both cases.

Native animated URL binding and empty-target handling otherwise passed this
scope. **163 exact-source reader/page tests passed**, with no failures or skips;
additional probes exposed the gaps. Browser replacement, latency and final CI
remain pending. No edits, local browser/profile, container or GitHub mutation.

CHANGES-NEEDED
