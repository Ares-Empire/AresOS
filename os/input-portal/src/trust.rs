//! Who may use the backend: which applications, and which caller on the bus.
//!
//! The backend sees every keystroke and the clipboard, so both answers are
//! "one, named exactly", and everything else is refused.

use std::{collections::HashSet, fs::File, io::Read, os::unix::fs::MetadataExt, path::Path};
use tracing::warn;

/// The portal frontend's bus name. Only its current owner may call the
/// `org.freedesktop.impl.portal.*` methods.
pub const FRONTEND_NAME: &str = "org.freedesktop.portal.Desktop";

/// The applications that may start a capture: one ID per line, in a root-owned
/// file of the image. There is no way to point the backend at another file.
pub const ALLOWED_APPS_PATH: &str = "/usr/share/aresos/input-portal/allowed-apps";

/// The owner the allow-list must have.
pub const ALLOWED_APPS_OWNER: u32 = 0;

/// Far more than a list of application IDs needs.
const MAX_LIST_BYTES: u64 = 64 * 1024;

/// The exact application IDs that may create a session. Default deny.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct AllowList {
    ids: HashSet<String>,
}

impl AllowList {
    /// One ID per line. Blank lines and lines starting with `#` are skipped;
    /// nothing is a pattern.
    pub fn parse(text: &str) -> Self {
        Self {
            ids: text
                .lines()
                .map(str::trim)
                .filter(|line| !line.is_empty() && !line.starts_with('#'))
                .map(str::to_owned)
                .collect(),
        }
    }

    /// Whether this exact ID is listed. The empty ID never is: it is what a host
    /// application without a desktop file gets, so it names nobody.
    pub fn allows(&self, app_id: &str) -> bool {
        !app_id.is_empty() && self.ids.contains(app_id)
    }

    /// Read the list. A file that is missing, unreadable, not a plain file, not
    /// owned by `owner`, or writable by anyone else allows nothing.
    pub fn load(path: &Path, owner: u32) -> Self {
        match read_list(path, owner) {
            Ok(text) => Self::parse(&text),
            Err(why) => {
                warn!(
                    path = %path.display(),
                    "the allow-list can't be used ({why}): every application is refused"
                );
                Self::default()
            }
        }
    }
}

fn read_list(path: &Path, owner: u32) -> Result<String, String> {
    let file = File::open(path).map_err(|err| format!("open failed: {err}"))?;
    // Checked on the open file, so what is checked is what is read.
    let meta = file.metadata().map_err(|err| format!("stat failed: {err}"))?;
    if !meta.is_file() {
        return Err("it is not a regular file".into());
    }
    if meta.uid() != owner {
        return Err(format!("its owner is uid {}, not {owner}", meta.uid()));
    }
    if meta.mode() & 0o022 != 0 {
        return Err("its group or everyone may write to it".into());
    }
    if meta.len() > MAX_LIST_BYTES {
        return Err(format!("it is larger than {MAX_LIST_BYTES} bytes"));
    }
    let mut text = String::new();
    file.take(MAX_LIST_BYTES)
        .read_to_string(&mut text)
        .map_err(|err| format!("read failed: {err}"))?;
    Ok(text)
}

/// Whether a message's sender is the frontend: both must be known and equal.
/// A message without a sender, or a bus where nobody owns the frontend's name,
/// is never the frontend.
pub fn is_frontend(sender: Option<&str>, frontend_owner: Option<&str>) -> bool {
    matches!((sender, frontend_owner), (Some(sender), Some(owner)) if !sender.is_empty() && sender == owner)
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;
    use std::path::PathBuf;
    use std::sync::atomic::{AtomicU32, Ordering};

    /// A file in the temp dir that is removed when the value is dropped.
    pub(crate) struct TempList {
        pub path: PathBuf,
        /// Who owns files this test process creates (root in the build container).
        pub owner: u32,
    }

    impl TempList {
        /// `None` gives a path where no file exists.
        pub(crate) fn new(contents: Option<&str>) -> Self {
            static NEXT: AtomicU32 = AtomicU32::new(0);
            let path = std::env::temp_dir().join(format!(
                "aresos-input-portal-test-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            let _ = std::fs::remove_file(&path);
            // The owner of a file made here; the missing-file case needs it too.
            let probe = path.with_extension("probe");
            std::fs::write(&probe, "").expect("write the probe");
            let owner = std::fs::metadata(&probe).expect("stat the probe").uid();
            std::fs::remove_file(&probe).expect("remove the probe");
            if let Some(contents) = contents {
                std::fs::write(&path, contents).expect("write the list");
                std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o644))
                    .expect("set the list's mode");
            }
            Self { path, owner }
        }

        fn load(&self) -> AllowList {
            AllowList::load(&self.path, self.owner)
        }
    }

    impl Drop for TempList {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.path);
        }
    }

    #[test]
    fn a_listed_id_is_allowed_and_nothing_else() {
        let list = TempList::new(Some("org.deskflow.deskflow\n")).load();
        assert!(list.allows("org.deskflow.deskflow"));
        for other in [
            "org.deskflow.Deskflow",
            "org.deskflow.deskflow2",
            "org.deskflow",
            "org.deskflow.deskflow ",
            " org.deskflow.deskflow",
            "org.deskflow.deskflow\n",
            "com.example.Other",
            "*",
        ] {
            assert!(!list.allows(other), "{other:?} must be refused");
        }
    }

    #[test]
    fn the_empty_id_is_never_allowed() {
        // Not with an empty list, not with blank lines, not next to real IDs.
        for contents in ["", "\n", "\n\n   \n", "org.deskflow.deskflow\n\n"] {
            assert!(!TempList::new(Some(contents)).load().allows(""), "{contents:?}");
        }
    }

    #[test]
    fn a_missing_file_denies_everyone() {
        let list = TempList::new(None).load();
        assert_eq!(list, AllowList::default());
        assert!(!list.allows("org.deskflow.deskflow"));
        assert!(!list.allows(""));
    }

    #[test]
    fn the_shipped_file_allows_only_deskflow() {
        let shipped = include_str!("../data/allowed-apps");
        assert_eq!(shipped, "org.deskflow.deskflow\n");
        assert!(AllowList::parse(shipped).allows("org.deskflow.deskflow"));
    }

    #[test]
    fn comments_blank_lines_and_line_ends_are_not_ids() {
        let list = AllowList::parse("# a comment\n\n  org.example.One  \r\norg.example.Two\n#org.example.Off\n");
        assert!(list.allows("org.example.One"));
        assert!(list.allows("org.example.Two"));
        assert!(!list.allows("org.example.Off"));
        assert!(!list.allows("#org.example.Off"));
        assert!(!list.allows("# a comment"));
        assert_eq!(list.ids.len(), 2);
    }

    #[test]
    fn a_file_someone_else_could_have_written_denies_everyone() {
        let listed = "org.deskflow.deskflow\n";

        // Not owned by the expected owner.
        let file = TempList::new(Some(listed));
        assert!(!AllowList::load(&file.path, file.owner.wrapping_add(1)).allows("org.deskflow.deskflow"));

        // Writable by the group, or by everyone.
        for mode in [0o664, 0o646, 0o666] {
            let file = TempList::new(Some(listed));
            std::fs::set_permissions(&file.path, std::fs::Permissions::from_mode(mode)).unwrap();
            assert!(!file.load().allows("org.deskflow.deskflow"), "mode {mode:o}");
        }

        // Not a regular file.
        let dir = TempList::new(None);
        std::fs::create_dir(&dir.path).unwrap();
        assert!(!dir.load().allows("org.deskflow.deskflow"));
        std::fs::remove_dir(&dir.path).unwrap();

        // Too large to be a list of IDs.
        let big = format!("org.deskflow.deskflow\n{}", "#\n".repeat(40_000));
        assert!(!TempList::new(Some(&big)).load().allows("org.deskflow.deskflow"));

        // And the same file, untouched, is accepted.
        assert!(TempList::new(Some(listed)).load().allows("org.deskflow.deskflow"));
    }

    #[test]
    fn only_the_owner_of_the_frontend_name_is_the_frontend() {
        assert!(is_frontend(Some(":1.5"), Some(":1.5")));
        assert!(!is_frontend(Some(":1.6"), Some(":1.5")));
        assert!(!is_frontend(None, Some(":1.5")));
        assert!(!is_frontend(Some(":1.5"), None));
        assert!(!is_frontend(None, None));
        assert!(!is_frontend(Some(""), Some("")));
    }
}
