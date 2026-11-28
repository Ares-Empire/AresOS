//! Whether sharing is on: the switch outside the image (brief 321, "The trust
//! model").
//!
//! The allow-list says *which* program may capture; this switch says *whether*
//! anything may. It is one root-owned file that only the owner's password turns
//! on, so a program of the same user that poses as Deskflow gets nothing until he
//! has said so. Everything that isn't plainly "on, in a file only root could have
//! written" is off.

use std::{
    fs::File,
    io::Read,
    os::unix::fs::MetadataExt,
    path::PathBuf,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
};

/// The switch. Its content is `on`, or sharing is off.
pub const SWITCH_PATH: &str = "/etc/aresos/input-portal/sharing";

/// The owner the switch and every folder above it must have.
pub const SWITCH_OWNER: u32 = 0;

/// Far more than `on` and a line end.
const MAX_SWITCH_BYTES: u64 = 64;

/// The switch file, and the folders above it that are checked with it.
#[derive(Debug, Clone)]
pub struct Switch {
    path: PathBuf,
    owner: u32,
    /// The topmost folder that is checked: `/` for the installed switch. Every
    /// folder from the file's own up to this one must be safe.
    root: PathBuf,
}

/// Why sharing is off.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Off {
    pub why: String,
    /// True when the file or a folder is there but unsafe or garbled, rather than
    /// simply missing: worth a warning every time it is read.
    pub suspicious: bool,
}

impl Off {
    fn suspicious(why: impl Into<String>) -> Self {
        Self {
            why: why.into(),
            suspicious: true,
        }
    }
}

impl std::fmt::Display for Off {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.why)
    }
}

impl Switch {
    /// The switch where the image's helper writes it.
    pub fn installed() -> Self {
        Self::new(PathBuf::from(SWITCH_PATH), SWITCH_OWNER, PathBuf::from("/"))
    }

    pub fn new(path: PathBuf, owner: u32, root: PathBuf) -> Self {
        Self { path, owner, root }
    }

    /// Read the switch now. `Ok` means sharing is on.
    ///
    /// Off: a missing file, content other than `on`, a file or folder that
    /// someone other than the owner (root) could have written, a symlink as the
    /// file or as any folder above it, or anything that isn't a regular file.
    /// The same rules as the allow-list's (`trust.rs`), and the folders too: a
    /// folder the user could write is a file the user could replace.
    pub fn read(&self) -> Result<(), Off> {
        self.check_folders()?;
        let text = self.read_file()?;
        // One line end is allowed; nothing else is a spelling of "on".
        match text.strip_suffix('\n').unwrap_or(&text) {
            "on" => Ok(()),
            _ => Err(Off::suspicious("its content is not `on`")),
        }
    }

    fn check_folders(&self) -> Result<(), Off> {
        let mut reached_root = false;
        for folder in self.path.ancestors().skip(1) {
            let meta = std::fs::symlink_metadata(folder).map_err(|err| Off {
                why: format!("{} can't be read: {err}", folder.display()),
                // A missing folder means the switch was never turned on.
                suspicious: err.kind() != std::io::ErrorKind::NotFound,
            })?;
            if meta.file_type().is_symlink() {
                return Err(Off::suspicious(format!("{} is a symlink", folder.display())));
            }
            if !meta.is_dir() {
                return Err(Off::suspicious(format!("{} is not a folder", folder.display())));
            }
            if meta.uid() != self.owner {
                return Err(Off::suspicious(format!(
                    "{} belongs to uid {}, not {}",
                    folder.display(),
                    meta.uid(),
                    self.owner
                )));
            }
            if meta.mode() & 0o022 != 0 {
                return Err(Off::suspicious(format!(
                    "{}'s group or everyone may write to it",
                    folder.display()
                )));
            }
            if folder == self.root.as_path() {
                reached_root = true;
                break;
            }
        }
        if !reached_root {
            return Err(Off::suspicious(format!(
                "{} is not inside {}",
                self.path.display(),
                self.root.display()
            )));
        }
        Ok(())
    }

    fn read_file(&self) -> Result<String, Off> {
        use rustix::fs::{Mode, OFlags};
        // NOFOLLOW: a symlink as the file itself fails here. NONBLOCK: a FIFO in its
        // place can't hold the backend waiting for a writer.
        let fd = rustix::fs::open(
            &self.path,
            OFlags::RDONLY | OFlags::NOFOLLOW | OFlags::NONBLOCK | OFlags::CLOEXEC,
            Mode::empty(),
        )
        .map_err(|err| match err {
            rustix::io::Errno::NOENT => Off {
                why: "there is no switch file".into(),
                suspicious: false,
            },
            rustix::io::Errno::LOOP => Off::suspicious("the switch file is a symlink"),
            err => Off::suspicious(format!("the switch file can't be opened: {err}")),
        })?;
        let file = File::from(fd);
        // Checked on the open file, so what is checked is what is read.
        let meta = file
            .metadata()
            .map_err(|err| Off::suspicious(format!("the switch file can't be read: {err}")))?;
        if !meta.is_file() {
            return Err(Off::suspicious("the switch is not a regular file"));
        }
        if meta.uid() != self.owner {
            return Err(Off::suspicious(format!(
                "the switch file belongs to uid {}, not {}",
                meta.uid(),
                self.owner
            )));
        }
        if meta.mode() & 0o022 != 0 {
            return Err(Off::suspicious("the switch file's group or everyone may write to it"));
        }
        if meta.len() > MAX_SWITCH_BYTES {
            return Err(Off::suspicious("the switch file is too large"));
        }
        let mut text = String::new();
        file.take(MAX_SWITCH_BYTES)
            .read_to_string(&mut text)
            .map_err(|err| Off::suspicious(format!("the switch file can't be read: {err}")))?;
        Ok(text)
    }

    #[cfg(test)]
    pub fn path(&self) -> &std::path::Path {
        &self.path
    }
}

/// The flag the input path reads before it hands on a single event: the Wayland
/// thread's forwarding and each EIS connection's writes. Closed the moment the
/// backend reads Off, so forwarding stops at once, before the teardown's commands
/// have reached either thread. Closed until a read of the switch has said on.
#[derive(Debug, Clone, Default)]
pub struct Gate(Arc<AtomicBool>);

impl Gate {
    pub fn is_open(&self) -> bool {
        self.0.load(Ordering::SeqCst)
    }

    /// Returns whether it was open before.
    pub fn open(&self) -> bool {
        self.0.swap(true, Ordering::SeqCst)
    }

    /// Returns whether it was open before.
    pub fn close(&self) -> bool {
        self.0.swap(false, Ordering::SeqCst)
    }
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;
    use std::path::Path;
    use std::sync::atomic::AtomicU32;

    /// A folder tree like `/etc/aresos/input-portal` in the temp dir, removed when
    /// the value is dropped. The switch is read with the tree's top as its root,
    /// since the temp dir itself is everyone's to write.
    pub(crate) struct TempSwitch {
        top: PathBuf,
        pub switch: Switch,
    }

    impl TempSwitch {
        /// `None` leaves the switch file out.
        pub(crate) fn new(contents: Option<&str>) -> Self {
            static NEXT: AtomicU32 = AtomicU32::new(0);
            let top = std::env::temp_dir().join(format!(
                "aresos-input-portal-switch-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, std::sync::atomic::Ordering::Relaxed)
            ));
            let _ = std::fs::remove_dir_all(&top);
            let folder = top.join("etc/aresos/input-portal");
            std::fs::create_dir_all(&folder).expect("make the switch's folders");
            for dir in [&top, &top.join("etc"), &top.join("etc/aresos"), &folder] {
                std::fs::set_permissions(dir, std::fs::Permissions::from_mode(0o755)).unwrap();
            }
            let owner = std::fs::metadata(&top).expect("stat the tree").uid();
            let switch = Switch::new(folder.join("sharing"), owner, top.clone());
            let made = Self { top, switch };
            made.set(contents);
            made
        }

        /// Write the switch as the helper will (one rename), or remove it.
        pub(crate) fn set(&self, contents: Option<&str>) {
            let path = self.switch.path();
            match contents {
                Some(contents) => {
                    let new = path.with_extension("new");
                    std::fs::write(&new, contents).expect("write the switch");
                    std::fs::set_permissions(&new, std::fs::Permissions::from_mode(0o644)).unwrap();
                    std::fs::rename(&new, path).expect("rename the switch into place");
                }
                None => {
                    let _ = std::fs::remove_file(path);
                }
            }
        }

        fn folder(&self, relative: &str) -> PathBuf {
            self.top.join(relative)
        }

        fn read(&self) -> Result<(), Off> {
            self.switch.read()
        }
    }

    impl Drop for TempSwitch {
        fn drop(&mut self) {
            // A test may have left a folder unwritable or replaced by a symlink.
            let _ = std::fs::remove_dir_all(&self.top);
        }
    }

    #[test]
    fn the_switch_is_on_only_for_on() {
        for on in ["on", "on\n"] {
            assert_eq!(TempSwitch::new(Some(on)).read(), Ok(()), "{on:?}");
        }
        for off in ["", "\n", "ON", "On", "on x", " on", "on ", "on\n\n", "on\r\n", "1", "yes", "true", "off"] {
            let read = TempSwitch::new(Some(off)).read();
            assert!(read.as_ref().is_err_and(|off| off.suspicious), "{off:?}: {read:?}");
        }
    }

    #[test]
    fn a_missing_switch_is_off_and_not_suspicious() {
        let read = TempSwitch::new(None).read();
        assert_eq!(read, Err(Off { why: "there is no switch file".into(), suspicious: false }));
        // Nor is a missing folder: the switch was never turned on.
        let switch = TempSwitch::new(None);
        std::fs::remove_dir(switch.folder("etc/aresos/input-portal")).unwrap();
        assert!(switch.read().is_err_and(|off| !off.suspicious));
    }

    #[test]
    fn a_switch_file_someone_else_could_have_written_is_off() {
        // Writable by the group or by everyone.
        for mode in [0o664, 0o646, 0o666] {
            let switch = TempSwitch::new(Some("on\n"));
            std::fs::set_permissions(switch.switch.path(), std::fs::Permissions::from_mode(mode)).unwrap();
            assert!(switch.read().is_err(), "mode {mode:o}");
        }

        // Not the owner's: the tree's owner is expected, and this switch expects another.
        let switch = TempSwitch::new(Some("on\n"));
        let other = Switch::new(switch.switch.path().to_owned(), switch.switch.owner.wrapping_add(1), switch.top.clone());
        assert!(other.read().is_err());

        // A symlink to a good "on" file.
        let switch = TempSwitch::new(None);
        let target = switch.folder("etc/aresos/real-switch");
        std::fs::write(&target, "on\n").unwrap();
        std::fs::set_permissions(&target, std::fs::Permissions::from_mode(0o644)).unwrap();
        std::os::unix::fs::symlink(&target, switch.switch.path()).unwrap();
        assert_eq!(switch.read(), Err(Off::suspicious("the switch file is a symlink")));

        // A folder, and a FIFO (which must not hang the read).
        let switch = TempSwitch::new(None);
        std::fs::create_dir(switch.switch.path()).unwrap();
        assert!(switch.read().is_err());
        let switch = TempSwitch::new(None);
        rustix::fs::mkfifoat(rustix::fs::CWD, switch.switch.path(), rustix::fs::Mode::from_raw_mode(0o644)).unwrap();
        assert_eq!(switch.read(), Err(Off::suspicious("the switch is not a regular file")));

        // Too large to be the switch, even if it starts with "on".
        let big = format!("on\n{}", " ".repeat(100));
        assert!(TempSwitch::new(Some(&big)).read().is_err());

        // And the same switch, untouched, is on.
        assert_eq!(TempSwitch::new(Some("on\n")).read(), Ok(()));
    }

    #[test]
    fn an_unsafe_folder_above_the_switch_turns_sharing_off() {
        for folder in ["etc/aresos/input-portal", "etc/aresos", "etc", ""] {
            // Writable by the group, or by everyone.
            for mode in [0o775, 0o757, 0o777, 0o1777] {
                let switch = TempSwitch::new(Some("on\n"));
                std::fs::set_permissions(switch.folder(folder), std::fs::Permissions::from_mode(mode)).unwrap();
                assert!(switch.read().is_err_and(|off| off.suspicious), "{folder:?} mode {mode:o}");
            }
        }

        // A folder replaced by a symlink to a tree that looks right.
        let switch = TempSwitch::new(Some("on\n"));
        let real = switch.folder("etc/aresos-real");
        std::fs::rename(switch.folder("etc/aresos"), &real).unwrap();
        std::os::unix::fs::symlink(&real, switch.folder("etc/aresos")).unwrap();
        assert!(switch.read().is_err_and(|off| off.suspicious && off.why.contains("is a symlink")));

        // A folder that belongs to someone else (only root can arrange it; the unit
        // tests run as root in the build container).
        let switch = TempSwitch::new(Some("on\n"));
        if std::os::unix::fs::chown(switch.folder("etc/aresos"), Some(4242), None).is_ok() {
            assert!(switch.read().is_err_and(|off| off.why.contains("belongs to uid 4242")));
        }

        // A switch outside the folder it is meant to be checked up to.
        let switch = TempSwitch::new(Some("on\n"));
        let elsewhere = Switch::new(switch.switch.path().to_owned(), switch.switch.owner, PathBuf::from("/nonexistent"));
        assert!(elsewhere.read().is_err());

        // The installed switch is checked all the way up to `/`.
        let installed = Switch::installed();
        assert_eq!(installed.path, Path::new(SWITCH_PATH));
        assert_eq!(installed.root, Path::new("/"));
        assert_eq!(installed.owner, 0);
    }

    #[test]
    fn the_gate_is_closed_until_opened() {
        let gate = Gate::default();
        assert!(!gate.is_open());
        let seen_by_the_input_path = gate.clone();
        assert!(!gate.open());
        assert!(seen_by_the_input_path.is_open());
        assert!(gate.close());
        assert!(!seen_by_the_input_path.is_open());
        assert!(!gate.close());
    }
}
