//! `org.freedesktop.impl.portal.InputCapture` and `.Clipboard` backend.
//!
//! xdg-desktop-portal owns the public-facing portal API and the Request objects;
//! a backend only has to answer the impl-side calls and emit the session
//! signals. That is why this implements the `impl.portal` interface rather than
//! standing up a second `org.freedesktop.portal.Desktop`.
//!
//! The backend hands out keystrokes and the clipboard, so every rule about who
//! gets them lives in [`State`]'s methods, and the D-Bus interfaces below only
//! unpack arguments and pack replies:
//!
//! - every method starts with [`State::authorize`]: the caller must be the
//!   current owner of `org.freedesktop.portal.Desktop`;
//! - a session exists only for an application on the allow-list, and only
//!   while the sharing switch says on ([`State::switch_locked`]): Off ends every
//!   session at once, and is read again wherever input or clipboard would leave;
//! - one session is armed at a time, and an activation goes only to it;
//! - a clipboard transfer goes only to the session it was announced to;
//! - a session that closes, loses its frontend or loses its EIS connection is
//!   removed whole: capture, barriers, clipboard claim and EIS devices.

use crate::{
    eis_server::{self, EisCommand, EisHandle},
    screens::{SharedScreens, Zone},
    sharing::{Gate, Switch},
    trust::{self, AllowList},
    wayland::{self, StartingWorker, WaylandCmd, WaylandEvent, WaylandHandle},
};
use std::{
    collections::{HashMap, VecDeque},
    os::fd::OwnedFd,
    os::unix::net::UnixStream,
    path::PathBuf,
    sync::{
        atomic::{AtomicU32, AtomicU64, Ordering},
        Arc, OnceLock,
    },
    time::Duration,
};
use tokio::sync::{mpsc, watch, Mutex};
#[cfg(test)]
use tokio::sync::oneshot;
use tracing::{debug, error, info, warn};
use zbus::{fdo, interface, message::Header, object_server::SignalEmitter, zvariant};
use zvariant::{ObjectPath, OwnedObjectPath, OwnedValue, Type, Value};

/// Capability bits, matching the portal spec.
pub const CAP_KEYBOARD: u32 = 1;
pub const CAP_POINTER: u32 = 2;
#[allow(dead_code)]
pub const CAP_TOUCHSCREEN: u32 = 4;

/// What this backend can capture, and so the most a session is ever granted.
const SUPPORTED_CAPABILITIES: u32 = CAP_KEYBOARD | CAP_POINTER;

const RESPONSE_SUCCESS: u32 = 0;

const PORTAL_PATH: &str = "/org/freedesktop/portal/desktop";
const DESKFLOW_ID: &str = "org.deskflow.deskflow";

/// Bounds on what one frontend may make the backend hold. Deskflow needs one
/// session, four barriers per screen and a handful of clipboard types.
const MAX_SESSIONS: usize = 16;
const MAX_BARRIERS: usize = 64;
const MAX_MIME_TYPES: usize = 64;
/// A longer type would not fit a Wayland message with the rest of the list.
const MAX_MIME_TYPE_BYTES: usize = 255;

type Results = HashMap<String, OwnedValue>;

/// How often the sharing switch is read while any session exists. The brief's
/// bound is 500 ms; half of it leaves room in the 2-second deadline from the
/// switch changing to the capture's end for the teardown and for the
/// compositor's confirmation ([`CONFIRM_TIMEOUT`]).
pub const SWITCH_INTERVAL: Duration = Duration::from_millis(250);

/// How long the compositor has to confirm that a capture is over: after Off
/// before the backend exits (and labwc drops the grab with the connection), and
/// before `ForceRelease` answers that it could not confirm.
pub const CONFIRM_TIMEOUT: Duration = Duration::from_secs(1);

/// How long a Wayland worker may take to bind what it needs and describe the
/// screens (the worker itself waits up to 5 seconds for the screens). The
/// process exits if startup times out, closing even a stuck socket.
const WORKER_START_TIMEOUT: Duration = Duration::from_secs(8);

/// A release or revoke arriving during shutdown waits on this same
/// compositor confirmation, even though every session has already closed.
type Teardown = watch::Receiver<Option<bool>>;

async fn teardown_confirmed(mut teardown: Teardown) -> bool {
    teardown.wait_for(Option::is_some).await.is_ok_and(|done| *done == Some(true))
}

/// How a worker is started: the real thread, or in tests a recorded handle.
enum Spawner {
    Wayland { idle_timeout: Duration },
    #[cfg(test)]
    Recording(Arc<std::sync::Mutex<Vec<RecordedWorker>>>, Arc<std::sync::atomic::AtomicBool>),
}

/// A worker the tests started: what was sent to it, and the sending end of its
/// events (dropped, the worker is gone as if its connection had ended).
#[cfg(test)]
struct RecordedWorker {
    cmds: calloop::channel::Channel<WaylandCmd>,
    events: Option<mpsc::UnboundedSender<WaylandEvent>>,
    ready: Option<oneshot::Sender<anyhow::Result<()>>>,
}

/// One zone as the portal wire format wants it: width, height, x, y.
#[derive(Debug, Clone, Copy, PartialEq, serde::Serialize, serde::Deserialize, Type, Value, OwnedValue)]
pub struct ZoneTuple {
    pub width: u32,
    pub height: u32,
    pub x: i32,
    pub y: i32,
}

impl From<Zone> for ZoneTuple {
    fn from(z: Zone) -> Self {
        Self {
            width: z.width,
            height: z.height,
            x: z.x,
            y: z.y,
        }
    }
}

/// A barrier the client asked us to watch.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Barrier {
    pub id: u32,
    pub x1: i32,
    pub y1: i32,
    pub x2: i32,
    pub y2: i32,
}

impl Barrier {
    pub fn is_vertical(&self) -> bool {
        self.x1 == self.x2
    }

    pub fn is_horizontal(&self) -> bool {
        self.y1 == self.y2
    }
}

/// One barrier as it arrives in `SetPointerBarriers`: its ID and position, each
/// missing when the client's dictionary lacked it or gave it the wrong type.
pub type BarrierSpec = (Option<u32>, Option<(i32, i32, i32, i32)>);

#[derive(Debug)]
pub struct Session {
    pub handle: OwnedObjectPath,
    pub app_id: String,
    /// What `Start` granted. EIS devices are cut down to this.
    pub capabilities: u32,
    /// The barriers this session set, and the zone set they were checked against.
    pub barriers: Vec<Barrier>,
    pub zone_set: u32,
    pub eis: Option<EisHandle>,
    /// False between `CreateSession2` and `Start`. The deprecated `CreateSession`
    /// produces a session that is started from the outset, which is the whole
    /// difference between the two.
    pub started: bool,
    /// Armed: its barriers are on the screen edges. At most one session is.
    pub enabled: bool,
    /// Non-zero while a capture run is in flight.
    pub activation_id: u32,
    /// The number of this session's last arming, zero while nothing of it is on
    /// the screen edges. Never used twice: a crossing counts only if it names
    /// this number, so one that was queued for an earlier arming, or for an
    /// earlier session with the same path, is refused.
    pub arming: u64,
    /// The Wayland thread's number for the crossing behind the capture run.
    pub crossing: u64,
    /// Set by `Clipboard.RequestClipboard`, which the spec requires before the
    /// session starts. `Start` reports it back as `clipboard_enabled`, and every
    /// other clipboard method refuses a session that never asked.
    pub clipboard_requested: bool,
}

impl Session {
    /// End this session's capture run, if it has one, and return its ID and
    /// the crossing it came from.
    fn stop_capture(&mut self) -> Option<(u32, u64)> {
        let id = std::mem::take(&mut self.activation_id);
        if id == 0 {
            return None;
        }
        if let Some(eis) = &self.eis {
            eis.send(EisCommand::StopEmulating);
        }
        Some((id, std::mem::take(&mut self.crossing)))
    }

    fn has_clipboard(&self) -> bool {
        self.started && self.clipboard_requested
    }
}

/// A read of the selection a session claimed, waiting for that session.
#[derive(Debug)]
struct Transfer {
    /// The only session that may collect it.
    session: OwnedObjectPath,
    fd: OwnedFd,
}

/// What the compositor says is on the clipboard right now.
///
/// Mirrored here rather than asked for on demand so that `SelectionOwnerChanged`
/// can be emitted the moment it changes, which is the only way a client learns
/// there is something new to copy across.
#[derive(Debug, Default)]
pub struct ClipboardTracker {
    pub mime_types: Vec<String>,
    /// True while the selection belongs to a portal session rather than a local
    /// application — the difference between "the remote machine copied this" and
    /// "this machine copied this".
    pub owned_by_session: bool,
    /// Which session claimed the selection, so `SelectionTransfer` goes to the
    /// one that can actually answer it.
    pub owner_session: Option<OwnedObjectPath>,
    /// Names the current claim. A paste the compositor asked of an earlier claim
    /// carries the earlier number and is dropped, so it can never be answered by
    /// the session that claimed afterwards.
    claim_id: u32,
    /// Reads of a session-owned selection, waiting for the client to answer with
    /// `SelectionWrite`. The fd is the compositor's own pipe: it is handed
    /// straight to the client so the content never passes through this process.
    transfers: HashMap<u32, Transfer>,
    /// Insertion order, so the oldest transfer is the one evicted.
    order: VecDeque<u32>,
    next_serial: u32,
}

/// How many unanswered reads to hold before dropping the oldest.
///
/// Every parked transfer is an open pipe. A client that is doing its job answers
/// within a round trip, so a backlog means nobody is going to: local applications
/// poll the clipboard constantly — a clipboard manager alone produces a steady
/// trickle — and without a cap those pipes accumulate until the process runs out
/// of file descriptors. Dropping the fd closes the pipe, which the waiting
/// application reads as "no data", the honest answer when the claim is unbacked.
const MAX_PENDING_TRANSFERS: usize = 16;

impl ClipboardTracker {
    /// Park a pending read for `session` and return the serial it answers with.
    fn begin_transfer(&mut self, session: &OwnedObjectPath, fd: OwnedFd) -> u32 {
        // Serial 0 is reserved so a missing value cannot look like a valid one.
        self.next_serial = self.next_serial.wrapping_add(1).max(1);
        let serial = self.next_serial;
        self.transfers.insert(
            serial,
            Transfer {
                session: session.clone(),
                fd,
            },
        );
        self.order.push_back(serial);

        while self.order.len() > MAX_PENDING_TRANSFERS {
            if let Some(stale) = self.order.pop_front() {
                // Dropping the fd is what signals EOF to the reader.
                if self.transfers.remove(&stale).is_some() {
                    debug!(serial = stale, "dropping an unanswered clipboard transfer");
                }
            }
        }
        serial
    }

    /// Hand a parked transfer to the session it was announced to. Any other
    /// session gets nothing, and the transfer stays parked for its owner.
    fn take_transfer(&mut self, session: &OwnedObjectPath, serial: u32) -> Option<OwnedFd> {
        if self.transfers.get(&serial)?.session != *session {
            return None;
        }
        self.order.retain(|s| *s != serial);
        self.transfers.remove(&serial).map(|transfer| transfer.fd)
    }

    /// Abandon every parked transfer, closing their pipes.
    fn clear_transfers(&mut self) {
        self.order.clear();
        self.transfers.clear();
    }
}

/// A signal for a client, kept apart from the bus so the rules can be tested
/// without one.
#[derive(Clone, PartialEq)]
pub enum Signal {
    Activated {
        session: OwnedObjectPath,
        activation_id: u32,
        barrier_id: u32,
        cursor: (f64, f64),
    },
    Deactivated {
        session: OwnedObjectPath,
        activation_id: u32,
    },
    Disabled {
        session: OwnedObjectPath,
    },
    ZonesChanged {
        session: OwnedObjectPath,
    },
    SelectionOwnerChanged {
        session: OwnedObjectPath,
        mime_types: Vec<String>,
        session_is_owner: bool,
    },
    SelectionTransfer {
        session: OwnedObjectPath,
        mime_type: String,
        serial: u32,
    },
    /// The backend closed the session: `Closed` on its impl-side Session object,
    /// which is then removed.
    SessionClosed {
        session: OwnedObjectPath,
    },
}

impl Signal {
    fn name(&self) -> &'static str {
        match self {
            Self::Activated { .. } => "Activated",
            Self::Deactivated { .. } => "Deactivated",
            Self::Disabled { .. } => "Disabled",
            Self::ZonesChanged { .. } => "ZonesChanged",
            Self::SelectionOwnerChanged { .. } => "SelectionOwnerChanged",
            Self::SelectionTransfer { .. } => "SelectionTransfer",
            Self::SessionClosed { .. } => "SessionClosed",
        }
    }

    fn session(&self) -> &OwnedObjectPath {
        match self {
            Self::Activated { session, .. }
            | Self::Deactivated { session, .. }
            | Self::Disabled { session }
            | Self::ZonesChanged { session }
            | Self::SelectionOwnerChanged { session, .. }
            | Self::SelectionTransfer { session, .. }
            | Self::SessionClosed { session } => session,
        }
    }
}

// The name and the session only: a signal carries the cursor position and the
// clipboard's types, and neither may reach a log through a `{:?}`.
impl std::fmt::Debug for Signal {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}({})", self.name(), self.session().as_str())
    }
}

/// Where the frontend's bus name is looked up.
enum Frontend {
    /// Ask the bus, for every call.
    Bus,
    /// A test sets the owner, and changes it to hand the name over.
    #[cfg(test)]
    Fixed(std::sync::Mutex<Option<String>>),
}

/// Where signals go, and where the impl-side Session objects are exported.
enum SignalSink {
    Bus,
    #[cfg(test)]
    Record {
        signals: Arc<std::sync::Mutex<Vec<(Option<String>, Signal)>>>,
        /// The paths that have a Session object.
        objects: Arc<std::sync::Mutex<std::collections::HashSet<OwnedObjectPath>>>,
    },
}

struct Trust {
    allow_list: PathBuf,
    allow_list_owner: u32,
    /// Whether sharing is on (`sharing.rs`).
    switch: Switch,
    frontend: Frontend,
    signals: SignalSink,
}

#[derive(Default)]
struct Inner {
    sessions: HashMap<OwnedObjectPath, Session>,
    /// Once teardown starts this process never admits a new session.
    teardown: Option<Teardown>,
    /// The unique bus name of the frontend that made every session in
    /// `sessions`: the one place their signals are sent to.
    frontend: Option<String>,
    clipboard: ClipboardTracker,
}

#[derive(Clone)]
pub struct State {
    inner: Arc<Mutex<Inner>>,
    next_activation: Arc<AtomicU32>,
    next_arming: Arc<std::sync::atomic::AtomicU64>,
    /// Signalled when the process must stop, with the reason for the exit.
    stop: Arc<tokio::sync::Notify>,
    stop_reason: Arc<OnceLock<Result<&'static str, &'static str>>>,
    /// Held while a Session object is exported or removed, so a removal can't
    /// take the object of a new session at the same path (`remove_session_object`).
    objects: Arc<Mutex<()>>,
    /// One worker per process. Keep its handle from launch through exit so
    /// Off and the release key can see it even during startup or teardown.
    worker: Arc<OnceLock<WaylandHandle>>,
    /// Serialize requests through worker readiness.
    worker_start: Arc<Mutex<()>>,
    crossings: Arc<AtomicU64>,
    spawner: Arc<Spawner>,
    screens: SharedScreens,
    keymap: eis_server::SharedKeymap,
    /// Signalled by each EIS task when its connection ends.
    eis_closed: mpsc::UnboundedSender<(String, u32)>,
    /// Filled in once the bus connection exists, which is after the interface
    /// itself has to be constructed.
    conn: Arc<OnceLock<zbus::Connection>>,
    trust: Arc<Trust>,
    /// Read by the input path (the Wayland thread and every EIS connection):
    /// closed the moment a read of the switch says off.
    gate: Gate,
}

fn unknown_session() -> fdo::Error {
    fdo::Error::InvalidArgs("unknown session".into())
}

fn no_clipboard() -> fdo::Error {
    fdo::Error::AccessDenied("this session has no clipboard access".into())
}

fn sharing_off() -> fdo::Error {
    fdo::Error::AccessDenied("sharing is off".into())
}

impl State {
    pub fn new(
        idle_timeout: Duration,
        screens: SharedScreens,
        keymap: eis_server::SharedKeymap,
        gate: Gate,
    ) -> (Self, mpsc::UnboundedReceiver<(String, u32)>) {
        Self::with_trust(
            Spawner::Wayland { idle_timeout },
            screens,
            keymap,
            gate,
            Trust {
                allow_list: PathBuf::from(trust::ALLOWED_APPS_PATH),
                allow_list_owner: trust::ALLOWED_APPS_OWNER,
                switch: Switch::installed(),
                frontend: Frontend::Bus,
                signals: SignalSink::Bus,
            },
        )
    }

    fn with_trust(
        spawner: Spawner,
        screens: SharedScreens,
        keymap: eis_server::SharedKeymap,
        gate: Gate,
        trust: Trust,
    ) -> (Self, mpsc::UnboundedReceiver<(String, u32)>) {
        let (eis_closed, closed_rx) = mpsc::unbounded_channel();
        let state = Self {
            inner: Arc::new(Mutex::new(Inner::default())),
            next_activation: Arc::new(AtomicU32::new(1)),
            next_arming: Arc::new(std::sync::atomic::AtomicU64::new(1)),
            stop: Arc::new(tokio::sync::Notify::new()),
            stop_reason: Arc::new(OnceLock::new()),
            objects: Arc::new(Mutex::new(())),
            worker: Arc::new(OnceLock::new()),
            worker_start: Arc::new(Mutex::new(())),
            crossings: Arc::new(AtomicU64::new(1)),
            spawner: Arc::new(spawner),
            screens,
            keymap,
            eis_closed,
            conn: Arc::new(OnceLock::new()),
            trust: Arc::new(trust),
            gate,
        };
        (state, closed_rx)
    }

    pub fn set_connection(&self, conn: zbus::Connection) {
        let _ = self.conn.set(conn);
    }

    fn connection(&self) -> Option<&zbus::Connection> {
        self.conn.get()
    }

    // ---- the Wayland worker ---------------------------------------------------

    fn wayland(&self) -> Option<&WaylandHandle> {
        self.worker.get()
    }

    pub fn worker_running(&self) -> bool {
        self.wayland().is_some()
    }

    /// Send a command to the running worker. With none running there is no
    /// barrier, no capture and no clipboard claim to act on, so it is dropped.
    fn send(&self, cmd: WaylandCmd) {
        match self.wayland() {
            Some(wayland) => wayland.send(cmd),
            // The command's name only: its fields carry positions and types.
            None => debug!(command = ?cmd, "no Wayland worker runs: nothing to send it to"),
        }
    }

    fn spawn_worker(&self) -> anyhow::Result<StartingWorker> {
        match &*self.spawner {
            Spawner::Wayland { idle_timeout } => wayland::start(
                self.keymap.clone(),
                *idle_timeout,
                self.screens.clone(),
                self.gate.clone(),
                self.trust.switch.clone(),
                self.crossings.clone(),
            ),
            #[cfg(test)]
            Spawner::Recording(workers, hold_ready) => {
                let (handle, cmds) = WaylandHandle::recording();
                let (events, event_rx) = mpsc::unbounded_channel();
                let (ready_tx, ready) = oneshot::channel();
                let ready_tx = if hold_ready.load(Ordering::Relaxed) {
                    Some(ready_tx)
                } else {
                    let _ = ready_tx.send(Ok(()));
                    None
                };
                workers.lock().expect("recorded workers").push(RecordedWorker {
                    cmds,
                    events: Some(events),
                    ready: ready_tx,
                });
                Ok(StartingWorker { handle, events: event_rx, ready })
            }
        }
    }

    /// Launch only for an authorized On request. Publish the handle before
    /// waiting for readiness, so the switch watcher can end a blocked startup.
    async fn ensure_worker(&self) -> fdo::Result<()> {
        let _one_start = self.worker_start.lock().await;
        let mut out = Vec::new();
        let (to, start) = {
            let mut inner = self.inner.lock().await;
            let start = if !self.switch_locked(&mut inner, &mut out) {
                Err(sharing_off())
            } else if self.worker_running() {
                Ok(None)
            } else {
                self.spawn_worker().map(|StartingWorker { handle, events, ready }| {
                    let _ = self.worker.set(handle);
                    Some((events, ready))
                }).map_err(|err| {
                    error!("could not start the Wayland worker: {err:#}");
                    fdo::Error::Failed("the backend could not reach the compositor".into())
                })
            };
            (inner.frontend.clone(), start)
        };
        self.emit_all(to, out).await;
        let Some((events, ready)) = start? else { return Ok(()) };
        let ready = tokio::time::timeout(WORKER_START_TIMEOUT, ready).await;

        // The worker checks immediately after opening the socket. Check here
        // too, since the registry and initial outputs can take time to arrive.
        self.with_sharing("CreateSession", |_, _| {
            if !matches!(ready, Ok(Ok(Ok(())))) {
                error!("could not start the Wayland worker: {ready:?}");
                self.request_stop(Err("the Wayland worker did not start"));
                return Err(fdo::Error::Failed("the backend could not reach the compositor".into()));
            }
            Ok(())
        }).await?;

        for screen in &self.screens.current().screens {
            info!(
                "screen {}: {}x{} at ({}, {}) scale {} {:?}",
                screen.name, screen.zone.width, screen.zone.height,
                screen.zone.x, screen.zone.y,
                screen.scale, screen.transform
            );
        }
        info!("Wayland worker started");
        tokio::spawn(pump_wayland_events(self.clone(), events));
        Ok(())
    }

    /// The last session is gone. End any crossing still on its way to the
    /// portal before asking the compositor to confirm the teardown.
    fn stop_worker_if_idle(&self, inner: &mut Inner) {
        if inner.sessions.is_empty() {
            self.begin_teardown(inner, "the last session ended");
        }
    }

    fn begin_teardown(&self, inner: &mut Inner, why: &'static str) {
        if !self.worker_running() || inner.teardown.is_some() || self.stop_reason.get().is_some() {
            return;
        }
        self.gate.close();
        self.release_everything();
        let (result, teardown) = watch::channel(None);
        inner.teardown = Some(teardown);
        let deadline = tokio::time::Instant::now() + CONFIRM_TIMEOUT;
        let state = self.clone();
        tokio::spawn(async move {
            let confirmed = state.wayland().expect("worker kept until exit")
                .confirm(deadline.saturating_duration_since(tokio::time::Instant::now())).await;
            result.send_replace(Some(confirmed));
            if confirmed {
                state.request_stop(Ok(why));
            } else {
                error!("{why}: the compositor did not confirm the end of the capture within a second");
                state.request_stop(Err("the compositor did not confirm the end of the capture"));
            }
        });
    }

    async fn offer_sharing_window(&self) {
        let Some(conn) = self.connection() else { return };
        let Some(runtime) = std::env::var_os("XDG_RUNTIME_DIR") else { return };
        let Ok(bus) = fdo::DBusProxy::new(conn).await else { return };
        let Ok(id) = bus.get_id().await else { return };
        // aresos-session starts a new bus for each login. Use a marker on that
        // bus so D-Bus activation after a crash cannot show the dialog again.
        let marker = PathBuf::from(runtime).join(format!("aresos-input-sharing-off-{id}"));
        if std::fs::OpenOptions::new().write(true).create_new(true).open(marker).is_ok() {
            match tokio::process::Command::new("/usr/bin/aresos-input-sharing")
                .stdin(std::process::Stdio::null())
                .stdout(std::process::Stdio::null())
                .stderr(std::process::Stdio::null())
                .spawn()
            {
                Ok(mut child) => {
                    tokio::spawn(async move { let _ = child.wait().await; });
                }
                Err(err) => warn!("could not open the sharing window: {err}"),
            }
        }
    }

    // ---- who may call -----------------------------------------------------

    /// The unique name that owns the frontend's bus name right now.
    ///
    /// Asked of the bus for every call rather than remembered: a remembered
    /// owner is wrong for a moment whenever the frontend restarts, and that
    /// moment is exactly when a stale answer would matter.
    async fn frontend_owner(&self) -> Option<String> {
        match &self.trust.frontend {
            Frontend::Bus => {
                let reply = self
                    .connection()?
                    .call_method(
                        Some("org.freedesktop.DBus"),
                        "/org/freedesktop/DBus",
                        Some("org.freedesktop.DBus"),
                        "GetNameOwner",
                        &(trust::FRONTEND_NAME,),
                    )
                    .await
                    .ok()?;
                reply.body().deserialize::<String>().ok()
            }
            #[cfg(test)]
            Frontend::Fixed(owner) => owner.lock().expect("fixed frontend").clone(),
        }
    }

    /// Refuse every caller but the portal frontend. Each impl method calls this
    /// before it reads its arguments or touches any state.
    async fn authorize(&self, sender: Option<&str>, method: &'static str) -> fdo::Result<()> {
        let owner = self.frontend_owner().await;
        if !trust::is_frontend(sender, owner.as_deref()) {
            warn!(method, sender = ?sender, "refused: the caller is not the portal frontend");
            return Err(fdo::Error::AccessDenied(
                "only the portal frontend may call this".into(),
            ));
        }
        self.adopt_frontend(sender).await;
        Ok(())
    }

    /// Make `sender`, which has just passed the frontend check, the frontend the
    /// sessions belong to.
    ///
    /// Every session here was made by one frontend (`Inner::frontend`). A caller
    /// that passed the check under another bus name is a new owner of the
    /// frontend's name, so the old owner's sessions end before this call touches
    /// anything: it can't get an old session's EIS socket or clipboard pipe by
    /// its path (REVIEW-3, finding 2; REVIEW-2, finding 3). The watch on the name
    /// does the same, but may not have run yet. Nobody is left to tell.
    async fn adopt_frontend(&self, sender: Option<&str>) {
        let mut orphaned = Vec::new();
        {
            let mut inner = self.inner.lock().await;
            if inner.frontend.as_deref() == sender {
                return;
            }
            let stale: Vec<OwnedObjectPath> = inner.sessions.keys().cloned().collect();
            if !stale.is_empty() {
                warn!(
                    "a new owner of the frontend's name: closing {} session(s) of the old one",
                    stale.len()
                );
            }
            for old in &stale {
                self.remove_session(&mut inner, old, &mut orphaned);
            }
            inner.frontend = sender.map(str::to_owned);
            if !stale.is_empty() {
                self.stop_worker_if_idle(&mut inner);
            }
        }
        self.emit_all(None, orphaned).await;
    }

    // ---- the sharing switch --------------------------------------------------

    /// Read the switch, with the lock held. On opens the gate. Off closes the
    /// gate first, so the input path stops forwarding at once, and then every
    /// session: its capture, barriers, EIS connection and clipboard claim go
    /// (their signals into `out`), and so nothing more leaves. Under the lock no
    /// session can be made or used between the read and the teardown, and the
    /// gate can't open again while a session from before the Off is left.
    fn switch_locked(&self, inner: &mut Inner, out: &mut Vec<Signal>) -> bool {
        if inner.teardown.is_some() || self.stop_reason.get().is_some() {
            return false;
        }
        let off = match self.trust.switch.read() {
            Ok(()) => {
                if !self.gate.open() {
                    info!("sharing is on");
                }
                return true;
            }
            Err(off) => off,
        };
        let was_open = self.gate.close();
        if off.suspicious {
            warn!("sharing is off: {off}");
        } else if was_open {
            info!("sharing is off: {off}");
        } else {
            debug!("sharing is off: {off}");
        }
        let handles: Vec<OwnedObjectPath> = inner.sessions.keys().cloned().collect();
        if !handles.is_empty() {
            warn!("sharing was turned off: closing {} session(s)", handles.len());
        }
        for handle in &handles {
            self.remove_session(inner, handle, out);
        }
        self.begin_teardown(inner, "sharing was turned off");
        false
    }

    /// Run `f` with the lock held, after a read of the switch under the same
    /// lock: Off refuses the call (and ends what is live) before `f` runs.
    async fn with_sharing<T>(
        &self,
        method: &'static str,
        f: impl FnOnce(&mut Inner, &mut Vec<Signal>) -> fdo::Result<T>,
    ) -> fdo::Result<T> {
        let mut out = Vec::new();
        let (to, result) = {
            let mut inner = self.inner.lock().await;
            let result = if self.switch_locked(&mut inner, &mut out) {
                f(&mut inner, &mut out)
            } else {
                warn!(method, "refused: sharing is off");
                Err(sharing_off())
            };
            (inner.frontend.clone(), result)
        };
        self.emit_all(to, out).await;
        result
    }

    /// Poll while a worker exists, including while it is still connecting.
    pub async fn reread_switch(&self) {
        let mut out = Vec::new();
        let to = {
            let mut inner = self.inner.lock().await;
            if !self.worker_running() {
                return;
            }
            self.switch_locked(&mut inner, &mut out);
            inner.frontend.clone()
        };
        self.emit_all(to, out).await;
    }

    /// `--revoke`: read the switch now and wait for any teardown it triggered
    /// or the switch watcher already started.
    async fn revoke(&self) -> String {
        let mut out = Vec::new();
        let (to, teardown) = {
            let mut inner = self.inner.lock().await;
            if self.switch_locked(&mut inner, &mut out) {
                return "sharing is on: nothing changed".to_owned();
            }
            (inner.frontend.clone(), inner.teardown.clone())
        };
        let closed = out
            .iter()
            .filter(|signal| matches!(signal, Signal::SessionClosed { .. }))
            .count();
        self.emit_all(to, out).await;
        let Some(teardown) = teardown else {
            return "sharing is off: there was nothing to close".to_owned();
        };
        if teardown_confirmed(teardown).await {
            format!("sharing is off: closed {closed} session(s)")
        } else {
            format!("sharing is off: closed {closed} session(s); the compositor did not confirm, so the backend stops")
        }
    }

    // ---- signals ----------------------------------------------------------

    /// Send signals to `to`: the unique bus name of the frontend that made the
    /// sessions they are about, read from `Inner::frontend` under the same lock
    /// that produced them. They go to that one connection and are never
    /// broadcast: `Activated` carries the cursor position and the clipboard
    /// signals carry types and transfer serials, which no other program on the
    /// bus has any business receiving.
    async fn emit_all(&self, to: Option<String>, signals: Vec<Signal>) {
        for signal in signals {
            self.emit(to.as_deref(), signal).await;
        }
    }

    async fn emit(&self, to: Option<&str>, signal: Signal) {
        // A closed session's object goes with its `Closed`, whether or not
        // anybody was left to tell.
        let closed = match &signal {
            Signal::SessionClosed { session } => Some(session.clone()),
            _ => None,
        };
        match &self.trust.signals {
            SignalSink::Bus => match self.connection() {
                Some(conn) => {
                    let name = signal.name();
                    if let Err(err) = send_signal(conn, to, signal).await {
                        error!(signal = name, "failed to emit a portal signal: {err}");
                    }
                }
                None => debug!(signal = signal.name(), "no bus connection yet, a signal was dropped"),
            },
            #[cfg(test)]
            SignalSink::Record { signals, .. } => {
                signals
                    .lock()
                    .expect("signal sink")
                    .push((to.map(str::to_owned), signal));
            }
        }
        if let Some(session) = closed {
            self.remove_session_object(&session).await;
        }
    }

    /// Export the impl-side Session object for a session just stored in
    /// `sessions`. An object already standing at the path is an earlier
    /// session's whose removal hasn't run yet: it stays and serves this session,
    /// since a `SessionObject` finds its session by path.
    async fn export_session_object(&self, handle: &OwnedObjectPath) -> fdo::Result<()> {
        let _objects = self.objects.lock().await;
        match &self.trust.signals {
            SignalSink::Bus => {
                let Some(conn) = self.connection() else {
                    return Ok(());
                };
                let object = SessionObject {
                    state: self.clone(),
                    handle: handle.clone(),
                };
                match conn.object_server().at(handle, object).await {
                    Ok(true) => {}
                    Ok(false) => debug!(session = %handle.as_str(), "an earlier object at this path serves the new session"),
                    Err(err) => {
                        return Err(fdo::Error::Failed(format!(
                            "failed to export the session object: {err}"
                        )))
                    }
                }
            }
            #[cfg(test)]
            SignalSink::Record { objects, .. } => {
                objects.lock().expect("object sink").insert(handle.clone());
            }
        }
        Ok(())
    }

    /// Remove the Session object at a closed session's path, unless a session
    /// with that path exists again (REVIEW-2, finding 4).
    ///
    /// A client can close a session and make a new one at the same path straight
    /// away; the old `Closed` may then go out after the new session was stored,
    /// and removing the object would leave the new session without `Close`. The
    /// check and the removal hold the same lock as `export_session_object`, so
    /// they can't straddle the new session's export.
    async fn remove_session_object(&self, handle: &OwnedObjectPath) {
        let _objects = self.objects.lock().await;
        if self.inner.lock().await.sessions.contains_key(handle) {
            debug!(session = %handle.as_str(), "a new session has this path: its object stays");
            return;
        }
        match &self.trust.signals {
            SignalSink::Bus => {
                if let Some(conn) = self.connection() {
                    let _ = conn.object_server().remove::<SessionObject, _>(handle).await;
                }
            }
            #[cfg(test)]
            SignalSink::Record { objects, .. } => {
                objects.lock().expect("object sink").remove(handle);
            }
        }
    }

    // ---- shared pieces, called with the lock held ---------------------------

    fn arm(&self, session: &mut Session) {
        if session.barriers.is_empty() {
            // Nothing to place; make sure nothing of an earlier set stays up.
            session.arming = 0;
            self.send(WaylandCmd::Disarm);
            return;
        }
        // A new number for every arming, see `Session::arming`.
        session.arming = self.next_arming.fetch_add(1, Ordering::Relaxed);
        self.send(WaylandCmd::Arm {
            session: session.handle.as_str().to_owned(),
            arming: session.arming,
            keyboard: session.capabilities & CAP_KEYBOARD != 0,
            zone_set: session.zone_set,
            barriers: session.barriers.clone(),
        });
    }

    /// Take a session's capture and its barriers away and tell its client.
    fn disarm_session(&self, session: &mut Session, out: &mut Vec<Signal>) {
        if let Some((activation_id, crossing)) = session.stop_capture() {
            self.send(WaylandCmd::EndCapture {
                crossing: Some(crossing),
                cursor_hint: None,
            });
            out.push(Signal::Deactivated {
                session: session.handle.clone(),
                activation_id,
            });
        }
        if session.enabled {
            session.enabled = false;
            session.arming = 0;
            // Also ends a crossing of this session the portal has not heard of
            // yet, and drops the input buffered for it.
            self.send(WaylandCmd::Disarm);
            out.push(Signal::Disabled {
                session: session.handle.clone(),
            });
        }
    }

    /// Give up the clipboard claim and abandon whatever reads were waiting on it.
    ///
    /// The two go together: once the selection is no longer ours, no `SelectionWrite`
    /// can arrive for a parked transfer, so holding those pipes open would leave the
    /// applications blocked on them waiting for a write that will never come.
    fn release_claim(&self, clipboard: &mut ClipboardTracker) {
        self.send(WaylandCmd::ClipboardRelease);
        clipboard.owned_by_session = false;
        clipboard.owner_session = None;
        clipboard.claim_id = clipboard.claim_id.wrapping_add(1);
        clipboard.clear_transfers();
    }

    /// Remove a session and everything it holds: its capture, its barriers, its
    /// clipboard claim and transfers, and its EIS connection. After this nothing
    /// refers to it, so nothing can be sent to it again.
    fn remove_session(&self, inner: &mut Inner, handle: &OwnedObjectPath, out: &mut Vec<Signal>) -> bool {
        let Some(mut session) = inner.sessions.remove(handle) else {
            return false;
        };
        if let Some((activation_id, crossing)) = session.stop_capture() {
            self.send(WaylandCmd::EndCapture {
                crossing: Some(crossing),
                cursor_hint: None,
            });
            out.push(Signal::Deactivated {
                session: handle.clone(),
                activation_id,
            });
        }
        if session.enabled || !inner.sessions.values().any(|s| s.enabled) {
            // Also ends a crossing of this session that is still on its way
            // here (the Wayland thread drops it with its buffered input). The
            // notice of it, when it comes, names an arming no session has.
            self.send(WaylandCmd::Disarm);
        }
        if let Some(eis) = session.eis.take() {
            eis.send(EisCommand::Close);
        }
        if inner.clipboard.owner_session.as_ref() == Some(handle) {
            // A selection whose owner has gone is a clipboard that hangs every
            // paste on this machine, so the claim has to go with the session.
            self.release_claim(&mut inner.clipboard);
        }
        out.push(Signal::SessionClosed {
            session: handle.clone(),
        });
        true
    }

    // ---- InputCapture -----------------------------------------------------

    /// `CreateSession` (with the capabilities it asks for) and `CreateSession2`
    /// (with `None`: they are settled in `Start`). Returns what was granted.
    pub async fn create_session(
        &self,
        sender: Option<&str>,
        handle: &OwnedObjectPath,
        app_id: &str,
        v1_capabilities: Option<u32>,
    ) -> fdo::Result<u32> {
        self.authorize(sender, "CreateSession").await?;

        // A host program without a desktop file reaches the backend with an
        // empty ID, so it names nobody: refused whatever the list holds.
        if app_id.is_empty() {
            warn!("refused: the application has no ID");
            return Err(fdo::Error::AccessDenied(
                "this application may not capture input".into(),
            ));
        }
        // Read for every session, so the list in force is the one on disk now.
        let allowed = AllowList::load(&self.trust.allow_list, self.trust.allow_list_owner);
        if !allowed.allows(app_id) {
            warn!(app_id = ?app_id, "refused: this application is not on the allow-list");
            return Err(fdo::Error::AccessDenied(
                "this application may not capture input".into(),
            ));
        }

        let granted = v1_capabilities.map_or(0, |requested| requested & SUPPORTED_CAPABILITIES);
        if v1_capabilities.is_some() && granted == 0 {
            return Err(fdo::Error::Failed("no supported capabilities requested".into()));
        }
        let started = v1_capabilities.is_some();

        let result = self.create_session_locked(handle, app_id, granted, started).await;
        if app_id == DESKFLOW_ID && matches!(&result, Err(fdo::Error::AccessDenied(_))) {
            debug!(app_id, "Deskflow requested a session while sharing is off");
            self.offer_sharing_window().await;
        }
        result?;

        // The backend owns the impl-side Session object.
        if let Err(err) = self.export_session_object(handle).await {
            let mut inner = self.inner.lock().await;
            inner.sessions.remove(handle);
            self.stop_worker_if_idle(&mut inner);
            return Err(err);
        }

        info!(app_id = ?app_id, session = %handle.as_str(), capabilities = granted, started, "session created");
        Ok(granted)
    }

    /// Start the worker if need be, then store the session: both only while the
    /// switch says on.
    async fn create_session_locked(
        &self,
        handle: &OwnedObjectPath,
        app_id: &str,
        granted: u32,
        started: bool,
    ) -> fdo::Result<()> {
        self.ensure_worker().await?;
        // The switch is read again under the lock that stores the session, so a
        // session can't be made after an Off that the timer reads a moment later.
        // `authorize` has made the caller the frontend these sessions belong to,
        // closing an earlier owner's first.
        self.with_sharing("CreateSession", |inner, _| {
            if inner.sessions.contains_key(handle) {
                return Err(fdo::Error::Failed("this session already exists".into()));
            }
            if inner.sessions.len() >= MAX_SESSIONS {
                return Err(fdo::Error::LimitsExceeded("too many sessions".into()));
            }
            inner.sessions.insert(
                handle.clone(),
                Session {
                    handle: handle.clone(),
                    app_id: app_id.to_owned(),
                    capabilities: granted,
                    barriers: Vec::new(),
                    zone_set: 0,
                    eis: None,
                    started,
                    enabled: false,
                    activation_id: 0,
                    arming: 0,
                    crossing: 0,
                    clipboard_requested: false,
                },
            );
            Ok(())
        })
        .await
    }

    /// Negotiate capabilities and start a session made by `CreateSession2`.
    /// Returns the grant and whether the clipboard is enabled.
    pub async fn start(
        &self,
        sender: Option<&str>,
        handle: &OwnedObjectPath,
        requested: u32,
    ) -> fdo::Result<(u32, bool)> {
        self.authorize(sender, "Start").await?;
        let granted = requested & SUPPORTED_CAPABILITIES;
        if granted == 0 {
            return Err(fdo::Error::Failed("no supported capabilities requested".into()));
        }

        let mut inner = self.inner.lock().await;
        let session = inner.sessions.get_mut(handle).ok_or_else(unknown_session)?;
        if session.started {
            return Err(fdo::Error::Failed("Start called twice".into()));
        }
        session.capabilities = granted;
        session.started = true;
        let clipboard_enabled = session.clipboard_requested;
        info!(
            session = %handle.as_str(),
            capabilities = granted,
            clipboard_enabled,
            "session started"
        );
        Ok((granted, clipboard_enabled))
    }

    /// The current snapshot's zones and its zone set.
    pub async fn get_zones(
        &self,
        sender: Option<&str>,
        handle: &OwnedObjectPath,
    ) -> fdo::Result<(Vec<ZoneTuple>, u32)> {
        self.authorize(sender, "GetZones").await?;
        if !self.inner.lock().await.sessions.contains_key(handle) {
            return Err(unknown_session());
        }
        let snapshot = self.screens.current();
        let zones: Vec<ZoneTuple> = snapshot.screens.iter().map(|s| s.zone.into()).collect();
        debug!(zone_set = snapshot.zone_set, "returning {} zone(s)", zones.len());
        Ok((zones, snapshot.zone_set))
    }

    /// Replace a session's barriers. Returns the IDs that were refused.
    pub async fn set_pointer_barriers(
        &self,
        sender: Option<&str>,
        handle: &OwnedObjectPath,
        specs: &[BarrierSpec],
        zone_set: u32,
    ) -> fdo::Result<Vec<u32>> {
        self.authorize(sender, "SetPointerBarriers").await?;
        let mut inner = self.inner.lock().await;
        let session = inner.sessions.get_mut(handle).ok_or_else(unknown_session)?;

        // A stale zone_set means the client is describing a layout we no longer
        // have; reject every barrier so it re-reads zones first.
        let snapshot = self.screens.current();
        let stale = zone_set != snapshot.zone_set;

        let mut accepted = Vec::new();
        let mut failed: Vec<u32> = Vec::new();
        for spec in specs {
            let (Some(id), Some((x1, y1, x2, y2))) = *spec else {
                if let Some(id) = spec.0 {
                    failed.push(id);
                }
                continue;
            };
            let barrier = Barrier { id, x1, y1, x2, y2 };
            // The spec allows only axis-aligned barriers.
            if stale
                || id == 0
                || (!barrier.is_vertical() && !barrier.is_horizontal())
                || accepted.len() >= MAX_BARRIERS
            {
                failed.push(id);
                continue;
            }
            accepted.push(barrier);
        }

        // Only a barrier on an outer edge of the current screens can become a
        // surface; the client learns about the others now, not at the crossing.
        let (_, misplaced) = wayland::place(&accepted, &snapshot.layout());
        accepted.retain(|barrier| !misplaced.contains(&barrier.id));
        failed.extend(misplaced);

        if stale {
            warn!(zone_set, current = snapshot.zone_set, "rejecting barriers for a stale zone_set");
        } else {
            info!("accepted {} barrier(s), rejected {}", accepted.len(), failed.len());
            session.barriers = accepted;
            session.zone_set = snapshot.zone_set;
            if session.enabled && session.activation_id == 0 {
                self.arm(session);
            }
        }
        Ok(failed)
    }

    /// Give the session's client the receiving end of a new EIS connection.
    pub async fn connect_to_eis(&self, sender: Option<&str>, handle: &OwnedObjectPath) -> fdo::Result<OwnedFd> {
        self.authorize(sender, "ConnectToEIS").await?;
        let mut inner = self.inner.lock().await;
        let session = inner.sessions.get_mut(handle).ok_or_else(unknown_session)?;
        if !session.started {
            // Before Start nothing has been granted, so there is nothing an EIS
            // connection could carry.
            return Err(fdo::Error::Failed("ConnectToEIS before Start".into()));
        }
        if session.eis.is_some() {
            return Err(fdo::Error::Failed(
                "EIS connection already established for this session".into(),
            ));
        }

        // The region has to be baked into the EIS devices as they are created.
        let region = self
            .screens
            .current()
            .region()
            .ok_or_else(|| fdo::Error::Failed("no valid, representable EIS output region".into()))?;

        let (ours, theirs) = UnixStream::pair()
            .map_err(|e| fdo::Error::Failed(format!("socketpair failed: {e}")))?;
        let eis = eis_server::spawn(
            ours,
            handle.as_str().to_owned(),
            self.keymap.clone(),
            self.eis_closed.clone(),
            Some(region),
            session.capabilities,
            self.gate.clone(),
        )
        .map_err(|e| fdo::Error::Failed(format!("EIS setup failed: {e:#}")))?;
        session.eis = Some(eis);

        info!(session = %handle.as_str(), "handed EIS socket to client");
        Ok(OwnedFd::from(theirs))
    }

    /// Arm a session. Any other armed session is disarmed first and told.
    pub async fn enable(&self, sender: Option<&str>, handle: &OwnedObjectPath) -> fdo::Result<()> {
        self.authorize(sender, "Enable").await?;
        self.with_sharing("Enable", |inner, out| self.enable_locked(inner, handle, out))
            .await
    }

    fn enable_locked(&self, inner: &mut Inner, handle: &OwnedObjectPath, out: &mut Vec<Signal>) -> fdo::Result<()> {
        {
            let session = inner.sessions.get(handle).ok_or_else(unknown_session)?;
            if !session.started {
                // A v2 session has no negotiated capabilities until Start, so arming
                // barriers now would capture on behalf of a session that was never
                // granted anything.
                return Err(fdo::Error::Failed("Enable called before Start".into()));
            }
            if session.eis.is_none() {
                return Err(fdo::Error::Failed("Enable called before ConnectToEIS".into()));
            }

            // One armed session: the screen edges belong to whoever asked last.
            for other in inner.sessions.values_mut() {
                if other.handle != *handle {
                    self.disarm_session(other, out);
                }
            }
            if let Some(session) = inner.sessions.get_mut(handle) {
                session.enabled = true;
                info!(session = %handle.as_str(), barriers = session.barriers.len(), "capture enabled");
                if session.activation_id == 0 {
                    self.arm(session);
                }
            }
        }
        Ok(())
    }

    pub async fn disable(&self, sender: Option<&str>, handle: &OwnedObjectPath) -> fdo::Result<()> {
        self.authorize(sender, "Disable").await?;
        let mut inner = self.inner.lock().await;
        let session = inner.sessions.get_mut(handle).ok_or_else(unknown_session)?;
        if let Some((_, crossing)) = session.stop_capture() {
            self.send(WaylandCmd::EndCapture {
                crossing: Some(crossing),
                cursor_hint: None,
            });
        }
        if session.enabled {
            session.enabled = false;
            session.arming = 0;
            // Free the screen edges; leaving the surfaces up would keep swallowing
            // clicks on the edge pixel column for no reason.
            self.send(WaylandCmd::Disarm);
        }
        info!(session = %handle.as_str(), "capture disabled");
        Ok(())
    }

    /// End the session's own capture run. A session that isn't capturing ends
    /// nothing, so one session can't release another's capture.
    pub async fn release(
        &self,
        sender: Option<&str>,
        handle: &OwnedObjectPath,
        cursor_hint: Option<(f64, f64)>,
    ) -> fdo::Result<()> {
        self.authorize(sender, "Release").await?;
        let mut inner = self.inner.lock().await;
        let session = inner.sessions.get_mut(handle).ok_or_else(unknown_session)?;
        let Some((_, crossing)) = session.stop_capture() else {
            return Ok(());
        };
        info!(session = %handle.as_str(), "capture released");
        // Unlock the pointer first, then rebuild the barriers so the pointer is
        // back under local control before an edge can trigger again.
        self.send(WaylandCmd::EndCapture {
            crossing: Some(crossing),
            cursor_hint,
        });
        if session.enabled {
            self.arm(session);
        }
        Ok(())
    }

    // ---- Clipboard ----------------------------------------------------------

    /// Grant a session access to the clipboard.
    ///
    /// The spec puts this before the session starts, which is what lets `Start`
    /// answer `clipboard_enabled` truthfully.
    pub async fn request_clipboard(&self, sender: Option<&str>, handle: &OwnedObjectPath) -> fdo::Result<()> {
        self.authorize(sender, "RequestClipboard").await?;
        self.with_sharing("RequestClipboard", |inner, _| {
            let session = inner.sessions.get_mut(handle).ok_or_else(unknown_session)?;
            if session.started {
                return Err(fdo::Error::Failed("RequestClipboard after Start".into()));
            }
            session.clipboard_requested = true;
            info!(session = %handle.as_str(), "clipboard access requested");
            Ok(())
        })
        .await
    }

    /// The session now holds clipboard content in these types.
    ///
    /// Claiming the selection discards whatever was on it, exactly as a local
    /// copy would; there is no way to put the previous content back afterwards.
    pub async fn set_selection(
        &self,
        sender: Option<&str>,
        handle: &OwnedObjectPath,
        mime_types: Vec<String>,
    ) -> fdo::Result<()> {
        self.authorize(sender, "SetSelection").await?;
        self.with_sharing("SetSelection", |inner, _| self.set_selection_locked(inner, handle, mime_types))
            .await
    }

    fn set_selection_locked(&self, inner: &mut Inner, handle: &OwnedObjectPath, mime_types: Vec<String>) -> fdo::Result<()> {
        if !inner.sessions.get(handle).is_some_and(Session::has_clipboard) {
            return Err(no_clipboard());
        }
        if mime_types.len() > MAX_MIME_TYPES
            || mime_types.iter().any(|m| m.is_empty() || m.len() > MAX_MIME_TYPE_BYTES)
        {
            return Err(fdo::Error::InvalidArgs("unusable list of types".into()));
        }

        let clipboard = &mut inner.clipboard;
        if mime_types.is_empty() {
            // Only the owner has a claim to give up.
            if clipboard.owner_session.as_ref() == Some(handle) {
                self.release_claim(clipboard);
            }
            return Ok(());
        }

        clipboard.claim_id = clipboard.claim_id.wrapping_add(1);
        clipboard.owner_session = Some(handle.clone());
        // Reads parked against the previous claim cannot be answered from the
        // new content, so let their readers see EOF now.
        clipboard.clear_transfers();
        info!(session = %handle.as_str(), types = mime_types.len(), "session claimed the clipboard");
        self.send(WaylandCmd::ClipboardClaim {
            claim_id: clipboard.claim_id,
            mime_types,
        });
        Ok(())
    }

    /// Hand over the pipe a pending read is waiting on.
    ///
    /// This is the compositor's own fd, passed straight through, so the content
    /// goes from the client to whoever is pasting without a copy in between. It
    /// goes only to the session the transfer was announced to.
    pub async fn selection_write(
        &self,
        sender: Option<&str>,
        handle: &OwnedObjectPath,
        serial: u32,
    ) -> fdo::Result<OwnedFd> {
        self.authorize(sender, "SelectionWrite").await?;
        self.with_sharing("SelectionWrite", |inner, _| {
            if !inner.sessions.get(handle).is_some_and(Session::has_clipboard) {
                return Err(no_clipboard());
            }
            inner.clipboard.take_transfer(handle, serial).ok_or_else(|| {
                // The serial is another session's, was answered already, or waited
                // long enough to be evicted.
                warn!(session = %handle.as_str(), serial, "refused: no such clipboard transfer for this session");
                fdo::Error::InvalidArgs(format!("no clipboard transfer with serial {serial}"))
            })
        })
        .await
    }

    /// The client finished writing, successfully or not.
    ///
    /// Nothing is left to do either way: the fd left this process with
    /// `SelectionWrite`, and closing it is what ends the transfer.
    pub async fn selection_write_done(
        &self,
        sender: Option<&str>,
        handle: &OwnedObjectPath,
        serial: u32,
        success: bool,
    ) -> fdo::Result<()> {
        self.authorize(sender, "SelectionWriteDone").await?;
        self.with_sharing("SelectionWriteDone", |_, _| Ok(())).await?;
        if !success {
            warn!(session = %handle.as_str(), serial, "the client failed to write clipboard content");
        }
        Ok(())
    }

    /// Read the current selection, as the read end of a pipe. The reply goes to
    /// the frontend for the session that asked, and to nobody else.
    pub async fn selection_read(
        &self,
        sender: Option<&str>,
        handle: &OwnedObjectPath,
        mime_type: String,
    ) -> fdo::Result<OwnedFd> {
        self.authorize(sender, "SelectionRead").await?;
        let may_read = |inner: &mut Inner, _: &mut Vec<Signal>| {
            if inner.sessions.get(handle).is_some_and(Session::has_clipboard) {
                Ok(())
            } else {
                Err(no_clipboard())
            }
        };
        self.with_sharing("SelectionRead", may_read).await?;
        if mime_type.is_empty() || mime_type.len() > MAX_MIME_TYPE_BYTES {
            return Err(fdo::Error::InvalidArgs("unusable type".into()));
        }

        let (reply_tx, reply_rx) = tokio::sync::oneshot::channel();
        self.send(WaylandCmd::ClipboardRead {
            mime_type,
            reply: reply_tx,
        });
        let pipe = reply_rx.await.ok().flatten();
        // Sharing may have gone off, or the session closed, while this call
        // waited for the Wayland thread: the pipe goes out only if neither did.
        // Refused, it is dropped here, and the owner writing into it sees nobody
        // reading.
        self.with_sharing("SelectionRead", may_read).await?;
        pipe.ok_or_else(|| fdo::Error::Failed("the selection does not offer that type".into()))
    }

    // ---- Session.Close and the other ways a session ends --------------------

    /// `Close` on the impl-side Session object.
    pub async fn close_session(&self, sender: Option<&str>, handle: &OwnedObjectPath) -> fdo::Result<()> {
        self.authorize(sender, "Close").await?;
        let mut out = Vec::new();
        let to;
        {
            let mut inner = self.inner.lock().await;
            to = inner.frontend.clone();
            if self.remove_session(&mut inner, handle, &mut out) {
                info!(session = %handle.as_str(), "session closed by the portal");
                self.stop_worker_if_idle(&mut inner);
            }
        }
        self.emit_all(to, out).await;
        Ok(())
    }

    /// The watch on the frontend's name saw `old_owner` give it up. Only the
    /// sessions that owner made are closed: by the time a late notice arrives,
    /// a new owner may already have made sessions of its own (REVIEW-3,
    /// finding 2), and those stay.
    pub async fn frontend_left(&self, old_owner: &str) {
        self.close_sessions(Some(old_owner), "the portal frontend left the bus")
            .await;
    }

    /// Close every session, or with `only_of` every session if they belong to
    /// that frontend and none otherwise.
    async fn close_sessions(&self, only_of: Option<&str>, why: &str) {
        let mut out = Vec::new();
        let to;
        {
            let mut inner = self.inner.lock().await;
            if only_of.is_some() && inner.frontend.as_deref() != only_of {
                return;
            }
            to = inner.frontend.take();
            let handles: Vec<OwnedObjectPath> = inner.sessions.keys().cloned().collect();
            if !handles.is_empty() {
                warn!("{why}: closing {} session(s)", handles.len());
            }
            for handle in handles {
                self.remove_session(&mut inner, &handle, &mut out);
            }
            self.stop_worker_if_idle(&mut inner);
        }
        self.emit_all(to, out).await;
    }

    /// The connection to the bus has ended. Nothing can reach this process any
    /// more: no `Close`, no `Disable`, no `--release`, no `--disarm`, and no
    /// notice that the frontend has gone. So everything ends here: every
    /// session is closed (its barriers go, its EIS connection is cut), whatever
    /// is captured is released, and `serve` is told to stop the process.
    pub async fn bus_lost(&self) {
        self.stop_serving("the session bus connection ended").await;
    }

    /// The connection to the compositor has ended (REVIEW-2, finding 2). No
    /// barrier can be placed and no crossing seen any more, while the bus would
    /// keep answering: `Enable` would succeed and sharing would look alive but
    /// be dead. So it ends as a lost bus does, and the next call from the
    /// frontend starts a fresh backend through D-Bus activation. No input can
    /// leak meanwhile: the compositor dropped the grab with the connection.
    pub async fn wayland_lost(&self) {
        self.stop_serving("the Wayland connection ended").await;
    }

    async fn stop_serving(&self, why: &'static str) {
        {
            let _inner = self.inner.lock().await;
            if self.stop_reason.set(Err(why)).is_err() {
                return;
            }
            self.gate.close();
            self.release_everything();
        }
        self.close_sessions(None, why).await;
        self.stop.notify_one();
    }

    fn request_stop(&self, reason: Result<&'static str, &'static str>) {
        if self.stop_reason.set(reason).is_ok() {
            self.stop.notify_one();
        }
    }

    /// Resolves once a teardown completed or a connection was lost.
    pub async fn wait_for_stop(&self) -> Result<&'static str, &'static str> {
        self.stop.notified().await;
        *self.stop_reason.get().expect("stop reason set before notification")
    }

    /// An EIS connection ended. If a session still depends on it, the session is
    /// over: a capture feeding a dead socket can never be ended by its client,
    /// and armed barriers with nowhere to send input would only strand the pointer.
    pub async fn eis_closed(&self, label: &str, eis_id: u32) {
        let Ok(handle) = OwnedObjectPath::try_from(label) else {
            return;
        };
        let mut out = Vec::new();
        let to;
        {
            let mut inner = self.inner.lock().await;
            to = inner.frontend.clone();
            let is_current = inner
                .sessions
                .get(&handle)
                .and_then(|s| s.eis.as_ref())
                .is_some_and(|eis| eis.id() == eis_id);
            if is_current && self.remove_session(&mut inner, &handle, &mut out) {
                warn!(session = %label, "its EIS connection ended: the session is closed");
                self.stop_worker_if_idle(&mut inner);
            }
        }
        self.emit_all(to, out).await;
    }

    // ---- the way out --------------------------------------------------------

    /// Unlock the pointer and clear the screen edges. Used on shutdown so the
    /// session is never left with a grab owned by a process that is going away.
    pub fn release_everything(&self) {
        self.send(WaylandCmd::EndCapture {
            crossing: None,
            cursor_hint: None,
        });
        self.send(WaylandCmd::Disarm);
    }

    /// End every in-flight capture, returning how many there were, once the
    /// compositor has confirmed it: the answer of `--release` must mean the
    /// pointer and the keyboard are back, not that their release is queued.
    /// Unconfirmed within [`CONFIRM_TIMEOUT`] it fails, and `--release` stops the
    /// backend it pinned.
    async fn force_release(&self, disarm: bool) -> fdo::Result<usize> {
        let mut out = Vec::new();
        let to;
        let (released, wayland) = {
            let mut inner = self.inner.lock().await;
            if let Some(teardown) = inner.teardown.clone() {
                drop(inner);
                return if teardown_confirmed(teardown).await {
                    Ok(0)
                } else {
                    Err(fdo::Error::Failed("the compositor did not confirm the release in time".into()))
                };
            }
            to = inner.frontend.clone();
            let mut released = 0;
            for session in inner.sessions.values_mut() {
                if let Some((activation_id, _)) = session.stop_capture() {
                    released += 1;
                    out.push(Signal::Deactivated {
                        session: session.handle.clone(),
                        activation_id,
                    });
                }
                if disarm && session.enabled {
                    session.enabled = false;
                    session.arming = 0;
                    out.push(Signal::Disabled {
                        session: session.handle.clone(),
                    });
                }
            }
            // Unlock first; the client being told afterwards is fine, the point is
            // that the local pointer comes back regardless of what the client does.
            // No crossing is named: whatever is captured ends, also a crossing
            // the portal has not heard of yet.
            self.send(WaylandCmd::EndCapture {
                crossing: None,
                cursor_hint: None,
            });
            if disarm {
                self.send(WaylandCmd::Disarm);
            }
            (released, self.wayland())
        };
        self.emit_all(to, out).await;
        if released > 0 {
            warn!("force-released {released} capture(s)");
        }
        // No worker runs: the backend holds no Wayland connection, so neither
        // the pointer nor the keyboard can be held by it.
        let Some(wayland) = wayland else {
            return Ok(released);
        };
        if !wayland.confirm(CONFIRM_TIMEOUT).await {
            error!("the compositor did not confirm that the pointer and the keyboard are free");
            return Err(fdo::Error::Failed(
                "the compositor did not confirm the release in time".into(),
            ));
        }
        Ok(released)
    }

    async fn status(&self) -> String {
        let inner = self.inner.lock().await;
        if inner.sessions.is_empty() {
            return "no sessions".to_owned();
        }
        inner
            .sessions
            .values()
            .map(|s| {
                format!(
                    "{}: app={:?} enabled={} barriers={} capturing={}",
                    s.handle.as_str(),
                    s.app_id,
                    s.enabled,
                    s.barriers.len(),
                    s.activation_id != 0
                )
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    // ---- what the Wayland thread observes ------------------------------------

    pub async fn handle_event(&self, event: WaylandEvent) {
        match event {
            WaylandEvent::Activated {
                session,
                arming,
                crossing,
                barrier_id,
                position,
            } => {
                self.activated(&session, arming, crossing, barrier_id, position)
                    .await;
            }
            WaylandEvent::CaptureLost { crossing } => self.capture_lost(crossing).await,
            WaylandEvent::OutputsChanged => self.screens_changed().await,
            WaylandEvent::ClipboardSelection {
                mime_types,
                is_ours,
            } => self.selection_changed(mime_types, is_ours).await,
            WaylandEvent::ClipboardSend {
                claim_id,
                mime_type,
                fd,
            } => self.selection_requested(claim_id, mime_type, fd).await,
            WaylandEvent::ClipboardCancelled { claim_id } => self.claim_cancelled(claim_id).await,
        }
    }

    /// The pointer crossed a barrier that arming `arming` put up for `label`,
    /// and the Wayland thread holds the pointer and the keyboard.
    ///
    /// The capture goes on only if that session is still armed by that very
    /// arming, set that barrier, and has an EIS connection. Otherwise it ends
    /// here and now: input taken from the user with no session to give it to
    /// must go straight back.
    async fn activated(&self, label: &str, arming: u64, crossing: u64, barrier_id: u32, position: (f64, f64)) {
        let mut out = Vec::new();
        let to;
        {
            let mut inner = self.inner.lock().await;
            to = inner.frontend.clone();
            // Before `Activated`: with sharing off every session is gone by the
            // lookup below, and the crossing stays local.
            self.switch_locked(&mut inner, &mut out);
            let handle = OwnedObjectPath::try_from(label).ok();
            let session = handle
                .as_ref()
                .and_then(|handle| inner.sessions.get_mut(handle))
                .filter(|s| {
                    s.enabled
                        && s.activation_id == 0
                        && s.eis.is_some()
                        // The crossing names the arming it came from. A session
                        // that was closed, disarmed or armed again since, or a
                        // new session with the same path, has another number.
                        && s.arming != 0
                        && s.arming == arming
                        && s.barriers.iter().any(|b| b.id == barrier_id)
                });
            match session {
                Some(session) => {
                    // Zero means "not capturing", so a wrap skips it.
                    let activation_id = self.next_activation.fetch_add(1, Ordering::Relaxed).max(1);
                    session.activation_id = activation_id;
                    session.crossing = crossing;
                    if let Some(eis) = &session.eis {
                        // The EIS sequence must equal the activation_id so the client
                        // can line up the event stream with this signal.
                        eis.send(EisCommand::StartEmulating {
                            sequence: activation_id,
                        });
                        // The Wayland thread already locked the pointer; this tells it
                        // where to send what that crossing captures.
                        self.send(WaylandCmd::AttachEis {
                            crossing,
                            eis: eis.clone(),
                        });
                    }
                    out.push(Signal::Activated {
                        session: session.handle.clone(),
                        activation_id,
                        barrier_id,
                        cursor: position,
                    });
                }
                None => {
                    warn!(session = %label, barrier_id, "a crossing for a session that may not capture: staying local");
                    self.send(WaylandCmd::EndCapture {
                        crossing: Some(crossing),
                        cursor_hint: None,
                    });
                    // The Wayland thread holds one capture at a time and it has
                    // just been ended, so a session that still counted as
                    // capturing isn't any more.
                    for session in inner.sessions.values_mut() {
                        if let Some((activation_id, _)) = session.stop_capture() {
                            out.push(Signal::Deactivated {
                                session: session.handle.clone(),
                                activation_id,
                            });
                        }
                    }
                    // Whatever is on the edges is out of step; put back what the
                    // armed session has, or nothing.
                    match inner.sessions.values_mut().find(|s| s.enabled) {
                        Some(armed) => self.arm(armed),
                        None => self.send(WaylandCmd::Disarm),
                    }
                }
            }
        }
        self.emit_all(to, out).await;
    }

    /// The grab of `crossing` is already gone (the watchdog, or the compositor
    /// took the lock, the surface, the pointer or the keyboard focus away);
    /// tell the session that owned it so the client stops
    /// expecting events, and put the barriers back.
    async fn capture_lost(&self, crossing: u64) {
        let mut out = Vec::new();
        let to;
        {
            let mut inner = self.inner.lock().await;
            to = inner.frontend.clone();
            for session in inner.sessions.values_mut() {
                if session.activation_id == 0 || session.crossing != crossing {
                    continue;
                }
                if let Some((activation_id, _)) = session.stop_capture() {
                    out.push(Signal::Deactivated {
                        session: session.handle.clone(),
                        activation_id,
                    });
                    if session.enabled {
                        self.arm(session);
                    }
                }
            }
        }
        self.emit_all(to, out).await;
    }

    /// The snapshot changed. The Wayland thread has already ended any capture
    /// and removed every barrier surface; here every session loses the barriers
    /// that describe an old zone set, its EIS devices get the new geometry, and
    /// its client is told to read the zones again.
    ///
    /// Barriers already set against the snapshot as it is now stay: a client can
    /// have read the new zones before this notice was handled, and its barriers
    /// are then on screen.
    async fn screens_changed(&self) {
        let snapshot = self.screens.current();
        let region = snapshot.region();
        let mut out = Vec::new();
        let to;
        {
            let mut inner = self.inner.lock().await;
            to = inner.frontend.clone();
            for session in inner.sessions.values_mut() {
                if let Some((activation_id, _)) = session.stop_capture() {
                    out.push(Signal::Deactivated {
                        session: session.handle.clone(),
                        activation_id,
                    });
                }
                if session.zone_set != snapshot.zone_set {
                    session.barriers.clear();
                    session.zone_set = 0;
                    session.arming = 0;
                }
                if let Some(eis) = &session.eis {
                    eis.send(EisCommand::SetRegion(region));
                }
                out.push(Signal::ZonesChanged {
                    session: session.handle.clone(),
                });
            }
        }
        self.emit_all(to, out).await;
    }

    /// What to tell every clipboard session about the selection as it is now.
    fn announce_selection(inner: &Inner) -> Vec<Signal> {
        let clipboard = &inner.clipboard;
        inner
            .sessions
            .values()
            .filter(|s| s.has_clipboard())
            .map(|s| Signal::SelectionOwnerChanged {
                session: s.handle.clone(),
                mime_types: clipboard.mime_types.clone(),
                session_is_owner: clipboard.owned_by_session
                    && clipboard.owner_session.as_ref() == Some(&s.handle),
            })
            .collect()
    }

    async fn selection_changed(&self, mime_types: Vec<String>, is_ours: bool) {
        let mut out = Vec::new();
        let to = {
            let mut inner = self.inner.lock().await;
            inner.clipboard.mime_types = mime_types;
            inner.clipboard.owned_by_session = is_ours;
            // With sharing off no session is left to be told.
            self.switch_locked(&mut inner, &mut out);
            // Every session with clipboard access needs to know, so it can offer
            // the new content to the machine on the other end.
            out.extend(Self::announce_selection(&inner));
            inner.frontend.clone()
        };
        self.emit_all(to, out).await;
    }

    /// Somebody local is pasting from the selection claim `claim_id` made.
    async fn selection_requested(&self, claim_id: u32, mime_type: String, fd: OwnedFd) {
        let mut out = Vec::new();
        let to = {
            let mut inner = self.inner.lock().await;
            // No new transfer starts with sharing off: every session, and so the
            // claim's owner, is gone by the lookup below.
            self.switch_locked(&mut inner, &mut out);
            let owner = inner
                .clipboard
                .owner_session
                .clone()
                .filter(|owner| claim_id == inner.clipboard.claim_id && inner.sessions.contains_key(owner));
            match owner {
                Some(owner) => {
                    let serial = inner.clipboard.begin_transfer(&owner, fd);
                    debug!(serial, "asking the session for clipboard content");
                    out.push(Signal::SelectionTransfer {
                        session: owner,
                        mime_type,
                        serial,
                    });
                }
                // Dropping `fd` here is what the paster reads as "no data".
                None => debug!("a paste arrived for a claim with no session behind it"),
            }
            inner.frontend.clone()
        };
        self.emit_all(to, out).await;
    }

    /// Another client took the selection from claim `claim_id`.
    async fn claim_cancelled(&self, claim_id: u32) {
        let mut out = Vec::new();
        let to = {
            let mut inner = self.inner.lock().await;
            if claim_id != inner.clipboard.claim_id {
                return;
            }
            let clipboard = &mut inner.clipboard;
            clipboard.owned_by_session = false;
            clipboard.owner_session = None;
            clipboard.claim_id = clipboard.claim_id.wrapping_add(1);
            // Nobody is going to answer these now.
            clipboard.clear_transfers();
            self.switch_locked(&mut inner, &mut out);
            out.extend(Self::announce_selection(&inner));
            inner.frontend.clone()
        };
        self.emit_all(to, out).await;
    }
}

/// Send one signal to the frontend `to` and to nobody else. With nobody to
/// tell, nothing is sent.
async fn send_signal(conn: &zbus::Connection, to: Option<&str>, signal: Signal) -> zbus::Result<()> {
    match to {
        Some(to) => send_signal_to(conn, to, signal).await,
        None => {
            debug!(signal = signal.name(), "no frontend to tell, a signal was dropped");
            Ok(())
        }
    }
}

/// Put one signal on the bus, addressed to `to`.
async fn send_signal_to(conn: &zbus::Connection, to: &str, signal: Signal) -> zbus::Result<()> {
    // A destination makes the bus deliver the signal to that one connection
    // instead of to everybody whose match rule fits.
    let to = zbus::names::BusName::try_from(to.to_owned())?;
    let portal = SignalEmitter::new(conn, PORTAL_PATH)?.set_destination(to.clone());
    let mut options: HashMap<String, Value<'_>> = HashMap::new();
    match signal {
        Signal::Activated {
            session,
            activation_id,
            barrier_id,
            cursor,
        } => {
            options.insert("activation_id".into(), Value::from(activation_id));
            options.insert("barrier_id".into(), Value::from(barrier_id));
            options.insert("cursor_position".into(), Value::from((cursor.0, cursor.1)));
            InputCapture::activated(&portal, session.as_ref(), options).await
        }
        Signal::Deactivated {
            session,
            activation_id,
        } => {
            options.insert("activation_id".into(), Value::from(activation_id));
            InputCapture::deactivated(&portal, session.as_ref(), options).await
        }
        Signal::Disabled { session } => InputCapture::disabled(&portal, session.as_ref(), options).await,
        Signal::ZonesChanged { session } => {
            InputCapture::zones_changed(&portal, session.as_ref(), options).await
        }
        Signal::SelectionOwnerChanged {
            session,
            mime_types,
            session_is_owner,
        } => {
            options.insert("mime_types".into(), Value::from(mime_types));
            options.insert("session_is_owner".into(), Value::from(session_is_owner));
            Clipboard::selection_owner_changed(&portal, session.as_ref(), options).await
        }
        Signal::SelectionTransfer {
            session,
            mime_type,
            serial,
        } => Clipboard::selection_transfer(&portal, session.as_ref(), &mime_type, serial).await,
        Signal::SessionClosed { session } => {
            let emitter = SignalEmitter::new(conn, session.into_inner())?.set_destination(to);
            SessionObject::closed(&emitter).await
        }
    }
}

fn sender_of<'a>(header: &'a Header<'_>) -> Option<&'a str> {
    header.sender().map(|sender| sender.as_str())
}

/// The capability bitmask a client asked for, or zero if it asked for nothing.
fn requested_capabilities(options: &HashMap<String, OwnedValue>) -> u32 {
    options
        .get("capabilities")
        .and_then(|v| u32::try_from(v).ok())
        .unwrap_or(0)
}

/// Helper for the ergonomics of building an `a{sv}`.
fn insert(map: &mut Results, key: &str, value: Value<'_>) {
    match OwnedValue::try_from(value) {
        Ok(v) => {
            map.insert(key.to_owned(), v);
        }
        Err(err) => error!("failed to encode `{key}` for D-Bus: {err}"),
    }
}

pub struct InputCapture {
    state: State,
}

impl InputCapture {
    pub fn new(state: State) -> Self {
        Self { state }
    }
}

#[interface(name = "org.freedesktop.impl.portal.InputCapture")]
impl InputCapture {
    /// Bitmask of what this backend can capture. Constant, per spec — not the
    /// currently-available set.
    #[zbus(property)]
    fn supported_capabilities(&self) -> u32 {
        SUPPORTED_CAPABILITIES
    }

    // Spelled lowercase in the spec, unlike every other member.
    //
    // Version 2 is what makes clipboard sharing reachable: xdg-desktop-portal
    // only offers the Clipboard interface to an InputCapture session from 1.21.1
    // onwards, and only through the v2 handshake. A 1.20 frontend ignores the
    // v2 members and keeps using CreateSession, so this stays backwards
    // compatible.
    #[zbus(property, name = "version")]
    fn version(&self) -> u32 {
        2
    }

    /// The deprecated v1 entry point. The session it makes is already started.
    async fn create_session(
        &self,
        #[zbus(header)] header: Header<'_>,
        _handle: OwnedObjectPath,
        session_handle: OwnedObjectPath,
        app_id: String,
        _parent_window: String,
        options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<(u32, Results)> {
        let granted = self
            .state
            .create_session(
                sender_of(&header),
                &session_handle,
                &app_id,
                Some(requested_capabilities(&options)),
            )
            .await?;
        let mut results = Results::new();
        insert(&mut results, "session_id", Value::from(session_handle.as_str().to_owned()));
        insert(&mut results, "capabilities", Value::from(granted));
        Ok((RESPONSE_SUCCESS, results))
    }

    /// The v2 entry point: creates the session without starting it.
    ///
    /// Capabilities are not negotiated here — that moves to `Start`, which is
    /// what gives `RequestClipboard` somewhere to sit in between.
    #[zbus(name = "CreateSession2")]
    async fn create_session2(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        app_id: String,
        _options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<Results> {
        self.state
            .create_session(sender_of(&header), &session_handle, &app_id, None)
            .await?;
        Ok(Results::new())
    }

    /// Negotiate capabilities and start a session made by `CreateSession2`.
    async fn start(
        &self,
        #[zbus(header)] header: Header<'_>,
        _handle: OwnedObjectPath,
        session_handle: OwnedObjectPath,
        _app_id: String,
        _parent_window: String,
        options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<(u32, Results)> {
        let (granted, clipboard_enabled) = self
            .state
            .start(sender_of(&header), &session_handle, requested_capabilities(&options))
            .await?;
        let mut results = Results::new();
        insert(&mut results, "capabilities", Value::from(granted));
        // Persistence is deliberately not offered: `restore_data` is omitted, so
        // a client asking for persist_mode gets a fresh prompt-free session each
        // time rather than a token that would restore nothing.
        insert(&mut results, "clipboard_enabled", Value::from(clipboard_enabled));
        Ok((RESPONSE_SUCCESS, results))
    }

    async fn get_zones(
        &self,
        #[zbus(header)] header: Header<'_>,
        _handle: OwnedObjectPath,
        session_handle: OwnedObjectPath,
        _app_id: String,
        _options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<(u32, Results)> {
        let (zones, zone_set) = self
            .state
            .get_zones(sender_of(&header), &session_handle)
            .await?;
        let mut results = Results::new();
        insert(&mut results, "zones", Value::from(zones));
        insert(&mut results, "zone_set", Value::from(zone_set));
        Ok((RESPONSE_SUCCESS, results))
    }

    async fn set_pointer_barriers(
        &self,
        #[zbus(header)] header: Header<'_>,
        _handle: OwnedObjectPath,
        session_handle: OwnedObjectPath,
        _app_id: String,
        _options: HashMap<String, OwnedValue>,
        barriers: Vec<HashMap<String, OwnedValue>>,
        zone_set: u32,
    ) -> fdo::Result<(u32, Results)> {
        let specs: Vec<BarrierSpec> = barriers
            .iter()
            .map(|spec| {
                (
                    spec.get("barrier_id").and_then(|v| u32::try_from(v).ok()),
                    spec.get("position")
                        .and_then(|v| <(i32, i32, i32, i32)>::try_from(v.clone()).ok()),
                )
            })
            .collect();
        let failed = self
            .state
            .set_pointer_barriers(sender_of(&header), &session_handle, &specs, zone_set)
            .await?;
        let mut results = Results::new();
        insert(&mut results, "failed_barriers", Value::from(failed));
        Ok((RESPONSE_SUCCESS, results))
    }

    // zbus would derive `ConnectToEis`; the spec capitalises the acronym.
    #[zbus(name = "ConnectToEIS")]
    async fn connect_to_eis(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        _app_id: String,
        _options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<zvariant::OwnedFd> {
        let fd = self
            .state
            .connect_to_eis(sender_of(&header), &session_handle)
            .await?;
        Ok(zvariant::OwnedFd::from(fd))
    }

    async fn enable(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        _app_id: String,
        _options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<(u32, Results)> {
        self.state.enable(sender_of(&header), &session_handle).await?;
        Ok((RESPONSE_SUCCESS, Results::new()))
    }

    async fn disable(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        _app_id: String,
        _options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<(u32, Results)> {
        self.state.disable(sender_of(&header), &session_handle).await?;
        Ok((RESPONSE_SUCCESS, Results::new()))
    }

    async fn release(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        _app_id: String,
        options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<(u32, Results)> {
        let cursor = options
            .get("cursor_position")
            .and_then(|v| <(f64, f64)>::try_from(v.clone()).ok());
        self.state
            .release(sender_of(&header), &session_handle, cursor)
            .await?;
        Ok((RESPONSE_SUCCESS, Results::new()))
    }

    #[zbus(signal)]
    pub async fn activated(
        emitter: &SignalEmitter<'_>,
        session_handle: ObjectPath<'_>,
        options: HashMap<String, Value<'_>>,
    ) -> zbus::Result<()>;

    #[zbus(signal)]
    pub async fn deactivated(
        emitter: &SignalEmitter<'_>,
        session_handle: ObjectPath<'_>,
        options: HashMap<String, Value<'_>>,
    ) -> zbus::Result<()>;

    #[zbus(signal)]
    pub async fn disabled(
        emitter: &SignalEmitter<'_>,
        session_handle: ObjectPath<'_>,
        options: HashMap<String, Value<'_>>,
    ) -> zbus::Result<()>;

    #[zbus(signal)]
    pub async fn zones_changed(
        emitter: &SignalEmitter<'_>,
        session_handle: ObjectPath<'_>,
        options: HashMap<String, Value<'_>>,
    ) -> zbus::Result<()>;
}

/// `org.freedesktop.impl.portal.Clipboard`.
///
/// The clipboard portal creates no session of its own: it attaches to a session
/// another portal already made, and xdg-desktop-portal only offers that to
/// InputCapture sessions from 1.21.1 onwards. Against an older frontend
/// everything here simply goes uncalled.
pub struct Clipboard {
    state: State,
}

impl Clipboard {
    pub fn new(state: State) -> Self {
        Self { state }
    }
}

#[interface(name = "org.freedesktop.impl.portal.Clipboard")]
impl Clipboard {
    // Spelled lowercase in the spec, unlike every other member.
    #[zbus(property, name = "version")]
    fn version(&self) -> u32 {
        1
    }

    async fn request_clipboard(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        _options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<()> {
        self.state
            .request_clipboard(sender_of(&header), &session_handle)
            .await
    }

    async fn set_selection(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        options: HashMap<String, OwnedValue>,
    ) -> fdo::Result<()> {
        let mime_types: Vec<String> = options
            .get("mime_types")
            .and_then(|v| Vec::<String>::try_from(v.clone()).ok())
            .unwrap_or_default();
        self.state
            .set_selection(sender_of(&header), &session_handle, mime_types)
            .await
    }

    async fn selection_write(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        serial: u32,
    ) -> fdo::Result<zvariant::OwnedFd> {
        let fd = self
            .state
            .selection_write(sender_of(&header), &session_handle, serial)
            .await?;
        Ok(zvariant::OwnedFd::from(fd))
    }

    async fn selection_write_done(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        serial: u32,
        success: bool,
    ) -> fdo::Result<()> {
        self.state
            .selection_write_done(sender_of(&header), &session_handle, serial, success)
            .await
    }

    async fn selection_read(
        &self,
        #[zbus(header)] header: Header<'_>,
        session_handle: OwnedObjectPath,
        mime_type: String,
    ) -> fdo::Result<zvariant::OwnedFd> {
        let fd = self
            .state
            .selection_read(sender_of(&header), &session_handle, mime_type)
            .await?;
        Ok(zvariant::OwnedFd::from(fd))
    }

    #[zbus(signal)]
    pub async fn selection_owner_changed(
        emitter: &SignalEmitter<'_>,
        session_handle: ObjectPath<'_>,
        options: HashMap<String, Value<'_>>,
    ) -> zbus::Result<()>;

    #[zbus(signal)]
    pub async fn selection_transfer(
        emitter: &SignalEmitter<'_>,
        session_handle: ObjectPath<'_>,
        mime_type: &str,
        serial: u32,
    ) -> zbus::Result<()>;
}

/// Out-of-band control, deliberately not on the spec interface.
///
/// This exists because every in-band escape can fail: the keyboard is grabbed,
/// the pointer is locked, and the client that is supposed to call `Release` may
/// be the thing that is broken. A D-Bus call works over SSH from another
/// machine, which is the only channel guaranteed to still be reachable.
///
/// It is open to every program on the user's session bus on purpose: all it can
/// do is end a capture, clear the screen edges, or say how many sessions exist.
/// It hands out no input, no clipboard and no file descriptor.
pub struct Control {
    state: State,
}

impl Control {
    pub fn new(state: State) -> Self {
        Self { state }
    }
}

#[interface(name = "org.aresos.InputPortal.Control")]
impl Control {
    /// Drop any active capture and give the pointer and keyboard back. Answers
    /// once the compositor has confirmed it, and fails when it hasn't within
    /// [`CONFIRM_TIMEOUT`].
    async fn force_release(&self) -> fdo::Result<String> {
        // Logged unconditionally: when someone reaches for this, knowing the
        // call arrived at all is the first thing worth confirming.
        info!("ForceRelease requested");
        Ok(match self.state.force_release(false).await? {
            0 => "no capture was active; barriers left as they were".to_owned(),
            released => format!("released {released} capture(s)"),
        })
    }

    /// Drop captures *and* tear the barrier surfaces down, so no edge can
    /// trigger again until a client re-enables. The armed session is told.
    async fn disarm(&self) -> fdo::Result<String> {
        info!("Disarm requested");
        let released = self.state.force_release(true).await?;
        Ok(format!("released {released} capture(s) and disarmed all barriers"))
    }

    /// Read the sharing switch now instead of at the next tick (`--revoke`; the
    /// switch's program runs it after turning sharing off).
    async fn revoke(&self) -> String {
        info!("Revoke requested");
        self.state.revoke().await
    }

    /// Human-readable summary, for checking state without a GUI.
    async fn status(&self) -> String {
        self.state.status().await
    }
}

/// Read the sharing switch every [`SWITCH_INTERVAL`] while any session exists
/// or the Wayland worker starts, so Off takes effect and the backend exits with
/// no second process (`--revoke` only makes it immediate).
pub async fn watch_switch(state: State) {
    let mut tick = tokio::time::interval(SWITCH_INTERVAL);
    tick.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);
    loop {
        tick.tick().await;
        state.reread_switch().await;
    }
}

/// React to EIS connections ending.
pub async fn handle_eis_closed(state: State, mut closed: mpsc::UnboundedReceiver<(String, u32)>) {
    while let Some((label, eis_id)) = closed.recv().await {
        state.eis_closed(&label, eis_id).await;
    }
}

/// Drive portal signals from what the Wayland worker observes.
async fn pump_wayland_events(state: State, mut events: mpsc::UnboundedReceiver<WaylandEvent>) {
    while let Some(event) = events.recv().await {
        state.handle_event(event).await;
    }
    warn!("the Wayland connection ended: closing every session and stopping");
    state.wayland_lost().await;
}

/// Close every session when the frontend's bus name changes hands or is given
/// up, and all of them, for good, when the bus connection itself ends.
pub async fn watch_frontend(state: State, mut changes: fdo::NameOwnerChangedStream) {
    use futures_util::StreamExt as _;

    while let Some(change) = changes.next().await {
        let Ok(args) = change.args() else {
            continue;
        };
        // Somebody owned the name until now. Whether nobody or somebody else owns
        // it from here on, the sessions that owner made have lost their frontend.
        if let Some(old_owner) = &**args.old_owner() {
            state.frontend_left(old_owner.as_str()).await;
        }
    }
    // The stream ends when the connection does, with no last word about the
    // frontend. From here on nobody could close a session or disarm a barrier,
    // so that is done now, and the process stops.
    warn!("the bus connection ended: closing every session and stopping");
    state.bus_lost().await;
}

/// The impl-side Session object xdg-desktop-portal closes when it is done.
pub struct SessionObject {
    state: State,
    handle: OwnedObjectPath,
}

#[interface(name = "org.freedesktop.impl.portal.Session")]
impl SessionObject {
    #[zbus(property, name = "version")]
    fn version(&self) -> u32 {
        1
    }

    async fn close(&self, #[zbus(header)] header: Header<'_>) -> fdo::Result<()> {
        self.state
            .close_session(sender_of(&header), &self.handle)
            .await
    }

    #[zbus(signal)]
    async fn closed(emitter: &SignalEmitter<'_>) -> zbus::Result<()>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::screens::tests::screen;
    use crate::sharing::tests::TempSwitch;
    use crate::trust::tests::TempList;

    const FRONTEND: &str = ":1.5";
    const STRANGER: &str = ":1.99";
    const APP: &str = "org.deskflow.deskflow";

    fn a_pipe() -> OwnedFd {
        // The read end: an fd whose only job here is to be held and dropped.
        rustix::pipe::pipe().expect("pipe").0
    }

    fn path(name: &str) -> OwnedObjectPath {
        OwnedObjectPath::try_from(format!("/org/freedesktop/portal/desktop/session/test/{name}")).unwrap()
    }

    /// The portal state with everything around it replaced: a recorded Wayland
    /// thread, recorded signals, a fixed frontend, and an allow-list and a sharing
    /// switch (on) in temp files.
    struct Rig {
        state: State,
        /// Every worker the state started, in order.
        workers: Arc<std::sync::Mutex<Vec<RecordedWorker>>>,
        hold_ready: Arc<std::sync::atomic::AtomicBool>,
        /// Commands taken from the channel and not yet returned by `cmds`.
        stash: std::sync::Mutex<Vec<WaylandCmd>>,
        /// The Wayland thread's confirmations nobody has answered yet: kept, so
        /// the backend's wait for them neither ends nor fails until a test says.
        syncs: std::sync::Mutex<Vec<tokio::sync::oneshot::Sender<()>>>,
        switch: TempSwitch,
        signals: Arc<std::sync::Mutex<Vec<(Option<String>, Signal)>>>,
        objects: Arc<std::sync::Mutex<std::collections::HashSet<OwnedObjectPath>>>,
        screens: SharedScreens,
        /// The clients' ends of the EIS connections, kept open.
        eis_clients: Vec<OwnedFd>,
        _list: TempList,
        _eis_closed: mpsc::UnboundedReceiver<(String, u32)>,
    }

    impl Rig {
        fn new() -> Self {
            Self::with(Some(&format!("{APP}\n")), Some(FRONTEND))
        }

        fn with(allow_list: Option<&str>, frontend: Option<&str>) -> Self {
            let list = TempList::new(allow_list);
            let workers = Arc::new(std::sync::Mutex::new(Vec::new()));
            let hold_ready = Arc::new(std::sync::atomic::AtomicBool::new(false));
            let signals = Arc::new(std::sync::Mutex::new(Vec::new()));
            let objects = Arc::new(std::sync::Mutex::new(std::collections::HashSet::new()));
            let screens = SharedScreens::new();
            // Two screens side by side: zone set 2.
            screens.commit(vec![screen("A", 0, 0, 1920, 1080), screen("B", 1920, 0, 1920, 1080)]);
            let switch = TempSwitch::new(Some("on\n"));
            let (state, eis_closed) = State::with_trust(
                Spawner::Recording(workers.clone(), hold_ready.clone()),
                screens.clone(),
                eis_server::SharedKeymap::default(),
                Gate::default(),
                Trust {
                    allow_list: list.path.clone(),
                    allow_list_owner: list.owner,
                    switch: switch.switch.clone(),
                    frontend: Frontend::Fixed(std::sync::Mutex::new(frontend.map(str::to_owned))),
                    signals: SignalSink::Record {
                        signals: signals.clone(),
                        objects: objects.clone(),
                    },
                },
            );
            Self {
                state,
                workers,
                hold_ready,
                stash: std::sync::Mutex::new(Vec::new()),
                syncs: std::sync::Mutex::new(Vec::new()),
                switch,
                signals,
                objects,
                screens,
                eis_clients: Vec::new(),
                _list: list,
                _eis_closed: eis_closed,
            }
        }

        /// Move what was sent to the Wayland thread out of the channel: the
        /// confirmations it was asked for aside, the rest into the stash.
        fn drain(&self) {
            for worker in self.workers.lock().unwrap().iter() {
                while let Ok(cmd) = worker.cmds.try_recv() {
                    match cmd {
                        WaylandCmd::Sync { done } => self.syncs.lock().unwrap().push(done),
                        cmd => self.stash.lock().unwrap().push(cmd),
                    }
                }
            }
        }

        /// How many workers the state has started.
        fn started(&self) -> usize {
            self.workers.lock().unwrap().len()
        }

        /// The newest worker's connection ends, as if the compositor had gone.
        fn end_connection(&self) {
            let events = self.workers.lock().unwrap().last_mut().and_then(|worker| worker.events.take());
            drop(events.expect("a worker with its events"));
        }

        /// Everything sent to the Wayland thread since the last call, but the
        /// confirmations it was asked for (`answer_syncs`, `refuse_syncs`).
        fn cmds(&self) -> Vec<WaylandCmd> {
            self.drain();
            std::mem::take(&mut *self.stash.lock().unwrap())
        }

        /// Confirm as the compositor would. Returns how many were waiting.
        fn answer_syncs(&self) -> usize {
            self.drain();
            let waiting = std::mem::take(&mut *self.syncs.lock().unwrap());
            let count = waiting.len();
            for done in waiting {
                let _ = done.send(());
            }
            count
        }

        /// Never confirm them, as a Wayland thread that has gone wouldn't.
        fn refuse_syncs(&self) -> usize {
            self.drain();
            std::mem::take(&mut *self.syncs.lock().unwrap()).len()
        }

        /// Let tasks the state spawned (the confirmation after Off) run.
        async fn settle(&self) {
            for _ in 0..5 {
                tokio::task::yield_now().await;
            }
        }

        /// Run `call`, confirming every Wayland sync it waits for.
        async fn confirmed<T>(&self, call: impl std::future::Future<Output = T>) -> T {
            tokio::pin!(call);
            loop {
                tokio::select! {
                    biased;
                    out = &mut call => return out,
                    () = tokio::task::yield_now() => {
                        self.answer_syncs();
                    }
                }
            }
        }

        fn set_sharing(&self, on: bool) {
            self.switch.set(on.then_some("on\n"));
        }

        fn signals(&self) -> Vec<Signal> {
            self.addressed().into_iter().map(|(_, signal)| signal).collect()
        }

        /// The signals since the last call, each with the bus name it was sent to.
        fn addressed(&self) -> Vec<(Option<String>, Signal)> {
            std::mem::take(&mut *self.signals.lock().unwrap())
        }

        async fn session_count(&self) -> usize {
            self.state.inner.lock().await.sessions.len()
        }

        /// A started session with the clipboard, both capabilities and an EIS
        /// connection, and one barrier on the right edge of the right screen.
        async fn session(&mut self, name: &str) -> OwnedObjectPath {
            let s = &self.state;
            let handle = path(name);
            s.create_session(Some(FRONTEND), &handle, APP, None).await.unwrap();
            s.request_clipboard(Some(FRONTEND), &handle).await.unwrap();
            s.start(Some(FRONTEND), &handle, CAP_KEYBOARD | CAP_POINTER).await.unwrap();
            self.eis_clients
                .push(s.connect_to_eis(Some(FRONTEND), &handle).await.unwrap());
            let zone_set = self.screens.current().zone_set;
            let failed = s
                .set_pointer_barriers(Some(FRONTEND), &handle, &[right_edge(7)], zone_set)
                .await
                .unwrap();
            assert!(failed.is_empty());
            self.cmds();
            self.signals();
            handle
        }

        async fn enabled(&self, handle: &OwnedObjectPath) -> bool {
            self.state.inner.lock().await.sessions[handle].enabled
        }

        /// Whether a Session object stands at this path.
        fn has_object(&self, handle: &OwnedObjectPath) -> bool {
            self.objects.lock().unwrap().contains(handle)
        }

        /// Hand the frontend's bus name to another connection.
        fn set_frontend(&self, owner: Option<&str>) {
            let Frontend::Fixed(fixed) = &self.state.trust.frontend else {
                unreachable!("the rig's frontend is fixed");
            };
            *fixed.lock().unwrap() = owner.map(str::to_owned);
        }
    }

    /// The right edge of the right screen of the rig's layout.
    fn right_edge(id: u32) -> BarrierSpec {
        (Some(id), Some((3840, 0, 3840, 1080)))
    }

    static NEXT_CROSSING: std::sync::atomic::AtomicU64 = std::sync::atomic::AtomicU64::new(1);

    /// What the Wayland thread reports when the pointer crosses `session`'s
    /// barrier as it is armed right now.
    async fn crossing_event(state: &State, session: &OwnedObjectPath, barrier_id: u32) -> WaylandEvent {
        let arming = state
            .inner
            .lock()
            .await
            .sessions
            .get(session)
            .map_or(0, |s| s.arming);
        WaylandEvent::Activated {
            session: session.as_str().to_owned(),
            arming,
            crossing: NEXT_CROSSING.fetch_add(1, Ordering::Relaxed),
            barrier_id,
            position: (3839.0, 500.0),
        }
    }

    async fn cross(state: &State, session: &OwnedObjectPath, barrier_id: u32) {
        let event = crossing_event(state, session, barrier_id).await;
        state.handle_event(event).await;
    }

    /// The Wayland thread lost the capture that is running.
    async fn lost(state: &State) {
        let crossing = state
            .inner
            .lock()
            .await
            .sessions
            .values()
            .find(|s| s.activation_id != 0)
            .map_or(0, |s| s.crossing);
        state.handle_event(WaylandEvent::CaptureLost { crossing }).await;
    }

    fn denied<T>(result: fdo::Result<T>) -> bool {
        matches!(result, Err(fdo::Error::AccessDenied(_)))
    }

    // ---- the allow-list ----

    #[tokio::test]
    async fn only_a_listed_application_gets_a_session() {
        let rig = Rig::new();
        let s = &rig.state;
        for (name, app_id) in [("a", ""), ("b", "org.example.Other"), ("c", "org.deskflow.deskflow.evil")] {
            assert!(denied(s.create_session(Some(FRONTEND), &path(name), app_id, None).await), "{app_id:?}");
            assert!(
                denied(s.create_session(Some(FRONTEND), &path(name), app_id, Some(CAP_POINTER)).await),
                "{app_id:?}"
            );
        }
        assert_eq!(rig.session_count().await, 0);

        s.create_session(Some(FRONTEND), &path("ok"), APP, None).await.unwrap();
        assert_eq!(rig.session_count().await, 1);
    }

    #[tokio::test]
    async fn a_missing_or_empty_allow_list_gives_nobody_a_session() {
        for list in [None, Some(""), Some("# nobody yet\n")] {
            let rig = Rig::with(list, Some(FRONTEND));
            for app_id in [APP, ""] {
                assert!(denied(rig.state.create_session(Some(FRONTEND), &path("a"), app_id, None).await));
            }
            assert_eq!(rig.session_count().await, 0);
        }
    }

    // ---- the caller check ----

    /// Every impl method, called by `sender`, against a state that has one
    /// complete, armed session with a parked clipboard transfer.
    async fn every_method_is_refused(rig: &mut Rig, sender: Option<&str>) {
        let victim = rig.session("victim").await;
        rig.state.enable(Some(FRONTEND), &victim).await.unwrap();
        rig.state
            .set_selection(Some(FRONTEND), &victim, vec!["text/plain".into()])
            .await
            .unwrap();
        let claim_id = rig.state.inner.lock().await.clipboard.claim_id;
        rig.state
            .handle_event(WaylandEvent::ClipboardSend {
                claim_id,
                mime_type: "text/plain".into(),
                fd: a_pipe(),
            })
            .await;
        let serial = match rig.signals().pop() {
            Some(Signal::SelectionTransfer { serial, .. }) => serial,
            other => panic!("expected a transfer, got {other:?}"),
        };
        rig.cmds();

        let s = &rig.state;
        let zone_set = rig.screens.current().zone_set;
        let fresh = path("fresh");
        assert!(denied(s.create_session(sender, &fresh, APP, Some(CAP_POINTER)).await), "CreateSession");
        assert!(denied(s.create_session(sender, &fresh, APP, None).await), "CreateSession2");
        assert!(denied(s.start(sender, &victim, CAP_POINTER).await), "Start");
        assert!(denied(s.get_zones(sender, &victim).await), "GetZones");
        assert!(
            denied(s.set_pointer_barriers(sender, &victim, &[right_edge(9)], zone_set).await),
            "SetPointerBarriers"
        );
        assert!(denied(s.connect_to_eis(sender, &victim).await), "ConnectToEIS");
        assert!(denied(s.enable(sender, &victim).await), "Enable");
        assert!(denied(s.disable(sender, &victim).await), "Disable");
        assert!(denied(s.release(sender, &victim, None).await), "Release");
        assert!(denied(s.request_clipboard(sender, &victim).await), "RequestClipboard");
        assert!(denied(s.set_selection(sender, &victim, vec!["text/html".into()]).await), "SetSelection");
        assert!(denied(s.selection_write(sender, &victim, serial).await), "SelectionWrite");
        assert!(denied(s.selection_write_done(sender, &victim, serial, true).await), "SelectionWriteDone");
        assert!(denied(s.selection_read(sender, &victim, "text/plain".into()).await), "SelectionRead");
        assert!(denied(s.close_session(sender, &victim).await), "Session.Close");

        // Nothing moved: no command, no signal, the session as it was.
        assert!(rig.cmds().is_empty());
        assert!(rig.signals().is_empty());
        assert_eq!(rig.session_count().await, 1);
        let inner = rig.state.inner.lock().await;
        let session = &inner.sessions[&victim];
        assert!(session.enabled);
        assert_eq!(session.barriers, [Barrier { id: 7, x1: 3840, y1: 0, x2: 3840, y2: 1080 }]);
        assert_eq!(inner.clipboard.owner_session.as_ref(), Some(&victim));
        assert_eq!(inner.clipboard.transfers.len(), 1, "the transfer's fd stayed here");
    }

    #[tokio::test]
    async fn every_method_refuses_a_caller_that_is_not_the_frontend() {
        every_method_is_refused(&mut Rig::new(), Some(STRANGER)).await;
    }

    #[tokio::test]
    async fn every_method_refuses_a_message_without_a_sender() {
        every_method_is_refused(&mut Rig::new(), None).await;
    }

    #[tokio::test]
    async fn nobody_is_the_frontend_when_the_frontend_is_not_on_the_bus() {
        let rig = Rig::with(Some(&format!("{APP}\n")), None);
        for sender in [Some(FRONTEND), Some(STRANGER), Some(""), None] {
            assert!(denied(rig.state.create_session(sender, &path("a"), APP, None).await));
        }
        assert_eq!(rig.session_count().await, 0);
    }

    fn message_from(sender: Option<&str>) -> zbus::Message {
        let mut builder = zbus::Message::method_call(PORTAL_PATH, "Call").unwrap();
        if let Some(sender) = sender {
            builder = builder.sender(sender).unwrap();
        }
        builder.build(&()).unwrap()
    }

    /// The same rule one layer up, through the methods the bus calls: each of
    /// them must take the sender from the message's header and pass it on. A
    /// method that forgot to would not answer `AccessDenied` here.
    #[tokio::test]
    async fn the_dbus_methods_refuse_every_caller_but_the_header_s_frontend() {
        for sender in [Some(STRANGER), None] {
            let mut rig = Rig::new();
            let victim = rig.session("victim").await;
            let input = InputCapture::new(rig.state.clone());
            let clip = Clipboard::new(rig.state.clone());
            let object = SessionObject {
                state: rig.state.clone(),
                handle: victim.clone(),
            };
            let message = message_from(sender);
            let h = || message.header();
            let o = || victim.clone();
            let app = || APP.to_owned();
            let opts = HashMap::<String, OwnedValue>::new;

            assert!(denied(input.create_session(h(), o(), path("x"), app(), String::new(), opts()).await));
            assert!(denied(input.create_session2(h(), path("x"), app(), opts()).await));
            assert!(denied(input.start(h(), o(), o(), app(), String::new(), opts()).await));
            assert!(denied(input.get_zones(h(), o(), o(), app(), opts()).await));
            assert!(denied(input.set_pointer_barriers(h(), o(), o(), app(), opts(), Vec::new(), 2).await));
            assert!(denied(input.connect_to_eis(h(), o(), app(), opts()).await));
            assert!(denied(input.enable(h(), o(), app(), opts()).await));
            assert!(denied(input.disable(h(), o(), app(), opts()).await));
            assert!(denied(input.release(h(), o(), app(), opts()).await));
            assert!(denied(clip.request_clipboard(h(), o(), opts()).await));
            assert!(denied(clip.set_selection(h(), o(), opts()).await));
            assert!(denied(clip.selection_write(h(), o(), 1).await));
            assert!(denied(clip.selection_write_done(h(), o(), 1, true).await));
            assert!(denied(clip.selection_read(h(), o(), "text/plain".into()).await));
            assert!(denied(object.close(h()).await));

            assert_eq!(rig.session_count().await, 1);
            assert!(rig.cmds().is_empty());
            assert!(rig.signals().is_empty());

            // The header's sender is what decides: the same calls from the
            // frontend's name go through.
            let message = message_from(Some(FRONTEND));
            assert!(input.get_zones(message.header(), o(), o(), app(), opts()).await.is_ok());
            assert!(input.enable(message.header(), o(), app(), opts()).await.is_ok());
            assert!(object.close(message.header()).await.is_ok());
            assert_eq!(rig.session_count().await, 0);
        }
    }

    // ---- one armed session, activations bound to it ----

    #[tokio::test]
    async fn enabling_a_second_session_disarms_the_first_and_tells_it() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        let b = rig.session("b").await;

        rig.state.enable(Some(FRONTEND), &a).await.unwrap();
        assert!(rig.enabled(&a).await);
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::Arm { session, .. }] if session == a.as_str()));
        assert!(rig.signals().is_empty());

        rig.state.enable(Some(FRONTEND), &b).await.unwrap();
        assert!(!rig.enabled(&a).await);
        assert!(rig.enabled(&b).await);
        assert_eq!(rig.signals(), [Signal::Disabled { session: a.clone() }]);
        let cmds = rig.cmds();
        assert!(matches!(
            &cmds[..],
            [WaylandCmd::Disarm, WaylandCmd::Arm { session, .. }] if session == b.as_str()
        ));

        // And back again: at no point are two armed.
        rig.state.enable(Some(FRONTEND), &a).await.unwrap();
        assert!(rig.enabled(&a).await && !rig.enabled(&b).await);
        assert_eq!(rig.signals(), [Signal::Disabled { session: b }]);
    }

    #[tokio::test]
    async fn enabling_a_second_session_ends_the_firsts_capture() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        let b = rig.session("b").await;
        rig.state.enable(Some(FRONTEND), &a).await.unwrap();
        cross(&rig.state, &a, 7).await;
        let activation_id = match &rig.signals()[..] {
            [Signal::Activated { session, activation_id, barrier_id: 7, .. }] if *session == a => *activation_id,
            other => panic!("expected one activation for a, got {other:?}"),
        };
        rig.cmds();

        rig.state.enable(Some(FRONTEND), &b).await.unwrap();
        assert_eq!(
            rig.signals(),
            [
                Signal::Deactivated { session: a.clone(), activation_id },
                Signal::Disabled { session: a.clone() }
            ]
        );
        let cmds = rig.cmds();
        assert!(matches!(
            &cmds[..],
            [WaylandCmd::EndCapture { .. }, WaylandCmd::Disarm, WaylandCmd::Arm { session, .. }] if session == b.as_str()
        ));
        assert_eq!(rig.state.inner.lock().await.sessions[&a].activation_id, 0);
    }

    #[tokio::test]
    async fn an_activation_goes_only_to_the_session_the_barrier_was_armed_for() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        let b = rig.session("b").await;
        rig.state.enable(Some(FRONTEND), &a).await.unwrap();
        rig.state.enable(Some(FRONTEND), &b).await.unwrap();
        rig.cmds();
        rig.signals();

        // A crossing that was armed for a, which is no longer the armed session:
        // nobody is activated, the capture ends, and b's barriers go back up.
        cross(&rig.state, &a, 7).await;
        assert!(rig.signals().is_empty());
        let cmds = rig.cmds();
        assert!(matches!(
            &cmds[..],
            [WaylandCmd::EndCapture { .. }, WaylandCmd::Arm { session, .. }] if session == b.as_str()
        ));

        // A barrier b never set.
        cross(&rig.state, &b, 8).await;
        assert!(rig.signals().is_empty());
        assert!(matches!(rig.cmds()[0], WaylandCmd::EndCapture { .. }));

        // A session that doesn't exist.
        cross(&rig.state, &path("ghost"), 7).await;
        assert!(rig.signals().is_empty());
        assert!(matches!(rig.cmds()[0], WaylandCmd::EndCapture { .. }));

        // b's own barrier: b, and only b, is activated and gets the input.
        cross(&rig.state, &b, 7).await;
        let signals = rig.signals();
        assert!(matches!(&signals[..], [Signal::Activated { session, barrier_id: 7, .. }] if *session == b));
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::AttachEis { .. }]));

        // The Wayland thread never reports a second crossing during a capture. If
        // the two ever fall out of step, the capture ends and the session is told,
        // instead of going on with nowhere to send the input.
        cross(&rig.state, &b, 7).await;
        assert!(matches!(&rig.signals()[..], [Signal::Deactivated { session, .. }] if *session == b));
        let cmds = rig.cmds();
        assert!(matches!(
            &cmds[..],
            [WaylandCmd::EndCapture { .. }, WaylandCmd::Arm { session, .. }] if session == b.as_str()
        ));
    }

    #[tokio::test]
    async fn release_ends_only_the_callers_own_capture() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        let b = rig.session("b").await;
        rig.state.enable(Some(FRONTEND), &b).await.unwrap();
        cross(&rig.state, &b, 7).await;
        rig.cmds();
        rig.signals();

        rig.state.release(Some(FRONTEND), &a, None).await.unwrap();
        assert!(rig.cmds().is_empty(), "a is not capturing, so it has nothing to release");
        assert_ne!(rig.state.inner.lock().await.sessions[&b].activation_id, 0);

        rig.state.release(Some(FRONTEND), &b, None).await.unwrap();
        let cmds = rig.cmds();
        assert!(matches!(
            &cmds[..],
            [WaylandCmd::EndCapture { .. }, WaylandCmd::Arm { session, .. }] if session == b.as_str()
        ));
    }

    // ---- capabilities ----

    #[tokio::test]
    async fn a_session_is_granted_only_what_the_backend_supports() {
        let rig = Rig::new();
        let s = &rig.state;

        s.create_session(Some(FRONTEND), &path("a"), APP, None).await.unwrap();
        // Nothing can be enabled or connected before Start granted anything.
        assert!(s.connect_to_eis(Some(FRONTEND), &path("a")).await.is_err());
        assert!(s.enable(Some(FRONTEND), &path("a")).await.is_err());
        assert!(s.start(Some(FRONTEND), &path("a"), CAP_TOUCHSCREEN).await.is_err());
        assert!(s.start(Some(FRONTEND), &path("a"), 0).await.is_err());
        let (granted, clipboard) = s
            .start(Some(FRONTEND), &path("a"), CAP_KEYBOARD | CAP_TOUCHSCREEN | 0x80)
            .await
            .unwrap();
        assert_eq!((granted, clipboard), (CAP_KEYBOARD, false));
        assert_eq!(s.inner.lock().await.sessions[&path("a")].capabilities, CAP_KEYBOARD);
        assert!(s.start(Some(FRONTEND), &path("a"), CAP_POINTER).await.is_err(), "Start twice");
        assert_eq!(s.inner.lock().await.sessions[&path("a")].capabilities, CAP_KEYBOARD);

        // The v1 call grants at creation.
        let granted = s
            .create_session(Some(FRONTEND), &path("b"), APP, Some(CAP_POINTER | CAP_TOUCHSCREEN))
            .await
            .unwrap();
        assert_eq!(granted, CAP_POINTER);
        assert!(s.create_session(Some(FRONTEND), &path("c"), APP, Some(CAP_TOUCHSCREEN)).await.is_err());

        // Enable still needs the EIS connection.
        assert!(s.enable(Some(FRONTEND), &path("b")).await.is_err());
        assert!(rig.cmds().is_empty());
    }

    // ---- the clipboard ----

    #[test]
    fn parked_transfers_are_capped() {
        let mut tracker = ClipboardTracker::default();
        for _ in 0..MAX_PENDING_TRANSFERS * 3 {
            tracker.begin_transfer(&path("a"), a_pipe());
        }
        // Local applications poll the clipboard indefinitely; without the cap
        // this is where the process runs out of file descriptors.
        assert_eq!(tracker.transfers.len(), MAX_PENDING_TRANSFERS);
        assert_eq!(tracker.order.len(), MAX_PENDING_TRANSFERS);
    }

    #[test]
    fn the_oldest_transfer_is_the_one_dropped() {
        let mut tracker = ClipboardTracker::default();
        let first = tracker.begin_transfer(&path("a"), a_pipe());
        for _ in 0..MAX_PENDING_TRANSFERS {
            tracker.begin_transfer(&path("a"), a_pipe());
        }
        assert!(
            tracker.take_transfer(&path("a"), first).is_none(),
            "the oldest transfer should have been evicted, not a newer one"
        );
    }

    #[test]
    fn taking_a_transfer_removes_it_once() {
        let mut tracker = ClipboardTracker::default();
        let serial = tracker.begin_transfer(&path("a"), a_pipe());
        assert!(tracker.take_transfer(&path("a"), serial).is_some());
        assert!(tracker.take_transfer(&path("a"), serial).is_none());
        assert!(tracker.order.is_empty(), "order must not keep a taken serial");
    }

    #[test]
    fn serials_never_reuse_zero() {
        // Zero is the "no such transfer" value, so a wrap must skip it.
        let mut tracker = ClipboardTracker { next_serial: u32::MAX, ..Default::default() };
        let serial = tracker.begin_transfer(&path("a"), a_pipe());
        assert_ne!(serial, 0);
    }

    #[test]
    fn a_transfer_can_only_be_taken_by_its_session_with_its_serial() {
        let mut tracker = ClipboardTracker::default();
        let serial = tracker.begin_transfer(&path("a"), a_pipe());
        assert!(tracker.take_transfer(&path("b"), serial).is_none());
        assert!(tracker.take_transfer(&path("a"), serial + 1).is_none());
        assert!(tracker.take_transfer(&path("a"), 0).is_none());
        // The wrong guesses cost the owner nothing.
        assert!(tracker.take_transfer(&path("a"), serial).is_some());
    }

    #[tokio::test]
    async fn a_clipboard_transfer_goes_only_to_the_session_that_owns_the_selection() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        let b = rig.session("b").await;
        let s = &rig.state;

        s.set_selection(Some(FRONTEND), &a, vec!["text/plain".into()]).await.unwrap();
        let claim_id = match &rig.cmds()[..] {
            [WaylandCmd::ClipboardClaim { claim_id, mime_types }] if mime_types == &["text/plain"] => *claim_id,
            other => panic!("expected one claim, got {other:?}"),
        };

        // A local paste: announced to a, the owner, and to nobody else.
        s.handle_event(WaylandEvent::ClipboardSend { claim_id, mime_type: "text/plain".into(), fd: a_pipe() })
            .await;
        let serial = match &rig.signals()[..] {
            [Signal::SelectionTransfer { session, mime_type, serial }] if *session == a && mime_type == "text/plain" => {
                *serial
            }
            other => panic!("expected one transfer for a, got {other:?}"),
        };

        // b knows the serial and still gets no file descriptor.
        assert!(s.selection_write(Some(FRONTEND), &b, serial).await.is_err());
        // Nor does a session that doesn't exist, or a wrong serial.
        assert!(s.selection_write(Some(FRONTEND), &path("ghost"), serial).await.is_err());
        assert!(s.selection_write(Some(FRONTEND), &a, serial + 1).await.is_err());
        // a gets it, once.
        assert!(s.selection_write(Some(FRONTEND), &a, serial).await.is_ok());
        assert!(s.selection_write(Some(FRONTEND), &a, serial).await.is_err());

        // b claims. A paste the compositor asked of a's claim is answered by nobody.
        s.set_selection(Some(FRONTEND), &b, vec!["text/plain".into()]).await.unwrap();
        s.handle_event(WaylandEvent::ClipboardSend { claim_id, mime_type: "text/plain".into(), fd: a_pipe() })
            .await;
        assert!(rig.signals().is_empty());
        assert!(s.inner.lock().await.clipboard.transfers.is_empty());

        // The selection as the compositor reports it: each session learns whether
        // it is the owner, and only b is.
        s.handle_event(WaylandEvent::ClipboardSelection { mime_types: vec!["text/plain".into()], is_ours: true })
            .await;
        let mut owners: Vec<(String, bool)> = rig
            .signals()
            .into_iter()
            .map(|signal| match signal {
                Signal::SelectionOwnerChanged { session, session_is_owner, .. } => {
                    (session.as_str().to_owned(), session_is_owner)
                }
                other => panic!("unexpected {other:?}"),
            })
            .collect();
        owners.sort();
        assert_eq!(owners, [(a.as_str().to_owned(), false), (b.as_str().to_owned(), true)]);

        // a giving up a claim it doesn't hold leaves b's claim alone.
        rig.cmds();
        s.set_selection(Some(FRONTEND), &a, vec![]).await.unwrap();
        assert!(rig.cmds().is_empty());
        assert_eq!(s.inner.lock().await.clipboard.owner_session, Some(b));
    }

    #[tokio::test]
    async fn the_clipboard_needs_request_clipboard_before_start() {
        let rig = Rig::new();
        let s = &rig.state;
        let plain = path("plain");
        s.create_session(Some(FRONTEND), &plain, APP, None).await.unwrap();
        let (_, clipboard) = s.start(Some(FRONTEND), &plain, CAP_POINTER).await.unwrap();
        assert!(!clipboard);
        // Too late now.
        assert!(s.request_clipboard(Some(FRONTEND), &plain).await.is_err());

        assert!(denied(s.set_selection(Some(FRONTEND), &plain, vec!["text/plain".into()]).await));
        assert!(denied(s.selection_read(Some(FRONTEND), &plain, "text/plain".into()).await));
        assert!(denied(s.selection_write(Some(FRONTEND), &plain, 1).await));
        assert!(rig.cmds().is_empty(), "no read or claim reached the compositor");

        // Requested, but not started yet: still nothing.
        let early = path("early");
        s.create_session(Some(FRONTEND), &early, APP, None).await.unwrap();
        s.request_clipboard(Some(FRONTEND), &early).await.unwrap();
        assert!(denied(s.selection_read(Some(FRONTEND), &early, "text/plain".into()).await));
        s.handle_event(WaylandEvent::ClipboardSelection { mime_types: vec!["text/plain".into()], is_ours: false })
            .await;
        assert!(rig.signals().is_empty(), "no session may see the selection yet");

        let (_, clipboard) = s.start(Some(FRONTEND), &early, CAP_POINTER).await.unwrap();
        assert!(clipboard);
        assert!(rig.cmds().is_empty());
    }

    // ---- teardown ----

    /// A session that is armed, capturing and holds the clipboard with a parked
    /// transfer: everything a teardown has to undo.
    async fn busy_session(rig: &mut Rig, name: &str) -> (OwnedObjectPath, u32) {
        let handle = rig.session(name).await;
        let s = &rig.state;
        s.enable(Some(FRONTEND), &handle).await.unwrap();
        cross(s, &handle, 7).await;
        s.set_selection(Some(FRONTEND), &handle, vec!["text/plain".into()]).await.unwrap();
        let claim_id = s.inner.lock().await.clipboard.claim_id;
        s.handle_event(WaylandEvent::ClipboardSend { claim_id, mime_type: "text/plain".into(), fd: a_pipe() })
            .await;
        let activation_id = s.inner.lock().await.sessions[&handle].activation_id;
        assert_ne!(activation_id, 0);
        rig.cmds();
        rig.signals();
        (handle, activation_id)
    }

    /// What must be true after any teardown of `handle`.
    async fn assert_torn_down(rig: &Rig, handle: &OwnedObjectPath, activation_id: u32) {
        let cmds = rig.cmds();
        assert!(cmds.iter().any(|c| matches!(c, WaylandCmd::EndCapture { .. })), "the capture ends");
        assert!(cmds.iter().any(|c| matches!(c, WaylandCmd::Disarm)), "the barriers go");
        assert!(cmds.iter().any(|c| matches!(c, WaylandCmd::ClipboardRelease)), "the claim goes");
        assert!(!cmds.iter().any(|c| matches!(c, WaylandCmd::Arm { .. })));
        assert_eq!(
            rig.signals(),
            [
                Signal::Deactivated { session: handle.clone(), activation_id },
                Signal::SessionClosed { session: handle.clone() }
            ]
        );
        {
            let inner = rig.state.inner.lock().await;
            assert!(!inner.sessions.contains_key(handle));
            assert!(inner.clipboard.owner_session.is_none());
            assert!(inner.clipboard.transfers.is_empty());
        }

        // A late crossing still stays local, including while the backend is
        // waiting for the compositor to confirm the last session's teardown.
        cross(&rig.state, handle, 7).await;
        assert!(rig.signals().is_empty());
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::EndCapture { .. }, WaylandCmd::Disarm]));
        assert!(rig.state.enable(Some(FRONTEND), handle).await.is_err());
        assert!(rig.state.selection_write(Some(FRONTEND), handle, 1).await.is_err());
        assert!(rig.cmds().is_empty());
    }

    #[tokio::test]
    async fn closing_a_session_removes_everything_it_held() {
        let mut rig = Rig::new();
        let (handle, activation_id) = busy_session(&mut rig, "a").await;
        rig.state.close_session(Some(FRONTEND), &handle).await.unwrap();
        assert_torn_down(&rig, &handle, activation_id).await;
    }

    #[tokio::test]
    async fn losing_the_frontend_closes_every_session() {
        let mut rig = Rig::new();
        let idle = rig.session("idle").await;
        let (handle, activation_id) = busy_session(&mut rig, "a").await;
        rig.state.frontend_left(FRONTEND).await;
        assert_eq!(rig.session_count().await, 0);
        let mut signals = rig.signals();
        signals.retain(|signal| *signal != Signal::SessionClosed { session: idle.clone() });
        rig.signals
            .lock()
            .unwrap()
            .extend(signals.into_iter().map(|signal| (Some(FRONTEND.to_owned()), signal)));
        assert_torn_down(&rig, &handle, activation_id).await;
    }

    #[tokio::test]
    async fn a_dead_eis_connection_closes_its_session_before_or_during_a_capture() {
        // During a capture.
        let mut rig = Rig::new();
        let (handle, activation_id) = busy_session(&mut rig, "a").await;
        let eis_id = rig.state.inner.lock().await.sessions[&handle].eis.as_ref().unwrap().id();
        // A notice about some other connection changes nothing.
        rig.state.eis_closed(handle.as_str(), eis_id.wrapping_add(1)).await;
        assert_eq!(rig.session_count().await, 1);
        assert!(rig.cmds().is_empty());
        rig.state.eis_closed(handle.as_str(), eis_id).await;
        assert_torn_down(&rig, &handle, activation_id).await;

        // Before any crossing: armed, not capturing.
        let mut rig = Rig::new();
        let handle = rig.session("b").await;
        rig.state.enable(Some(FRONTEND), &handle).await.unwrap();
        rig.cmds();
        let eis_id = rig.state.inner.lock().await.sessions[&handle].eis.as_ref().unwrap().id();
        rig.state.eis_closed(handle.as_str(), eis_id).await;
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::Disarm, WaylandCmd::EndCapture { .. }, WaylandCmd::Disarm]));
        assert_eq!(rig.signals(), [Signal::SessionClosed { session: handle.clone() }]);
        cross(&rig.state, &handle, 7).await;
        assert!(rig.signals().is_empty(), "the next crossing stays local");
        assert!(!rig.cmds().iter().any(|cmd| matches!(cmd, WaylandCmd::Arm { .. })));
        assert_eq!(rig.confirmed(rig.state.wait_for_stop()).await, Ok("the last session ended"));
    }

    #[tokio::test]
    async fn the_way_out_ends_a_capture_and_disarm_tells_the_session() {
        let mut rig = Rig::new();
        let (handle, activation_id) = busy_session(&mut rig, "a").await;

        assert_eq!(rig.confirmed(rig.state.force_release(false)).await.unwrap(), 1);
        assert_eq!(rig.signals(), [Signal::Deactivated { session: handle.clone(), activation_id }]);
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::EndCapture { .. }]));
        assert!(rig.enabled(&handle).await, "--release leaves the barriers armed");
        assert_eq!(rig.confirmed(rig.state.force_release(false)).await.unwrap(), 0);
        rig.cmds();

        assert_eq!(rig.confirmed(rig.state.force_release(true)).await.unwrap(), 0);
        assert_eq!(rig.signals(), [Signal::Disabled { session: handle.clone() }]);
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::EndCapture { .. }, WaylandCmd::Disarm]));
        assert!(!rig.enabled(&handle).await);
        assert!(rig.state.status().await.contains("enabled=false"));
    }

    // ---- zones and barriers ----

    #[tokio::test]
    async fn zones_come_from_the_snapshot() {
        let mut rig = Rig::new();
        let handle = rig.session("a").await;
        let (zones, zone_set) = rig.state.get_zones(Some(FRONTEND), &handle).await.unwrap();
        assert_eq!(zone_set, rig.screens.current().zone_set);
        assert_eq!(
            zones,
            [
                ZoneTuple { width: 1920, height: 1080, x: 0, y: 0 },
                ZoneTuple { width: 1920, height: 1080, x: 1920, y: 0 }
            ]
        );
        assert!(rig.state.get_zones(Some(FRONTEND), &path("ghost")).await.is_err());
    }

    #[tokio::test]
    async fn barriers_must_fit_the_current_zone_set() {
        let mut rig = Rig::new();
        let handle = rig.session("a").await;
        let s = &rig.state;
        let zone_set = rig.screens.current().zone_set;

        let specs = [
            right_edge(1),
            (Some(2), Some((0, 0, 0, 1080))),       // the left edge of the left screen
            (Some(3), Some((1920, 0, 1920, 1080))), // between the two screens
            (Some(4), Some((500, 0, 500, 1080))),   // inside a screen
            (Some(5), Some((0, 0, 100, 100))),      // not along an axis
            (Some(0), Some((0, 0, 0, 1080))),       // zero is not an ID
            (Some(6), None),                        // no position
            (None, Some((0, 0, 0, 1080))),          // no ID to report
        ];
        let mut failed = s.set_pointer_barriers(Some(FRONTEND), &handle, &specs, zone_set).await.unwrap();
        failed.sort_unstable();
        assert_eq!(failed, [0, 3, 4, 5, 6]);
        let ids: Vec<u32> = s.inner.lock().await.sessions[&handle].barriers.iter().map(|b| b.id).collect();
        assert_eq!(ids, [1, 2]);
        assert!(rig.cmds().is_empty(), "not armed, so nothing is placed");

        // An old zone set: every barrier fails and the ones in force stay.
        let failed = s.set_pointer_barriers(Some(FRONTEND), &handle, &[right_edge(9)], zone_set - 1).await.unwrap();
        assert_eq!(failed, [9]);
        assert_eq!(s.inner.lock().await.sessions[&handle].barriers.len(), 2);

        // Setting barriers on the armed session puts them on screen, tagged with
        // the session and the zone set they were checked against.
        s.enable(Some(FRONTEND), &handle).await.unwrap();
        rig.cmds();
        s.set_pointer_barriers(Some(FRONTEND), &handle, &[right_edge(1)], zone_set).await.unwrap();
        match &rig.cmds()[..] {
            [WaylandCmd::Arm { session, zone_set: armed_for, barriers, .. }] => {
                assert_eq!(session, handle.as_str());
                assert_eq!(*armed_for, zone_set);
                assert_eq!(barriers.len(), 1);
            }
            other => panic!("expected one Arm, got {other:?}"),
        }
    }

    #[tokio::test]
    async fn new_screens_drop_the_barriers_and_tell_every_session() {
        let mut rig = Rig::new();
        let idle = rig.session("idle").await;
        let (handle, activation_id) = busy_session(&mut rig, "a").await;
        let old_zone_set = rig.screens.current().zone_set;

        // The right screen is unplugged. The Wayland thread commits the snapshot
        // (ending the capture and clearing the surfaces itself) and reports it.
        rig.screens.commit(vec![screen("A", 0, 0, 1920, 1080)]).expect("a change");
        rig.state.handle_event(WaylandEvent::OutputsChanged).await;

        let mut signals = rig.signals();
        signals.sort_by_key(|signal| (signal.session().as_str().to_owned(), signal.name()));
        assert_eq!(
            signals,
            [
                Signal::Deactivated { session: handle.clone(), activation_id },
                Signal::ZonesChanged { session: handle.clone() },
                Signal::ZonesChanged { session: idle.clone() },
            ]
        );
        {
            let inner = rig.state.inner.lock().await;
            assert!(inner.sessions.values().all(|s| s.barriers.is_empty() && s.activation_id == 0));
        }
        assert!(!rig.cmds().iter().any(|c| matches!(c, WaylandCmd::Arm { .. })), "nothing is re-armed from old barriers");

        // A second notice for the same snapshot (the compositor can report one
        // change in several steps) tells the clients again and takes nothing more.
        rig.signals();
        rig.state.handle_event(WaylandEvent::OutputsChanged).await;
        assert_eq!(rig.signals().len(), 2);

        // The old zone set is refused, and so is the old screen's edge even with
        // the new number; the new right edge is accepted and armed.
        let s = &rig.state;
        let (zones, zone_set) = s.get_zones(Some(FRONTEND), &handle).await.unwrap();
        assert_ne!(zone_set, old_zone_set);
        assert_eq!(zones.len(), 1);
        assert_eq!(s.set_pointer_barriers(Some(FRONTEND), &handle, &[right_edge(7)], old_zone_set).await.unwrap(), [7]);
        assert_eq!(s.set_pointer_barriers(Some(FRONTEND), &handle, &[right_edge(7)], zone_set).await.unwrap(), [7]);
        let new_edge = (Some(7), Some((1920, 0, 1920, 1080)));
        assert!(s.set_pointer_barriers(Some(FRONTEND), &handle, &[new_edge], zone_set).await.unwrap().is_empty());
        // The misplaced set cleared the edges; the good one is on them now.
        let cmds = rig.cmds();
        assert!(matches!(
            &cmds[..],
            [WaylandCmd::Disarm, WaylandCmd::Arm { zone_set: armed_for, barriers, .. }]
                if *armed_for == zone_set && barriers.len() == 1
        ));

        // A late notice about the snapshot these barriers were set against
        // leaves them in force: they are the ones on screen.
        s.handle_event(WaylandEvent::OutputsChanged).await;
        assert_eq!(s.inner.lock().await.sessions[&handle].barriers.len(), 1);
        cross(s, &handle, 7).await;
        assert!(rig.signals().iter().any(|signal| matches!(signal, Signal::Activated { .. })));
    }

    // ---- logs ----

    #[derive(Clone, Default)]
    struct LogBuffer(Arc<std::sync::Mutex<Vec<u8>>>);

    impl std::io::Write for LogBuffer {
        fn write(&mut self, bytes: &[u8]) -> std::io::Result<usize> {
            self.0.lock().unwrap().extend_from_slice(bytes);
            Ok(bytes.len())
        }

        fn flush(&mut self) -> std::io::Result<()> {
            Ok(())
        }
    }

    /// A whole session at trace level, with a marked cursor position, release
    /// hint and clipboard type, through the accepted paths and the refused ones.
    #[tokio::test]
    async fn the_log_at_trace_carries_no_position_no_hint_and_no_clipboard_type() {
        let buffer = LogBuffer::default();
        let writer = buffer.clone();
        let subscriber = tracing_subscriber::fmt()
            .with_max_level(tracing::Level::TRACE)
            .with_ansi(false)
            // A timestamp's digits could spell a marker by chance.
            .without_time()
            .with_writer(move || writer.clone())
            .finish();
        // Process-wide, not for this thread only: with a thread's own subscriber,
        // tracing switches off for good any log line that another test's thread
        // reaches first. So this also collects what the other tests log from
        // here on, which only makes the check wider. No other test installs one.
        tracing::subscriber::set_global_default(subscriber).expect("the only subscriber in the tests");

        let marked_position = (8_123_456.25, 9_234_567.5);
        let marked_type = "text/x-marker-8123456".to_owned();
        let mut rig = Rig::new();
        let handle = rig.session("logged").await;
        let s = &rig.state;
        let crossing_at_mark = |session: &str, arming: u64| WaylandEvent::Activated {
            session: session.to_owned(),
            arming,
            crossing: NEXT_CROSSING.fetch_add(1, Ordering::Relaxed),
            barrier_id: 7,
            position: marked_position,
        };
        let arming_now = || async { s.inner.lock().await.sessions[&handle].arming };

        s.enable(Some(FRONTEND), &handle).await.unwrap();
        s.handle_event(crossing_at_mark(handle.as_str(), arming_now().await)).await;
        s.release(Some(FRONTEND), &handle, Some(marked_position)).await.unwrap();
        s.set_selection(Some(FRONTEND), &handle, vec![marked_type.clone()]).await.unwrap();
        let claim_id = s.inner.lock().await.clipboard.claim_id;
        s.handle_event(WaylandEvent::ClipboardSelection { mime_types: vec![marked_type.clone()], is_ours: true })
            .await;
        s.handle_event(WaylandEvent::ClipboardSend { claim_id, mime_type: marked_type.clone(), fd: a_pipe() })
            .await;
        // The refusals log too.
        s.handle_event(WaylandEvent::ClipboardSend {
            claim_id: claim_id.wrapping_add(1),
            mime_type: marked_type.clone(),
            fd: a_pipe(),
        })
        .await;
        assert!(s.selection_write(Some(FRONTEND), &handle, 9999).await.is_err());
        assert!(s.selection_read(Some(STRANGER), &handle, marked_type.clone()).await.is_err());
        assert!(s.set_selection(Some(FRONTEND), &path("ghost"), vec![marked_type.clone()]).await.is_err());
        assert!(s.release(Some(STRANGER), &handle, Some(marked_position)).await.is_err());
        s.handle_event(crossing_at_mark("/ghost", 1)).await;
        s.handle_event(crossing_at_mark(handle.as_str(), arming_now().await)).await;
        lost(s).await;
        s.handle_event(WaylandEvent::ClipboardCancelled { claim_id }).await;
        s.handle_event(WaylandEvent::OutputsChanged).await;
        s.close_session(Some(FRONTEND), &handle).await.unwrap();

        let log = String::from_utf8(buffer.0.lock().unwrap().clone()).unwrap();
        // This test's own lines are there, from every level.
        let session = "session=/org/freedesktop/portal/desktop/session/test/logged";
        for expected in [
            format!("session started {session}"),
            format!("capture released {session}"),
            format!("session claimed the clipboard {session}"),
            format!("refused: no such clipboard transfer for this session {session}"),
            "DEBUG aresos_input_portal::portal: asking the session for clipboard content".to_owned(),
        ] {
            assert!(log.contains(&expected), "{expected:?} is missing, so the log was not captured:\n{log}");
        }
        // Seven digits above the largest process ID, so no number the tests log
        // for another reason (a temp file's name carries the PID) can match.
        for secret in ["8123456", "9234567", "marker"] {
            assert!(!log.contains(secret), "{secret:?} is in the log:\n{log}");
        }
    }

    // ---- REVIEW-1 ------------------------------------------------------------

    #[tokio::test]
    async fn a_crossing_queued_for_a_closed_session_never_reaches_a_new_session_with_its_path() {
        let mut rig = Rig::new();
        let old = rig.session("same").await;
        rig.session("idle").await;
        rig.state.enable(Some(FRONTEND), &old).await.unwrap();
        // The pointer crosses, and the notice is on its way to the portal.
        let queued = crossing_event(&rig.state, &old, 7).await;
        rig.cmds();

        rig.state.close_session(Some(FRONTEND), &old).await.unwrap();
        // Disarm is what makes the Wayland thread drop the crossing and the
        // input it buffered (no EndCapture: the portal knew of no capture).
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::Disarm]));

        // A new session with the same path and the same barrier ID, armed.
        let new = rig.session("same").await;
        assert_eq!(new, old);
        rig.state.enable(Some(FRONTEND), &new).await.unwrap();
        rig.cmds();
        rig.signals();

        rig.state.handle_event(queued).await;
        let cmds = rig.cmds();
        assert!(
            !cmds.iter().any(|c| matches!(c, WaylandCmd::AttachEis { .. })),
            "the old crossing gets no EIS connection"
        );
        assert!(matches!(&cmds[0], WaylandCmd::EndCapture { crossing: Some(_), .. }));
        assert!(!rig.signals().iter().any(|s| matches!(s, Signal::Activated { .. })));
        assert_eq!(rig.state.inner.lock().await.sessions[&new].activation_id, 0);

        // The new session's own crossing counts.
        cross(&rig.state, &new, 7).await;
        assert!(rig.cmds().iter().any(|c| matches!(c, WaylandCmd::AttachEis { .. })));
        assert!(matches!(&rig.signals()[..], [Signal::Activated { session, .. }] if *session == new));
    }

    #[tokio::test]
    async fn every_arming_has_its_own_number_and_a_crossing_of_an_earlier_one_is_refused() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        rig.state.enable(Some(FRONTEND), &a).await.unwrap();
        let first = rig.state.inner.lock().await.sessions[&a].arming;
        let early = crossing_event(&rig.state, &a, 7).await;

        // Disabled and enabled again: armed anew, with a new number.
        rig.state.disable(Some(FRONTEND), &a).await.unwrap();
        assert_eq!(rig.state.inner.lock().await.sessions[&a].arming, 0);
        rig.state.enable(Some(FRONTEND), &a).await.unwrap();
        let second = rig.state.inner.lock().await.sessions[&a].arming;
        assert!(first != 0 && second != 0 && first != second);
        let armed: Vec<u64> = rig
            .cmds()
            .iter()
            .filter_map(|c| match c {
                WaylandCmd::Arm { arming, .. } => Some(*arming),
                _ => None,
            })
            .collect();
        assert_eq!(armed, [first, second], "the Wayland thread is given the same numbers");
        rig.signals();

        rig.state.handle_event(early).await;
        assert!(rig.signals().is_empty(), "nobody is told of a capture");
        assert_eq!(rig.state.inner.lock().await.sessions[&a].activation_id, 0);
    }

    #[tokio::test]
    async fn a_lost_capture_ends_only_the_capture_it_names() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        rig.state.enable(Some(FRONTEND), &a).await.unwrap();
        cross(&rig.state, &a, 7).await;
        rig.cmds();
        rig.signals();

        // The loss of some other crossing changes nothing.
        rig.state
            .handle_event(WaylandEvent::CaptureLost { crossing: u64::MAX })
            .await;
        assert!(rig.signals().is_empty());
        assert!(rig.cmds().is_empty());
        assert_ne!(rig.state.inner.lock().await.sessions[&a].activation_id, 0);

        // The loss of this one (the layer closed, the pointer went away, the
        // lock was dropped) reaches the client, and the barriers go back up.
        lost(&rig.state).await;
        assert!(matches!(&rig.signals()[..], [Signal::Deactivated { session, .. }] if *session == a));
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::Arm { .. }]));
        assert_eq!(rig.state.inner.lock().await.sessions[&a].activation_id, 0);
    }

    #[tokio::test]
    async fn every_signal_goes_to_the_frontend_that_made_the_session_and_to_nobody_else() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        let b = rig.session("b").await;
        let s = &rig.state;
        s.enable(Some(FRONTEND), &a).await.unwrap();
        cross(s, &a, 7).await;
        s.enable(Some(FRONTEND), &b).await.unwrap();
        s.handle_event(WaylandEvent::ClipboardSelection {
            mime_types: vec!["text/plain".into()],
            is_ours: false,
        })
        .await;
        s.set_selection(Some(FRONTEND), &b, vec!["text/plain".into()])
            .await
            .unwrap();
        let claim_id = s.inner.lock().await.clipboard.claim_id;
        s.handle_event(WaylandEvent::ClipboardSend {
            claim_id,
            mime_type: "text/plain".into(),
            fd: a_pipe(),
        })
        .await;
        rig.screens.commit(vec![screen("A", 0, 0, 1920, 1080)]);
        s.handle_event(WaylandEvent::OutputsChanged).await;
        s.close_session(Some(FRONTEND), &a).await.unwrap();

        let sent = rig.addressed();
        for name in [
            "Activated",
            "Deactivated",
            "Disabled",
            "SelectionOwnerChanged",
            "SelectionTransfer",
            "ZonesChanged",
            "SessionClosed",
        ] {
            assert!(sent.iter().any(|(_, signal)| signal.name() == name), "{name} was sent");
        }
        for (to, signal) in &sent {
            assert_eq!(to.as_deref(), Some(FRONTEND), "{signal:?}");
        }
    }

    #[tokio::test]
    async fn losing_the_bus_closes_every_session_gives_the_input_back_and_stops_the_backend() {
        let mut rig = Rig::new();
        let (busy, _) = busy_session(&mut rig, "busy").await;
        rig.session("idle").await;
        rig.cmds();
        rig.signals();

        rig.state.bus_lost().await;
        assert_eq!(rig.session_count().await, 0);
        let cmds = rig.cmds();
        assert!(
            matches!(cmds.first(), Some(WaylandCmd::EndCapture { crossing: None, .. })),
            "whatever is captured is released first"
        );
        assert!(cmds.iter().any(|c| matches!(c, WaylandCmd::Disarm)), "the barriers go");

        // A crossing after that stays local.
        cross(&rig.state, &busy, 7).await;
        assert!(!rig.cmds().iter().any(|c| matches!(c, WaylandCmd::AttachEis { .. })));
        assert!(!rig.signals().iter().any(|s| matches!(s, Signal::Activated { .. })));

        // `serve` waits on this to end the process.
        let why = tokio::time::timeout(std::time::Duration::from_secs(1), rig.state.wait_for_stop())
            .await
            .expect("the backend is told to stop");
        assert_eq!(why, Err("the session bus connection ended"));
    }

    // ---- 316's follow-ups, brief 321 "What to build" 1 ----

    #[tokio::test]
    async fn losing_the_wayland_connection_closes_every_session_and_stops_the_backend() {
        let mut rig = Rig::new();
        let (busy, _) = busy_session(&mut rig, "busy").await;
        let idle = rig.session("idle").await;
        rig.cmds();
        rig.signals();

        // The running worker holds the sending end; it ends with its connection.
        // Its commands are read before the pump has seen the end.
        rig.end_connection();
        tokio::time::timeout(std::time::Duration::from_secs(1), async {
            while rig.session_count().await > 0 {
                tokio::task::yield_now().await;
            }
        })
        .await
        .expect("the pump sees the end");
        rig.settle().await;

        assert_eq!(rig.session_count().await, 0);
        let closed: Vec<Signal> = rig
            .signals()
            .into_iter()
            .filter(|signal| matches!(signal, Signal::SessionClosed { .. }))
            .collect();
        assert_eq!(closed.len(), 2, "both sessions are closed and their clients told");
        assert!(!rig.has_object(&busy) && !rig.has_object(&idle));
        let cmds = rig.cmds();
        assert!(matches!(cmds.first(), Some(WaylandCmd::EndCapture { crossing: None, .. })));
        assert!(cmds.iter().any(|c| matches!(c, WaylandCmd::Disarm)));
        let why = tokio::time::timeout(std::time::Duration::from_secs(1), rig.state.wait_for_stop())
            .await
            .expect("the backend is told to stop");
        assert_eq!(why, Err("the Wayland connection ended"));
    }

    #[tokio::test]
    async fn a_new_owner_of_the_frontend_name_gets_nothing_of_the_old_owner_s_sessions() {
        const NEW: &str = ":1.6";
        let mut rig = Rig::new();
        let (old, _) = busy_session(&mut rig, "old").await;
        let s = &rig.state;
        s.handle_event(WaylandEvent::ClipboardSelection {
            mime_types: vec!["text/plain".into()],
            is_ours: false,
        })
        .await;
        rig.cmds();
        rig.signals();

        // The name changes hands; the watch has not run yet.
        rig.set_frontend(Some(NEW));
        // The old owner is refused like any stranger.
        assert!(denied(s.selection_read(Some(FRONTEND), &old, "text/plain".into()).await));
        assert_eq!(rig.session_count().await, 1);

        // The new owner's first call, whichever method it is, closes the old
        // owner's sessions before it looks: no pipe and no EIS socket for it.
        assert!(s.selection_read(Some(NEW), &old, "text/plain".into()).await.is_err());
        assert!(!rig.cmds().iter().any(|c| matches!(c, WaylandCmd::ClipboardRead { .. })));
        assert_eq!(rig.session_count().await, 0);
        assert!(s.connect_to_eis(Some(NEW), &old).await.is_err());
        // The old session's signals go to nobody, and certainly not to the new owner.
        let sent = rig.addressed();
        assert!(sent.iter().any(|(_, signal)| *signal == Signal::SessionClosed { session: old.clone() }));
        assert!(sent.iter().all(|(to, _)| to.is_none()), "{sent:?}");

        // After activation of a fresh backend, a late notice that the old
        // owner left cannot close a session of the new owner.
        assert_eq!(rig.confirmed(s.wait_for_stop()).await, Ok("the last session ended"));
        let fresh = Rig::with(Some(APP), Some(NEW));
        let s = &fresh.state;
        let new = path("new");
        s.create_session(Some(NEW), &new, APP, None).await.unwrap();
        s.frontend_left(FRONTEND).await;
        assert_eq!(fresh.session_count().await, 1);
        // The notice for the new owner does.
        s.frontend_left(NEW).await;
        assert_eq!(fresh.session_count().await, 0);
        assert_eq!(fresh.confirmed(s.wait_for_stop()).await, Ok("the last session ended"));
    }

    #[tokio::test]
    async fn a_session_made_at_a_path_just_closed_keeps_its_object() {
        let mut rig = Rig::new();
        let handle = rig.session("reused").await;
        assert!(rig.has_object(&handle));

        // `Close` and `CreateSession2` for the same path right after each other:
        // the new session is stored before the old one's `Closed` goes out.
        let mut out = Vec::new();
        {
            let mut inner = rig.state.inner.lock().await;
            assert!(rig.state.remove_session(&mut inner, &handle, &mut out));
        }
        rig.state
            .create_session(Some(FRONTEND), &handle, APP, None)
            .await
            .unwrap();
        rig.state.emit_all(Some(FRONTEND.to_owned()), out).await;
        assert!(rig.has_object(&handle), "the new session can still be closed");

        // Closing the new session removes the object.
        rig.state.close_session(Some(FRONTEND), &handle).await.unwrap();
        assert_eq!(rig.session_count().await, 0);
        assert!(!rig.has_object(&handle));
    }

    #[tokio::test]
    async fn an_empty_id_is_refused_whatever_the_list_holds() {
        let rig = Rig::with(Some("\n \norg.deskflow.deskflow\n\n"), Some(FRONTEND));
        let result = rig.state.create_session(Some(FRONTEND), &path("a"), "", None).await;
        assert!(denied(result));
        assert_eq!(rig.session_count().await, 0);
        assert!(!rig.has_object(&path("a")));
    }

    #[test]
    fn a_signals_debug_form_carries_no_position_and_no_types() {
        let activated = Signal::Activated {
            session: path("a"),
            activation_id: 31337,
            barrier_id: 4242,
            cursor: (1234.5, 678.25),
        };
        let offered = Signal::SelectionOwnerChanged {
            session: path("a"),
            mime_types: vec!["text/x-marker".into()],
            session_is_owner: true,
        };
        let text = format!("{activated:?} {offered:?}");
        for secret in ["1234", "678", "marker"] {
            assert!(!text.contains(secret), "{text}");
        }
    }

    // ---- the sharing switch (brief 321) ----

    fn sharing_was_off<T>(result: fdo::Result<T>) -> bool {
        matches!(result, Err(fdo::Error::AccessDenied(why)) if why == "sharing is off")
    }

    /// Whether every writer of the pipe whose read end this is has gone.
    fn writers_gone(read: &OwnedFd) -> bool {
        use rustix::event::{poll, PollFd, PollFlags, Timespec};
        let mut fds = [PollFd::new(read, PollFlags::IN)];
        let now = Timespec { tv_sec: 0, tv_nsec: 0 };
        poll(&mut fds, Some(&now)).unwrap();
        fds[0].revents().contains(PollFlags::HUP)
    }

    #[tokio::test]
    async fn with_sharing_off_a_listed_application_gets_no_session() {
        let rig = Rig::new();
        let s = &rig.state;
        for switch in [None, Some("ON\n"), Some("off\n"), Some("on x\n")] {
            rig.switch.set(switch);
            assert!(sharing_was_off(s.create_session(Some(FRONTEND), &path("a"), APP, None).await), "{switch:?}");
            assert!(sharing_was_off(s.create_session(Some(FRONTEND), &path("b"), APP, Some(CAP_POINTER)).await), "{switch:?}");
            assert!(!s.gate.is_open(), "{switch:?}");
        }
        assert_eq!(rig.session_count().await, 0);
        assert!(!rig.has_object(&path("a")));
        // The list still decides first: an unlisted ID is refused as before.
        rig.set_sharing(true);
        assert!(denied(s.create_session(Some(FRONTEND), &path("c"), "org.example.Other", None).await));
        s.create_session(Some(FRONTEND), &path("d"), APP, None).await.unwrap();
        assert!(s.gate.is_open(), "on opens the gate for the input path");
    }

    #[tokio::test]
    async fn turning_sharing_off_ends_everything_without_revoke() {
        let mut rig = Rig::new();
        let (a, activation_id) = busy_session(&mut rig, "a").await;
        let b = rig.session("b").await;
        assert!(rig.state.gate.is_open());

        // Nobody calls --revoke: the timer reads the switch while sessions exist.
        let timer = tokio::spawn(watch_switch(rig.state.clone()));
        rig.set_sharing(false);
        tokio::time::sleep(SWITCH_INTERVAL * 2).await;

        assert!(!rig.state.gate.is_open(), "forwarding stops at once");
        assert_eq!(rig.session_count().await, 0, "every session is closed");
        let signals = rig.signals();
        assert!(signals.contains(&Signal::Deactivated { session: a.clone(), activation_id }));
        for handle in [&a, &b] {
            assert!(signals.contains(&Signal::SessionClosed { session: handle.clone() }));
            assert!(!rig.has_object(handle));
        }
        let cmds = rig.cmds();
        assert!(cmds.iter().any(|c| matches!(c, WaylandCmd::EndCapture { crossing: Some(_), .. })), "the capture ends");
        assert!(cmds.iter().any(|c| matches!(c, WaylandCmd::EndCapture { crossing: None, .. })), "and anything else captured");
        assert!(cmds.iter().any(|c| matches!(c, WaylandCmd::ClipboardRelease)), "the claim goes");
        assert!(matches!(cmds.last(), Some(WaylandCmd::Disarm)), "no barrier stays up");
        {
            let inner = rig.state.inner.lock().await;
            assert!(inner.clipboard.owner_session.is_none() && inner.clipboard.transfers.is_empty());
        }

        // Confirmation ends the process and takes its connection with it.
        assert_eq!(rig.answer_syncs(), 1);
        assert_eq!(rig.state.wait_for_stop().await, Ok("sharing was turned off"));
        timer.abort();
    }

    #[tokio::test]
    async fn enable_and_each_crossing_read_the_switch() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        rig.set_sharing(false);
        assert!(sharing_was_off(rig.state.enable(Some(FRONTEND), &a).await));
        assert_eq!(rig.session_count().await, 0, "the refusal ended the session too");
        rig.settle().await;
        rig.answer_syncs();

        // Armed with sharing on, then off before the crossing reaches the portal
        // (the Wayland thread already holds the grab): no Activated, and the
        // crossing goes back to the local screen.
        let mut rig = Rig::new();
        let b = rig.session("b").await;
        rig.state.enable(Some(FRONTEND), &b).await.unwrap();
        let crossing = crossing_event(&rig.state, &b, 7).await;
        rig.cmds();
        rig.signals();
        rig.set_sharing(false);
        rig.state.handle_event(crossing).await;
        let signals = rig.signals();
        assert!(!signals.iter().any(|s| matches!(s, Signal::Activated { .. })), "{signals:?}");
        assert!(signals.contains(&Signal::SessionClosed { session: b.clone() }));
        // The crossing the portal hasn't let through ends, with whatever
        // else is captured.
        assert!(rig.cmds().iter().any(|c| matches!(c, WaylandCmd::EndCapture { crossing: None, .. })));
        assert!(!rig.state.gate.is_open());
        rig.settle().await;
        assert_eq!(rig.answer_syncs(), 1);
    }

    #[tokio::test]
    async fn every_clipboard_call_reads_the_switch() {
        let mut rig = Rig::new();
        let (a, _) = busy_session(&mut rig, "a").await;
        let serial = rig.state.inner.lock().await.clipboard.transfers.keys().copied().next().unwrap();
        // A session made with sharing on and not started yet, for RequestClipboard.
        let fresh = path("fresh");
        rig.state.create_session(Some(FRONTEND), &fresh, APP, None).await.unwrap();
        rig.set_sharing(false);
        let s = &rig.state;
        assert!(sharing_was_off(s.request_clipboard(Some(FRONTEND), &fresh).await));
        assert!(sharing_was_off(s.set_selection(Some(FRONTEND), &a, vec!["text/plain".into()]).await));
        assert!(sharing_was_off(s.selection_write(Some(FRONTEND), &a, serial).await), "no descriptor");
        assert!(sharing_was_off(s.selection_write_done(Some(FRONTEND), &a, serial, true).await));
        assert!(sharing_was_off(s.selection_read(Some(FRONTEND), &a, "text/plain".into()).await), "no descriptor");
        assert!(!rig.cmds().iter().any(|c| matches!(c, WaylandCmd::ClipboardRead { .. } | WaylandCmd::ClipboardClaim { .. })));

        // No new transfer starts either way: a local paste and a local copy
        // after Off reach no session, and the paster's pipe is let go.
        rig.signals();
        let (read, write) = rustix::pipe::pipe().unwrap();
        let claim_id = s.inner.lock().await.clipboard.claim_id;
        s.handle_event(WaylandEvent::ClipboardSend { claim_id, mime_type: "text/plain".into(), fd: write }).await;
        assert!(writers_gone(&read), "the paste's pipe was dropped");
        s.handle_event(WaylandEvent::ClipboardSelection { mime_types: vec!["text/plain".into()], is_ours: false }).await;
        assert_eq!(rig.signals(), [], "no transfer and no announcement");
        rig.settle().await;
        rig.answer_syncs();
    }

    #[tokio::test]
    async fn a_clipboard_read_hands_out_no_descriptor_if_sharing_went_off_while_it_waited() {
        // Two ways the read is overtaken during its wait for the Wayland thread:
        // sharing goes off, or the session is closed.
        for overtaken_by_off in [true, false] {
            let mut rig = Rig::new();
            let a = rig.session("a").await;
            let state = rig.state.clone();
            let session = a.clone();
            let read = tokio::spawn(async move { state.selection_read(Some(FRONTEND), &session, "text/plain".into()).await });
            let mut reply = None;
            for _ in 0..50 {
                tokio::task::yield_now().await;
                reply = rig.cmds().into_iter().find_map(|cmd| match cmd {
                    WaylandCmd::ClipboardRead { reply, .. } => Some(reply),
                    _ => None,
                });
                if reply.is_some() {
                    break;
                }
            }
            let reply = reply.expect("the read asked the Wayland thread");

            if overtaken_by_off {
                rig.set_sharing(false);
            } else {
                rig.state.close_session(Some(FRONTEND), &a).await.unwrap();
            }
            let (pipe, write) = rustix::pipe::pipe().unwrap();
            reply.send(Some(pipe)).unwrap();
            let result = read.await.unwrap();
            if overtaken_by_off {
                assert!(sharing_was_off(result), "no descriptor comes back");
                assert_eq!(rig.session_count().await, 0);
            } else {
                assert!(denied(result), "no descriptor comes back");
            }
            // The backend let go of the read end: the owner writing finds nobody.
            assert_eq!(rustix::io::write(&write, b"x"), Err(rustix::io::Errno::PIPE));
        }

        // Not overtaken, the same read gets the pipe.
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        let state = rig.state.clone();
        let read = tokio::spawn(async move { state.selection_read(Some(FRONTEND), &a, "text/plain".into()).await });
        let mut reply = None;
        for _ in 0..50 {
            tokio::task::yield_now().await;
            reply = rig.cmds().into_iter().find_map(|cmd| match cmd {
                WaylandCmd::ClipboardRead { reply, .. } => Some(reply),
                _ => None,
            });
            if reply.is_some() {
                break;
            }
        }
        reply.unwrap().send(Some(a_pipe())).unwrap();
        assert!(read.await.unwrap().is_ok());
    }

    #[tokio::test]
    async fn revoke_reads_the_switch_now_and_answers_after_the_compositor() {
        let mut rig = Rig::new();
        busy_session(&mut rig, "a").await;
        // On: it changes nothing. It can't turn sharing on or off by itself.
        assert_eq!(rig.state.revoke().await, "sharing is on: nothing changed");
        assert_eq!(rig.session_count().await, 1);
        assert!(rig.state.gate.is_open());

        rig.set_sharing(false);
        let state = rig.state.clone();
        let revoke = tokio::spawn(async move { state.revoke().await });
        rig.settle().await;
        assert!(!revoke.is_finished(), "it waits for the compositor");
        assert_eq!(rig.session_count().await, 0, "the sessions are closed at once");
        assert!(!rig.state.gate.is_open());
        assert_eq!(rig.answer_syncs(), 1);
        assert_eq!(revoke.await.unwrap(), "sharing is off: closed 1 session(s)");
        assert_eq!(rig.state.wait_for_stop().await, Ok("sharing was turned off"));
        assert_eq!(rig.state.revoke().await, "sharing is off: closed 0 session(s)");
    }

    #[tokio::test]
    async fn off_unconfirmed_by_the_compositor_stops_the_backend() {
        // The compositor never answers (labwc stopped): the backend stops a
        // second after it read Off.
        let mut rig = Rig::new();
        busy_session(&mut rig, "a").await;
        rig.set_sharing(false);
        let began = std::time::Instant::now();
        let said = rig.state.revoke().await;
        assert!(said.ends_with("the compositor did not confirm, so the backend stops"), "{said}");
        let took = began.elapsed();
        assert!(took >= CONFIRM_TIMEOUT && took < CONFIRM_TIMEOUT + Duration::from_millis(500), "{took:?}");
        assert_eq!(rig.state.wait_for_stop().await, Err("the compositor did not confirm the end of the capture"));

        // From the timer's read, the confirmation runs on its own task; a
        // Wayland thread that is gone never confirms either.
        let mut rig = Rig::new();
        busy_session(&mut rig, "a").await;
        rig.set_sharing(false);
        rig.state.reread_switch().await;
        rig.settle().await;
        assert_eq!(rig.refuse_syncs(), 1);
        rig.settle().await;
        assert_eq!(rig.state.wait_for_stop().await, Err("the compositor did not confirm the end of the capture"));
    }

    #[tokio::test]
    async fn force_release_answers_only_after_the_compositor_confirms() {
        let mut rig = Rig::new();
        busy_session(&mut rig, "a").await;
        let state = rig.state.clone();
        let release = tokio::spawn(async move { state.force_release(false).await });
        rig.settle().await;
        assert!(!release.is_finished(), "the teardown is only queued: no answer yet");
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::EndCapture { .. }]), "asked after the teardown");
        assert_eq!(rig.answer_syncs(), 1);
        assert_eq!(release.await.unwrap().unwrap(), 1);

        // Unconfirmed, it fails, and `--release` then kills the backend it pinned.
        let state = rig.state.clone();
        let release = tokio::spawn(async move { state.force_release(false).await });
        rig.settle().await;
        assert_eq!(rig.refuse_syncs(), 1);
        assert!(release.await.unwrap().is_err());
    }

    // ---- the Wayland worker (brief 321, step 3 review, finding 1) ----

    #[tokio::test]
    async fn the_wayland_worker_starts_only_for_an_authorized_session_while_sharing_is_on() {
        let rig = Rig::new();
        let s = &rig.state;
        // Off: the bus side answers and refuses, and no worker means no Wayland
        // connection: no output management, no clipboard data control.
        rig.set_sharing(false);
        assert!(sharing_was_off(s.create_session(Some(FRONTEND), &path("a"), APP, None).await));
        assert!(sharing_was_off(s.create_session(Some(FRONTEND), &path("a"), APP, Some(CAP_POINTER)).await));
        assert_eq!(rig.started(), 0);
        assert!(!s.worker_running());
        // On, but refused by another check: still none.
        rig.set_sharing(true);
        assert!(denied(s.create_session(Some(STRANGER), &path("b"), APP, None).await));
        assert!(denied(s.create_session(Some(FRONTEND), &path("c"), "org.example.Other", None).await));
        assert!(denied(s.create_session(Some(FRONTEND), &path("d"), "", None).await));
        assert_eq!(rig.started(), 0);
        // The status and the way out need none: nothing to confirm without a connection.
        assert_eq!(s.status().await, "no sessions");
        assert_eq!(s.force_release(false).await.unwrap(), 0);
        assert_eq!(rig.refuse_syncs(), 0);
        rig.state.reread_switch().await;
        assert_eq!(rig.started(), 0);
        // An authorized request while on: one worker, for every session.
        s.create_session(Some(FRONTEND), &path("e"), APP, None).await.unwrap();
        s.create_session(Some(FRONTEND), &path("f"), APP, None).await.unwrap();
        assert_eq!(rig.started(), 1);
        assert!(s.worker_running());
    }

    #[tokio::test]
    async fn off_during_startup_exits_with_or_without_worker_readiness() {
        for becomes_ready in [true, false] {
            let rig = Rig::new();
            rig.hold_ready.store(true, Ordering::Relaxed);
            let state = rig.state.clone();
            let create = tokio::spawn(async move {
                state.create_session(Some(FRONTEND), &path("starting"), APP, None).await
            });
            rig.settle().await;
            assert_eq!(rig.started(), 1);
            assert!(!create.is_finished());
            rig.set_sharing(false);

            if becomes_ready {
                // The startup path itself notices Off without the watcher.
                rig.workers.lock().unwrap()[0].ready.take().unwrap().send(Ok(())).unwrap();
                assert!(sharing_was_off(create.await.unwrap()));
                rig.settle().await;
                assert_eq!(rig.answer_syncs(), 1);
                assert_eq!(rig.state.wait_for_stop().await, Ok("sharing was turned off"));
            } else {
                // A round trip stuck at startup cannot keep the socket open
                // until the much later startup timeout.
                let timer = tokio::spawn(watch_switch(rig.state.clone()));
                let reason = tokio::time::timeout(SWITCH_INTERVAL + CONFIRM_TIMEOUT + Duration::from_millis(300),
                                                  rig.state.wait_for_stop()).await.unwrap();
                assert_eq!(reason, Err("the compositor did not confirm the end of the capture"));
                assert!(!create.is_finished());
                create.abort();
                timer.abort();
            }
            assert!(!rig.state.gate.is_open());
            assert_eq!(rig.session_count().await, 0);
        }
    }

    #[tokio::test]
    async fn release_during_off_teardown_waits_for_the_same_confirmation() {
        for confirmed in [true, false] {
            let mut rig = Rig::new();
            let (a, _) = busy_session(&mut rig, "a").await;
            rig.set_sharing(false);
            rig.state.reread_switch().await;
            assert!(!rig.has_object(&a));
            assert!(!rig.state.gate.is_open());
            let state = rig.state.clone();
            let release = tokio::spawn(async move { state.force_release(false).await });
            rig.settle().await;
            assert!(!release.is_finished(), "closed sessions do not mean labwc gave back the grab");

            // Turning it back on cannot reopen the gate in the process that
            // holds the old connection.
            rig.set_sharing(true);
            assert!(rig.state.create_session(Some(FRONTEND), &path("late"), APP, None).await.is_err());
            assert!(!rig.state.gate.is_open());
            if confirmed {
                assert_eq!(rig.answer_syncs(), 1);
                assert_eq!(release.await.unwrap().unwrap(), 0);
                assert_eq!(rig.state.wait_for_stop().await, Ok("sharing was turned off"));
            } else {
                assert_eq!(rig.refuse_syncs(), 1);
                assert!(release.await.unwrap().is_err(), "the pidfd fallback must run");
                assert_eq!(rig.state.wait_for_stop().await, Err("the compositor did not confirm the end of the capture"));
            }
        }
    }

    #[tokio::test]
    async fn the_last_session_ends_the_backend_after_confirmation() {
        let mut rig = Rig::new();
        let a = rig.session("a").await;
        let b = rig.session("b").await;
        rig.state.enable(Some(FRONTEND), &b).await.unwrap();
        rig.state.close_session(Some(FRONTEND), &a).await.unwrap();
        assert!(rig.state.gate.is_open(), "b still needs it");
        assert_eq!(rig.answer_syncs(), 0);
        rig.cmds();
        rig.state.close_session(Some(FRONTEND), &b).await.unwrap();
        assert!(rig.state.stop_reason.get().is_none(), "wait for labwc");
        assert!(matches!(&rig.cmds()[..], [WaylandCmd::Disarm, WaylandCmd::EndCapture { .. }, WaylandCmd::Disarm]));
        assert_eq!(rig.confirmed(rig.state.wait_for_stop()).await, Ok("the last session ended"));
        assert!(!rig.state.gate.is_open());
    }

    #[test]
    fn off_takes_effect_within_the_two_second_deadline() {
        assert!(SWITCH_INTERVAL <= Duration::from_millis(500), "the brief's bound on the reread");
        // The switch read late by a whole interval, the compositor never
        // confirming, and the process's own grace before it exits: still inside.
        assert!(SWITCH_INTERVAL + CONFIRM_TIMEOUT + crate::SHUTDOWN_GRACE < Duration::from_millis(1600));
        // The backend gives up on the compositor before `--release` gives up on it.
        assert!(CONFIRM_TIMEOUT < crate::release::DEADLINE);
    }
}
