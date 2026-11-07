# 17e checkpoint qualification — CHECK ONLY

This is a disposable experiment, not AresOS's tool service. Read
`briefs/17e-chrome-checkpoint.md` and the report before interpreting a green job.
Green means the recorded experiment and receiver audit completed; the report
separately says which qualification conditions hold.

All browser/profile operations require `linux` and `GITHUB_ACTIONS=true` before
browser helpers are imported. Never run a browser on the owner's Mac. CI runs
official branded stable Chrome, headed under Xvfb, with its sandbox, without a
debugging port or certificate-error flags. Diagnostic CDP goes through the
policy-installed extension and the existing native-messaging relay.

The runner creates `areschrome` and `aresproxy`. An inet nftables output chain
permits the browser uid only TCP to `127.0.0.1:18080`; IPv4/IPv6 and UDP are
otherwise rejected. Fixed-proxy policy removes implicit loopback bypasses.
The proxy CA key and SQLite ledger are in an `aresproxy`-owned 0700 directory;
its control socket is not accessible to the browser. Xvfb's disposable authority
cookie is copied into the synthetic browser home, never uploaded.

`checkpoint.py` uses mitmproxy 12.2.1, upstream certificate validation, lazy
connections and non-streamed requests. HTTP requests, WS handshakes, reassembled
messages and payload-bearing control frames wait at the checkpoint. The WS
control-frame seam wraps a pinned upstream layer immediately before SendData;
the public websocket_end hook is too late. This seam needs requalification on
every mitmproxy update. Unsupported opaque TCP tunnels are disabled.
Unexpected addon or event-loop errors stop the entire checkpoint: upstream's
default log-and-continue behavior cannot be used for this boundary.
Upstream certificate sniffing is disabled so generating a browser-facing leaf
does not require contacting the destination before its held request is approved.
Known oversized finite uploads are discarded in bounded chunks and receive 413;
they never become an empty-body approval. This uses another small pinned HTTP
layer seam, since an early close left Chrome's upload promise pending in CI.

Approval identifies a RAM-held flow by an independent operation ID. SQLite
WAL/FULL consumption precedes forwarding. Restart marks consumed operations
unknown and unconsumed captures lost; neither is replayed. Missing/forged/stale
attribution never grants permission. The experiment deliberately guards the
whole browser, including GET, to measure a conservative boundary. Account and
document generation changes are signaled by the trusted diagnostic runner;
this is not an automatic account detector or a production approval endpoint.

The four workflow phases are:

- `core`: routing, connections, attribution, complete bodies, competitions,
  chunked and fragmented wire clients, exhaustion and proxy outage.
- `lifecycle`: durable barriers, crashes, cancellation and retained outboxes.
- `transports`: independent HTTP/3 and WebRTC/TURN peers, TLS and service probes.
- `public`: the same ten anonymous public visits, direct and intercepted in one
  job, fingerprint echo, resources, synthetic background hold counts and a real
  service notification answered through 17d's dunst action-menu helper.

Python dependencies are locked in `requirements.lock`; `requirements.txt` lists
the direct choices. The unchanged 17d WebTransport receiver uses its own pinned
aioquic 1.3.0 environment because mitmproxy requires aioquic 1.2.0. Added OS
packages and the runner distribution are fixed in the workflow. Chrome stable's
actual version, resolved dependencies, commit and run ID are printed per job.

Artifacts contain receiver hashes/lengths, checkpoint IDs/states, timings and
screenshots. They contain no request bodies, cookie/header values, private keys,
profiles or SDP. Raw Chrome/mitmproxy console files stay outside artifacts and
are deleted at shutdown. Public fingerprint output is reduced to fingerprints;
the IP/echoed headers and its screenshot are not retained. Body buffers have
32 MiB per-operation and 64 MiB pending limits, 256 captures, 90-second expiry,
and a 768 MiB process address-space ceiling. Metadata exhaustion refuses sends.
These limits are experiment settings, not recommended owner budgets.
