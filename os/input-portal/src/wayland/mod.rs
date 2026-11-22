//! Barrier surfaces on the compositor side.
//!
//! niri has no protocol for "tell me when the pointer hits this line", so a
//! barrier is approximated with a one-pixel `wlr-layer-shell` surface pinned to
//! the matching screen edge. The pointer entering that surface *is* the barrier
//! crossing.
//!
//! Wayland event queues are not `Send`, so all of this lives on its own thread
//! and talks to the portal through calloop channels.

mod clipboard;
mod heads;
mod state;


use crate::portal::Barrier;
use crate::screens::SharedScreens;
use anyhow::{Context, Result};
use std::os::fd::OwnedFd;
use std::thread;
use tokio::sync::{mpsc, oneshot};
use tracing::{info, warn};

use smithay_client_toolkit::reexports::protocols as wayland_protocols;

/// Which screen edge a barrier sits on.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Edge {
    Left,
    Right,
    Top,
    Bottom,
}

/// How deep the barrier surface reaches into the output, in logical pixels.
///
/// Detection only ever uses the outermost pixel — the input region is a single
/// row or column — but `zwp_locked_pointer_v1::set_cursor_position_hint` takes
/// surface-local coordinates, so a one-pixel surface can only slide the cursor
/// *along* the edge. The extra depth is what makes it possible to put the
/// cursor back inside the screen when a capture ends.
pub const BARRIER_DEPTH: u32 = 64;

/// How far inside the edge the cursor is placed on release.
///
/// Far enough that it is clear of the input region and cannot immediately
/// retrigger the barrier it just came back through.
pub const RELEASE_INSET: f64 = 8.0;

/// A barrier resolved against the current output layout.
#[derive(Debug, Clone)]
pub struct PlacedBarrier {
    pub id: u32,
    pub edge: Edge,
    /// Name of the output this edge belongs to.
    pub output: String,
    /// Surface size in logical pixels, including [`BARRIER_DEPTH`].
    pub size: (u32, u32),
    /// Distance from the anchored corner, in logical pixels.
    pub margin: (i32, i32),
    /// Global logical position of the surface's top-left corner, used to turn
    /// surface-local pointer coordinates back into portal coordinates.
    pub origin: (i32, i32),
}

impl PlacedBarrier {
    /// The input region, in surface-local coordinates: the one-pixel strip on
    /// the outer edge. Everything else in the surface stays click-through.
    pub fn input_strip(&self) -> (i32, i32, i32, i32) {
        let (w, h) = (self.size.0 as i32, self.size.1 as i32);
        match self.edge {
            Edge::Left => (0, 0, 1, h),
            Edge::Right => (w - 1, 0, 1, h),
            Edge::Top => (0, 0, w, 1),
            Edge::Bottom => (0, h - 1, w, 1),
        }
    }

    /// Where to leave the cursor when a capture on this barrier ends, in
    /// surface-local coordinates. `along` is the position on the edge axis.
    pub fn release_hint(&self, along: f64) -> (f64, f64) {
        let (w, h) = (f64::from(self.size.0), f64::from(self.size.1));
        match self.edge {
            Edge::Left => (RELEASE_INSET, along.clamp(0.0, h - 1.0)),
            Edge::Right => (w - 1.0 - RELEASE_INSET, along.clamp(0.0, h - 1.0)),
            Edge::Top => (along.clamp(0.0, w - 1.0), RELEASE_INSET),
            Edge::Bottom => (along.clamp(0.0, w - 1.0), h - 1.0 - RELEASE_INSET),
        }
    }
}

/// Commands sent to the Wayland thread.
pub enum WaylandCmd {
    /// Put one session's barrier surfaces on screen. Replaces any existing set,
    /// and ends whatever capture came from it.
    ///
    /// `zone_set` is the snapshot the barriers were checked against; if the
    /// screens have changed since, nothing is placed. `session` and `arming`
    /// come back in [`WaylandEvent::Activated`]: `arming` is a number the portal
    /// never uses twice, so a crossing names the one arming it came from and
    /// can't be taken for a later one of the same session path.
    Arm {
        session: String,
        arming: u64,
        /// Whether the session was granted the keyboard. If so, a crossing only
        /// counts once the barrier's surface has keyboard focus.
        keyboard: bool,
        zone_set: u32,
        barriers: Vec<Barrier>,
    },
    /// Tear every barrier surface down, freeing the screen edges. A crossing
    /// that came from them ends too, and the input buffered for it is dropped.
    Disarm,
    /// Attach the EIS connection that the input of crossing `crossing` should
    /// be written to.
    ///
    /// The pointer is already locked by the time this arrives. If that crossing
    /// is over by then, nothing is attached and the portal is told
    /// ([`WaylandEvent::CaptureLost`]).
    AttachEis {
        crossing: u64,
        eis: crate::eis_server::EisHandle,
    },
    /// Release the pointer and give the local cursor back.
    EndCapture {
        /// The crossing to end, so a late command can't end a newer capture.
        /// `None` ends whatever is captured (the way out, and shutdown).
        crossing: Option<u64>,
        /// Where to leave the cursor, in global logical coordinates.
        cursor_hint: Option<(f64, f64)>,
    },
    /// Ask the selection owner for the clipboard content.
    ///
    /// The reply is the read end of a pipe the owner writes into, so the bytes
    /// never pass through this process. `None` means nothing is on the clipboard
    /// in that type.
    ClipboardRead {
        mime_type: String,
        reply: oneshot::Sender<Option<OwnedFd>>,
    },
    /// Take ownership of the clipboard, advertising these types. `claim_id`
    /// comes back with every paste asked of this claim.
    ClipboardClaim { claim_id: u32, mime_types: Vec<String> },
    /// Give up an earlier claim.
    ClipboardRelease,
    /// Answer `done` once the compositor has processed every request this
    /// thread made for the commands before this one (a `wl_display.sync`): after
    /// `EndCapture` that the lock is destroyed and the keyboard given back.
    Sync { done: oneshot::Sender<()> },
    Shutdown,
}

// Names only, for both enums: they carry cursor positions and clipboard types,
// and neither may reach a log or an error through a `{:?}`.
impl std::fmt::Debug for WaylandCmd {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Arm { .. } => "Arm",
            Self::Disarm => "Disarm",
            Self::AttachEis { .. } => "AttachEis",
            Self::EndCapture { .. } => "EndCapture",
            Self::ClipboardRead { .. } => "ClipboardRead",
            Self::ClipboardClaim { .. } => "ClipboardClaim",
            Self::ClipboardRelease => "ClipboardRelease",
            Self::Sync { .. } => "Sync",
            Self::Shutdown => "Shutdown",
        })
    }
}

impl std::fmt::Debug for WaylandEvent {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Activated { .. } => "Activated",
            Self::CaptureLost { .. } => "CaptureLost",
            Self::OutputsChanged => "OutputsChanged",
            Self::ClipboardSelection { .. } => "ClipboardSelection",
            Self::ClipboardSend { .. } => "ClipboardSend",
            Self::ClipboardCancelled { .. } => "ClipboardCancelled",
        })
    }
}

/// Events raised by the Wayland thread.
pub enum WaylandEvent {
    /// The pointer crossed a barrier that was armed for `session` by the arming
    /// `arming`, and the compositor has granted the grab: the pointer is locked
    /// and, for a session with the keyboard, the barrier has keyboard focus.
    /// `crossing` names this capture from here on. Position is in global
    /// logical coordinates.
    Activated {
        session: String,
        arming: u64,
        crossing: u64,
        barrier_id: u32,
        position: (f64, f64),
    },
    /// The capture of `crossing` ended without the portal asking, so the portal
    /// still has to emit `Deactivated`. Happens when the compositor drops the
    /// lock, closes the surface or takes the pointer or the keyboard focus
    /// away, on the idle watchdog and on the escape combination.
    CaptureLost { crossing: u64 },
    /// A new snapshot of the screens was committed; zones and barriers are
    /// stale. Any capture has been ended and every barrier surface removed.
    OutputsChanged,
    /// The clipboard selection changed. `is_ours` distinguishes a change this
    /// process caused from one a local application caused.
    ClipboardSelection {
        mime_types: Vec<String>,
        is_ours: bool,
    },
    /// Somebody is pasting from the selection claim `claim_id` made, and wants
    /// the content written into `fd`.
    ClipboardSend {
        claim_id: u32,
        mime_type: String,
        fd: OwnedFd,
    },
    /// Claim `claim_id` was taken over by another client.
    ClipboardCancelled { claim_id: u32 },
}

pub struct WaylandHandle {
    cmd_tx: calloop::channel::Sender<WaylandCmd>,
}

impl WaylandHandle {
    pub fn send(&self, cmd: WaylandCmd) {
        // The error would hand the command back; it is dropped unprinted.
        if self.cmd_tx.send(cmd).is_err() {
            warn!("Wayland thread is gone, dropping a command");
        }
    }

    /// Whether the compositor confirms, within `within`, that it has processed
    /// everything sent to the Wayland thread before this call ([`WaylandCmd::Sync`]).
    /// A stopped compositor, or a thread that is gone, never confirms.
    pub async fn confirm(&self, within: std::time::Duration) -> bool {
        let (done, confirmed) = oneshot::channel();
        self.send(WaylandCmd::Sync { done });
        matches!(tokio::time::timeout(within, confirmed).await, Ok(Ok(())))
    }

    /// A handle with no Wayland thread behind it: the test reads what was sent.
    #[cfg(test)]
    pub fn recording() -> (Self, calloop::channel::Channel<WaylandCmd>) {
        let (cmd_tx, cmd_rx) = calloop::channel::channel();
        (Self { cmd_tx }, cmd_rx)
    }
}

impl Drop for WaylandHandle {
    fn drop(&mut self) {
        let _ = self.cmd_tx.send(WaylandCmd::Shutdown);
    }
}

/// The idle watchdog's timeout when nothing sets one: off (brief 321, "The trust
/// model"). Upstream ended a capture after 15 seconds without input, but the owner
/// reads on the other machine for longer than that every day: control would fall
/// back to this laptop unseen and his next keys would land in a local window. The
/// release chord and the teardown for a dead client end a capture instead.
/// `Duration::MAX` is "never".
pub const DEFAULT_IDLE_TIMEOUT: std::time::Duration = std::time::Duration::MAX;

/// The idle timeout `ARESOS_INPUT_PORTAL_IDLE_TIMEOUT` asks for, in seconds; `0`
/// and an unset variable mean no watchdog, and anything else falls back to that.
pub fn idle_timeout_from_env() -> std::time::Duration {
    idle_timeout(std::env::var("ARESOS_INPUT_PORTAL_IDLE_TIMEOUT").ok().as_deref())
}

fn idle_timeout(raw: Option<&str>) -> std::time::Duration {
    let Some(raw) = raw else {
        return DEFAULT_IDLE_TIMEOUT;
    };
    match raw.trim().parse::<u64>() {
        Ok(0) => std::time::Duration::MAX,
        Ok(secs) => std::time::Duration::from_secs(secs),
        Err(_) => {
            warn!("ignoring unparseable ARESOS_INPUT_PORTAL_IDLE_TIMEOUT={raw:?}");
            DEFAULT_IDLE_TIMEOUT
        }
    }
}

/// Start a Wayland worker: a thread with its own connection to the compositor.
///
/// Returns a handle for sending commands plus the stream of barrier events,
/// once the worker has bound what it needs and taken its first snapshot of the
/// screens. It is started only for a session the portal has authorized while
/// sharing is on, and it stops (its connection, and every binding with it,
/// goes) when the last [`WaylandHandle`] is dropped. A worker that is not ready
/// within `within` is given up: a stopped compositor must not hold the caller.
///
/// `gate` is read before every captured event is handed on: closed (sharing is
/// off), nothing is forwarded or buffered. `crossings` numbers the crossings of
/// every worker of the process.
pub async fn start(
    keymap: crate::eis_server::SharedKeymap,
    idle_timeout: std::time::Duration,
    screens: SharedScreens,
    gate: crate::sharing::Gate,
    crossings: std::sync::Arc<std::sync::atomic::AtomicU64>,
    within: std::time::Duration,
) -> Result<(WaylandHandle, mpsc::UnboundedReceiver<WaylandEvent>)> {
    let (cmd_tx, cmd_rx) = calloop::channel::channel::<WaylandCmd>();
    let (event_tx, event_rx) = mpsc::unbounded_channel::<WaylandEvent>();
    let (ready_tx, ready_rx) = std::sync::mpsc::channel::<Result<()>>();

    thread::Builder::new()
        .name("wayland-barriers".into())
        .spawn(move || match state::run(cmd_rx, event_tx, keymap, idle_timeout, screens, gate, crossings, &ready_tx) {
            Ok(()) => info!("Wayland worker stopped"),
            Err(err) => {
                // If startup failed the error goes to `ready_rx`; a later failure
                // has nobody left to report to, so log it here.
                let _ = ready_tx.send(Err(anyhow::anyhow!("{err:#}")));
                warn!("Wayland worker failed: {err:#}");
            }
        })
        .context("failed to start the Wayland thread")?;
    // Made before the wait: given up, it is dropped, and the worker that
    // becomes ready later finds `Shutdown` waiting and stops.
    let handle = WaylandHandle { cmd_tx };

    let ready = tokio::task::spawn_blocking(move || ready_rx.recv_timeout(within))
        .await
        .context("the wait for the Wayland worker failed")?;
    match ready {
        Ok(result) => result?,
        Err(std::sync::mpsc::RecvTimeoutError::Timeout) => {
            anyhow::bail!("the compositor did not answer the Wayland worker within {within:?}")
        }
        Err(std::sync::mpsc::RecvTimeoutError::Disconnected) => {
            anyhow::bail!("the Wayland worker exited before signalling readiness")
        }
    }
    Ok((handle, event_rx))
}

/// Whether another output lies directly against the stretch `lo..hi` of an
/// output's edge: `line` is the edge's coordinate across it (x for a left or
/// right edge, y for a top or bottom one).
///
/// The pointer crossing such an edge is only moving to the next screen, so a
/// barrier there would capture on every move between the user's own screens.
/// The portal specification says so too: "A pointer barrier must be situated
/// at the outside boundary of the union of all zones."
fn faces_another_output(
    edge: Edge,
    line: i32,
    (lo, hi): (i32, i32),
    this: usize,
    outputs: &[(String, (i32, i32), (i32, i32))],
) -> bool {
    outputs.iter().enumerate().any(|(index, (_, (x, y), (w, h)))| {
        let (x, y, w, h) = (*x, *y, *w, *h);
        let (touches, span) = match edge {
            Edge::Right => (x == line, (y, y + h)),
            Edge::Left => (x + w == line, (y, y + h)),
            Edge::Bottom => (y == line, (x, x + w)),
            Edge::Top => (y + h == line, (x, x + w)),
        };
        index != this && touches && lo.max(span.0) < hi.min(span.1)
    })
}

/// Resolve barriers against the output layout.
///
/// A barrier that does not lie exactly on an outer output edge cannot be
/// represented as a layer surface, so it is dropped and reported back to the
/// caller. That includes a barrier any part of which faces another output.
pub fn place(
    barriers: &[Barrier],
    outputs: &[(String, (i32, i32), (i32, i32))],
) -> (Vec<PlacedBarrier>, Vec<u32>) {
    let mut placed = Vec::new();
    let mut rejected = Vec::new();

    for b in barriers {
        let Some(p) = place_one(b, outputs) else {
            rejected.push(b.id);
            continue;
        };
        placed.push(p);
    }

    (placed, rejected)
}

fn place_one(
    b: &Barrier,
    outputs: &[(String, (i32, i32), (i32, i32))],
) -> Option<PlacedBarrier> {
    for (index, (name, (ox, oy), (ow, oh))) in outputs.iter().enumerate() {
        let (ox, oy, ow, oh) = (*ox, *oy, *ow, *oh);

        // The specification counts a barrier's last pixel in ("a barrier spanning
        // x1=0, x2=1 is exactly two pixels wide"): the right edge of a 1080-high
        // zone is y1=0, y2=1079. So the span ends one past the larger coordinate.
        // A client that gives the zone's full height instead is cut to the output
        // just below, as before.
        if b.is_vertical() {
            let (lo, hi) = (b.y1.min(b.y2), b.y1.max(b.y2).saturating_add(1));
            // Clip the barrier to this output's vertical extent.
            let (top, bottom) = (lo.max(oy), hi.min(oy + oh));
            if top >= bottom {
                continue;
            }
            let edge = if b.x1 == ox + ow {
                Edge::Right
            } else if b.x1 == ox {
                Edge::Left
            } else {
                continue;
            };
            if faces_another_output(edge, b.x1, (top, bottom), index, outputs) {
                return None;
            }
            let height = u32::try_from(bottom - top).ok()?;
            // The surface reaches inward from the edge, so a right-anchored one
            // starts BARRIER_DEPTH short of the output's right side.
            let depth = i32::try_from(BARRIER_DEPTH).ok()?;
            let origin_x = if edge == Edge::Right {
                ox + ow - depth
            } else {
                ox
            };
            return Some(PlacedBarrier {
                id: b.id,
                edge,
                output: name.clone(),
                size: (BARRIER_DEPTH, height),
                margin: (top - oy, 0),
                origin: (origin_x, top),
            });
        }

        if b.is_horizontal() {
            let (lo, hi) = (b.x1.min(b.x2), b.x1.max(b.x2).saturating_add(1));
            let (left, right) = (lo.max(ox), hi.min(ox + ow));
            if left >= right {
                continue;
            }
            let edge = if b.y1 == oy + oh {
                Edge::Bottom
            } else if b.y1 == oy {
                Edge::Top
            } else {
                continue;
            };
            if faces_another_output(edge, b.y1, (left, right), index, outputs) {
                return None;
            }
            let width = u32::try_from(right - left).ok()?;
            let depth = i32::try_from(BARRIER_DEPTH).ok()?;
            let origin_y = if edge == Edge::Bottom {
                oy + oh - depth
            } else {
                oy
            };
            return Some(PlacedBarrier {
                id: b.id,
                edge,
                output: name.clone(),
                size: (width, BARRIER_DEPTH),
                margin: (0, left - ox),
                origin: (left, origin_y),
            });
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    fn outputs() -> Vec<(String, (i32, i32), (i32, i32))> {
        // The real layout on the development machine: a 4K monitor with the
        // laptop panel below it and offset to the right.
        vec![
            ("HDMI-A-1".into(), (0, 0), (3072, 1728)),
            ("eDP-2".into(), (298, 1728), (1706, 1066)),
        ]
    }

    #[test]
    fn places_a_full_height_right_edge_barrier() {
        let b = Barrier { id: 1, x1: 3072, y1: 0, x2: 3072, y2: 1728 };
        let (placed, rejected) = place(&[b], &outputs());
        assert!(rejected.is_empty());
        assert_eq!(placed.len(), 1);
        let p = &placed[0];
        assert_eq!(p.edge, Edge::Right);
        assert_eq!(p.output, "HDMI-A-1");
        assert_eq!(p.size, (BARRIER_DEPTH, 1728));
        // The surface reaches inward, so it starts BARRIER_DEPTH short of 3072.
        assert_eq!(p.origin, (3072 - BARRIER_DEPTH as i32, 0));
    }

    #[test]
    fn places_a_left_edge_barrier_on_the_offset_output() {
        let b = Barrier { id: 2, x1: 298, y1: 1728, x2: 298, y2: 2794 };
        let (placed, _) = place(&[b], &outputs());
        assert_eq!(placed.len(), 1);
        assert_eq!(placed[0].edge, Edge::Left);
        assert_eq!(placed[0].output, "eDP-2");
        assert_eq!(placed[0].origin, (298, 1728));
    }

    #[test]
    fn clips_a_barrier_that_overhangs_the_output() {
        // Synergy may describe an edge spanning the whole desktop height even
        // though the output is shorter.
        let b = Barrier { id: 3, x1: 3072, y1: -500, x2: 3072, y2: 9000 };
        let (placed, _) = place(&[b], &outputs());
        assert_eq!(placed[0].size, (BARRIER_DEPTH, 1728));
        assert_eq!(placed[0].margin, (0, 0));
    }

    #[test]
    fn input_strip_hugs_the_outer_edge_only() {
        let right = Barrier { id: 1, x1: 3072, y1: 0, x2: 3072, y2: 1728 };
        let (placed, _) = place(&[right], &outputs());
        // Rightmost column of the surface, one pixel wide, full height.
        assert_eq!(placed[0].input_strip(), (BARRIER_DEPTH as i32 - 1, 0, 1, 1728));

        let left = Barrier { id: 2, x1: 298, y1: 1728, x2: 298, y2: 2794 };
        let (placed, _) = place(&[left], &outputs());
        assert_eq!(placed[0].input_strip(), (0, 0, 1, 1066));
    }

    #[test]
    fn release_hint_lands_inside_the_screen_clear_of_the_strip() {
        let right = Barrier { id: 1, x1: 3072, y1: 0, x2: 3072, y2: 1728 };
        let (placed, _) = place(&[right], &outputs());
        let p = &placed[0];
        let (x, y) = p.release_hint(900.0);

        // Inward of the input strip, so returning cannot immediately retrigger.
        let strip_x = f64::from(p.input_strip().0);
        assert!(x < strip_x - 1.0, "hint x {x} must be clear of strip at {strip_x}");
        assert!(x > 0.0);
        // The position along the edge is preserved.
        assert_eq!(y, 900.0);
    }

    #[test]
    fn release_hint_is_clamped_to_the_surface() {
        let left = Barrier { id: 2, x1: 298, y1: 1728, x2: 298, y2: 2794 };
        let (placed, _) = place(&[left], &outputs());
        let p = &placed[0];
        assert_eq!(p.release_hint(-5000.0).1, 0.0);
        assert_eq!(p.release_hint(99999.0).1, 1065.0);
    }

    #[test]
    fn a_barrier_covers_its_last_pixel() {
        // The specification's own example: two 1920x1080 zones side by side,
        // and the six barriers it permits there.
        let side_by_side: Vec<(String, (i32, i32), (i32, i32))> = vec![
            ("A".into(), (0, 0), (1920, 1080)),
            ("B".into(), (1920, 0), (1920, 1080)),
        ];
        let permitted = [
            Barrier { id: 1, x1: 0, y1: 0, x2: 1919, y2: 0 },
            Barrier { id: 2, x1: 0, y1: 1080, x2: 1919, y2: 1080 },
            Barrier { id: 3, x1: 1920, y1: 0, x2: 3839, y2: 0 },
            Barrier { id: 4, x1: 1920, y1: 1080, x2: 3839, y2: 1080 },
            Barrier { id: 5, x1: 0, y1: 0, x2: 0, y2: 1079 },
            Barrier { id: 6, x1: 3840, y1: 0, x2: 3840, y2: 1079 },
        ];
        let (placed, rejected) = place(&permitted, &side_by_side);
        assert!(rejected.is_empty());
        let got: Vec<(u32, &str, Edge, (u32, u32))> =
            placed.iter().map(|p| (p.id, p.output.as_str(), p.edge, p.size)).collect();
        assert_eq!(
            got,
            [
                (1, "A", Edge::Top, (1920, BARRIER_DEPTH)),
                (2, "A", Edge::Bottom, (1920, BARRIER_DEPTH)),
                (3, "B", Edge::Top, (1920, BARRIER_DEPTH)),
                (4, "B", Edge::Bottom, (1920, BARRIER_DEPTH)),
                (5, "A", Edge::Left, (BARRIER_DEPTH, 1080)),
                (6, "B", Edge::Right, (BARRIER_DEPTH, 1080)),
            ]
        );
        // A single pixel is a barrier one pixel long.
        let dot = Barrier { id: 7, x1: 0, y1: 500, x2: 0, y2: 500 };
        assert_eq!(place(&[dot], &side_by_side).0[0].size, (BARRIER_DEPTH, 1));
    }

    #[test]
    fn rejects_a_barrier_between_two_outputs() {
        let side_by_side: Vec<(String, (i32, i32), (i32, i32))> = vec![
            ("A".into(), (0, 0), (1920, 1080)),
            ("B".into(), (1920, 0), (1920, 1080)),
        ];
        // A's right edge is B's left edge: crossing it is moving to B.
        let between = Barrier { id: 1, x1: 1920, y1: 0, x2: 1920, y2: 1080 };
        let left = Barrier { id: 2, x1: 0, y1: 0, x2: 0, y2: 1080 };
        let right = Barrier { id: 3, x1: 3840, y1: 0, x2: 3840, y2: 1080 };
        let top_of_b = Barrier { id: 4, x1: 1920, y1: 0, x2: 3839, y2: 0 };
        let (placed, rejected) = place(&[between, left, right, top_of_b], &side_by_side);
        assert_eq!(rejected, vec![1]);
        let on: Vec<(u32, &str, Edge)> = placed.iter().map(|p| (p.id, p.output.as_str(), p.edge)).collect();
        assert_eq!(on, [(2, "A", Edge::Left), (3, "B", Edge::Right), (4, "B", Edge::Top)]);

        // The same holds whichever output is listed first.
        let reversed: Vec<_> = side_by_side.iter().rev().cloned().collect();
        assert_eq!(place(&[between], &reversed).1, vec![1]);
    }

    #[test]
    fn rejects_a_barrier_that_partly_faces_another_output() {
        // The monitor's bottom edge runs along the laptop panel's top edge for
        // part of its length; the panel's top edge faces the monitor all along.
        let monitor_bottom = Barrier { id: 1, x1: 0, y1: 1728, x2: 3071, y2: 1728 };
        let panel_top = Barrier { id: 2, x1: 298, y1: 1728, x2: 2003, y2: 1728 };
        // The panel's sides and bottom, and the monitor's top, face nothing.
        let panel_left = Barrier { id: 3, x1: 298, y1: 1728, x2: 298, y2: 2793 };
        let panel_bottom = Barrier { id: 4, x1: 298, y1: 2794, x2: 2003, y2: 2794 };
        let monitor_top = Barrier { id: 5, x1: 0, y1: 0, x2: 3071, y2: 0 };
        let (placed, rejected) =
            place(&[monitor_bottom, panel_top, panel_left, panel_bottom, monitor_top], &outputs());
        assert_eq!(rejected, vec![1, 2]);
        let ids: Vec<u32> = placed.iter().map(|p| p.id).collect();
        assert_eq!(ids, [3, 4, 5]);
    }

    #[test]
    fn an_output_that_only_touches_at_a_corner_blocks_nothing() {
        let diagonal: Vec<(String, (i32, i32), (i32, i32))> = vec![
            ("A".into(), (0, 0), (1920, 1080)),
            ("B".into(), (1920, 1080), (1920, 1080)),
        ];
        let right_of_a = Barrier { id: 1, x1: 1920, y1: 0, x2: 1920, y2: 1079 };
        let bottom_of_a = Barrier { id: 2, x1: 0, y1: 1080, x2: 1919, y2: 1080 };
        let (placed, rejected) = place(&[right_of_a, bottom_of_a], &diagonal);
        assert!(rejected.is_empty());
        assert_eq!(placed[0].edge, Edge::Right);
        assert_eq!(placed[1].edge, Edge::Bottom);
    }

    #[test]
    fn the_idle_watchdog_is_off_unless_a_timeout_is_set() {
        use std::time::Duration;
        assert_eq!(idle_timeout(None), Duration::MAX);
        assert_eq!(idle_timeout(Some("0")), Duration::MAX);
        assert_eq!(idle_timeout(Some(" 3\n")), Duration::from_secs(3));
        assert_eq!(idle_timeout(Some("15")), Duration::from_secs(15));
        for not_a_number in ["", "-1", "1.5", "15s", "never"] {
            assert_eq!(idle_timeout(Some(not_a_number)), Duration::MAX, "{not_a_number:?}");
        }
    }

    #[test]
    fn rejects_a_barrier_that_is_not_on_any_edge() {
        let b = Barrier { id: 4, x1: 1500, y1: 0, x2: 1500, y2: 1728 };
        let (placed, rejected) = place(&[b], &outputs());
        assert!(placed.is_empty());
        assert_eq!(rejected, vec![4]);
    }
}
