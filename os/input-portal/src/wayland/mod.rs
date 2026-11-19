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
    /// Put one session's barrier surfaces on screen. Replaces any existing set.
    ///
    /// `zone_set` is the snapshot the barriers were checked against; if the
    /// screens have changed since, nothing is placed. `session` comes back in
    /// [`WaylandEvent::Activated`], so a crossing names the session whose
    /// barrier it was.
    Arm {
        session: String,
        zone_set: u32,
        barriers: Vec<Barrier>,
    },
    /// Tear every barrier surface down, freeing the screen edges.
    Disarm,
    /// Attach the EIS connection that captured input should be written to.
    ///
    /// The pointer is already locked by the time this arrives — locking happens
    /// the instant the barrier is crossed so no motion is lost to the round trip
    /// through the portal — so this only hands over the destination.
    AttachEis(crate::eis_server::EisHandle),
    /// Release the pointer and give the local cursor back.
    EndCapture {
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
    Shutdown,
}

// Names only, for both enums: they carry cursor positions and clipboard types,
// and neither may reach a log or an error through a `{:?}`.
impl std::fmt::Debug for WaylandCmd {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Arm { .. } => "Arm",
            Self::Disarm => "Disarm",
            Self::AttachEis(_) => "AttachEis",
            Self::EndCapture { .. } => "EndCapture",
            Self::ClipboardRead { .. } => "ClipboardRead",
            Self::ClipboardClaim { .. } => "ClipboardClaim",
            Self::ClipboardRelease => "ClipboardRelease",
            Self::Shutdown => "Shutdown",
        })
    }
}

impl std::fmt::Debug for WaylandEvent {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Activated { .. } => "Activated",
            Self::CaptureLost => "CaptureLost",
            Self::OutputsChanged => "OutputsChanged",
            Self::ClipboardSelection { .. } => "ClipboardSelection",
            Self::ClipboardSend { .. } => "ClipboardSend",
            Self::ClipboardCancelled { .. } => "ClipboardCancelled",
        })
    }
}

/// Events raised by the Wayland thread.
pub enum WaylandEvent {
    /// The pointer crossed a barrier that was armed for `session`. Position is
    /// in global logical coordinates.
    Activated {
        session: String,
        barrier_id: u32,
        position: (f64, f64),
    },
    /// Capture ended without the client asking, so the portal still has to emit
    /// `Deactivated`. Happens when the compositor drops the lock or the user
    /// hits the escape combination.
    CaptureLost,
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

/// Start the Wayland thread.
///
/// Returns a handle for sending commands plus the stream of barrier events.
/// Default idle timeout before a capture is force-released.
///
/// A capture that is doing its job never goes quiet for this long, because the
/// user is driving the remote screen with this machine's own mouse and keyboard.
pub const DEFAULT_IDLE_TIMEOUT: std::time::Duration = std::time::Duration::from_secs(15);

/// Read the idle timeout from the environment, falling back to the default.
///
/// `0` disables the watchdog, which is only sensible when something else is
/// guaranteed to end the capture.
pub fn idle_timeout_from_env() -> std::time::Duration {
    match std::env::var("ARESOS_INPUT_PORTAL_IDLE_TIMEOUT") {
        Ok(raw) => match raw.trim().parse::<u64>() {
            Ok(0) => {
                warn!("idle watchdog disabled; a stuck capture will need ForceRelease");
                std::time::Duration::MAX
            }
            Ok(secs) => std::time::Duration::from_secs(secs),
            Err(_) => {
                warn!("ignoring unparseable ARESOS_INPUT_PORTAL_IDLE_TIMEOUT={raw:?}");
                DEFAULT_IDLE_TIMEOUT
            }
        },
        Err(_) => DEFAULT_IDLE_TIMEOUT,
    }
}

pub fn spawn(
    keymap: crate::eis_server::SharedKeymap,
    idle_timeout: std::time::Duration,
    screens: SharedScreens,
) -> Result<(WaylandHandle, mpsc::UnboundedReceiver<WaylandEvent>)> {
    let (cmd_tx, cmd_rx) = calloop::channel::channel::<WaylandCmd>();
    let (event_tx, event_rx) = mpsc::unbounded_channel::<WaylandEvent>();
    let (ready_tx, ready_rx) = std::sync::mpsc::channel::<Result<()>>();

    thread::Builder::new()
        .name("wayland-barriers".into())
        .spawn(move || match state::run(cmd_rx, event_tx, keymap, idle_timeout, screens, &ready_tx) {
            Ok(()) => info!("Wayland barrier thread stopped"),
            Err(err) => {
                // If startup failed the error goes to `ready_rx`; a later failure
                // has nobody left to report to, so log it here.
                let _ = ready_tx.send(Err(anyhow::anyhow!("{err:#}")));
                warn!("Wayland barrier thread failed: {err:#}");
            }
        })
        .context("failed to start the Wayland thread")?;

    ready_rx
        .recv()
        .context("Wayland thread exited before signalling readiness")??;

    Ok((WaylandHandle { cmd_tx }, event_rx))
}

/// Whether another output lies directly against the stretch `lo..hi` of an
/// output's edge: `line` is the edge's coordinate across it (x for a left or
/// right edge, y for a top or bottom one).
///
/// The pointer crossing such an edge is only moving to the next screen, so a
/// barrier there would capture on every move between the user's own screens.
/// The portal specification rejects these, and clients count on it: Deskflow
/// asks for all four edges of every zone and expects the inner ones to fail.
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

        if b.is_vertical() {
            let (lo, hi) = (b.y1.min(b.y2), b.y1.max(b.y2));
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
            let (lo, hi) = (b.x1.min(b.x2), b.x1.max(b.x2));
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
    fn rejects_a_barrier_that_is_not_on_any_edge() {
        let b = Barrier { id: 4, x1: 1500, y1: 0, x2: 1500, y2: 1728 };
        let (placed, rejected) = place(&[b], &outputs());
        assert!(placed.is_empty());
        assert_eq!(rejected, vec![4]);
    }
}
