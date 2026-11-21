CHANGES-NEEDED

**1. OPEN — App identity.** The default-deny rule still admits the stock Deskflow Flatpak if the native launch resolves to `org.deskflow.deskflow`, which the Flatpak already uses without impersonation. Require package (c) to prove through the real frontend that the native launch is accepted and the stock Flatpak is refused before enabling sharing, and keep sharing disabled if their IDs collide.

**2. RESOLVED — Session routing.** The brief requires one armed session, binds barriers and activations to their session, limits EIS devices to granted capabilities, and checks clipboard transfers against their session. Every backend method checks the frontend caller, and the harness exercises caller, session and capability refusals.

**3. RESOLVED — Teardown.** Session close, frontend loss and EIS loss must end capture, remove barriers and drop the clipboard claim. The harness checks that the next crossing stays local, tests EIS loss both before and during capture, and verifies Super+Shift+Escape under the exclusive grab.

**7. RESOLVED — Harness isolation.** The brief requires a disposable rootless container with scratch home, config and runtime directories, verified private endpoints, and exclusion of host display, bus and input-device mounts. It forbids activation-environment updates and upstream installer execution, and scopes timeouts and cleanup to the harness.
