//! xdg-desktop-portal InputCapture and Clipboard backend for labwc (AresOS).
//!
//! labwc has no InputCapture portal of its own, so `CreateSession` fails for
//! every client. This process fills that gap, for the applications on its
//! allow-list and for nobody else (`src/trust.rs`, `src/portal.rs`), and only
//! while the owner's sharing switch is on (`src/sharing.rs`).

mod eis_server;
mod portal;
mod release;
mod screens;
mod sharing;
mod trust;
mod wayland;

use anyhow::{Context, Result};
use tracing::{info, warn, Level};
use tracing_subscriber::{filter::Targets, layer::SubscriberExt, util::SubscriberInitExt};

const BUS_NAME: &str = "org.freedesktop.impl.portal.desktop.aresos-input";
const PORTAL_PATH: &str = "/org/freedesktop/portal/desktop";
const CONTROL_PATH: &str = "/org/aresos/InputPortal/Control";
const CONTROL_IFACE: &str = "org.aresos.InputPortal.Control";

/// The one log setting: `error`, `warn`, `info` (the default), `debug` or `trace`.
const LOG_VARIABLE: &str = "ARESOS_INPUT_PORTAL_LOG";

/// How long a stopping backend waits after giving the pointer back, so the
/// compositor gets the release before the connection goes.
pub(crate) const SHUTDOWN_GRACE: std::time::Duration = std::time::Duration::from_millis(150);

/// Variables that make a dependency print every protocol message it handles
/// (key codes, pointer motion, clipboard types) to stderr.
const WIRE_DUMP_VARIABLES: [&str; 2] = ["WAYLAND_DEBUG", "REIS_DEBUG"];

fn main() -> Result<()> {
    // Before anything else, and before any other thread exists: the libraries
    // read these when they connect, and a keystroke must never reach a log.
    for name in WIRE_DUMP_VARIABLES {
        // SAFETY: this is the first statement of `main`; the process has one
        // thread, so nothing else can be reading the environment.
        unsafe { std::env::remove_var(name) };
    }

    let raw_level = std::env::var(LOG_VARIABLE).ok();
    let level = log_level(raw_level.as_deref());
    // This crate logs at the chosen level, and its own messages are written to
    // carry no key, no position and no clipboard content. The libraries stay at
    // warnings whatever is chosen: their debug output describes the messages
    // they carry, and no setting may turn that on.
    tracing_subscriber::registry()
        .with(tracing_subscriber::fmt::layer())
        .with(
            Targets::new()
                .with_default(Level::WARN)
                .with_target(env!("CARGO_CRATE_NAME"), level.unwrap_or(Level::INFO)),
        )
        .init();
    if level.is_none() {
        warn!("ignoring {LOG_VARIABLE}: expected error, warn, info, debug or trace");
    }

    tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .context("failed to start the async runtime")?
        .block_on(run())
}

/// The level `ARESOS_INPUT_PORTAL_LOG` asks for: `info` when it is unset, and
/// `None` when it is set to something that isn't a level. `RUST_LOG` is not read.
fn log_level(raw: Option<&str>) -> Option<Level> {
    let Some(raw) = raw else {
        return Some(Level::INFO);
    };
    match raw.trim().to_ascii_lowercase().as_str() {
        "error" => Some(Level::ERROR),
        "warn" => Some(Level::WARN),
        "info" => Some(Level::INFO),
        "debug" => Some(Level::DEBUG),
        "trace" => Some(Level::TRACE),
        _ => None,
    }
}

async fn run() -> Result<()> {
    // These run against an already-running instance and exit; they exist so a
    // stranded pointer can be recovered over SSH without knowing D-Bus syntax.
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        // The release key: confirmed by the backend, or the backend is killed.
        Some("--release") => release::run(BUS_NAME, CONTROL_PATH, CONTROL_IFACE).await,
        Some("--disarm") => call_control("Disarm", BUS_NAME).await,
        // The sharing switch runs this after turning sharing off. Only a
        // backend that is running has anything to end: none is started for it.
        Some("--revoke") => match running_backend().await? {
            Some(owner) => call_control("Revoke", &owner).await,
            None => {
                println!("no backend is running: nothing to revoke");
                Ok(())
            }
        },
        Some("--status") => call_control("Status", BUS_NAME).await,
        Some(other) => anyhow::bail!(
            "unknown argument {other:?}; expected --release, --disarm, --revoke or --status"
        ),
        None => serve().await,
    }
}

/// The unique bus name of the running backend, if one runs.
async fn running_backend() -> Result<Option<String>> {
    let conn = zbus::Connection::session()
        .await
        .context("failed to connect to the session bus")?;
    let dbus = zbus::fdo::DBusProxy::new(&conn)
        .await
        .context("failed to reach the bus itself")?;
    match dbus.get_name_owner(BUS_NAME.try_into()?).await {
        Ok(owner) => Ok(Some(owner.to_string())),
        Err(zbus::fdo::Error::NameHasNoOwner(_)) => Ok(None),
        Err(err) => Err(err).context("failed to ask the bus who owns the backend's name"),
    }
}

/// Invoke a method on a running instance and print what it says.
async fn call_control(method: &str, destination: &str) -> Result<()> {
    let conn = zbus::Connection::session()
        .await
        .context("failed to connect to the session bus")?;
    let reply: String = conn
        .call_method(Some(destination), CONTROL_PATH, Some(CONTROL_IFACE), method, &())
        .await
        .with_context(|| format!("{method} failed; is aresos-input-portal running?"))?
        .body()
        .deserialize()
        .context("unexpected reply")?;
    println!("{reply}");
    Ok(())
}

async fn serve() -> Result<()> {
    // The keymap is captured from the compositor by the Wayland thread and read
    // back when an EIS keyboard device is created.
    let keymap: eis_server::SharedKeymap = std::sync::Arc::default();
    let idle_timeout = wayland::idle_timeout_from_env();
    let screens = screens::SharedScreens::new();
    // Closed until a read of the sharing switch says on.
    let gate = sharing::Gate::default();

    // Fails here, with a clear message, when there is no compositor or it lacks
    // a protocol the backend needs.
    let (wayland, wayland_events) = wayland::spawn(keymap.clone(), idle_timeout, screens.clone(), gate.clone())
        .context("failed to start the Wayland barrier thread")?;
    for screen in &screens.current().screens {
        info!(
            "screen {}: {}x{} at ({}, {}) scale {} {:?}",
            screen.name,
            screen.zone.width,
            screen.zone.height,
            screen.zone.x,
            screen.zone.y,
            screen.scale,
            screen.transform
        );
    }

    let (state, eis_closed) = portal::State::new(std::sync::Arc::new(wayland), screens, keymap, gate);
    let conn = zbus::connection::Builder::session()
        .context("failed to connect to the session bus")?
        .serve_at(PORTAL_PATH, portal::InputCapture::new(state.clone()))
        .context("failed to export the InputCapture interface")?
        .serve_at(PORTAL_PATH, portal::Clipboard::new(state.clone()))
        .context("failed to export the Clipboard interface")?
        .serve_at(CONTROL_PATH, portal::Control::new(state.clone()))
        .context("failed to export the control interface")?
        .build()
        .await
        .context("failed to start the D-Bus service")?;

    // The state needs the connection to ask who the frontend is and to emit
    // signals, and the watch on the frontend has to be in place before the
    // first session can exist. So both come before the bus name: until the name
    // is ours, no frontend can reach the interfaces.
    state.set_connection(conn.clone());
    let frontend_changes = zbus::fdo::DBusProxy::new(&conn)
        .await
        .context("failed to reach the bus itself")?
        .receive_name_owner_changed_with_args(&[(0, trust::FRONTEND_NAME)])
        .await
        .context("failed to watch the portal frontend's bus name")?;
    tokio::spawn(portal::watch_frontend(state.clone(), frontend_changes));
    tokio::spawn(portal::pump_wayland_events(state.clone(), wayland_events));
    tokio::spawn(portal::handle_eis_closed(state.clone(), eis_closed));
    tokio::spawn(portal::watch_switch(state.clone()));

    // Not queued behind another owner: a second backend has no business waiting.
    let reply = conn
        .request_name_with_flags(BUS_NAME, zbus::fdo::RequestNameFlags::DoNotQueue.into())
        .await
        .context("failed to claim the backend bus name")?;
    anyhow::ensure!(
        matches!(
            reply,
            zbus::fdo::RequestNameReply::PrimaryOwner | zbus::fdo::RequestNameReply::AlreadyOwner
        ),
        "the backend bus name is taken"
    );

    if idle_timeout == std::time::Duration::MAX {
        info!("{BUS_NAME} ready at {PORTAL_PATH}; idle watchdog disabled");
    } else {
        info!(
            "{BUS_NAME} ready at {PORTAL_PATH}; capture auto-releases after {}s idle",
            idle_timeout.as_secs()
        );
    }

    let lost = tokio::select! {
        result = tokio::signal::ctrl_c() => {
            result.context("failed to wait for shutdown signal")?;
            None
        }
        // Every session is closed by now.
        why = state.wait_for_stop() => Some(why),
    };
    info!("shutting down");

    // Never exit leaving the pointer locked.
    state.release_everything();
    tokio::time::sleep(SHUTDOWN_GRACE).await;
    // Without its bus the backend can serve nobody and nobody can stop a
    // capture; without its Wayland connection it can place no barrier. Either
    // way it ends, and the next call from a frontend starts a fresh one.
    if let Some(why) = lost {
        anyhow::bail!("{why}");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_log_level_is_one_plain_word() {
        assert_eq!(log_level(None), Some(Level::INFO));
        assert_eq!(log_level(Some("trace")), Some(Level::TRACE));
        assert_eq!(log_level(Some(" Debug\n")), Some(Level::DEBUG));
        assert_eq!(log_level(Some("WARN")), Some(Level::WARN));
        assert_eq!(log_level(Some("error")), Some(Level::ERROR));
        assert_eq!(log_level(Some("info")), Some(Level::INFO));
        // No filter syntax: nothing here can name a library and turn its
        // debug output on.
        for not_a_level in ["", "zbus=trace", "trace,reis=trace", "aresos_input_portal=trace", "5"] {
            assert_eq!(log_level(Some(not_a_level)), None, "{not_a_level:?}");
        }
    }
}
