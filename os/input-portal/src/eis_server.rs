//! EIS (emulated input server) side of the portal.
//!
//! `ConnectToEIS` hands the client one end of a socketpair; this module owns the
//! other end. The client connects as a *receiver* context, so we are the ones
//! creating devices and pushing events at it.
//!
//! The connection lives in its own task. Everything the portal side needs to do
//! is expressed as an [`EisCommand`] so the D-Bus handlers never touch reis
//! objects directly.

use anyhow::{Context as _, Result};
use reis::{
    eis::{self, device::DeviceType},
    enumflags2::BitFlags,
    handshake::EisHandshaker,
    request::{Connection, DeviceCapability, EisRequest, EisRequestConverter},
    PendingRequestResult,
};
use std::{
    os::fd::{AsFd, OwnedFd},
    os::unix::net::UnixStream,
    sync::{Arc, RwLock},
    time::{Duration, Instant},
};
use tokio::{io::unix::AsyncFd, sync::mpsc};
use tracing::{debug, info, warn};

use crate::sharing::Gate;

/// Everything the capture side can ask the EIS connection to emit.
#[derive(Clone)]
pub enum EisCommand {
    /// Begin a capture run. `sequence` must match the `activation_id` sent in
    /// the portal's `Activated` signal — that pairing is the whole point of the
    /// id, it lets the client attribute an event stream to one activation.
    StartEmulating { sequence: u32 },
    StopEmulating,
    Motion { dx: f32, dy: f32 },
    Button { button: u32, press: bool },
    Scroll { dx: f32, dy: f32 },
    ScrollDiscrete { dx: i32, dy: i32 },
    ScrollStop,
    Key { keycode: u32, press: bool },
    /// Close the frame; every batch of events needs one to be delivered.
    Frame,
    /// The screens changed: replace the devices with ones that carry this region.
    SetRegion(Option<Region>),
    /// The session is over: disconnect the receiver and end the connection's task.
    Close,
}

// The command's name and nothing else: these carry key codes, button codes and
// motion, and none of that may reach a log or an error through a `{:?}`.
impl std::fmt::Debug for EisCommand {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::StartEmulating { .. } => "StartEmulating",
            Self::StopEmulating => "StopEmulating",
            Self::Motion { .. } => "Motion",
            Self::Button { .. } => "Button",
            Self::Scroll { .. } => "Scroll",
            Self::ScrollDiscrete { .. } => "ScrollDiscrete",
            Self::ScrollStop => "ScrollStop",
            Self::Key { .. } => "Key",
            Self::Frame => "Frame",
            Self::SetRegion(_) => "SetRegion",
            Self::Close => "Close",
        })
    }
}

/// What a seat may offer a session that was granted these portal capabilities
/// (`CAP_*` bits): pointer, button and scroll for the pointer, keyboard for the
/// keyboard, and nothing for a bit the backend doesn't know.
pub fn seat_capabilities(grant: u32) -> BitFlags<DeviceCapability> {
    let mut capabilities = BitFlags::empty();
    if grant & crate::portal::CAP_POINTER != 0 {
        capabilities |=
            DeviceCapability::Pointer | DeviceCapability::Button | DeviceCapability::Scroll;
    }
    if grant & crate::portal::CAP_KEYBOARD != 0 {
        capabilities |= DeviceCapability::Keyboard;
    }
    capabilities
}

/// Which of the two devices (pointer, keyboard) a receiver gets: what it bound,
/// cut down to what its session was granted. Asking for more gets it nothing more.
pub fn bound_devices(grant: u32, bound: BitFlags<DeviceCapability>) -> (bool, bool) {
    let allowed = seat_capabilities(grant) & bound;
    (
        allowed.contains(DeviceCapability::Pointer),
        allowed.contains(DeviceCapability::Keyboard),
    )
}

/// Logical area the emulated devices cover, in the compositor's coordinate space.
///
/// A libei client reads `ei_device.region` while it builds the device for
/// `EI_EVENT_DEVICE_ADDED` and never revisits it — there is no region event —
/// so a region arriving after `ei_device.done` is silently ignored. Without one
/// Deskflow keeps its 1x1 fallback: every activation collapses onto (0, 0) and
/// only the top edge stays reachable.
#[derive(Debug, Clone, Copy)]
pub struct Region {
    pub width: u32,
    pub height: u32,
}

/// Send handle for an EIS connection.
#[derive(Debug, Clone)]
pub struct EisHandle {
    tx: mpsc::UnboundedSender<EisCommand>,
    id: u32,
}

impl EisHandle {
    pub fn send(&self, cmd: EisCommand) {
        // A closed channel means the client dropped the EIS socket; the portal
        // session will be torn down through its own path, so drop the event.
        if self.tx.send(cmd).is_err() {
            debug!("EIS command dropped: connection is gone");
        }
    }

    /// Names this connection among all the ones this process ever made, so the
    /// notice that one ended can't be taken for another's.
    pub fn id(&self) -> u32 {
        self.id
    }
}

/// Devices we hand the client once it binds a seat.
#[derive(Default)]
struct Devices {
    keyboard: Option<reis::request::Device>,
    pointer: Option<reis::request::Device>,
    emulating: bool,
    /// The seat the receiver bound, and which devices (pointer, keyboard) it may
    /// have there: kept so the devices can be made again when the screens change.
    seat: Option<reis::request::Seat>,
    wanted: (bool, bool),
}

impl Devices {
    /// Create the devices the receiver may have and doesn't have yet.
    fn ensure(
        &mut self,
        conn: &Connection,
        sequence: &mut u32,
        keymap: &SharedKeymap,
        region: Option<Region>,
    ) {
        let Some(seat) = self.seat.clone() else {
            return;
        };
        if self.wanted.0 && self.pointer.is_none() {
            self.pointer = Some(add_device(
                "aresos-capture-pointer",
                DeviceCapability::Pointer | DeviceCapability::Button | DeviceCapability::Scroll,
                &seat,
                conn,
                sequence,
                None,
                region,
            ));
        }
        if self.wanted.1 && self.keyboard.is_none() {
            let map = keymap.read().ok().and_then(|k| k.clone());
            self.keyboard = Some(add_device(
                "aresos-capture-keyboard",
                DeviceCapability::Keyboard.into(),
                &seat,
                conn,
                sequence,
                map.as_deref(),
                region,
            ));
        }
    }

    /// Replace the devices with new ones for `region`. A receiver reads a
    /// device's region once, when the device appears, so new geometry needs new
    /// devices.
    fn rebuild(
        &mut self,
        conn: &Connection,
        sequence: &mut u32,
        keymap: &SharedKeymap,
        region: Option<Region>,
    ) {
        for device in [self.pointer.take(), self.keyboard.take()]
            .into_iter()
            .flatten()
        {
            device.remove();
        }
        self.emulating = false;
        self.ensure(conn, sequence, keymap, region);
    }

    /// `sharing` is the gate (`sharing.rs`) as it is now: closed, no input goes
    /// out even inside a capture run.
    fn apply(&mut self, cmd: &EisCommand, started: Instant, sharing: bool) {
        if !input_allowed(self.emulating && sharing, cmd) {
            return;
        }
        match cmd {
            EisCommand::StartEmulating { sequence } => {
                if self.emulating {
                    return;
                }
                for dev in [self.pointer.as_ref(), self.keyboard.as_ref()]
                    .into_iter()
                    .flatten()
                {
                    dev.start_emulating(*sequence);
                }
                self.emulating = true;
            }
            EisCommand::StopEmulating => {
                if !self.emulating {
                    return;
                }
                for dev in [self.pointer.as_ref(), self.keyboard.as_ref()]
                    .into_iter()
                    .flatten()
                {
                    dev.stop_emulating();
                }
                self.emulating = false;
            }
            EisCommand::Motion { dx, dy } => {
                if let Some(p) = self
                    .pointer
                    .as_ref()
                    .and_then(reis::request::Device::interface::<eis::Pointer>)
                {
                    p.motion_relative(*dx, *dy);
                }
            }
            EisCommand::Button { button, press } => {
                if let Some(b) = self
                    .pointer
                    .as_ref()
                    .and_then(reis::request::Device::interface::<eis::Button>)
                {
                    b.button(
                        *button,
                        if *press {
                            eis::button::ButtonState::Press
                        } else {
                            eis::button::ButtonState::Released
                        },
                    );
                }
            }
            EisCommand::Scroll { dx, dy } => {
                if let Some(s) = self
                    .pointer
                    .as_ref()
                    .and_then(reis::request::Device::interface::<eis::Scroll>)
                {
                    s.scroll(*dx, *dy);
                }
            }
            EisCommand::ScrollDiscrete { dx, dy } => {
                if let Some(s) = self
                    .pointer
                    .as_ref()
                    .and_then(reis::request::Device::interface::<eis::Scroll>)
                {
                    s.scroll_discrete(*dx, *dy);
                }
            }
            EisCommand::ScrollStop => {
                if let Some(s) = self
                    .pointer
                    .as_ref()
                    .and_then(reis::request::Device::interface::<eis::Scroll>)
                {
                    s.scroll_stop(1, 1, 0);
                }
            }
            EisCommand::Key { keycode, press } => {
                if let Some(k) = self
                    .keyboard
                    .as_ref()
                    .and_then(reis::request::Device::interface::<eis::Keyboard>)
                {
                    k.key(
                        *keycode,
                        if *press {
                            eis::keyboard::KeyState::Press
                        } else {
                            eis::keyboard::KeyState::Released
                        },
                    );
                }
            }
            EisCommand::Frame => {
                let time = u64::try_from(started.elapsed().as_micros()).unwrap_or(u64::MAX);
                for dev in [self.pointer.as_ref(), self.keyboard.as_ref()]
                    .into_iter()
                    .flatten()
                {
                    dev.frame(time);
                }
            }
            // Handled by the connection's task, which owns what they need.
            EisCommand::SetRegion(_) | EisCommand::Close => {}
        }
    }
}

/// Whether `cmd` may be written to the receiver while its devices are (or are
/// not) `emulating`. Input goes out only inside a capture run, between
/// `StartEmulating` and `StopEmulating` (REVIEW-3, finding 1).
///
/// When the portal ends a run (another session armed, `Release`, the way out),
/// it stops emulation here at once but the Wayland thread's teardown is queued
/// behind it: a key or button that thread handles in between still arrives on
/// this channel, after the client was told `Deactivated`. It is dropped here.
/// The next run's first keys are not: the portal sends `StartEmulating` on this
/// channel before it sends `AttachEis` to the Wayland thread, and that thread
/// writes what it held for the crossing only once `AttachEis` has come, so
/// those keys always come after the `StartEmulating` that lets them through.
fn input_allowed(emulating: bool, cmd: &EisCommand) -> bool {
    match cmd {
        EisCommand::Motion { .. }
        | EisCommand::Button { .. }
        | EisCommand::Scroll { .. }
        | EisCommand::ScrollDiscrete { .. }
        | EisCommand::ScrollStop
        | EisCommand::Key { .. }
        | EisCommand::Frame => emulating,
        EisCommand::StartEmulating { .. }
        | EisCommand::StopEmulating
        | EisCommand::SetRegion(_)
        | EisCommand::Close => true,
    }
}

/// The compositor's current xkb keymap, shared with the Wayland thread.
///
/// Devices are created when the client binds a seat, which can happen before or
/// after the keymap is known, so this is read at device-creation time rather
/// than passed in.
pub type SharedKeymap = Arc<RwLock<Option<String>>>;

/// Take over one end of a socketpair and serve EIS on it.
///
/// `closed_tx` receives the session label and the connection's id when the
/// connection ends for any reason. A capture must never outlive the connection
/// it feeds — that is how the pointer ends up locked with nothing able to
/// release it.
///
/// `region` is the geometry the client will size this screen with. It has to be
/// known here rather than sent later: see [`Region`].
///
/// `capabilities` is what the session was granted (`CAP_*` bits). The seat
/// offers that and no more, whatever the receiver asks to bind.
///
/// `gate` is read before every input event is written: when sharing goes off,
/// nothing more goes out, also what is already queued on this channel.
pub fn spawn(
    socket: UnixStream,
    label: String,
    keymap: SharedKeymap,
    closed_tx: mpsc::UnboundedSender<(String, u32)>,
    region: Option<Region>,
    capabilities: u32,
    gate: Gate,
) -> Result<EisHandle> {
    static NEXT_ID: std::sync::atomic::AtomicU32 = std::sync::atomic::AtomicU32::new(1);

    let context = eis::Context::new(socket).context("failed to create EIS context")?;
    let (tx, rx) = mpsc::unbounded_channel();
    let id = NEXT_ID.fetch_add(1, std::sync::atomic::Ordering::Relaxed);

    tokio::spawn(async move {
        if let Err(err) = run(context, rx, &label, &keymap, region, capabilities, &gate).await {
            warn!(session = %label, "EIS connection ended: {err:#}");
        } else {
            info!(session = %label, "EIS connection closed");
        }
        let _ = closed_tx.send((label, id));
    });

    Ok(EisHandle { tx, id })
}

/// Copy the keymap into a sealed memfd for handing to the client.
fn keymap_fd(keymap: &str) -> Option<(OwnedFd, u32)> {
    use std::io::Write;

    let fd = rustix::fs::memfd_create("aresos-input-keymap", rustix::fs::MemfdFlags::CLOEXEC)
        .map_err(|e| warn!("memfd_create failed: {e}"))
        .ok()?;
    let mut file = std::fs::File::from(fd);
    // xkb keymaps passed over a file descriptor are NUL-terminated.
    file.write_all(keymap.as_bytes()).ok()?;
    file.write_all(b"\0").ok()?;
    file.flush().ok()?;

    let size = u32::try_from(keymap.len() + 1).ok()?;
    Some((file.into(), size))
}

async fn run(
    context: eis::Context,
    mut rx: mpsc::UnboundedReceiver<EisCommand>,
    label: &str,
    keymap: &SharedKeymap,
    mut region: Option<Region>,
    capabilities: u32,
    gate: &Gate,
) -> Result<()> {
    let started = Instant::now();
    // SAFETY: the context keeps its socket open for as long as any clone of it
    // lives, the `AsyncFd` owns this clone until the task ends, and the
    // context's raw fd is always that one socket. (`AsyncFd::with_interest`,
    // which upstream used, is the unsound constructor of RUSTSEC-2026-0386.)
    let async_fd = unsafe {
        AsyncFd::register_with_interest(context.clone(), tokio::io::Interest::READABLE)
    }
    .map_err(std::io::Error::from)
    .context("failed to register EIS fd with the reactor")?;

    let mut handshaker = EisHandshaker::new(&context, 1);
    let mut connected: Option<(Connection, EisRequestConverter)> = None;
    let mut devices = Devices::default();
    let mut sequence: u32 = 0;

    loop {
        tokio::select! {
            cmd = rx.recv() => match cmd {
                // The session is gone (it was closed, or every handle to this
                // connection was dropped): the receiver must not keep a live
                // connection to a backend that has forgotten it.
                None | Some(EisCommand::Close) => {
                    if let Some((conn, _)) = &connected {
                        conn.disconnected(eis::connection::DisconnectReason::Disconnected, None);
                    }
                    let _ = context.flush();
                    return Ok(());
                }
                Some(EisCommand::SetRegion(new_region)) => {
                    region = new_region;
                    if let Some((conn, _)) = &connected {
                        devices.rebuild(conn, &mut sequence, keymap, region);
                        let _ = context.flush();
                    }
                }
                // Commands are only meaningful once devices exist; before that the
                // client has not bound a seat yet and there is nothing to emit on.
                Some(cmd) => {
                    if connected.is_some() {
                        devices.apply(&cmd, started, gate.is_open());
                        let _ = context.flush();
                    }
                }
            },
            guard = async_fd.readable() => {
                let mut guard = guard.context("EIS fd poll failed")?;
                match context.read() {
                    Ok(_) => {}
                    Err(err) if err.kind() == std::io::ErrorKind::UnexpectedEof => {
                        return Ok(());
                    }
                    Err(err) => return Err(err).context("EIS socket read failed"),
                }
                guard.clear_ready();

                match &mut connected {
                    None => {
                        if let Some((conn, converter)) =
                            drive_handshake(&mut handshaker, &context, capabilities)?
                        {
                            info!(session = %label, "EIS handshake complete, client is a {:?} context", conn.context_type());
                            connected = Some((conn, converter));
                        }
                    }
                    Some((conn, converter)) => {
                        if !drive_requests(
                            &context,
                            conn,
                            converter,
                            &mut devices,
                            &mut sequence,
                            label,
                            keymap,
                            region,
                            capabilities,
                        )? {
                            return Ok(());
                        }
                    }
                }
                let _ = context.flush();
            }
        }
    }
}

/// Feed pending requests to the handshaker until it produces a response.
fn drive_handshake(
    handshaker: &mut EisHandshaker,
    context: &eis::Context,
    capabilities: u32,
) -> Result<Option<(Connection, EisRequestConverter)>> {
    while let Some(result) = context.pending_request() {
        // reis keeps its own `request_result` helper crate-private, so unwrap the
        // pending result here. During the handshake there is no object to blame
        // for an InvalidObject, so it is a protocol error like any other.
        let request = match result {
            PendingRequestResult::Request(r) => r,
            PendingRequestResult::ParseError(err) => {
                anyhow::bail!("EIS handshake parse error: {err}")
            }
            PendingRequestResult::InvalidObject(id) => {
                anyhow::bail!("EIS handshake referenced invalid object {id}")
            }
        };
        if let Some(resp) = handshaker.handle_request(request)? {
            let converter = EisRequestConverter::new(context, resp, 1);
            let conn = converter.handle().clone();

            if !conn.has_interface("ei_seat") || !conn.has_interface("ei_device") {
                conn.disconnected(
                    eis::connection::DisconnectReason::Protocol,
                    Some("need ei_seat and ei_device"),
                );
                let _ = context.flush();
                anyhow::bail!("client lacks ei_seat/ei_device support");
            }

            // The client drives capability negotiation from here via ei_seat.bind,
            // which hands the seat back to us, so this handle is not needed.
            // The seat offers what the session was granted and nothing else.
            let _seat = conn.add_seat(Some("aresos-capture"), seat_capabilities(capabilities));
            let _ = context.flush();
            return Ok(Some((conn, converter)));
        }
    }
    let _ = context.flush();
    Ok(None)
}

/// Returns `false` once the client has disconnected.
fn drive_requests(
    context: &eis::Context,
    conn: &Connection,
    converter: &mut EisRequestConverter,
    devices: &mut Devices,
    sequence: &mut u32,
    label: &str,
    keymap: &SharedKeymap,
    region: Option<Region>,
    capabilities: u32,
) -> Result<bool> {
    while let Some(result) = context.pending_request() {
        let request = match result {
            PendingRequestResult::Request(r) => r,
            PendingRequestResult::ParseError(err) => {
                anyhow::bail!("EIS parse error: {err}");
            }
            PendingRequestResult::InvalidObject(id) => {
                debug!(session = %label, "EIS request for unknown object {id}");
                conn.connection().invalid_object(conn.last_serial(), id);
                continue;
            }
        };
        converter.handle_request(request)?;

        while let Some(req) = converter.next_request() {
            match req {
                EisRequest::Disconnect => return Ok(false),
                EisRequest::Bind(bind) => {
                    let caps = bind.capabilities;
                    debug!(session = %label, "client bound seat with {caps:?}");

                    // What it bound, cut down to what the session was granted.
                    let (pointer, keyboard) = bound_devices(capabilities, caps);
                    devices.seat = Some(bind.seat.clone());
                    devices.wanted.0 |= pointer;
                    devices.wanted.1 |= keyboard;
                    devices.ensure(conn, sequence, keymap, region);
                }
                _ => {}
            }
        }
    }
    Ok(true)
}

fn add_device(
    name: &str,
    capabilities: BitFlags<DeviceCapability>,
    seat: &reis::request::Seat,
    conn: &Connection,
    sequence: &mut u32,
    keymap: Option<&str>,
    region: Option<Region>,
) -> reis::request::Device {
    let device = seat.add_device(Some(name), DeviceType::Virtual, capabilities, |dev| {
        // Both of these have to go out before ei_device.done, which is exactly
        // what this callback is for.
        //
        // The region is read by the client while it builds the device and never
        // looked at again, so sending it later is the same as not sending it.
        if let Some(region) = region {
            // `dev` is the high-level wrapper; the `ei_device` object underneath
            // is the one that carries the region request.
            dev.device()
                .region(0, 0, region.width, region.height, 1.0);
            debug!("reported device region {}x{}", region.width, region.height);
        }

        // Without the keymap deskflow logs "does not have a keymap, we are
        // guessing" and assumes a US layout, mistranslating every non-US keycode
        // on the remote screen.
        // Only keyboard devices carry a keymap; pointers legitimately have none.
        let Some(kb) = dev.interface::<eis::Keyboard>() else {
            return;
        };
        let Some(keymap) = keymap else {
            warn!("no keymap captured from the compositor yet; the client will guess a layout");
            return;
        };
        if let Some((fd, size)) = keymap_fd(keymap) {
            kb.keymap(eis::keyboard::KeymapType::Xkb, size, fd.as_fd());
            debug!("sent a {size} byte xkb keymap to the client");
        }
    });
    device.resumed();
    // A receiver context expects the device to be emulating before events flow.
    // We do not start here — capture has not been activated yet — but record the
    // context type so `StartEmulating` knows it is meaningful.
    if conn.context_type() == eis::handshake::ContextType::Receiver {
        *sequence = sequence.wrapping_add(1);
    }
    device
}

/// How long to wait for a client to finish its handshake before giving up.
#[allow(dead_code)]
pub const HANDSHAKE_TIMEOUT: Duration = Duration::from_secs(10);

#[cfg(test)]
mod tests {
    use super::*;
    use crate::portal::{CAP_KEYBOARD, CAP_POINTER, CAP_TOUCHSCREEN};

    fn everything() -> BitFlags<DeviceCapability> {
        BitFlags::all()
    }

    #[test]
    fn the_seat_offers_what_was_granted_and_nothing_else() {
        assert_eq!(seat_capabilities(0), BitFlags::empty());
        assert_eq!(seat_capabilities(CAP_KEYBOARD), DeviceCapability::Keyboard);
        assert_eq!(
            seat_capabilities(CAP_POINTER),
            DeviceCapability::Pointer | DeviceCapability::Button | DeviceCapability::Scroll
        );
        assert_eq!(
            seat_capabilities(CAP_KEYBOARD | CAP_POINTER),
            DeviceCapability::Pointer
                | DeviceCapability::Button
                | DeviceCapability::Scroll
                | DeviceCapability::Keyboard
        );
        // A bit this backend can't serve gives the seat nothing.
        assert_eq!(seat_capabilities(CAP_TOUCHSCREEN), BitFlags::empty());
        assert_eq!(seat_capabilities(u32::MAX), seat_capabilities(CAP_KEYBOARD | CAP_POINTER));
        for grant in 0..8 {
            let seat = seat_capabilities(grant);
            assert!(!seat.contains(DeviceCapability::Touch), "{grant}");
            assert!(!seat.contains(DeviceCapability::PointerAbsolute), "{grant}");
        }
    }

    #[test]
    fn a_receiver_gets_only_devices_its_session_was_granted() {
        // (pointer, keyboard) for a receiver that binds everything there is.
        assert_eq!(bound_devices(0, everything()), (false, false));
        assert_eq!(bound_devices(CAP_KEYBOARD, everything()), (false, true));
        assert_eq!(bound_devices(CAP_POINTER, everything()), (true, false));
        assert_eq!(bound_devices(CAP_KEYBOARD | CAP_POINTER, everything()), (true, true));
        assert_eq!(bound_devices(CAP_TOUCHSCREEN, everything()), (false, false));
    }

    #[test]
    fn a_receiver_gets_only_devices_it_bound() {
        let both = CAP_KEYBOARD | CAP_POINTER;
        assert_eq!(bound_devices(both, BitFlags::empty()), (false, false));
        assert_eq!(bound_devices(both, DeviceCapability::Keyboard.into()), (false, true));
        assert_eq!(bound_devices(both, DeviceCapability::Pointer.into()), (true, false));
        // Buttons alone are not a pointer.
        assert_eq!(bound_devices(both, DeviceCapability::Button | DeviceCapability::Scroll), (false, false));
        // Granted the pointer, binding the keyboard: neither.
        assert_eq!(bound_devices(CAP_POINTER, DeviceCapability::Keyboard.into()), (false, false));
    }

    #[test]
    fn input_reaches_the_receiver_only_inside_a_capture_run() {
        let started = Instant::now();
        let mut devices = Devices::default();
        let input = [
            EisCommand::Key { keycode: 30, press: true },
            EisCommand::Button { button: 272, press: true },
            EisCommand::Motion { dx: 1.0, dy: 1.0 },
            EisCommand::Scroll { dx: 0.0, dy: 1.0 },
            EisCommand::ScrollDiscrete { dx: 0, dy: 120 },
            EisCommand::ScrollStop,
            EisCommand::Frame,
        ];
        let passes = |devices: &Devices| -> Vec<bool> {
            input.iter().map(|cmd| input_allowed(devices.emulating, cmd)).collect()
        };

        // Before any capture nothing goes out.
        assert!(passes(&devices).iter().all(|passes| !passes));

        // Session A's capture.
        devices.apply(&EisCommand::StartEmulating { sequence: 1 }, started, true);
        assert!(passes(&devices).iter().all(|passes| *passes));

        // Session B arms: the portal stops A's run. A key the Wayland thread
        // handled before its queued teardown arrives after that and is dropped.
        devices.apply(&EisCommand::StopEmulating, started, true);
        assert!(passes(&devices).iter().all(|passes| !passes));

        // A's next capture: its first keys follow its StartEmulating and go out.
        devices.apply(&EisCommand::StartEmulating { sequence: 2 }, started, true);
        assert!(passes(&devices).iter().all(|passes| *passes));

        // The commands that manage the run are never held back.
        for control in [
            EisCommand::StartEmulating { sequence: 3 },
            EisCommand::StopEmulating,
            EisCommand::SetRegion(None),
            EisCommand::Close,
        ] {
            assert!(input_allowed(false, &control), "{control:?}");
        }
    }

    #[test]
    fn a_closed_gate_drops_input_even_inside_a_capture_run() {
        let started = Instant::now();
        let mut devices = Devices::default();
        // A capture run is going, with sharing on.
        devices.apply(&EisCommand::StartEmulating { sequence: 1 }, started, true);
        assert!(devices.emulating);
        // Sharing goes off: the gate closes before the portal's StopEmulating
        // and Close have come through this channel. Every input command that is
        // still queued is dropped where it would be written.
        let gate = Gate::default();
        assert!(!gate.is_open());
        for cmd in [
            EisCommand::Key { keycode: 30, press: true },
            EisCommand::Button { button: 272, press: false },
            EisCommand::Motion { dx: 1.0, dy: 1.0 },
            EisCommand::Scroll { dx: 0.0, dy: 1.0 },
            EisCommand::ScrollDiscrete { dx: 0, dy: 120 },
            EisCommand::ScrollStop,
            EisCommand::Frame,
        ] {
            assert!(!input_allowed(devices.emulating && gate.is_open(), &cmd), "{cmd:?}");
            assert!(input_allowed(devices.emulating && !gate.is_open(), &cmd), "{cmd:?} with the gate open");
        }
        // The run's own commands still pass, so the teardown can stop it.
        devices.apply(&EisCommand::StopEmulating, started, gate.is_open());
        assert!(!devices.emulating);
    }

    #[test]
    fn a_commands_debug_form_is_its_name() {
        let commands = [
            EisCommand::Key { keycode: 31337, press: true },
            EisCommand::Button { button: 27272, press: false },
            EisCommand::Motion { dx: 1234.5, dy: 6789.25 },
            EisCommand::Scroll { dx: 1234.5, dy: 6789.25 },
            EisCommand::ScrollDiscrete { dx: 31337, dy: 27272 },
            EisCommand::StartEmulating { sequence: 31337 },
        ];
        let text = format!("{commands:?}");
        assert_eq!(text, "[Key, Button, Motion, Scroll, ScrollDiscrete, StartEmulating]");
    }
}
