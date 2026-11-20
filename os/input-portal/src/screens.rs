//! The screens, read from labwc's `zwlr_output_manager_v1`, as one committed snapshot.
//!
//! Upstream asked niri for the layout on demand (`niri msg --json outputs`) and kept
//! a second layout on the Wayland side for placing barrier surfaces. Two sources can
//! disagree for a moment, and a barrier accepted against one layout could be placed
//! against the other. Here there is one [`Snapshot`]: the Wayland thread builds it
//! from the output manager's heads each time the compositor commits a change
//! (`done`), and the portal's zones, the barrier surfaces and the EIS device regions
//! all read that same value. Its `zone_set` number changes exactly when the screens
//! do, which is what lets barriers for an old layout be refused.

use crate::eis_server::Region;
use std::sync::{Arc, PoisonError, RwLock};

/// `wl_output.transform`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum Transform {
    #[default]
    Normal,
    Rotated90,
    Rotated180,
    Rotated270,
    Flipped,
    Flipped90,
    Flipped180,
    Flipped270,
}

impl Transform {
    /// A quarter turn shows the mode's width as the screen's height.
    pub fn swaps_width_and_height(self) -> bool {
        matches!(
            self,
            Self::Rotated90 | Self::Rotated270 | Self::Flipped90 | Self::Flipped270
        )
    }
}

/// One head as `zwlr_output_head_v1` describes it.
#[derive(Debug, Clone, PartialEq)]
pub struct Head {
    pub name: Option<String>,
    pub enabled: bool,
    /// Position in the compositor's layout, in logical pixels.
    pub position: (i32, i32),
    /// The current mode's size in hardware pixels.
    pub mode: Option<(i32, i32)>,
    pub scale: f64,
    pub transform: Transform,
}

impl Default for Head {
    fn default() -> Self {
        Self {
            name: None,
            enabled: false,
            position: (0, 0),
            mode: None,
            scale: 1.0,
            transform: Transform::Normal,
        }
    }
}

/// One portal zone: width, height, x-offset, y-offset, in logical pixels.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Zone {
    pub width: u32,
    pub height: u32,
    pub x: i32,
    pub y: i32,
}

/// An enabled screen that also exists as a `wl_output`.
#[derive(Debug, Clone, PartialEq)]
pub struct Screen {
    /// The head's name, which is also its `wl_output`'s name.
    pub name: String,
    pub zone: Zone,
    pub scale: f64,
    pub transform: Transform,
}

/// The logical size labwc gives an output with this mode, scale and transform.
///
/// This is wlroots' `wlr_output_effective_resolution`: swap the sides for a
/// quarter turn, then divide by the scale in single precision and drop the
/// fraction. Doing it the same way matters at fractional scale, where rounding
/// instead would put a zone's edge one pixel off the real screen edge.
pub fn logical_size(mode: (i32, i32), scale: f64, transform: Transform) -> Option<(u32, u32)> {
    let (width, height) = if transform.swaps_width_and_height() {
        (mode.1, mode.0)
    } else {
        mode
    };
    if width <= 0 || height <= 0 || !scale.is_finite() || scale <= 0.0 {
        return None;
    }
    #[allow(clippy::cast_possible_truncation, clippy::cast_precision_loss, clippy::cast_sign_loss)]
    let logical = |pixels: i32| (pixels as f32 / scale as f32) as u32;
    let (width, height) = (logical(width), logical(height));
    (width > 0 && height > 0).then_some((width, height))
}

/// Turn the heads of one `done` into screens.
///
/// A head counts when it is enabled, has a current mode, and `is_wl_output` knows
/// its name: a barrier surface needs the `wl_output`, so a head that has none yet
/// (or no longer) is not a place a capture can start from.
///
/// The order is fixed (by position, then name), so the same layout always gives
/// the same list and comparing two lists says whether anything changed.
pub fn screens_from_heads(heads: &[Head], is_wl_output: impl Fn(&str) -> bool) -> Vec<Screen> {
    let mut screens: Vec<Screen> = heads
        .iter()
        .filter(|head| head.enabled)
        .filter_map(|head| {
            let name = head.name.as_deref()?;
            if !is_wl_output(name) {
                return None;
            }
            let (width, height) = logical_size(head.mode?, head.scale, head.transform)?;
            Some(Screen {
                name: name.to_owned(),
                zone: Zone {
                    width,
                    height,
                    x: head.position.0,
                    y: head.position.1,
                },
                scale: head.scale,
                transform: head.transform,
            })
        })
        .collect();
    screens.sort_by(|a, b| {
        (a.zone.x, a.zone.y, a.name.as_str()).cmp(&(b.zone.x, b.zone.y, b.name.as_str()))
    });
    screens
}

/// The screens at one moment, with the number that names this layout.
#[derive(Debug, Clone, PartialEq)]
pub struct Snapshot {
    /// The portal's `zone_set`. Never zero.
    pub zone_set: u32,
    pub screens: Vec<Screen>,
}

impl Snapshot {
    /// `(name, logical position, logical size)` per screen, for placing barriers.
    pub fn layout(&self) -> Vec<(String, (i32, i32), (i32, i32))> {
        self.screens
            .iter()
            .filter_map(|screen| {
                let size = (
                    i32::try_from(screen.zone.width).ok()?,
                    i32::try_from(screen.zone.height).ok()?,
                );
                Some((screen.name.clone(), (screen.zone.x, screen.zone.y), size))
            })
            .collect()
    }

    /// Size of the screens' bounding box in logical pixels.
    /// EIS advertises this size at (0, 0); portal coordinates remain in the
    /// compositor's space. This fixes sizing only, not the client's mapping
    /// between those spaces.
    pub fn region(&self) -> Option<Region> {
        let mut bounds: Option<(i64, i64, i64, i64)> = None;
        for screen in &self.screens {
            let z = screen.zone;
            if z.width == 0 || z.height == 0 {
                continue;
            }
            let x = i64::from(z.x);
            let y = i64::from(z.y);
            let right = x + i64::from(z.width);
            let bottom = y + i64::from(z.height);
            bounds = Some(match bounds {
                None => (x, y, right, bottom),
                Some((left, top, r, b)) => (left.min(x), top.min(y), r.max(right), b.max(bottom)),
            });
        }
        let (left, top, right, bottom) = bounds?;
        // Reject unrepresentable geometry instead of silently truncating it.
        Some(Region {
            width: u32::try_from(right - left).ok()?,
            height: u32::try_from(bottom - top).ok()?,
        })
    }
}

/// The one snapshot, shared by the Wayland thread (which writes it) and the
/// portal (which reads it).
#[derive(Debug, Clone)]
pub struct SharedScreens(Arc<RwLock<Arc<Snapshot>>>);

impl SharedScreens {
    /// No screens yet. The first real layout becomes zone set 2.
    pub fn new() -> Self {
        Self(Arc::new(RwLock::new(Arc::new(Snapshot {
            zone_set: 1,
            screens: Vec::new(),
        }))))
    }

    pub fn current(&self) -> Arc<Snapshot> {
        self.0
            .read()
            .unwrap_or_else(PoisonError::into_inner)
            .clone()
    }

    /// Make `screens` the snapshot. Returns the new snapshot when it differs from
    /// the old one, and `None` (nothing changes, the zone set keeps its number)
    /// when it doesn't.
    pub fn commit(&self, screens: Vec<Screen>) -> Option<Arc<Snapshot>> {
        let mut current = self.0.write().unwrap_or_else(PoisonError::into_inner);
        if current.screens == screens {
            return None;
        }
        let next = Arc::new(Snapshot {
            // Zero is skipped on a wrap so it can never name a layout.
            zone_set: current.zone_set.wrapping_add(1).max(1),
            screens,
        });
        *current = next.clone();
        Some(next)
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;

    fn head(name: &str, x: i32, y: i32, mode: (i32, i32), scale: f64, transform: Transform) -> Head {
        Head {
            name: Some(name.into()),
            enabled: true,
            position: (x, y),
            mode: Some(mode),
            scale,
            transform,
        }
    }

    fn zones(heads: &[Head]) -> Vec<(String, (u32, u32, i32, i32))> {
        screens_from_heads(heads, |_| true)
            .into_iter()
            .map(|s| (s.name, (s.zone.width, s.zone.height, s.zone.x, s.zone.y)))
            .collect()
    }

    /// A screen for other modules' tests.
    pub(crate) fn screen(name: &str, x: i32, y: i32, width: u32, height: u32) -> Screen {
        Screen {
            name: name.into(),
            zone: Zone { width, height, x, y },
            scale: 1.0,
            transform: Transform::Normal,
        }
    }

    #[test]
    fn an_integer_scale_divides_the_mode() {
        let heads = [head("A", 0, 0, (3840, 2160), 2.0, Transform::Normal)];
        assert_eq!(zones(&heads), [("A".to_owned(), (1920, 1080, 0, 0))]);
    }

    #[test]
    fn a_fractional_scale_drops_the_fraction_as_wlroots_does() {
        // 2560x1600 at 1.5 is 1706.67 x 1066.67: labwc's output is 1706x1066.
        assert_eq!(logical_size((2560, 1600), 1.5, Transform::Normal), Some((1706, 1066)));
        assert_eq!(logical_size((1920, 1080), 1.25, Transform::Normal), Some((1536, 864)));
        // 2560 / 1.75 = 1462.86, 1440 / 1.75 = 822.86.
        assert_eq!(logical_size((2560, 1440), 1.75, Transform::Normal), Some((1462, 822)));
        // The protocol carries the scale in 1/256 steps: "1.33" arrives as 341/256.
        assert_eq!(
            logical_size((1920, 1080), 341.0 / 256.0, Transform::Normal),
            Some((1441, 810))
        );
        // A division that comes out whole stays whole.
        assert_eq!(logical_size((3840, 2160), 1.5, Transform::Normal), Some((2560, 1440)));
    }

    #[test]
    fn a_quarter_turn_swaps_width_and_height() {
        for turned in [
            Transform::Rotated90,
            Transform::Rotated270,
            Transform::Flipped90,
            Transform::Flipped270,
        ] {
            assert_eq!(logical_size((1920, 1080), 1.0, turned), Some((1080, 1920)), "{turned:?}");
        }
        for upright in [
            Transform::Normal,
            Transform::Rotated180,
            Transform::Flipped,
            Transform::Flipped180,
        ] {
            assert_eq!(logical_size((1920, 1080), 1.0, upright), Some((1920, 1080)), "{upright:?}");
        }
        // The turn comes before the scale.
        assert_eq!(logical_size((2560, 1600), 1.5, Transform::Rotated90), Some((1066, 1706)));
    }

    #[test]
    fn a_disabled_head_is_no_zone() {
        let mut off = head("B", 1920, 0, (1920, 1080), 1.0, Transform::Normal);
        off.enabled = false;
        let heads = [head("A", 0, 0, (1920, 1080), 1.0, Transform::Normal), off];
        assert_eq!(zones(&heads), [("A".to_owned(), (1920, 1080, 0, 0))]);
    }

    #[test]
    fn a_head_without_a_mode_a_name_or_a_sane_scale_is_no_zone() {
        let mut no_mode = head("A", 0, 0, (1, 1), 1.0, Transform::Normal);
        no_mode.mode = None;
        let mut no_name = head("B", 0, 0, (1920, 1080), 1.0, Transform::Normal);
        no_name.name = None;
        let heads = [
            no_mode,
            no_name,
            head("C", 0, 0, (1920, 1080), 0.0, Transform::Normal),
            head("D", 0, 0, (1920, 1080), f64::NAN, Transform::Normal),
            head("E", 0, 0, (0, 1080), 1.0, Transform::Normal),
            head("F", 0, 0, (-1920, 1080), 1.0, Transform::Normal),
        ];
        assert!(zones(&heads).is_empty());
    }

    #[test]
    fn a_head_with_no_wl_output_is_no_zone() {
        let heads = [
            head("A", 0, 0, (1920, 1080), 1.0, Transform::Normal),
            head("B", 1920, 0, (1920, 1080), 1.0, Transform::Normal),
        ];
        let screens = screens_from_heads(&heads, |name| name == "B");
        assert_eq!(screens.len(), 1);
        assert_eq!(screens[0].name, "B");
    }

    #[test]
    fn side_by_side_and_stacked() {
        let side = [
            head("A", 0, 0, (1920, 1080), 1.0, Transform::Normal),
            head("B", 1920, 0, (2560, 1440), 1.0, Transform::Normal),
        ];
        assert_eq!(
            zones(&side),
            [("A".to_owned(), (1920, 1080, 0, 0)), ("B".to_owned(), (2560, 1440, 1920, 0))]
        );
        // The real layout upstream was developed on: a 4K monitor at 1.25 above
        // the laptop panel at 1.5.
        let stacked = [
            head("eDP-2", 298, 1728, (2560, 1600), 1.5, Transform::Normal),
            head("HDMI-A-1", 0, 0, (3840, 2160), 1.25, Transform::Normal),
        ];
        assert_eq!(
            zones(&stacked),
            [
                ("HDMI-A-1".to_owned(), (3072, 1728, 0, 0)),
                ("eDP-2".to_owned(), (1706, 1066, 298, 1728))
            ]
        );
    }

    #[test]
    fn the_order_does_not_depend_on_the_order_of_the_heads() {
        let a = head("A", 0, 0, (1920, 1080), 1.0, Transform::Normal);
        let b = head("B", 1920, 0, (1920, 1080), 1.0, Transform::Normal);
        let c = head("C", 0, 1080, (1920, 1080), 1.0, Transform::Normal);
        // Two heads at one position (mirrored) fall back to the name.
        let d = head("D", 0, 0, (1920, 1080), 1.0, Transform::Normal);
        let one = zones(&[a.clone(), b.clone(), c.clone(), d.clone()]);
        let other = zones(&[d, c, b, a]);
        assert_eq!(one, other);
        let names: Vec<&str> = one.iter().map(|(name, _)| name.as_str()).collect();
        assert_eq!(names, ["A", "D", "C", "B"]);
    }

    #[test]
    fn the_zone_set_changes_exactly_when_the_screens_do() {
        let shared = SharedScreens::new();
        let before = shared.current();
        assert!(before.screens.is_empty());

        let first = shared.commit(vec![screen("A", 0, 0, 1920, 1080)]).expect("a change");
        assert_ne!(first.zone_set, before.zone_set);
        assert_eq!(shared.current(), first);

        // The same screens again: nothing changed, nothing is announced.
        assert!(shared.commit(vec![screen("A", 0, 0, 1920, 1080)]).is_none());
        assert_eq!(shared.current().zone_set, first.zone_set);

        // Hotplug, a move, and unplugging everything each give a new zone set.
        let mut seen = vec![before.zone_set, first.zone_set];
        for screens in [
            vec![screen("A", 0, 0, 1920, 1080), screen("B", 1920, 0, 1920, 1080)],
            vec![screen("A", 0, 0, 1920, 1080), screen("B", 0, 1080, 1920, 1080)],
            vec![],
        ] {
            let next = shared.commit(screens).expect("a change");
            assert!(!seen.contains(&next.zone_set));
            seen.push(next.zone_set);
        }
    }

    #[test]
    fn the_zone_set_is_never_zero() {
        let shared = SharedScreens(Arc::new(RwLock::new(Arc::new(Snapshot {
            zone_set: u32::MAX,
            screens: Vec::new(),
        }))));
        let next = shared.commit(vec![screen("A", 0, 0, 1, 1)]).expect("a change");
        assert_eq!(next.zone_set, 1);
    }

    #[test]
    fn the_layout_is_the_zones() {
        let snapshot = Snapshot {
            zone_set: 2,
            screens: vec![screen("A", -1920, 0, 1920, 1080), screen("B", 0, 0, 2560, 1440)],
        };
        assert_eq!(
            snapshot.layout(),
            [
                ("A".to_owned(), (-1920, 0), (1920, 1080)),
                ("B".to_owned(), (0, 0), (2560, 1440))
            ]
        );
    }

    // Upstream's region tests, against the snapshot.

    fn size(screens: &[Screen]) -> Option<(u32, u32)> {
        Snapshot { zone_set: 1, screens: screens.to_vec() }
            .region()
            .map(|r| (r.width, r.height))
    }

    #[test]
    fn negative_horizontal_and_vertical() {
        assert_eq!(
            size(&[screen("a", -1920, 0, 1920, 1080), screen("b", 0, 0, 1920, 1080)]),
            Some((3840, 1080))
        );
        assert_eq!(
            size(&[screen("a", 0, -1080, 1920, 1080), screen("b", 0, 0, 1920, 1080)]),
            Some((1920, 2160))
        );
    }

    #[test]
    fn mixed_resolution_scale_and_portrait_logical_sizes() {
        let screens = [
            screen("a", -1920, 0, 1920, 1080),
            screen("b", 0, -360, 2560, 1440),
            screen("c", 2560, 0, 1080, 1920),
        ];
        assert_eq!(size(&screens), Some((5560, 2280)));
        let mut reversed = screens.to_vec();
        reversed.reverse();
        assert_eq!(size(&screens), size(&reversed));
    }

    #[test]
    fn translation_overlap_and_gaps() {
        assert_eq!(size(&[screen("a", 100, 200, 1920, 1080)]), Some((1920, 1080)));
        assert_eq!(size(&[screen("a", -3000, -2000, 1920, 1080)]), Some((1920, 1080)));
        assert_eq!(
            size(&[screen("a", 0, 0, 1920, 1080), screen("b", 0, 0, 1920, 1080)]),
            Some((1920, 1080))
        );
        assert_eq!(
            size(&[screen("a", 0, 0, 100, 100), screen("b", 200, 200, 100, 100)]),
            Some((300, 300))
        );
    }

    #[test]
    fn empty_degenerate_and_overflow() {
        assert_eq!(size(&[]), None);
        assert_eq!(size(&[screen("a", 0, 0, 0, 1080)]), None);
        assert_eq!(
            size(&[screen("a", i32::MIN, 0, 0, 1), screen("b", 0, 0, 100, 100)]),
            Some((100, 100))
        );
        assert_eq!(
            size(&[screen("a", i32::MIN, 0, 1, 1), screen("b", i32::MAX, 0, 1, 1)]),
            None
        );
        assert_eq!(size(&[screen("a", i32::MAX, 0, u32::MAX, 1)]), Some((u32::MAX, 1)));
    }

    #[test]
    fn recomputation_after_hotplug() {
        let mut screens = vec![screen("a", 0, 0, 1920, 1080)];
        assert_eq!(size(&screens), Some((1920, 1080)));
        screens.push(screen("b", -2560, 0, 2560, 1440));
        assert_eq!(size(&screens), Some((4480, 1440)));
        screens.remove(0);
        assert_eq!(size(&screens), Some((2560, 1440)));
        screens.clear();
        assert_eq!(size(&screens), None);
    }
}
