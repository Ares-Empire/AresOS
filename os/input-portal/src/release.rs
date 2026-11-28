//! `--release`: the way out, also against a backend that is stuck.
//!
//! The release key runs this. It asks the running backend over the bus, and the
//! backend answers only once the compositor has confirmed the pointer lock and
//! the keyboard are given back. A backend that doesn't answer that way within
//! [`DEADLINE`] (stopped, hung, or its compositor stopped) is killed, and labwc
//! drops the grab with its connection. The kill goes through a pidfd taken
//! before the question: never by PID or by name, so a process that took the PID
//! or the bus name in the meantime is never hit (brief 321, "The trust model").

use anyhow::{bail, ensure, Context, Result};
use rustix::process::{pidfd_open, pidfd_send_signal, Pid, PidfdFlags, Signal};
use std::os::fd::{AsFd, AsRawFd, OwnedFd};
use std::path::Path;
use std::time::Duration;

/// Where the image installs the backend: `--release` signals no other program.
pub const INSTALLED: &str = "/usr/libexec/aresos-input-portal";

/// How long the backend has to give a confirmed answer before it is killed.
pub const DEADLINE: Duration = Duration::from_secs(2);

const DESKFLOW_LAUNCHER: &str = "/usr/libexec/aresos-deskflow";
const DESKFLOW_CORE: &str = "/usr/bin/deskflow-core";

/// One process, held by a pidfd, and its PID as this process sees it.
pub struct Pinned {
    pidfd: OwnedFd,
    pub pid: i32,
}

/// What the kill found.
#[derive(Debug, PartialEq, Eq)]
pub enum Killed {
    Now,
    /// The pinned process had already ended; nothing was signalled.
    AlreadyGone,
}

impl Pinned {
    /// Pin the process with this PID now.
    pub fn open(pid: i32) -> Result<Self> {
        let raw = Pid::from_raw(pid).context("not a process ID")?;
        let pidfd = pidfd_open(raw, PidfdFlags::empty()).with_context(|| format!("pidfd_open({pid}) failed"))?;
        Ok(Self { pidfd, pid })
    }

    /// Take a pidfd someone else made (the bus's `ProcessFD`) and read its PID.
    pub fn from_pidfd(pidfd: OwnedFd) -> Result<Self> {
        let fdinfo = std::fs::read_to_string(format!("/proc/self/fdinfo/{}", pidfd.as_raw_fd()))
            .context("the pidfd's fdinfo can't be read")?;
        let pid = pid_in_fdinfo(&fdinfo).context("the pidfd names no process this one can see")?;
        Ok(Self { pidfd, pid })
    }

    /// Whether the pinned process is still running. A pidfd turns readable when
    /// its process has ended, and stays so even if the PID is taken again.
    pub fn alive(&self) -> bool {
        !self.exited_within(0).unwrap_or(true)
    }

    fn exited_within(&self, milliseconds: i64) -> rustix::io::Result<bool> {
        use rustix::event::{poll, PollFd, PollFlags, Timespec};
        let mut fds = [PollFd::new(&self.pidfd, PollFlags::IN)];
        let timeout = Timespec { tv_sec: 0, tv_nsec: milliseconds * 1_000_000 };
        poll(&mut fds, Some(&timeout)).map(|ready| ready > 0)
    }

    /// The pinned process runs `installed` as the user `uid`, or this fails.
    ///
    /// Both are read through `/proc/<pid>`; they are the pinned process's only
    /// if it is still running after the read, since a running process keeps its
    /// PID. So the pidfd is asked last.
    pub fn verify(&self, installed: &Path, uid: u32) -> Result<()> {
        let exe = std::fs::read_link(format!("/proc/{}/exe", self.pid))
            .with_context(|| format!("can't see which program pid {} runs", self.pid))?;
        let status = std::fs::read_to_string(format!("/proc/{}/status", self.pid))
            .with_context(|| format!("can't read the status of pid {}", self.pid))?;
        ensure!(self.alive(), "pid {} ended while it was being checked", self.pid);
        ensure!(
            exe == installed,
            "pid {} runs {}, not {}",
            self.pid,
            exe.display(),
            installed.display()
        );
        let uids = uids_in_status(&status).with_context(|| format!("pid {}'s status has no user", self.pid))?;
        ensure!(uids.iter().all(|&id| id == uid), "pid {} runs as another user", self.pid);
        Ok(())
    }

    /// SIGKILL through the pidfd, never by PID.
    pub fn kill(&self) -> Result<Killed> {
        match pidfd_send_signal(&self.pidfd, Signal::KILL) {
            Ok(()) => Ok(Killed::Now),
            Err(rustix::io::Errno::SRCH) => Ok(Killed::AlreadyGone),
            Err(err) => bail!("could not kill pid {}: {err}", self.pid),
        }
    }
}

fn process_start(stat: &str) -> Option<u64> {
    // Field 22 of /proc/PID/stat. The comm in parentheses can contain spaces and ')' itself.
    stat.rsplit_once(") ")?.1.split_whitespace().nth(19)?.parse().ok()
}

fn deskflow_process(record: &str, uid: u32, matches_program: impl FnOnce(&Path) -> bool) -> Option<Pinned> {
    use std::os::unix::fs::MetadataExt;
    let (pid, start) = record.split_once(' ')?;
    let pinned = Pinned::open(pid.parse().ok()?).ok()?;
    let proc = std::path::PathBuf::from(format!("/proc/{}", pinned.pid));
    let actual_start = process_start(&std::fs::read_to_string(proc.join("stat")).ok()?)?;
    (actual_start == start.parse::<u64>().ok()?
        && proc.metadata().ok()?.uid() == uid
        && matches_program(&proc)
        && pinned.alive()).then_some(pinned)
}

fn stop_guarded_deskflow() -> Result<()> {
    use std::io::Read;
    use std::os::unix::fs::{MetadataExt, OpenOptionsExt};

    let Some(runtime) = std::env::var_os("XDG_RUNTIME_DIR") else { return Ok(()) };
    let runtime = Path::new(&runtime);
    let uid = rustix::process::getuid().as_raw();
    let dir = runtime.symlink_metadata()?;
    ensure!(runtime.is_absolute() && dir.is_dir() && dir.uid() == uid && dir.mode() & 0o077 == 0,
            "Deskflow's runtime directory is not private");
    let record = match std::fs::OpenOptions::new().read(true)
        .custom_flags(rustix::fs::OFlags::NOFOLLOW.bits() as i32 | rustix::fs::OFlags::NONBLOCK.bits() as i32)
        .open(runtime.join("aresos-deskflow.pid")) {
        Ok(file) => file,
        Err(err) if err.kind() == std::io::ErrorKind::NotFound => return Ok(()),
        Err(err) => return Err(err.into()),
    };
    let meta = record.metadata()?;
    ensure!(meta.is_file() && meta.uid() == uid && meta.mode() & 0o077 == 0 && meta.len() <= 128,
            "Deskflow's process record is not private");
    let mut text = String::new();
    record.take(129).read_to_string(&mut text)?;
    let mut records = text.lines();
    let launcher = records.next().and_then(|line| deskflow_process(line, uid, |proc| {
        std::fs::read(proc.join("cmdline")).is_ok_and(|argv| {
            let argv: Vec<_> = argv.split(|byte| *byte == 0).collect();
            argv.get(..3) == Some(&[b"/usr/bin/python3".as_slice(), b"-I", DESKFLOW_LAUNCHER.as_bytes()])
        })
    }));
    let core = records.next().and_then(|line| deskflow_process(line, uid, |proc| {
        std::fs::read_link(proc.join("exe")).is_ok_and(|path| path == Path::new(DESKFLOW_CORE))
    }));
    if let Some(core) = &core {
        core.kill().context("stop the guarded Deskflow core")?;
    }
    if let Some(launcher) = &launcher {
        // Give the guard time to reap the core and remove its private profile. If the guard is
        // stuck, stop it too. When no core has started, killing the guard closes the startup pipe.
        if core.is_none() || !launcher.exited_within(200).unwrap_or(false) {
            launcher.kill().context("stop the guarded Deskflow launcher")?;
        }
        eprintln!("aresos-input-portal --release: stopped guarded Deskflow");
    }
    Ok(())
}

/// The `Pid:` of a pidfd's fdinfo: absent, or -1 once the process has ended,
/// or 0 when it lives in a PID namespace this process can't see.
fn pid_in_fdinfo(fdinfo: &str) -> Option<i32> {
    let pid: i32 = fdinfo.lines().find_map(|line| line.strip_prefix("Pid:"))?.trim().parse().ok()?;
    (pid > 0).then_some(pid)
}

/// The four user IDs (real, effective, saved, filesystem) of a `/proc/<pid>/status`.
fn uids_in_status(status: &str) -> Option<[u32; 4]> {
    let line = status.lines().find_map(|line| line.strip_prefix("Uid:"))?;
    let ids: Vec<u32> = line.split_whitespace().map(str::parse).collect::<Result<_, _>>().ok()?;
    ids.try_into().ok()
}

/// `--release`, against the backend that owns `bus_name` on the session bus.
pub async fn run(bus_name: &str, path: &str, interface: &str) -> Result<()> {
    let conn = zbus::Connection::session()
        .await
        .context("failed to connect to the session bus")?;
    let dbus = zbus::fdo::DBusProxy::new(&conn)
        .await
        .context("failed to reach the bus itself")?;
    let name = zbus::names::BusName::try_from(bus_name).context("the backend's bus name")?;
    let Some(owner) = name_owner(&dbus, &name).await? else {
        println!("no backend is running: nothing is captured");
        return Ok(());
    };
    let (pinned, how) = pin(&dbus, &name, &owner).await?;
    eprintln!(
        "aresos-input-portal --release: pinned the backend, pid {}; asking it to release (pinned {how})",
        pinned.pid
    );

    // The question goes to the connection that was pinned, not to the name: a
    // new owner of the name is not the instance this pidfd holds.
    let answer = tokio::time::timeout(
        DEADLINE,
        conn.call_method(Some(owner.as_ref()), path, Some(interface), "ForceRelease", &()),
    )
    .await;
    let why = match answer {
        Ok(Ok(reply)) => match reply.body().deserialize::<String>() {
            Ok(said) => {
                println!("{said}");
                return Ok(());
            }
            Err(err) => format!("its answer could not be read: {err}"),
        },
        Ok(Err(err)) => format!("it answered {err}"),
        Err(_) => format!("no answer within {} s", DEADLINE.as_secs()),
    };
    eprintln!(
        "aresos-input-portal --release: no confirmed release ({why}); killing pid {} through its pidfd",
        pinned.pid
    );
    // Deskflow reconnects on loss of the backend. Stop the core before dropping the grab so a
    // fresh activation cannot immediately take the keyboard and pointer again.
    if pinned.alive() {
        if let Err(err) = stop_guarded_deskflow() {
            eprintln!("aresos-input-portal --release: could not stop guarded Deskflow: {err:#}");
        }
    }
    match pinned.kill()? {
        Killed::Now => println!("killed the backend (pid {}): the compositor drops its grab", pinned.pid),
        Killed::AlreadyGone => println!("the pinned backend (pid {}) had already ended", pinned.pid),
    }
    Ok(())
}

async fn name_owner(
    dbus: &zbus::fdo::DBusProxy<'_>,
    name: &zbus::names::BusName<'_>,
) -> Result<Option<zbus::names::OwnedUniqueName>> {
    match dbus.get_name_owner(name.clone()).await {
        Ok(owner) => Ok(Some(owner)),
        Err(zbus::fdo::Error::NameHasNoOwner(_)) => Ok(None),
        Err(err) => Err(err).context("failed to ask the bus who owns the backend's name"),
    }
}

/// Pin the process behind the connection `owner`, which owns `name`: by the
/// bus's `ProcessFD` where it gives one, otherwise by `pidfd_open` on its PID and
/// a second look that the same connection still owns the name (a connection
/// can't outlive its process, so its PID can't have been taken by another).
/// Then the pinned process must be the installed backend, run by this user.
/// Also says which of the two ways it was pinned.
async fn pin(
    dbus: &zbus::fdo::DBusProxy<'_>,
    name: &zbus::names::BusName<'_>,
    owner: &zbus::names::OwnedUniqueName,
) -> Result<(Pinned, &'static str)> {
    let credentials = dbus
        .get_connection_credentials(owner.as_ref().into())
        .await
        .context("failed to ask the bus about the backend's connection")?;
    let (pinned, how) = match credentials.process_fd() {
        Some(pidfd) => {
            let pinned = Pinned::from_pidfd(pidfd.as_fd().try_clone_to_owned().context("copy the bus's pidfd")?)?;
            if let Some(pid) = credentials.process_id() {
                ensure!(
                    u32::try_from(pinned.pid) == Ok(pid),
                    "the bus's pidfd and process ID disagree"
                );
            }
            (pinned, "by the bus's ProcessFD")
        }
        None => {
            let pid = credentials.process_id().context("the bus gave no process for the backend")?;
            let pinned = Pinned::open(i32::try_from(pid).context("not a process ID")?)?;
            let again = name_owner(dbus, name).await?;
            ensure!(
                again.as_ref() == Some(owner),
                "the backend's bus name changed hands while it was being pinned"
            );
            (pinned, "by pidfd_open on the bus's process ID")
        }
    };
    let uid = rustix::process::getuid().as_raw();
    if let Some(bus_uid) = credentials.unix_user_id() {
        ensure!(bus_uid == uid, "the backend's connection belongs to another user");
    }
    pinned.verify(Path::new(INSTALLED), uid)?;
    Ok((pinned, how))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::{Child, Command};

    fn sleeper() -> Child {
        Command::new("sleep").arg("30").spawn().expect("start sleep")
    }

    #[test]
    fn the_numbers_come_from_proc() {
        assert_eq!(pid_in_fdinfo("pos:\t0\nflags:\t02000002\nmnt_id:\t15\nino:\t1057\nPid:\t4242\nNSpid:\t4242\n"), Some(4242));
        assert_eq!(pid_in_fdinfo("Pid:\t-1\n"), None, "the process has ended");
        assert_eq!(pid_in_fdinfo("Pid:\t0\n"), None, "another PID namespace");
        assert_eq!(pid_in_fdinfo("pos:\t0\n"), None);
        assert_eq!(uids_in_status("Name:\tx\nUid:\t1000\t1000\t1000\t1000\nGid:\t5\t5\t5\t5\n"), Some([1000; 4]));
        assert_eq!(uids_in_status("Uid:\t1000\t0\t1000\t1000\n"), Some([1000, 0, 1000, 1000]));
        assert_eq!(uids_in_status("Uid:\t1000\t1000\n"), None);
        assert_eq!(uids_in_status("Gid:\t1\t1\t1\t1\n"), None);
    }

    #[test]
    fn a_pidfd_from_elsewhere_gives_its_pid() {
        let own = std::process::id() as i32;
        let made_elsewhere = Pinned::open(own).unwrap().pidfd;
        assert_eq!(Pinned::from_pidfd(made_elsewhere).unwrap().pid, own);
    }

    #[test]
    fn only_the_installed_program_of_this_user_passes() {
        let own = Pinned::open(std::process::id() as i32).unwrap();
        let exe = std::env::current_exe().unwrap();
        let uid = rustix::process::getuid().as_raw();
        own.verify(&exe, uid).expect("this test process, as itself");
        assert!(own.verify(Path::new(INSTALLED), uid).is_err(), "another program");
        assert!(own.verify(&exe, uid.wrapping_add(1)).is_err(), "another user");

        // A process that has ended passes nothing, whatever it ran.
        let mut child = sleeper();
        let pinned = Pinned::open(child.id() as i32).unwrap();
        assert!(pinned.alive());
        child.kill().unwrap();
        child.wait().unwrap();
        assert!(!pinned.alive());
        assert!(pinned.verify(Path::new("/usr/bin/sleep"), uid).is_err());
    }

    #[test]
    fn the_kill_reaches_the_pinned_process_and_no_other() {
        // A stuck process that is pinned is killed.
        let mut stuck = sleeper();
        let pinned = Pinned::open(stuck.id() as i32).unwrap();
        assert_eq!(pinned.kill().unwrap(), Killed::Now);
        use std::os::unix::process::ExitStatusExt;
        assert_eq!(stuck.wait().unwrap().signal(), Some(9));

        // The pinned process ends and another starts (it may even get the same
        // PID, or take the bus name): the kill finds the pinned one gone, and
        // the newcomer keeps running.
        let mut first = sleeper();
        let pinned = Pinned::open(first.id() as i32).unwrap();
        first.kill().unwrap();
        first.wait().unwrap();
        let mut newcomer = sleeper();
        assert_eq!(pinned.kill().unwrap(), Killed::AlreadyGone);
        std::thread::sleep(Duration::from_millis(100));
        assert!(newcomer.try_wait().unwrap().is_none(), "the newcomer was not touched");
        newcomer.kill().unwrap();
        newcomer.wait().unwrap();
    }

    #[test]
    fn deskflow_record_must_match_the_current_process_start_and_program() {
        let mut child = sleeper();
        let pid = child.id();
        let stat = std::fs::read_to_string(format!("/proc/{pid}/stat")).unwrap();
        let start = process_start(&stat).unwrap();
        let uid = rustix::process::getuid().as_raw();
        let sleep = |proc: &Path| std::fs::read_link(proc.join("exe")).unwrap() == Path::new("/usr/bin/sleep");
        assert!(deskflow_process(&format!("{pid} {start}"), uid, sleep).is_some());
        assert!(deskflow_process(&format!("{pid} {}", start.wrapping_add(1)), uid, sleep).is_none());
        assert!(deskflow_process(&format!("{pid} {start}"), uid, |_| false).is_none());
        child.kill().unwrap();
        child.wait().unwrap();
    }
}
