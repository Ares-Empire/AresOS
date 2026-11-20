//! The compositor's screens through `zwlr_output_manager_v1`.
//!
//! The manager describes every head with a burst of events and closes each
//! change with `done`. Only what stood at a `done` is ever handed on: a
//! half-described layout is never a snapshot.
//!
//! Nothing here asks the compositor to change anything; the configuration half
//! of the protocol is not used.

use smithay_client_toolkit::{
    dispatch2::Dispatch2,
    reexports::client::{
        event_created_child,
        globals::{BindError, GlobalList},
        protocol::wl_output,
        Connection, Dispatch, Proxy, QueueHandle, WEnum,
    },
    reexports::protocols_wlr::output_management::v1::client::{
        zwlr_output_head_v1::{self, ZwlrOutputHeadV1},
        zwlr_output_manager_v1::{self, ZwlrOutputManagerV1},
        zwlr_output_mode_v1::{self, ZwlrOutputModeV1},
    },
};
use tracing::warn;

use crate::screens::{Head, Transform};

/// What the Wayland thread does when the compositor commits a layout.
pub trait HeadsHandler: Sized {
    fn heads(&mut self) -> &mut HeadsState;

    /// A `done` arrived: [`HeadsState::committed`] is the new layout.
    fn heads_done(&mut self);
}

/// User data for the manager, the heads and the modes. None of them carries
/// state of its own; it lives in [`HeadsState`], keyed by the object.
#[derive(Debug, Clone, Copy)]
pub struct ManagerData;
#[derive(Debug, Clone, Copy)]
pub struct HeadData;
#[derive(Debug, Clone, Copy)]
pub struct ModeData;

struct HeadEntry {
    proxy: ZwlrOutputHeadV1,
    /// `mode` stays empty here; it is looked up from `current_mode` at `done`.
    head: Head,
    current_mode: Option<ZwlrOutputModeV1>,
}

pub struct HeadsState {
    _manager: ZwlrOutputManagerV1,
    heads: Vec<HeadEntry>,
    modes: Vec<(ZwlrOutputModeV1, (i32, i32))>,
    committed: Option<Vec<Head>>,
}

impl HeadsState {
    pub fn bind<D>(globals: &GlobalList, qh: &QueueHandle<D>) -> Result<Self, BindError>
    where
        D: Dispatch<ZwlrOutputManagerV1, ManagerData> + 'static,
    {
        let manager = globals.bind(qh, 1..=4, ManagerData)?;
        Ok(Self {
            _manager: manager,
            heads: Vec::new(),
            modes: Vec::new(),
            committed: None,
        })
    }

    /// The heads as they stood at the last `done`; `None` before the first one.
    pub fn committed(&self) -> Option<&[Head]> {
        self.committed.as_deref()
    }

    fn entry(&mut self, proxy: &ZwlrOutputHeadV1) -> Option<&mut HeadEntry> {
        self.heads.iter_mut().find(|entry| &entry.proxy == proxy)
    }

    fn commit(&mut self) {
        let committed = self
            .heads
            .iter()
            .map(|entry| Head {
                mode: entry.current_mode.as_ref().and_then(|current| {
                    self.modes
                        .iter()
                        .find(|(mode, _)| mode == current)
                        .map(|(_, size)| *size)
                }),
                ..entry.head.clone()
            })
            .collect();
        self.committed = Some(committed);
    }
}

fn transform_of(transform: WEnum<wl_output::Transform>) -> Transform {
    match transform {
        WEnum::Value(wl_output::Transform::_90) => Transform::Rotated90,
        WEnum::Value(wl_output::Transform::_180) => Transform::Rotated180,
        WEnum::Value(wl_output::Transform::_270) => Transform::Rotated270,
        WEnum::Value(wl_output::Transform::Flipped) => Transform::Flipped,
        WEnum::Value(wl_output::Transform::Flipped90) => Transform::Flipped90,
        WEnum::Value(wl_output::Transform::Flipped180) => Transform::Flipped180,
        WEnum::Value(wl_output::Transform::Flipped270) => Transform::Flipped270,
        WEnum::Value(_) => Transform::Normal,
        WEnum::Unknown(raw) => {
            warn!("a head reported the unknown transform {raw}; treating it as not turned");
            Transform::Normal
        }
    }
}

impl<D> Dispatch2<ZwlrOutputManagerV1, D> for ManagerData
where
    D: Dispatch<ZwlrOutputHeadV1, HeadData> + HeadsHandler + 'static,
{
    event_created_child!(D, ZwlrOutputManagerV1, [
        zwlr_output_manager_v1::EVT_HEAD_OPCODE => (ZwlrOutputHeadV1, HeadData)
    ]);

    fn event(
        &self,
        state: &mut D,
        _: &ZwlrOutputManagerV1,
        event: <ZwlrOutputManagerV1 as Proxy>::Event,
        _: &Connection,
        _: &QueueHandle<D>,
    ) {
        use zwlr_output_manager_v1::Event;

        match event {
            Event::Head { head } => state.heads().heads.push(HeadEntry {
                proxy: head,
                head: Head::default(),
                current_mode: None,
            }),
            Event::Done { .. } => {
                state.heads().commit();
                state.heads_done();
            }
            Event::Finished => {
                // No more updates will come, so no layout can be trusted from
                // here on: with no screens there are no zones and no barriers.
                warn!("the compositor ended zwlr_output_manager_v1; no screen can be captured from");
                let heads = state.heads();
                heads.heads.clear();
                heads.modes.clear();
                heads.commit();
                state.heads_done();
            }
            _ => {}
        }
    }
}

impl<D> Dispatch2<ZwlrOutputHeadV1, D> for HeadData
where
    D: Dispatch<ZwlrOutputModeV1, ModeData> + HeadsHandler + 'static,
{
    event_created_child!(D, ZwlrOutputHeadV1, [
        zwlr_output_head_v1::EVT_MODE_OPCODE => (ZwlrOutputModeV1, ModeData)
    ]);

    fn event(
        &self,
        state: &mut D,
        proxy: &ZwlrOutputHeadV1,
        event: <ZwlrOutputHeadV1 as Proxy>::Event,
        _: &Connection,
        _: &QueueHandle<D>,
    ) {
        use zwlr_output_head_v1::Event;

        let heads = state.heads();
        if let Event::Mode { mode } = event {
            // Its size follows in the mode's own events.
            heads.modes.push((mode, (0, 0)));
            return;
        }
        if matches!(event, Event::Finished) {
            tracing::debug!("the compositor retired a head");
            heads.heads.retain(|entry| &entry.proxy != proxy);
            if proxy.version() >= 3 {
                proxy.release();
            }
            return;
        }
        let Some(entry) = heads.entry(proxy) else {
            return;
        };
        match event {
            Event::Name { name } => entry.head.name = Some(name),
            Event::Enabled { enabled } => entry.head.enabled = enabled != 0,
            Event::CurrentMode { mode } => entry.current_mode = Some(mode),
            Event::Position { x, y } => entry.head.position = (x, y),
            Event::Transform { transform } => entry.head.transform = transform_of(transform),
            Event::Scale { scale } => entry.head.scale = scale,
            _ => {}
        }
    }
}

impl<D> Dispatch2<ZwlrOutputModeV1, D> for ModeData
where
    D: HeadsHandler + 'static,
{
    fn event(
        &self,
        state: &mut D,
        proxy: &ZwlrOutputModeV1,
        event: <ZwlrOutputModeV1 as Proxy>::Event,
        _: &Connection,
        _: &QueueHandle<D>,
    ) {
        use zwlr_output_mode_v1::Event;

        let heads = state.heads();
        match event {
            Event::Size { width, height } => {
                if let Some((_, size)) = heads.modes.iter_mut().find(|(mode, _)| mode == proxy) {
                    *size = (width, height);
                }
            }
            Event::Finished => {
                tracing::debug!("the compositor retired a mode of a head");
                heads.modes.retain(|(mode, _)| mode != proxy);
                for entry in &mut heads.heads {
                    if entry.current_mode.as_ref() == Some(proxy) {
                        entry.current_mode = None;
                    }
                }
                if proxy.version() >= 3 {
                    proxy.release();
                }
            }
            _ => {}
        }
    }
}
