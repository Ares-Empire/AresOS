#!/usr/bin/python3 -I
"""Package 316's harness, inside its container: the tests of briefs/316-input-portal.md, "Tests", and the
switch and way-out checks of briefs/321-deskflow-image.md, "What to build" 1 (test8, test9), and the shortcuts
gate of its "What to build" 6 (test10).

in-container.sh starts this once the container has proved it is cut off from the host. It starts a private
session bus and a private headless labwc with two outputs, a full-screen probe window, a virtual pointer and
a virtual keyboard, and then plays the portal frontend against the backend: one bus connection owns
org.freedesktop.portal.Desktop and makes the calls in the real order, a second one (the stranger) makes the
calls that must be refused and listens for signals it must never get, and eis-receiver plays Deskflow's end
of each EIS connection.

Every check prints one PASS or FAIL line; all of them, with the logs, land in /evidence. Exit 0 when every
check passed, 1 when one failed, 2 when the setup itself could not be used (nothing was tested). Every wait
has a time limit, and at the end only the processes started here are stopped.
"""
import ctypes
import json
import os
import re
import select
import signal
import socket
import stat
import subprocess
import sys
import time
import traceback

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

EV = "/evidence"
RUNTIME = os.environ["XDG_RUNTIME_DIR"]
BUS_PATH = f"{RUNTIME}/bus"
BUS_ADDR = f"unix:path={BUS_PATH}"
DISPLAY_NAME = "wayland-0"
BACKEND = "/usr/libexec/aresos-input-portal"
WLH = "/opt/harness/bin/wl-harness"
RECEIVER = "/opt/harness/bin/eis-receiver"
NAME = "org.freedesktop.impl.portal.desktop.aresos-input"
FRONTEND_NAME = "org.freedesktop.portal.Desktop"
PORTAL = "/org/freedesktop/portal/desktop"
IC = "org.freedesktop.impl.portal.InputCapture"
CLIP = "org.freedesktop.impl.portal.Clipboard"
SESSION = "org.freedesktop.impl.portal.Session"
APP = "org.aresos.harness"
DENIED = "org.freedesktop.DBus.Error.AccessDenied"
# The sharing switch, which in-container.sh installs on. Only test8 changes it, and puts it back.
SWITCH = "/etc/aresos/input-portal/sharing"
V = GLib.Variant

# The only environment any process of the harness gets: nothing is inherited.
ENV = {
    "PATH": "/usr/bin:/usr/sbin",
    "LANG": "C.UTF-8",
    "NO_COLOR": "1",
    "DBUS_SESSION_BUS_ADDRESS": BUS_ADDR,
    **{k: os.environ[k] for k in ("HOME", "XDG_RUNTIME_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME")},
}
CLIENT_ENV = {**ENV, "WAYLAND_DISPLAY": DISPLAY_NAME}

results = []
procs = {}
buses = []
ZONES = []


def check(test, what, ok, detail=""):
    ok = bool(ok)
    line = f"{'PASS' if ok else 'FAIL'} {test} {what}" + (f" [{detail}]" if detail and not ok else "")
    print(line, flush=True)
    results.append(line)
    return ok


def info(text):
    print(f"INFO {text}", flush=True)
    results.append(f"INFO {text}")


def pump(duration=0.03):
    """Let the bus connections deliver their signals."""
    context = GLib.MainContext.default()
    end = time.monotonic() + duration
    while True:
        while context.pending():
            context.iteration(False)
        if time.monotonic() >= end:
            return
        time.sleep(0.01)


def wait_for(predicate, timeout):
    end = time.monotonic() + timeout
    while True:
        pump()
        value = predicate()
        if value or time.monotonic() >= end:
            return value


# ---- processes ------------------------------------------------------------------------------------------------


def spawn(name, argv, env, **popen):
    if "stdout" not in popen:
        popen["stdout"] = open(f"{EV}/{name}.log", "ab", buffering=0)
        popen["stderr"] = subprocess.STDOUT
    popen.setdefault("stdin", subprocess.DEVNULL)
    process = subprocess.Popen(argv, env=dict(env), **popen)
    procs[name] = process
    return process


def stop(name, sig=signal.SIGTERM, timeout=5):
    """Stop one process this harness started. Returns its exit code."""
    process = procs.pop(name, None)
    if process is None:
        return None
    if process.poll() is None:
        process.send_signal(sig)
        try:
            process.wait(timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(5)
    return process.returncode


def tool(argv, timeout=10):
    return subprocess.run(argv, env=CLIENT_ENV, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)


def log_of(name):
    try:
        with open(f"{EV}/{name}.log", errors="replace") as handle:
            return handle.read()
    except FileNotFoundError:
        return ""


def lines_of(name):
    return log_of(name).splitlines()


def start_bus():
    if os.path.exists(BUS_PATH):
        os.unlink(BUS_PATH)
    spawn("dbus-daemon", ["dbus-daemon", "--session", "--nofork", "--nopidfile", f"--address={BUS_ADDR}"], ENV)
    if not wait_for(lambda: os.path.exists(BUS_PATH), 5):
        raise RuntimeError("the private bus did not start")


class Reply:
    def __init__(self, value=None, fds=None, error=None):
        self.value = value.unpack() if value is not None else None
        self.fds = fds
        self.error = Gio.DBusError.get_remote_error(error) if error is not None else None
        self.message = error.message if error is not None else ""
        self.ok = error is None
        self.nfds = fds.get_length() if fds is not None else 0

    def fd(self):
        """The reply's file descriptor, taken out of the message: no second copy stays open in this process,
        so the other end sees end-of-file when the test closes it."""
        return self.fds.steal_fds()[self.value[0]]


class Bus:
    """One connection to the private bus, with every signal it is sent."""

    def __init__(self, label):
        self.label = label
        self.signals = []
        flags = Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
        self.conn = Gio.DBusConnection.new_for_address_sync(BUS_ADDR, flags, None, None)
        self.conn.set_exit_on_close(False)
        self.unique = self.conn.get_unique_name()
        # No filter at all: the match rule is type='signal', everything the bus is willing to deliver.
        self.conn.signal_subscribe(None, None, None, None, None, Gio.DBusSignalFlags.NONE, self._signal)
        buses.append(self)

    def _signal(self, _conn, sender, path, iface, member, params, *_):
        # t: when the harness saw it, so a deadline is measured from the far side.
        self.signals.append({"sender": sender, "path": path, "iface": iface, "member": member, "args": params.unpack(), "t": time.monotonic()})

    def call(self, path, iface, method, params=None, dest=NAME, timeout=5000, activate=False):
        flags = Gio.DBusCallFlags.NONE if activate else Gio.DBusCallFlags.NO_AUTO_START
        try:
            value, fds = self.conn.call_with_unix_fd_list_sync(
                dest, path, iface, method, params, None, flags, timeout, None, None
            )
            return Reply(value, fds)
        except GLib.Error as error:
            return Reply(error=error)

    def call_async(self, path, iface, method, params=None, dest=NAME, timeout=5000):
        """Send a call and return at once; the reply lands in the returned dict's "reply" while pump() runs."""
        box = {}

        def done(conn, result, *_):
            try:
                value, fds = conn.call_with_unix_fd_list_finish(result)
                box["reply"] = Reply(value, fds)
            except GLib.Error as error:
                box["reply"] = Reply(error=error)

        self.conn.call_with_unix_fd_list(dest, path, iface, method, params, None, Gio.DBusCallFlags.NO_AUTO_START, timeout, None, None, done, None)
        return box

    def own_frontend(self):
        reply = self.call("/org/freedesktop/DBus", "org.freedesktop.DBus", "RequestName", V("(su)", (FRONTEND_NAME, 4)), dest="org.freedesktop.DBus")
        if not reply.ok or reply.value[0] != 1:
            raise RuntimeError(f"could not own {FRONTEND_NAME}: {reply.message}")

    def has_owner(self, name):
        reply = self.call("/org/freedesktop/DBus", "org.freedesktop.DBus", "NameHasOwner", V("(s)", (name,)), dest="org.freedesktop.DBus")
        return reply.ok and reply.value[0]

    def backend_pid(self):
        reply = self.call("/org/freedesktop/DBus", "org.freedesktop.DBus", "GetConnectionUnixProcessID",
                          V("(s)", (NAME,)), dest="org.freedesktop.DBus")
        return reply.value[0] if reply.ok else None

    def sig(self, member, session=None, start=0, predicate=None):
        """Portal signals since `start`, for one session path when given."""
        found = []
        for signal_ in self.signals[start:]:
            if signal_["member"] != member or not signal_["iface"].startswith("org.freedesktop.impl.portal"):
                continue
            about = signal_["args"][0] if signal_["args"] else signal_["path"]
            if session is not None and about != session:
                continue
            if predicate is None or predicate(signal_):
                found.append(signal_)
        return found

    def close(self):
        self.conn.close_sync(None)


class VInput:
    """wl-harness input: a virtual pointer or keyboard that lives until it is stopped."""

    def __init__(self, kind):
        self.kind = kind
        self.name = f"vinput-{kind}"
        self.process = None
        self.start()

    def start(self):
        self.process = spawn(
            self.name, [WLH, "input", self.kind], CLIENT_ENV,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(f"{EV}/{self.name}.log", "ab"), bufsize=0,
        )
        self._expect("READY")

    def _expect(self, word):
        ready, _, _ = select.select([self.process.stdout], [], [], 5)
        line = self.process.stdout.readline().decode().strip() if ready else "(nothing within 5 s)"
        if line != word:
            raise RuntimeError(f"{self.name}: expected {word}, got {line!r}")

    def cmd(self, line):
        self.process.stdin.write((line + "\n").encode())
        self._expect("OK")

    def stop(self):
        stop(self.name)


class Session:
    """One portal session, driven the way xdg-desktop-portal drives the backend."""

    count = 0

    def __init__(self, fe, name, caps=3, clipboard=True, app_id=APP):
        Session.count += 1
        self.fe, self.name, self.caps, self.clipboard, self.app_id = fe, name, caps, clipboard, app_id
        self.path = f"/org/freedesktop/portal/desktop/session/harness/{name.replace('-', '_')}"
        self.request = f"/org/freedesktop/portal/desktop/request/harness/r{Session.count}"
        self.receiver = f"eis-{Session.count:02d}-{name}"

    def call(self, iface, method, params, path=PORTAL):
        return self.fe.call(path, iface, method, params)

    def must(self, iface, method, params, path=PORTAL):
        reply = self.call(iface, method, params, path)
        if not reply.ok:
            raise RuntimeError(f"{method} for {self.name}: {reply.error} {reply.message}")
        return reply

    def create(self):
        return self.call(IC, "CreateSession2", V("(osa{sv})", (self.path, self.app_id, {})))

    def connect_eis(self):
        reply = self.must(IC, "ConnectToEIS", V("(osa{sv})", (self.path, self.app_id, {})))
        fd = reply.fd()
        spawn(self.receiver, [RECEIVER, str(fd)], ENV, pass_fds=[fd])
        # The receiver holds the only copy from here on: when it dies, the connection dies.
        os.close(fd)
        if not wait_for(lambda: any(line.startswith("DEVICE_RESUMED") for line in self.eis()), 5):
            raise RuntimeError(f"the EIS receiver of {self.name} got no device: {self.eis()}")

    def zones(self):
        reply = self.must(IC, "GetZones", V("(oosa{sv})", (self.request, self.path, self.app_id, {})))
        return [tuple(zone) for zone in reply.value[1]["zones"]], reply.value[1]["zone_set"]

    def set_barriers(self, barriers, zone_set):
        wire = [{"barrier_id": V("u", barrier_id), "position": V("(iiii)", position)} for barrier_id, position in barriers.items()]
        reply = self.must(IC, "SetPointerBarriers", V("(oosa{sv}aa{sv}u)", (self.request, self.path, self.app_id, {}, wire, zone_set)))
        return sorted(reply.value[1]["failed_barriers"])

    def enable(self):
        return self.must(IC, "Enable", V("(osa{sv})", (self.path, self.app_id, {})))

    def release(self, cursor=None):
        options = {"cursor_position": V("(dd)", cursor)} if cursor else {}
        return self.must(IC, "Release", V("(osa{sv})", (self.path, self.app_id, options)))

    def open(self, armed=True):
        """The real order: CreateSession2, RequestClipboard, Start, ConnectToEIS, the receiver's devices,
        GetZones, SetPointerBarriers, Enable. `armed` sets barrier 1 on the left outer edge and enables."""
        reply = self.create()
        if not reply.ok:
            raise RuntimeError(f"CreateSession2 for {self.name}: {reply.error} {reply.message}")
        if self.clipboard:
            self.must(CLIP, "RequestClipboard", V("(oa{sv})", (self.path, {})))
        started = self.must(IC, "Start", V("(oossa{sv})", (self.request, self.path, self.app_id, "", {"capabilities": V("u", self.caps)})))
        self.granted = started.value[1]
        self.connect_eis()
        if armed:
            zones, zone_set = self.zones()
            failed = self.set_barriers({1: edges(zones)["left"]}, zone_set)
            if failed:
                raise RuntimeError(f"the left edge was refused for {self.name}")
            self.enable()
        return self

    def eis(self):
        return lines_of(self.receiver)

    def regions(self):
        """The regions of the pointer device as the receiver has it now."""
        added = [line for line in self.eis() if line.startswith("DEVICE_ADDED") and " pointer=1" in line]
        if not added:
            return None
        return [tuple(int(n) for n in re.split("[,x]", field[7:])) for field in added[-1].split() if field.startswith("region=")]

    def kill_receiver(self):
        stop(self.receiver, signal.SIGKILL)

    def close(self):
        return self.fe.call(self.path, SESSION, "Close")

    def shut(self):
        self.close()
        stop(self.receiver)


# ---- the screens, the pointer and the probe window ---------------------------------------------------------------


def randr_outputs():
    """The enabled outputs as wlr-randr reports them: name -> (width, height, x, y) in logical pixels."""
    report = tool(["wlr-randr", "--json"])
    outputs = {}
    for output in json.loads(report.stdout):
        if not output["enabled"]:
            continue
        mode = next(m for m in output["modes"] if m["current"])
        width, height = mode["width"], mode["height"]
        if "90" in output["transform"] or "270" in output["transform"]:
            width, height = height, width
        outputs[output["name"]] = (round(width / output["scale"]), round(height / output["scale"]), output["position"]["x"], output["position"]["y"])
    return outputs


def randr_zones():
    return list(randr_outputs().values())


def box(zones):
    """The layout's bounding box: left, top, width, height."""
    left, top = min(x for w, h, x, y in zones), min(y for w, h, x, y in zones)
    return left, top, max(x + w for w, h, x, y in zones) - left, max(y + h for w, h, x, y in zones) - top


def region_of(zones):
    """What the backend tells EIS for these zones: the bounding box's size, at (0, 0)."""
    return [(0, 0, *box(zones)[2:])]


def leftmost(zones):
    return min(zones, key=lambda zone: zone[2])


def rightmost(zones):
    return max(zones, key=lambda zone: zone[2] + zone[0])


def edges(zones):
    """Barrier positions (x1, y1, x2, y2) as the portal counts them: ends inclusive, the right and bottom
    edges one past the last pixel."""
    lw, lh, lx, ly = leftmost(zones)
    rw, rh, rx, ry = rightmost(zones)
    return {
        "left": (lx, ly, lx, ly + lh - 1),
        "right": (rx + rw, ry, rx + rw, ry + rh - 1),
        "top-right": (rx, ry, rx + rw - 1, ry),
        "bottom-left": (lx, ly + lh, lx + lw - 1, ly + lh),
        "inner": (lx + lw, ly, lx + lw, ly + lh - 1),
    }


def goto(x, y):
    """Put the pointer at a layout position (wlroots spreads an absolute position over the layout's box)."""
    left, top, width, height = box(ZONES)
    vptr.cmd(f"abs {x - left} {y - top} {width} {height}")


def approach(edge="left", along=None):
    """Go near an outer edge. Returns the one relative move that then pushes the pointer through it."""
    lw, lh, lx, ly = leftmost(ZONES)
    rw, rh, rx, ry = rightmost(ZONES)
    if edge == "left":
        goto(lx + 200, along if along is not None else ly + lh // 2)
        return "rel -400 0"
    if edge == "right":
        goto(rx + rw - 100, along if along is not None else ry + rh // 2)
        return "rel 300 0"
    if edge == "top-right":
        goto(rx + rw // 2, ry + 100)
        return "rel 0 -300"
    goto(lx + lw // 2, ly + lh - 100)
    return "rel 0 300"


def push(edge="left", along=None):
    """Go near an outer edge and push the pointer through it."""
    vptr.cmd(approach(edge, along))


def window():
    return lines_of("window")


def window_gets(action, wanted):
    seen = len(window())
    action()
    return bool(wait_for(lambda: any(line.startswith(wanted) for line in window()[seen:]), 2))


def local_motion():
    """The pointer is free: moved over the probe window, the window sees it move."""
    def move():
        # The window fills the leftmost output, and stays there: only the right one is ever changed.
        width, height, x, y = leftmost(ZONES)
        goto(x + width // 2, y + height // 2)
        vptr.cmd("rel 9 9")
    return window_gets(move, "MOTION")


def local_button():
    def click():
        vptr.cmd("btn 272 1")
        vptr.cmd("btn 272 0")
    return window_gets(click, "BUTTON 272 1")


def local_key():
    def tap():
        vkbd.cmd("key 57 1")
        vkbd.cmd("key 57 0")
    return window_gets(tap, "KEY 57 1")


def burst():
    """Synthetic input for a capture: motion, a button, the wheel and two keys."""
    for _ in range(3):
        vptr.cmd("rel -7 3")
    vptr.cmd("btn 272 1")
    vptr.cmd("btn 272 0")
    vptr.cmd("axis 1")
    for code in (30, 48):
        vkbd.cmd(f"key {code} 1")
        vkbd.cmd(f"key {code} 0")


BURST = ["MOTION -7.00 3.00", "BUTTON 272 1", "BUTTON 272 0", "KEY 30 1", "KEY 30 0", "KEY 48 1", "KEY 48 0"]


def capture(session, edge="left", along=None, timeout=3, shove=None):
    """Cross the session's barrier. Returns the Activated signal's options, or None. `shove` is the last
    move when the pointer has been brought near the edge already."""
    mark = len(session.fe.signals)
    if shove:
        vptr.cmd(shove)
    else:
        push(edge, along)
    got = wait_for(lambda: session.fe.sig("Activated", session.path, mark), timeout)
    return got[0]["args"][1] if got else None


def stays_local(fe, backend, edge="left"):
    """Push through an edge: nobody is activated, the backend takes no grab, the pointer stays free."""
    mark = len(fe.signals)
    grabs = log_of(backend).count("the grab is held")
    push(edge)
    activated = wait_for(lambda: fe.sig("Activated", None, mark), 1.0)
    return not activated and log_of(backend).count("the grab is held") == grabs and local_motion()


backends = 0


def start_backend(admin, extra=None):
    global backends
    backends += 1
    name = f"backend-{backends}"
    spawn(name, [BACKEND], {**CLIENT_ENV, "ARESOS_INPUT_PORTAL_LOG": "debug", **(extra or {})})
    if not wait_for(lambda: admin.has_owner(NAME), 10):
        raise RuntimeError(f"{name} did not take its bus name: {log_of(name)[-600:]}")
    return name


def closed_backend(name):
    """Check that the backend exited on its own after its last session."""
    code = procs[name].wait(timeout=3)
    if code != 0:
        raise RuntimeError(f"{name} did not exit cleanly: {code}, {log_of(name)[-600:]}")
    return stop(name)


def read_fd(fd, timeout=3):
    data = b""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        ready, _, _ = select.select([fd], [], [], 0.2)
        if ready:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            data += chunk
    os.close(fd)
    return data


def copy(text, mime=None):
    argv = ["wl-copy"] + (["--type", mime] if mime else []) + [text]
    subprocess.run(argv, env=CLIENT_ENV, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)


def paste_through(owner, fe, text, mime=None, thief=None):
    """A local paste (wl-paste) of a selection the session `owner` claimed: answer the transfer with `text`.
    Returns what wl-paste printed, the transfer signals, and the reply `thief` got for the same serial."""
    mark = len(fe.signals)
    paster = subprocess.Popen(
        ["wl-paste", "--no-newline"] + (["--type", mime] if mime else []),
        env=CLIENT_ENV, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    transfers = wait_for(lambda: fe.sig("SelectionTransfer", None, mark), 3)
    stolen = None
    if transfers:
        serial = transfers[0]["args"][2]
        if thief is not None:
            stolen = thief.call(CLIP, "SelectionWrite", V("(ou)", (thief.path, serial)))
        write = owner.call(CLIP, "SelectionWrite", V("(ou)", (owner.path, serial)))
        if write.ok:
            fd = write.fd()
            os.write(fd, text.encode())
            os.close(fd)
            owner.call(CLIP, "SelectionWriteDone", V("(oub)", (owner.path, serial, True)))
    try:
        pasted = paster.communicate(timeout=5)[0].decode()
    except subprocess.TimeoutExpired:
        paster.kill()
        pasted = "(wl-paste got nothing within 5 s)"
    return pasted, transfers or [], stolen


# ---- the tests -----------------------------------------------------------------------------------------------------


def test1_zones(fe, backend):
    global ZONES
    T = "test1"
    randr = randr_zones()
    session = Session(fe, "zones").open(armed=False)
    zones, zone_set = session.zones()
    check(T, "GetZones gives the two outputs as wlr-randr reports them", len(zones) == 2 and sorted(zones) == sorted(randr), f"zones {zones}, wlr-randr {randr}")
    check(T, "the EIS pointer's region covers exactly those outputs", session.regions() == region_of(zones), f"{session.regions()} for {zones}")
    edge = edges(zones)
    failed = session.set_barriers({1: edge["left"], 2: edge["right"], 3: edge["top-right"], 4: edge["bottom-left"], 9: edge["inner"]}, zone_set)
    check(T, "barriers on four outer edges are accepted, the one between the two outputs is refused", failed == [9], f"failed {failed}")
    session.enable()
    check(T, "four barrier surfaces are placed", wait_for(lambda: "armed 4 barrier surface(s)" in log_of(backend), 2))
    _, _, width, height = box(zones)
    on_edge = {
        "left": lambda p: p[0] < 1.5,
        "right": lambda p: p[0] > width - 1.5,
        "top-right": lambda p: p[1] < 1.5 and p[0] >= leftmost(zones)[0],
        "bottom-left": lambda p: p[1] > height - 1.5 and p[0] < leftmost(zones)[0],
    }
    for barrier_id, name in ((1, "left"), (2, "right"), (3, "top-right"), (4, "bottom-left")):
        activated = capture(session, name)
        check(T, f"the {name} edge's surface is where the output's edge is: crossing it activates barrier {barrier_id} there",
              activated and activated["barrier_id"] == barrier_id and on_edge[name](activated["cursor_position"]), f"{activated}")
        session.release()
        pump(0.2)

    # An output changes: scale 2 halves the right output's logical size. (The probe window is on the left one.)
    right = max(randr_outputs().items(), key=lambda item: item[1][2] + item[1][0])[0]
    mark, seen = len(fe.signals), len(session.eis())
    tool(["wlr-randr", "--output", right, "--scale", "2"])
    changed = wait_for(lambda: fe.sig("ZonesChanged", session.path, mark), 5)
    randr2 = randr_zones()
    zones2, zone_set2 = session.zones()
    check(T, "changing an output brings ZonesChanged, and GetZones follows wlr-randr with a new zone set",
          changed and sorted(zones2) == sorted(randr2) and zones2 != zones and zone_set2 != zone_set, f"{zones2} set {zone_set2}, wlr-randr {randr2}")
    ZONES = zones2
    check(T, "barriers for the old zone set are refused", session.set_barriers({1: edge["left"]}, zone_set) == [1])
    check(T, "the old barrier surfaces are gone: the old edge no longer captures", stays_local(fe, backend))
    after = session.eis()[seen:]
    check(T, "EIS: the old devices are removed and the new ones carry the new geometry",
          any(line.startswith("DEVICE_REMOVED") for line in after) and session.regions() == region_of(zones2), f"{session.regions()} for {zones2}: {after}")
    failed = session.set_barriers({5: edges(zones2)["right"]}, zone_set2)
    activated = capture(session, "right")
    check(T, "barriers for the new zone set capture again, without another Enable", failed == [] and activated and activated["barrier_id"] == 5, f"failed {failed}, {activated}")
    session.release()

    mark = len(fe.signals)
    tool(["wlr-randr", "--output", right, "--scale", "1"])
    changed = wait_for(lambda: fe.sig("ZonesChanged", session.path, mark) and sorted(session.zones()[0]) == sorted(zones), 5)
    check(T, "changing it back brings ZonesChanged and the first zones again", changed, f"{session.zones()}")
    ZONES = session.zones()[0]
    session.shut()


def test1_output_off(fe, admin):
    """The last part of test 1, late in the run: the right output stays off from here on (see
    control_output_cycle for why it is not switched on again)."""
    global ZONES
    T = "test1"
    backend = start_backend(admin)
    session = Session(fe, "output-off").open()
    zones, zone_set = session.zones()
    right = max(randr_outputs().items(), key=lambda item: item[1][2] + item[1][0])[0]
    mark = len(fe.signals)
    tool(["wlr-randr", "--output", right, "--off"])
    changed = wait_for(lambda: fe.sig("ZonesChanged", session.path, mark), 5)
    randr = randr_zones()
    zones2, zone_set2 = session.zones()
    check(T, "disabling an output brings ZonesChanged and leaves one zone, as wlr-randr reports it", changed and len(zones2) == 1 and zones2 == randr and zone_set2 != zone_set, f"{zones2}, wlr-randr {randr}")
    ZONES = zones2
    check(T, "barriers for the zone set with two outputs are refused", session.set_barriers({1: edges(zones)["left"]}, zone_set) == [1])
    check(T, "EIS has the one output's geometry", wait_for(lambda: session.regions() == region_of(zones2), 2), f"{session.regions()} for {zones2}")
    failed = session.set_barriers({6: edges(zones2)["right"]}, zone_set2)
    activated = capture(session, "right")
    check(T, "the edge that faced the disabled output is an outer edge now: its barrier is accepted and captures", failed == [] and activated and activated["barrier_id"] == 6, f"failed {failed}, {activated}")
    session.release()
    session.shut()
    stop(backend, signal.SIGINT)


def control_output_cycle():
    """Not a test of the backend's rules, and it decides nothing about the run's result. The first run of this
    harness switched a headless output off and on again and labwc aborted (wlroots: head_send_state:
    Assertion `found' failed). This shows when: a fresh labwc each time, with nobody else on
    zwlr_output_manager_v1, with a client that only listens there, and with the backend."""
    def fresh_labwc():
        stop("labwc")
        for stale in (f"{RUNTIME}/{DISPLAY_NAME}", f"{RUNTIME}/{DISPLAY_NAME}.lock"):
            if os.path.exists(stale):
                os.unlink(stale)
        start_labwc()
        pump(0.5)

    def cycle():
        right = max(randr_outputs().items(), key=lambda item: item[1][2] + item[1][0])[0]
        for number, step in enumerate(("--off", "--on", "--off", "--on"), 1):
            tool(["wlr-randr", "--output", right, step])
            pump(0.7)
            if procs["labwc"].poll() is not None:
                return f"labwc aborts at step {number} ({step}): {(lines_of('labwc') or ['(no message)'])[-1]}"
        return "labwc keeps running"

    fresh_labwc()
    info(f"control: nobody else on zwlr_output_manager_v1; wlr-randr switches an output off, on, off, on: {cycle()}")
    fresh_labwc()
    spawn("output-listener", [WLH, "outputs"], CLIENT_ENV)
    pump(0.5)
    info(f"control: a client that only listens on zwlr_output_manager_v1 is connected; off, on, off, on: {cycle()}")
    stop("output-listener")
    fresh_labwc()
    start_bus()
    backend = start_backend(Bus("stranger-3"))
    # The backend binds the output manager only while a session needs its worker.
    frontend = Bus("frontend-control")
    frontend.own_frontend()
    session = Session(frontend, "control").open(armed=False)
    bound = wayland_connections(procs[backend].pid)
    info(f"control: the backend is connected ({bound} Wayland connection, a session open); off, on, off, on: {cycle()}; "
         f"the backend saw {log_of(backend).count('retired a mode')} mode(s) and {log_of(backend).count('retired a head')} head(s) retired")
    stop(session.receiver)
    stop(backend, signal.SIGINT)


def test2_crossing(fe, backend):
    T = "test2"
    session = Session(fe, "crossing").open()
    check(T, "before the capture the local window receives motion, a button and a key", local_motion() and local_button() and local_key())
    # Near the edge first (the window sees that move), so that everything from here on is the crossing.
    shove = approach("left")
    pump(0.3)
    seen_window, seen_eis, seen_log = len(window()), len(session.eis()), len(log_of(backend))
    activated = capture(session, shove=shove)
    if not check(T, "crossing the barrier: Activated arrives", activated, log_of(backend)[seen_log:][-1500:]):
        session.shut()
        return
    log = log_of(backend)[seen_log:]
    asked, locked, focused, held = (log.find(text) for text in (
        "asking the compositor for the grab", "the compositor granted the pointer lock",
        "the barrier's surface has keyboard focus", "the grab is held"))
    check(T, "labwc granted the pointer lock and the keyboard focus before Activated was sent (REVIEW-1, finding 3)",
          0 <= asked < locked < held and asked < focused < held, f"offsets {asked} {locked} {focused} {held}")
    burst()
    arrived = wait_for(lambda: all(line in session.eis()[seen_eis:] for line in BURST) and any(line.startswith("SCROLL") for line in session.eis()[seen_eis:]), 3)
    eis = session.eis()[seen_eis:]
    check(T, "EIS emulation starts with the activation's number", any(line.startswith("START") and line.endswith(f"sequence={activated['activation_id']}") for line in eis), f"{eis[:6]}")
    check(T, "motion, a button, scroll and keys arrive over EIS", arrived, f"{eis}")
    pump(0.4)
    leaked = [line for line in window()[seen_window:] if line.split()[0] in ("ENTER", "MOTION", "BUTTON", "AXIS", "KEY")]
    check(T, "the local window receives none of them, from the crossing on", not leaked and "LEAVE" in window()[seen_window:], f"{window()[seen_window:]}")
    session.release()
    check(T, "Release: EIS emulation stops", wait_for(lambda: any(line.startswith("STOP") for line in session.eis()[seen_eis:]), 2))
    check(T, "after the capture the local window receives motion, a button and a key again", local_motion() and local_button() and local_key())
    session.shut()


def test3_ways_out(fe, backend):
    T = "test3"
    session = Session(fe, "ways-out").open()

    activated = capture(session)
    seen = len(session.eis())
    session.release()
    check(T, "Release ends the capture and the pointer moves locally again",
          activated and wait_for(lambda: any(line.startswith("STOP") for line in session.eis()[seen:]), 2) and local_motion() and local_key())

    activated = capture(session)
    mark = len(fe.signals)
    said = tool([BACKEND, "--release"]).stdout.strip()
    ended = wait_for(lambda: fe.sig("Deactivated", session.path, mark), 3)
    check(T, "--release ends the capture (Deactivated with its activation_id) and the pointer moves locally again",
          activated and ended and ended[0]["args"][1]["activation_id"] == activated["activation_id"] and "released 1" in said and local_motion() and local_key(), f"{said!r} {ended}")

    activated = capture(session)
    mark = len(fe.signals)
    said = tool([BACKEND, "--disarm"]).stdout.strip()
    ended = wait_for(lambda: fe.sig("Deactivated", session.path, mark) and fe.sig("Disabled", session.path, mark), 3)
    check(T, "--disarm ends the capture and disarms (Deactivated, Disabled) and the pointer moves locally again",
          activated and ended and "released 1" in said and local_motion() and local_key(), f"{said!r}")
    check(T, "after --disarm a crossing stays local", stays_local(fe, backend))
    session.enable()

    activated = capture(session)
    mark, seen, seen_log = len(fe.signals), len(session.eis()), len(log_of(backend))
    # Super_L, Shift_L, Escape: the real keys, pressed one after the other under the grab.
    for command in ("key 125 1", "key 42 1", "key 1 1", "key 1 0", "key 42 0", "key 125 0"):
        vkbd.cmd(command)
    ended = wait_for(lambda: fe.sig("Deactivated", session.path, mark), 3)
    requested = "ForceRelease requested" in log_of(backend)[seen_log:]
    check(T, "Super+Shift+Escape, pressed through the virtual keyboard while the backend holds the grab, ends the capture",
          activated and ended and requested, f"activated {bool(activated)}, Deactivated {bool(ended)}, labwc ran --release {requested}")
    check(T, "and the pointer and the keyboard are local again", local_motion() and local_key())
    info(f"test3 the chord's keys as the EIS receiver saw them: {[line for line in session.eis()[seen:] if line.startswith('KEY')]}")
    session.shut()


def test3_kill_and_watchdog(fe, admin, backend):
    T = "test3"
    session = Session(fe, "killed").open()
    activated = capture(session)
    stop(backend, signal.SIGKILL)
    check(T, "killing the backend ends the capture: the pointer and the keyboard are local again", activated and local_motion() and local_key())
    stop(session.receiver)

    backend = start_backend(admin, {"ARESOS_INPUT_PORTAL_IDLE_TIMEOUT": "3"})
    session = Session(fe, "idle").open()
    activated = capture(session)
    mark, began = len(fe.signals), time.monotonic()
    ended = wait_for(lambda: fe.sig("Deactivated", session.path, mark), 8)
    took = time.monotonic() - began
    check(T, "the idle watchdog (set to 3 s) ends a capture that carries no input", activated and ended and 2.0 <= took <= 5.0, f"Deactivated {bool(ended)} after {took:.1f} s")
    check(T, "and the pointer and the keyboard are local again", local_motion() and local_key())
    session.shut()
    stop(backend, signal.SIGINT)


def test4_teardown(fe, admin, backend):
    T = "test4"
    session = Session(fe, "closed").open()
    mark = len(fe.signals)
    session.close()
    check(T, "Close: the session is closed and its EIS receiver disconnected",
          wait_for(lambda: fe.sig("Closed", session.path, mark), 3) and wait_for(lambda: "DISCONNECT" in session.eis(), 3), f"{session.eis()[-3:]}")
    check(T, "after Close a crossing stays local", stays_local(fe, backend))
    closed_backend(backend)

    backend = start_backend(admin)
    session = Session(fe, "eis-dies-first").open()
    mark = len(fe.signals)
    session.kill_receiver()
    check(T, "the EIS connection dies before a crossing: the session is closed", wait_for(lambda: fe.sig("Closed", session.path, mark), 3))
    check(T, "and a crossing stays local", stays_local(fe, backend))
    closed_backend(backend)

    backend = start_backend(admin)
    session = Session(fe, "eis-dies-capturing").open()
    activated = capture(session)
    mark = len(fe.signals)
    session.kill_receiver()
    ended = wait_for(lambda: fe.sig("Deactivated", session.path, mark) and fe.sig("Closed", session.path, mark), 3)
    check(T, "the EIS connection dies during a capture: Deactivated, the session is closed, input is local again", activated and ended and local_motion() and local_key())
    check(T, "and a new crossing stays local", stays_local(fe, backend))
    closed_backend(backend)

    backend = start_backend(admin)
    session = Session(fe, "frontend-drops").open()
    fe.close()
    gone = wait_for(lambda: "DISCONNECT" in session.eis(), 3)
    code = closed_backend(backend)
    check(T, "the frontend connection drops: its session is closed and its EIS receiver disconnected", gone and code == 0, f"backend exit {code}")
    stop(session.receiver)
    fe = Bus("frontend-2")
    fe.own_frontend()
    check(T, "and a crossing stays local", stays_local(fe, backend))
    return fe


def test5_clipboard(fe, _backend):
    T = "test5"
    session = Session(fe, "clipboard").open()
    text = "aresos-316 copied on this machine 6f1d"
    mark = len(fe.signals)
    copy(text)
    offered = wait_for(lambda: fe.sig("SelectionOwnerChanged", session.path, mark, lambda s: not s["args"][1].get("session_is_owner")
                                      and any(t.startswith("text/plain") for t in s["args"][1].get("mime_types", []))), 3)
    check(T, "text copied with wl-copy is offered to the session: SelectionOwnerChanged with its MIME types", offered, f"{fe.sig('SelectionOwnerChanged', None, mark)}")
    read = session.call(CLIP, "SelectionRead", V("(os)", (session.path, "text/plain;charset=utf-8")))
    got = read_fd(read.fd()) if read.ok else read.message.encode()
    check(T, "a read through the session's transfer file descriptor gets the text", got == text.encode(), f"{got!r}")

    text = "aresos-316 written by the session 9c2e"
    mark = len(fe.signals)
    session.must(CLIP, "SetSelection", V("(oa{sv})", (session.path, {"mime_types": V("as", ["text/plain;charset=utf-8", "text/plain"])})))
    owns = wait_for(lambda: fe.sig("SelectionOwnerChanged", session.path, mark, lambda s: s["args"][1].get("session_is_owner")), 3)
    pasted, transfers, _ = paste_through(session, fe, text)
    check(T, "a write through the session lands on the selection: wl-paste shows it", owns and transfers and pasted == text, f"owner signal {bool(owns)}, transfers {transfers}, wl-paste {pasted!r}")
    session.shut()


def test6_refusals(fe, stranger, backend):
    T = "test6"
    for app_id, what in (("org.example.unlisted", "an app_id that is not on the allow-list"), ("", "the empty app_id")):
        reply = Session(fe, "refused", app_id=app_id).create()
        check(T, f"{what} is refused, and no file descriptor comes back", reply.error == DENIED and reply.nfds == 0, f"{reply.error} {reply.message}")
    check(T, "neither left a session behind", tool([BACKEND, "--status"]).stdout.strip() == "no sessions")

    first = Session(fe, "first").open()
    path, request, none = first.path, first.request, {}
    theirs = "/org/freedesktop/portal/desktop/session/harness/stranger"
    calls = [
        (PORTAL, IC, "CreateSession2", V("(osa{sv})", (theirs, APP, none))),
        (PORTAL, IC, "CreateSession", V("(oossa{sv})", (request, theirs, APP, "", {"capabilities": V("u", 3)}))),
        (PORTAL, IC, "Start", V("(oossa{sv})", (request, path, APP, "", {"capabilities": V("u", 3)}))),
        (PORTAL, IC, "GetZones", V("(oosa{sv})", (request, path, APP, none))),
        (PORTAL, IC, "SetPointerBarriers", V("(oosa{sv}aa{sv}u)", (request, path, APP, none, [], 1))),
        (PORTAL, IC, "ConnectToEIS", V("(osa{sv})", (path, APP, none))),
        (PORTAL, IC, "Enable", V("(osa{sv})", (path, APP, none))),
        (PORTAL, IC, "Disable", V("(osa{sv})", (path, APP, none))),
        (PORTAL, IC, "Release", V("(osa{sv})", (path, APP, none))),
        (PORTAL, CLIP, "RequestClipboard", V("(oa{sv})", (path, none))),
        (PORTAL, CLIP, "SetSelection", V("(oa{sv})", (path, {"mime_types": V("as", ["text/plain"])}))),
        (PORTAL, CLIP, "SelectionWrite", V("(ou)", (path, 1))),
        (PORTAL, CLIP, "SelectionWriteDone", V("(oub)", (path, 1, True))),
        (PORTAL, CLIP, "SelectionRead", V("(os)", (path, "text/plain"))),
        (path, SESSION, "Close", None),
    ]
    wrong = []
    for object_path, iface, method, params in calls:
        reply = stranger.call(object_path, iface, method, params)
        if reply.error != DENIED or reply.nfds:
            wrong.append((method, reply.error, reply.nfds))
    check(T, f"a bus name that isn't the frontend is refused on all {len(calls)} methods, InputCapture, Clipboard and Session.Close, and gets no file descriptor", not wrong, f"{wrong}")
    activated = capture(first)
    check(T, "the frontend's session is untouched by them and still captures", activated)
    first.release()

    # Two sessions of the frontend, the same barrier ID on the same edge.
    mark = len(fe.signals)
    second = Session(fe, "second").open()
    disarmed = wait_for(lambda: fe.sig("Disabled", first.path, mark), 3)
    seen_first, seen_second, mark = len(first.eis()), len(second.eis()), len(fe.signals)
    push("left")
    activations = wait_for(lambda: fe.sig("Activated", None, mark), 3) or []
    burst()
    wait_for(lambda: "KEY 48 0" in second.eis()[seen_second:], 2)
    pump(0.3)
    reached_first = [line for line in first.eis()[seen_first:] if line.split()[0] in ("START", "MOTION", "BUTTON", "KEY", "SCROLL", "SCROLL_DISCRETE")]
    check(T, "enabling a second session disarms the first (Disabled); a crossing activates the second only, and the first receives no input",
          disarmed and activations and all(s["args"][0] == second.path for s in fe.sig("Activated", None, mark)) and not reached_first
          and all(line in second.eis()[seen_second:] for line in BURST), f"Disabled {bool(disarmed)}, Activated {activations}, first got {reached_first}")
    second.release()

    text = "aresos-316 the second session's clipboard 41ab"
    mark = len(fe.signals)
    second.must(CLIP, "SetSelection", V("(oa{sv})", (second.path, {"mime_types": V("as", ["text/plain;charset=utf-8", "text/plain"])})))
    wait_for(lambda: fe.sig("SelectionOwnerChanged", second.path, mark, lambda s: s["args"][1].get("session_is_owner")), 3)
    pasted, transfers, stolen = paste_through(second, fe, text, thief=first)
    check(T, "a clipboard transfer is announced to the owning session only; the first session's SelectionWrite with its serial is refused with no file descriptor, the owner's works",
          transfers and all(s["args"][0] == second.path for s in transfers) and stolen is not None and not stolen.ok and stolen.nfds == 0 and pasted == text,
          f"transfers {transfers}, the thief got {stolen and (stolen.error, stolen.nfds)}, wl-paste {pasted!r}")
    first.shut()
    second.shut()
    closed_backend(backend)

    # A session that was granted the pointer only; its receiver binds everything.
    backend = start_backend(stranger)
    pointer_only = Session(fe, "pointer-only", caps=2).open()
    seats = [line for line in pointer_only.eis() if line.startswith("SEAT ")]
    devices = [line for line in pointer_only.eis() if line.startswith("DEVICE_ADDED")]
    seen = len(pointer_only.eis())
    activated = capture(pointer_only)
    burst()
    wait_for(lambda: "BUTTON 272 0" in pointer_only.eis()[seen:], 2)
    pump(0.3)
    got = pointer_only.eis()[seen:]
    check(T, "an EIS receiver that binds every capability gets only what Start granted: no keyboard on the seat, no keyboard device, no key",
          pointer_only.granted.get("capabilities") == 2 and seats and all(" keyboard=0" in line for line in seats + devices) and len(devices) == 1
          and activated and "MOTION -7.00 3.00" in got and not [line for line in got if line.startswith("KEY")],
          f"granted {pointer_only.granted}, seat {seats}, devices {devices}, got {got}")
    pointer_only.release()
    pointer_only.shut()
    closed_backend(backend)


def review5_pointer_device(fe, backend):
    """REVIEW-1's finding 5 (a closed layer or a lost pointer capability must be reported) has no trigger of
    its own under labwc: labwc closes a layer surface only with its output, which changes the screens anyway
    (test 1), and it keeps the seat's pointer capability when the last pointer device goes. This shows the
    second, and that a capture then still ends the usual way. The rule itself is unit-tested."""
    global vptr
    T = "review1-finding5"
    session = Session(fe, "pointer-device-gone").open()
    activated = capture(session)
    mark, caps = len(fe.signals), [line for line in window() if line.startswith("SEAT_CAPS")]
    vptr.stop()
    pump(1.0)
    kept = [line for line in window() if line.startswith("SEAT_CAPS")] == caps and not fe.sig("Deactivated", session.path, mark)
    vptr = VInput("pointer")
    info(f"review1-finding5 the only pointer device was removed during a capture: labwc {'kept' if kept else 'changed'} the seat's capabilities ({caps[-1] if caps else 'none seen'})")
    session.release()
    check(T, "with the pointer device gone and back the capture still ends on Release, and input is local again",
          activated and wait_for(lambda: any(line.startswith("STOP") for line in session.eis()), 2) and local_motion() and local_key())
    session.shut()


def test7_logs(fe, stranger, admin):
    T = "test7"
    backend = start_backend(admin, {"ARESOS_INPUT_PORTAL_LOG": "trace", "RUST_LOG": "trace", "WAYLAND_DEBUG": "1", "REIS_DEBUG": "1"})
    errors = []
    session = Session(fe, "logged").open()
    mime, marker = "text/x-aresosmark-51c2", "ARESOSMARK7f3a9c51"
    mark = len(fe.signals)
    copy(f"{marker} copied", mime)
    wait_for(lambda: fe.sig("SelectionOwnerChanged", session.path, mark), 3)
    read = session.call(CLIP, "SelectionRead", V("(os)", (session.path, mime)))
    copied = read_fd(read.fd()) if read.ok else b""
    absent = session.call(CLIP, "SelectionRead", V("(os)", (session.path, "text/x-aresosmark-absent")))
    errors.append(absent.message)
    mark = len(fe.signals)
    session.must(CLIP, "SetSelection", V("(oa{sv})", (session.path, {"mime_types": V("as", [mime])})))
    wait_for(lambda: fe.sig("SelectionOwnerChanged", session.path, mark), 3)
    pasted, _, _ = paste_through(session, fe, f"{marker} written", mime)
    errors.append(session.call(CLIP, "SelectionWrite", V("(ou)", (session.path, 424242))).message)

    seen = len(session.eis())
    activated = capture(session, along=437)
    for command in ("rel -123.25 77.5", "rel -123.25 77.5", "btn 275 1", "btn 275 0", "axis 3"):
        vptr.cmd(command)
    for code in (183, 184, 185):
        vkbd.cmd(f"key {code} 1")
        vkbd.cmd(f"key {code} 0")
    delivered = wait_for(lambda: "KEY 185 0" in session.eis()[seen:] and "MOTION -123.25 77.50" in session.eis()[seen:], 3)
    session.release(cursor=(611.0, 437.0))
    errors.append(stranger.call(PORTAL, IC, "ConnectToEIS", V("(osa{sv})", (session.path, APP, {}))).message)
    errors.append(Session(fe, "refused", app_id="org.example.unlisted").create().message)
    activated_again = capture(session, along=437)
    status = tool([BACKEND, "--status"])
    released = tool([BACKEND, "--release"])
    session.shut()
    code = closed_backend(backend)
    check(T, "the marked run really happened: clipboard read and written, a capture with keys, motion, a button and scroll over EIS",
          copied == f"{marker} copied".encode() and pasted == f"{marker} written" and activated and delivered and activated_again and code == 0,
          f"copied {copied!r}, pasted {pasted!r}, activated {bool(activated)}, delivered {bool(delivered)}, exit {code}")

    log = re.sub(r"\x1b\[[0-9;]*m", "", log_of(backend))
    body = [re.sub(r"^\S+Z\s+", "", line) for line in log.splitlines()]
    levels = {level: sum(1 for line in body if line.startswith(level)) for level in ("TRACE", "DEBUG", "INFO", "WARN", "ERROR")}
    info(f"test7 the verbose log has {len(body)} lines: {levels}")
    check(T, "the verbose log is there, with the backend's debug lines", levels["DEBUG"] > 10 and levels["INFO"] > 5)
    check(T, "WAYLAND_DEBUG and REIS_DEBUG in the backend's environment switch no wire dump on",
          not [line for line in body if re.search(r"wl_keyboard|wl_pointer|zwp_relative_pointer|ei_keyboard|ei_pointer|\bei_\w+@", line)])
    forbidden = {
        "the clipboard marker or its type": r"(?i)aresosmark",
        "a key code": r"\b18[345]\b",
        "the button code": r"\b275\b",
        "a motion value": r"123\.25|77\.5",
        "the crossing's coordinate": r"\b437\b",
        "the release hint": r"\b611\b",
    }
    said = "\n".join(errors + [status.stdout, status.stderr, released.stdout, released.stderr])
    for what, pattern in forbidden.items():
        hits = [line for line in body if re.search(pattern, line)]
        check(T, f"no line of the verbose log carries {what}", not hits, f"{hits[:3]}")
        check(T, f"no error or command output carries {what}", not re.search(pattern, said), said)
    with open(f"{EV}/test7-errors-and-output.txt", "w") as handle:
        handle.write(said + "\n")


def review2_bus_loss(fe, admin):
    T = "review1-finding2"
    backend = start_backend(admin)
    session = Session(fe, "bus-dies-armed").open()
    stop("dbus-daemon", signal.SIGKILL)
    exited = wait_for(lambda: procs[backend].poll() is not None, 5)
    check(T, "the bus dies while a session is armed: the backend closes the session (EIS disconnected) and exits with an error",
          exited and procs[backend].returncode != 0 and wait_for(lambda: "DISCONNECT" in session.eis(), 3), f"exit {procs[backend].returncode}, EIS {session.eis()[-2:]}")
    push("left")
    check(T, "and the next crossing stays local", local_motion() and local_key())
    stop(backend)
    stop(session.receiver)

    start_bus()
    admin = Bus("stranger-2")
    fe = Bus("frontend-3")
    fe.own_frontend()
    backend = start_backend(admin)
    session = Session(fe, "bus-dies-capturing").open()
    activated = capture(session)
    stop("dbus-daemon", signal.SIGKILL)
    exited = wait_for(lambda: procs[backend].poll() is not None, 5)
    check(T, "the bus dies during a capture: the backend gives the input back and exits with an error",
          activated and exited and procs[backend].returncode != 0 and local_motion() and local_key(), f"activated {bool(activated)}, exit {procs[backend].returncode}")
    push("left")
    check(T, "and the next crossing stays local", local_motion() and local_key())
    stop(backend)
    stop(session.receiver)


def review4_signals():
    T = "review1-finding4"
    members = ("Activated", "Deactivated", "Disabled", "ZonesChanged", "SelectionOwnerChanged", "SelectionTransfer", "Closed")
    frontends = [bus for bus in buses if bus.label.startswith("frontend")]
    strangers = [bus for bus in buses if bus.label.startswith("stranger")]
    got = {member: sum(len(bus.sig(member)) for bus in frontends) for member in members}
    leaked = [s for bus in strangers for s in bus.signals if s["iface"].startswith("org.freedesktop.impl.portal")]
    heard = sum(1 for bus in strangers for s in bus.signals if s["member"] == "NameOwnerChanged")
    info(f"review1-finding4 the frontend connections received {got}; the strangers heard {heard} NameOwnerChanged broadcasts")
    check(T, "the frontend received every kind of portal signal", all(got.values()), f"{got}")
    check(T, "a second bus connection, subscribed to every signal on the bus for the whole run, received none of them", heard > 0 and not leaked, f"{leaked[:3]}")


# ---- brief 321: the sharing switch and the way out ------------------------------------------------------------------


def set_switch(content):
    """Write the switch as the image's helper will (one rename; root's, 0644), or remove it (None)."""
    if content is None:
        if os.path.lexists(SWITCH):
            os.unlink(SWITCH)
        return
    new = SWITCH + ".new"
    with open(new, "w") as handle:
        handle.write(content)
    os.chmod(new, 0o644)
    os.replace(new, SWITCH)


def is_input(line):
    return line.split()[:1] in (["MOTION"], ["BUTTON"], ["KEY"], ["SCROLL"], ["SCROLL_DISCRETE"], ["SCROLL_STOP"])


def status_of():
    return tool([BACKEND, "--status"]).stdout.strip()


SYS_PIDFD_GETFD = 438  # the same number on every architecture
libc = ctypes.CDLL(None, use_errno=True)


def wayland_connections(pid):
    """How many of process `pid`'s sockets are connected to labwc's Wayland socket. Read from the outside, not
    from the backend's word: each socket descriptor is copied here with pidfd_getfd(2) and asked for its peer."""
    display = f"{RUNTIME}/{DISPLAY_NAME}"
    count = 0
    pidfd = os.pidfd_open(pid)
    try:
        for name in os.listdir(f"/proc/{pid}/fd"):
            try:
                if not os.readlink(f"/proc/{pid}/fd/{name}").startswith("socket:"):
                    continue
            except OSError:
                continue  # closed meanwhile
            fd = libc.syscall(SYS_PIDFD_GETFD, pidfd, int(name), 0)
            if fd < 0:
                if ctypes.get_errno() == 9:  # EBADF: closed meanwhile
                    continue
                raise OSError(ctypes.get_errno(), f"pidfd_getfd of descriptor {name} of {pid}")
            try:
                sock = socket.socket(fileno=fd)
            except OSError:
                os.close(fd)
                continue
            with sock:  # closes this copy only
                try:
                    if sock.family == socket.AF_UNIX and sock.getpeername() == display:
                        count += 1
                except OSError:
                    pass  # not connected
    finally:
        os.close(pidfd)
    return count


def paste_now():
    """What a local paste gets right now, or why it got nothing."""
    try:
        pasted = tool(["wl-paste", "--no-newline"], timeout=5)
        return pasted.stdout if pasted.returncode == 0 else f"(nothing: exit {pasted.returncode})"
    except subprocess.TimeoutExpired:
        return "(wl-paste got nothing within 5 s)"


def test8_switch(fe, admin):
    T = "test8"
    backend = start_backend(admin)
    pid = procs[backend].pid
    pump(0.3)
    idle_connections = wayland_connections(pid)
    folder = os.path.dirname(SWITCH)
    real = f"{folder}/real-switch"

    def symlinked():
        set_switch(None)
        with open(real, "w") as handle:
            handle.write("on\n")
        os.chmod(real, 0o644)
        os.symlink(real, SWITCH)

    def unlinked():
        for path in (SWITCH, real):
            if os.path.lexists(path):
                os.unlink(path)

    try:
        # Off, in each way the switch can be off: the allow-listed ID is refused.
        for what, make, undo in (
            ("the switch file removed", lambda: set_switch(None), lambda: None),
            ("the switch saying ON", lambda: set_switch("ON\n"), lambda: None),
            ("the switch a symlink to a file that says on", symlinked, unlinked),
            ("the switch's folder writable by everyone", lambda: os.chmod(folder, 0o777), lambda: os.chmod(folder, 0o755)),
        ):
            make()
            reply = Session(fe, "switch-off", app_id=APP).create()
            undo()
            set_switch("on\n")
            check(T, f"with {what}, the listed app_id is refused (sharing is off), and no file descriptor comes back",
                  reply.error == DENIED and "sharing is off" in reply.message and reply.nfds == 0, f"{reply.error} {reply.message}")
        check(T, "none of them left a session behind", status_of() == "no sessions")
        off_connections = wayland_connections(pid)
        check(T, "the backend holds no Wayland connection with the switch on and no session (nothing needs its worker), "
                 "nor while Off after four refused requests", idle_connections == 0 and off_connections == 0,
              f"{idle_connections} with no session, {off_connections} while Off")

        # The switch removed while input is flowing, and nobody calls --revoke.
        session = Session(fe, "off-while-typing").open()
        on_connections = wayland_connections(pid)
        activated = capture(session)
        burst()
        flowing = wait_for(lambda: "KEY 48 0" in session.eis(), 2)
        mark, began = len(fe.signals), time.monotonic()
        set_switch(None)
        at_deadline = None
        while time.monotonic() - began < 2.6:
            vkbd.cmd("key 30 1")
            vkbd.cmd("key 30 0")
            vptr.cmd("rel -3 2")
            pump(0.02)
            if at_deadline is None and time.monotonic() - began >= 2.0:
                at_deadline = len(session.eis())
        pump(0.3)
        closed, ended = fe.sig("Closed", session.path, mark), fe.sig("Deactivated", session.path, mark)
        closed_after = closed[0]["t"] - began if closed else None
        ended_after = ended[0]["t"] - began if ended else None
        late = [line for line in session.eis()[at_deadline or 0:] if is_input(line)]
        info(f"test8 the switch removed during a capture: Deactivated after {ended_after and round(ended_after, 2)} s, Closed after {closed_after and round(closed_after, 2)} s")
        check(T, "the switch file removed while input flows, nobody calls --revoke: within 2 s the capture has ended (Deactivated) and the session is closed",
              activated and flowing and closed and ended and closed_after <= 2.0 and ended_after <= 2.0, f"activated {bool(activated)}, flowing {bool(flowing)}, Deactivated {ended_after}, Closed {closed_after}")
        check(T, "from the 2 s deadline on no event reaches the client, though keys and motion kept coming", at_deadline is not None and not late, f"{late[:5]}")
        check(T, "its EIS receiver is disconnected and the backend's bus name is free", "DISCONNECT" in session.eis() and not admin.has_owner(NAME), f"{session.eis()[-2:]}")
        check(T, "the pointer and the keyboard are local again, and the next crossing stays local", local_motion() and local_key() and stays_local(fe, backend))
        check(T, "the compositor confirmed the end of the capture: the backend exited cleanly", procs[backend].poll() == 0)
        check(T, "an authorized session while On starts one Wayland connection, which closes with the process after Off",
              on_connections == 1 and not os.path.exists(f"/proc/{pid}"), f"{on_connections} while On")
        stop(backend)
        stop(session.receiver)

        # A frontend discovery call while Off activates a fresh, bus-only
        # instance. Use it for the next authorized request while On.
        discovered = fe.call(PORTAL, "org.freedesktop.DBus.Properties", "Get",
                             V("(ss)", (IC, "version")), activate=True)
        fresh_pid = admin.backend_pid()
        check(T, "D-Bus activates a fresh backend for discovery while Off, without a Wayland connection",
              discovered.ok and fresh_pid and fresh_pid != pid and wayland_connections(fresh_pid) == 0,
              f"{discovered.value}, previous pid {pid}, fresh pid {fresh_pid}")

        # The same with a clipboard read in flight: the read is on its way to a backend that is stopped for the
        # moment, and the switch goes off before it gets there.
        set_switch("on\n")
        session = Session(fe, "off-while-reading").open(armed=False)
        again_connections = wayland_connections(fresh_pid)
        mark = len(fe.signals)
        copy("aresos-321 a clipboard read in flight 3d7e")
        offered = wait_for(lambda: fe.sig("SelectionOwnerChanged", session.path, mark), 3)
        os.kill(fresh_pid, signal.SIGSTOP)
        try:
            pending = fe.call_async(PORTAL, CLIP, "SelectionRead", V("(os)", (session.path, "text/plain;charset=utf-8")))
            pump(0.2)
            mark = len(fe.signals)
            set_switch(None)
        finally:
            os.kill(fresh_pid, signal.SIGCONT)
        got = wait_for(lambda: pending.get("reply"), 3)
        if got and got.ok and got.nfds:
            os.close(got.fd())
        closed = wait_for(lambda: fe.sig("Closed", session.path, mark), 3)
        check(T, "the same with a clipboard read in flight: no file descriptor comes back, and the session is closed",
              offered and got and not got.ok and got.nfds == 0 and closed, f"offered {bool(offered)}, reply {got and (got.ok, got.error, got.nfds)}, Closed {bool(closed)}")
        stopped = wait_for(lambda: not admin.has_owner(NAME), 1.0)
        check(T, "On again: the activated backend starts one connection, and Off ends that process too",
              again_connections == 1 and stopped, f"{again_connections} while On")
        stop(session.receiver)

        # After Off no new clipboard transfer starts, either way.
        set_switch("on\n")
        backend = start_backend(admin)
        session = Session(fe, "off-clipboard").open(armed=False)
        mark = len(fe.signals)
        session.must(CLIP, "SetSelection", V("(oa{sv})", (session.path, {"mime_types": V("as", ["text/plain;charset=utf-8", "text/plain"])})))
        owns = wait_for(lambda: fe.sig("SelectionOwnerChanged", session.path, mark, lambda s: s["args"][1].get("session_is_owner")), 3)
        mark = len(fe.signals)
        set_switch(None)
        closed = wait_for(lambda: fe.sig("Closed", session.path, mark), 3)
        pasted = paste_now()
        write = session.call(CLIP, "SelectionWrite", V("(ou)", (session.path, 1)))
        read = session.call(CLIP, "SelectionRead", V("(os)", (session.path, "text/plain")))
        if read.ok and read.nfds:
            os.close(read.fd())
        claim = session.call(CLIP, "SetSelection", V("(oa{sv})", (session.path, {"mime_types": V("as", ["text/plain"])})))
        copy("aresos-321 copied after Off 5a1b")
        pump(0.5)
        transfers, announced = fe.sig("SelectionTransfer", None, mark), fe.sig("SelectionOwnerChanged", None, mark)
        check(T, "after Off no new clipboard transfer starts either way: a local paste asks no session (no SelectionTransfer) and gets nothing of it; "
                 "SelectionWrite, SelectionRead and SetSelection are refused with no file descriptor; a local copy is offered to nobody",
              owns and closed and not transfers and "aresos" not in pasted and not write.ok and write.nfds == 0 and not read.ok and read.nfds == 0
              and not claim.ok and not announced,
              f"owned {bool(owns)}, Closed {bool(closed)}, transfers {len(transfers)}, paste {'got text' if 'aresos' in pasted else pasted}, "
              f"write {write.error}, read {read.error} {read.nfds}, claim {claim.error}, announced {len(announced)}")
        stop(session.receiver)

        # --revoke only makes it immediate.
        closed_backend(backend)
        set_switch("on\n")
        backend = start_backend(admin)
        session = Session(fe, "revoked").open()
        activated = capture(session)
        mark = len(fe.signals)
        said_on = tool([BACKEND, "--revoke"]).stdout.strip()
        kept = not fe.sig("Closed", session.path, mark) and "capturing=true" in status_of()
        set_switch(None)
        said = tool([BACKEND, "--revoke"]).stdout.strip()
        closed = wait_for(lambda: fe.sig("Closed", session.path, mark), 1)
        code = closed_backend(backend)
        check(T, "--revoke with the switch on changes nothing: the capture holds", "sharing is on" in said_on and kept, f"{said_on!r}")
        check(T, "--revoke right after the switch is removed: by its answer the session is closed and the capture over",
              activated and said.startswith(("sharing is off", "no backend is running")) and code == 0 and closed and local_motion() and local_key(), f"{said!r}, exit {code}")
        stop(session.receiver)

        # labwc can't confirm the end of the capture: the backend exits, and labwc drops the grab with it.
        set_switch("on\n")
        backend = start_backend(admin)
        session = Session(fe, "off-labwc-stopped").open()
        activated = capture(session)
        os.kill(procs["labwc"].pid, signal.SIGSTOP)
        try:
            began = time.monotonic()
            set_switch(None)
            exited = wait_for(lambda: procs[backend].poll() is not None, 4)
            took = time.monotonic() - began
        finally:
            os.kill(procs["labwc"].pid, signal.SIGCONT)
        code = procs[backend].returncode
        info(f"test8 with labwc stopped the backend exited {round(took, 2)} s after the switch was removed, code {code}")
        check(T, "labwc stopped so it can't confirm: within 2 s of the switch going off the backend exits with an error",
              activated and exited and code not in (None, 0, -signal.SIGKILL) and took <= 2.0, f"exit {code} after {took:.2f} s")
        pump(0.5)
        check(T, "after SIGCONT labwc has dropped the grab: the pointer and the keyboard are local again", local_motion() and local_key())
        stop(session.receiver)
        stop(backend)
    finally:
        unlinked()
        os.chmod(folder, 0o755)
        set_switch("on\n")


def test9_way_out(fe, admin):
    T = "test9"
    chord = ("key 125 1", "key 42 1", "key 1 1", "key 1 0", "key 42 0", "key 125 0")

    # The backend stopped: the chord's --release gets no answer and kills it through its pidfd.
    backend = start_backend(admin)
    session = Session(fe, "chord-backend-stopped").open()
    activated = capture(session)
    os.kill(procs[backend].pid, signal.SIGSTOP)
    began = time.monotonic()
    for command in chord:
        vkbd.cmd(command)
    exited = wait_for(lambda: procs[backend].poll() is not None, 5)
    took = time.monotonic() - began
    code = procs[backend].returncode
    check(T, "the backend stopped with SIGSTOP: Super+Shift+Escape runs --release, which gets no answer within 2 s and kills it through its pidfd",
          activated and exited and code == -signal.SIGKILL and 1.5 <= took <= 3.5, f"exit {code} after {took:.2f} s; labwc: {lines_of('labwc')[-3:]}")
    check(T, "and the pointer and the keyboard are local again", local_motion() and local_key())
    stop(session.receiver)
    stop(backend)

    # labwc stopped, so no confirmation can come: --release run by hand ends the backend.
    backend = start_backend(admin)
    session = Session(fe, "release-labwc-stopped").open()
    activated = capture(session)
    os.kill(procs["labwc"].pid, signal.SIGSTOP)
    try:
        began = time.monotonic()
        released = tool([BACKEND, "--release"])
        took = time.monotonic() - began
        exited = wait_for(lambda: procs[backend].poll() is not None, 3)
    finally:
        os.kill(procs["labwc"].pid, signal.SIGCONT)
    code = procs[backend].returncode
    check(T, "labwc stopped with SIGSTOP: --release run by hand gets no confirmed answer and kills the backend through its pidfd",
          activated and exited and code == -signal.SIGKILL and "killed the backend" in released.stdout and took <= 3.0,
          f"exit {code} after {took:.2f} s; --release said {released.stdout!r} {released.stderr!r}")
    pump(0.5)
    check(T, "after SIGCONT the pointer and the keyboard are local", local_motion() and local_key())
    stop(session.receiver)
    stop(backend)

    # A process that takes the bus name after --release made its pidfd is neither asked nor killed.
    first = start_backend(admin)
    first_pid = procs[first].pid
    os.kill(first_pid, signal.SIGSTOP)  # so that --release's question waits
    releaser = subprocess.Popen([BACKEND, "--release"], env=CLIENT_ENV, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pinned = ""
    try:
        end = time.monotonic() + 5
        while "pinned the backend" not in pinned and time.monotonic() < end:
            ready, _, _ = select.select([releaser.stderr], [], [], 0.5)
            if ready:
                line = releaser.stderr.readline().decode()
                if not line:
                    break
                pinned += line
        os.kill(releaser.pid, signal.SIGSTOP)
        stop(first, signal.SIGKILL)
        # The bus has seen it go before the second one takes the name.
        wait_for(lambda: not admin.has_owner(NAME), 3)
        second = start_backend(admin)
    finally:
        os.kill(releaser.pid, signal.SIGCONT)
    out, err = releaser.communicate(timeout=10)
    pump(0.3)
    alive = procs[second].poll() is None
    asked = "ForceRelease requested" in log_of(second)
    check(T, "a backend that takes the bus name after --release pinned the old one is neither asked nor killed: the kill finds the pinned process gone",
          f"pid {first_pid};" in pinned and alive and not asked and "had already ended" in out.decode(),
          f"pinned {pinned.strip()!r}, second alive {alive}, asked {asked}, --release said {out.decode()!r} {err.decode()!r}")
    stop(second, signal.SIGINT)


# ---- labwc's bindings during a capture (brief 321, "What to build" 6) ---------------------------------------------

BINDINGS = f"{EV}/bindings.log"
# evdev codes of the keys the gate is tried with.
ESC, TAB, KEY_A, CTRL, SHIFT, ALT, F4, DOWN, MUTE, VOLUME_UP, SUPER, BRIGHTNESS_UP = 1, 15, 30, 29, 42, 56, 62, 108, 113, 115, 125, 225
MIDDLE = 274
RECOVERY_PID = "/harness/recovery-window.pid"


def ran():
    """The test bindings that ran so far, one name per run (in-container.sh's /harness/binding)."""
    with open(BINDINGS) as handle:
        return handle.read().split()


def keys(*codes):
    """Press the keys in order and release them in reverse, as a chord is typed."""
    for code in codes:
        vkbd.cmd(f"key {code} 1")
    for code in reversed(codes):
        vkbd.cmd(f"key {code} 0")


def typed(*codes):
    """What a client that gets every one of those key events sees."""
    return [f"KEY {code} 1" for code in codes] + [f"KEY {code} 0" for code in reversed(codes)]


def in_order(lines, wanted):
    """The wanted lines appear in this order (others may lie between); a wanted line ending in * is a prefix."""
    rest = iter(lines)
    return all(any(line.startswith(want[:-1]) if want.endswith("*") else line == want for line in rest) for want in wanted)


def quiet(action, settle=0.4):
    """Run the action. True when no test binding ran and the probe window was not asked to close."""
    before, seen = len(ran()), len(window())
    action()
    pump(settle)
    return len(ran()) == before and "CLOSE" not in window()[seen:]


def test10_shortcuts(fe, admin):
    T = "test10"
    backend = start_backend(admin)
    session = Session(fe, "shortcuts").open()

    def runs(action, name):
        before = len(ran())
        action()
        return bool(wait_for(lambda: name in ran()[before:], 2))

    def alt_middle():
        vkbd.cmd(f"key {ALT} 1")
        vptr.cmd(f"btn {MIDDLE} 1")
        vptr.cmd(f"btn {MIDDLE} 0")
        vkbd.cmd(f"key {ALT} 0")

    def alt_scroll():
        vkbd.cmd(f"key {ALT} 1")
        vptr.cmd("axis 1")
        vkbd.cmd(f"key {ALT} 0")

    def bindings_act(where):
        """Every unmarked binding acts: the control for each probe the gate is then tried with."""
        media = all(runs(lambda code=code: keys(code), name) for code, name in ((VOLUME_UP, "volume-up"), (MUTE, "mute"), (BRIGHTNESS_UP, "brightness-up")))
        check(T, f"{where} the media keys and a lone Super run their commands", media and runs(lambda: keys(SUPER), "lone-super"), f"{ran()[-6:]}")
        check(T, f"{where} the mouse bindings (Alt+Middle, Alt+scroll in every context) run their commands",
              runs(alt_middle, "mouse-press") and runs(alt_scroll, "mouse-scroll"), f"{ran()[-6:]}")
        check(T, f"{where} Alt+F4 asks the window to close", window_gets(lambda: keys(ALT, F4), "CLOSE"), f"{window()[-4:]}")

    def recovery_window(expect_key=True):
        seen = len(lines_of("recovery-window"))

        def events():
            return lines_of("recovery-window")[seen:]

        keys(SUPER, CTRL, ESC)
        focused = False
        try:
            opened = wait_for(lambda: any(line.startswith("CONFIGURED ") for line in events()), 3)
            if opened and expect_key:
                focused = wait_for(lambda: "KBD_ENTER" in events(), 2)
                if focused:
                    keys(KEY_A)
                    return opened, wait_for(lambda: in_order(events(), typed(KEY_A)), 2)
            return opened, False
        finally:
            if os.path.exists(RECOVERY_PID):
                with open(RECOVERY_PID) as handle:
                    pid = int(handle.read())
                os.unlink(RECOVERY_PID)
                seen_probe = len(window())
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                if focused:
                    wait_for(lambda: "KBD_ENTER" in window()[seen_probe:], 2)

    # Outside a capture every binding works as before.
    bindings_act("outside a capture")
    seen = len(window())
    vkbd.cmd(f"key {ALT} 1")
    vkbd.cmd(f"key {TAB} 1")
    vkbd.cmd(f"key {TAB} 0")
    switcher = wait_for(lambda: "KBD_LEAVE" in window()[seen:], 2)
    vkbd.cmd(f"key {ALT} 0")
    check(T, "outside a capture Alt+Tab starts the window switcher (the window loses the keyboard until Alt is released)",
          switcher and wait_for(lambda: in_order(window()[seen:], ["KBD_LEAVE", "KBD_ENTER"]), 2), f"{window()[seen:]}")
    opened, got_key = recovery_window()
    check(T, "outside a capture Super+Ctrl+Escape opens the recovery window and it gets the next key", opened and got_key)

    # During a capture: nothing on the compositor's side, and every key and button reaches the client.
    activated = capture(session)
    if not check(T, "the capture for the gate starts", activated, log_of(backend)[-800:]):
        session.shut()
        stop(backend, signal.SIGINT)
        return
    mark, seen_window = len(fe.signals), len(window())

    def reaches(action, wanted):
        seen = len(session.eis())
        silent = quiet(action)
        arrived = wait_for(lambda: in_order(session.eis()[seen:], wanted), 2)
        return silent and bool(arrived), f"nothing ran {silent}; the client got {[line for line in session.eis()[seen:] if not line.startswith('MOD')]}"

    def tried(what, action, wanted):
        ok, detail = reaches(lambda: (action(), keys(KEY_A)), wanted + typed(KEY_A))
        check(T, f"during a capture {what}, and the next key reaches the client too", ok, detail)

    tried("Alt+F4 closes nothing and reaches the client", lambda: keys(ALT, F4), typed(ALT, F4))
    # Down is a window-switcher key: a switcher that had started would take it.
    tried("Alt+Tab starts no window switcher: Tab and then Down reach the client",
          lambda: (vkbd.cmd(f"key {ALT} 1"), keys(TAB), keys(DOWN), vkbd.cmd(f"key {ALT} 0")),
          [f"KEY {ALT} 1", *typed(TAB), *typed(DOWN), f"KEY {ALT} 0"])
    tried("a lone Super runs nothing and reaches the client", lambda: keys(SUPER), typed(SUPER))
    tried("the volume, mute and brightness keys run nothing and reach the client",
          lambda: (keys(VOLUME_UP), keys(MUTE), keys(BRIGHTNESS_UP)), typed(VOLUME_UP) + typed(MUTE) + typed(BRIGHTNESS_UP))
    tried("Ctrl+Alt+Escape (the backend's former chord) reaches the client", lambda: keys(CTRL, ALT, ESC), typed(CTRL, ALT, ESC))
    tried("the mouse bindings run nothing: Alt+Middle and Alt+scroll reach the client",
          lambda: (alt_middle(), alt_scroll()), [f"KEY {ALT} 1", f"BUTTON {MIDDLE} 1", f"BUTTON {MIDDLE} 0", f"KEY {ALT} 0", f"KEY {ALT} 1", "SCROLL*", f"KEY {ALT} 0"])
    pump(0.3)
    leaked = [line for line in window()[seen_window:] if line.split()[0] in ("ENTER", "MOTION", "BUTTON", "AXIS", "KEY", "KBD_ENTER", "CLOSE")]
    check(T, "the capture held through all of them: no Deactivated, and the local window got nothing",
          not fe.sig("Deactivated", session.path, mark) and not leaked, f"{leaked}")

    # The second marked chord (the first, Super+Shift+Escape, is test3's and test9's): out, and the terminal.
    opened, got_key = recovery_window()
    ended = wait_for(lambda: fe.sig("Deactivated", session.path, mark), 3)
    check(T, "during a capture Super+Ctrl+Escape releases it and opens the recovery window",
          ended and opened, f"Deactivated {bool(ended)}, opened {bool(opened)}")
    check(T, "the new recovery window gets the next key and the pointer is local again", got_key and local_motion())

    # A binding held as the capture starts: its release action and its repeats are dropped.
    shove = approach("left")
    before = len(ran())
    vkbd.cmd(f"key {SUPER} 1")
    activated = capture(session, shove=shove)
    seen = len(session.eis())
    vkbd.cmd(f"key {SUPER} 0")
    keys(KEY_A)
    arrived = wait_for(lambda: in_order(session.eis()[seen:], typed(KEY_A)), 2)
    pump(0.4)
    check(T, "a lone Super held as the capture starts runs no release action, and the next key reaches the client",
          activated and arrived and ran()[before:] == [], f"activated {bool(activated)}, ran {ran()[before:]}, the client got {session.eis()[seen:]}")
    session.release()
    local = local_key()
    before = len(ran())
    vkbd.cmd(f"key {VOLUME_UP} 1")
    pump(1.5)
    vkbd.cmd(f"key {VOLUME_UP} 0")
    pump(0.3)
    repeats = ran()[before:].count("volume-up")
    check(T, "outside a capture a held volume key repeats its command (the control for the next check)", local and repeats >= 4, f"{repeats} runs in 1.5 s")
    shove = approach("left")
    vkbd.cmd(f"key {VOLUME_UP} 1")
    activated = capture(session, shove=shove)
    pump(0.3)  # a command started just before the capture has written its line by now
    before = len(ran())
    pump(1.5)
    during = ran()[before:]
    vkbd.cmd(f"key {VOLUME_UP} 0")
    seen = len(session.eis())
    keys(KEY_A)
    check(T, "a volume key held as the capture starts repeats nothing during it, and the next key reaches the client",
          activated and during == [] and wait_for(lambda: in_order(session.eis()[seen:], typed(KEY_A)), 2), f"activated {bool(activated)}, ran {during} in 1.5 s")
    session.release()
    check(T, "after these captures the pointer and the keyboard are local again", local_motion() and local_key())
    session.shut()
    stop(backend, signal.SIGINT)

    # What the gate relies on: it knows the capture surface by its layer namespace. Any other layer surface that
    # holds the keyboard exclusively keeps labwc's bindings, which is also what a labwc without the patch does
    # for the capture surface: the same probes, the same focus, and Alt+F4 closes a window.
    def layer(namespace, name):
        spawn(name, [WLH, "layer", namespace], CLIENT_ENV)
        return bool(wait_for(lambda: "KBD_ENTER" in lines_of(name), 5))

    focused = layer("harness-other-layer", "layer-other")
    seen = len(lines_of("layer-other"))
    keys(KEY_A)
    check(T, "a layer surface with another namespace gets the keyboard exclusively",
          focused and wait_for(lambda: in_order(lines_of("layer-other")[seen:], typed(KEY_A)), 2), f"{lines_of('layer-other')[-6:]}")
    bindings_act("under a layer surface with another namespace")
    stop("layer-other")

    focused = layer("aresos-input-barrier", "layer-barrier")
    seen = len(lines_of("layer-barrier"))
    silent = quiet(lambda: (keys(ALT, F4), keys(VOLUME_UP), keys(SUPER), alt_middle(), alt_scroll()))
    got = wait_for(lambda: in_order(lines_of("layer-barrier")[seen:], typed(ALT, F4) + typed(VOLUME_UP) + typed(SUPER)), 2)
    check(T, "under a layer surface with the capture surface's namespace the same keys and buttons run nothing, and the keys reach that surface",
          focused and silent and got, f"focused {focused}, nothing ran {silent}, it got {lines_of('layer-barrier')[seen:]}")
    opened, _ = recovery_window(expect_key=False)
    check(T, "and Super+Ctrl+Escape still opens the recovery window there", opened)
    stop("layer-barrier")
    pump(0.3)
    check(T, "with the layer surfaces gone the window has the keyboard again and the bindings act", local_key() and runs(lambda: keys(VOLUME_UP), "volume-up"))


# ---- the run -------------------------------------------------------------------------------------------------------


def isolation_of_clients():
    """Every process of the harness has the private bus and the private labwc, and nothing else."""
    wrong = []
    for name, process in procs.items():
        with open(f"/proc/{process.pid}/environ", "rb") as handle:
            env = dict(item.split("=", 1) for item in handle.read().decode().split("\0") if "=" in item)
        expected_display = None if name in ("dbus-daemon", "labwc") else DISPLAY_NAME
        if (env.get("DBUS_SESSION_BUS_ADDRESS") != BUS_ADDR or env.get("XDG_RUNTIME_DIR") != RUNTIME
                or env.get("WAYLAND_DISPLAY") != expected_display or "DISPLAY" in env or not env.get("HOME", "").startswith("/tmp/harness-home.")):
            wrong.append(name)
    check("isolation", f"each of the harness's {len(procs)} processes ({', '.join(sorted(procs))}) has the private bus, the scratch runtime dir and home, and only the private labwc as display", not wrong, f"{wrong}")
    sockets = subprocess.run(["find", "/", "(", "-path", "/proc", "-o", "-path", "/sys", ")", "-prune", "-o", "-type", "s", "-print"], capture_output=True, text=True).stdout.split()
    foreign = [path for path in sockets if not path.startswith((RUNTIME + "/", "/tmp/.X11-unix/"))]
    check("isolation", "the only sockets in the container are the harness's own (the private bus, labwc's Wayland socket and labwc's own Xwayland)", not foreign, f"{foreign}")
    with open(f"{EV}/isolation-sockets.txt", "w") as handle:
        handle.write("\n".join(sockets) + "\n")


def start_labwc():
    """A headless labwc with two outputs. It is given the private bus only so that its key binding can reach
    the backend, and told not to update any activation environment."""
    spawn("labwc", ["labwc", "-C", f"{ENV['XDG_CONFIG_HOME']}/labwc"],
          {**ENV, "WLR_BACKENDS": "headless", "WLR_RENDERER": "pixman", "WLR_HEADLESS_OUTPUTS": "2", "WLR_LIBINPUT_NO_DEVICES": "1", "LABWC_UPDATE_ACTIVATION_ENV": "0"})
    if not wait_for(lambda: os.path.exists(f"{RUNTIME}/{DISPLAY_NAME}"), 10):
        raise RuntimeError(f"labwc did not start: {log_of('labwc')[-600:]}")


def setup():
    global vptr, vkbd, ZONES
    start_bus()
    start_labwc()
    update = tool(["dbus-update-activation-environment", "WAYLAND_DISPLAY"])
    if update.returncode:
        raise RuntimeError(update.stderr)
    offered = tool(["wayland-info"]).stdout
    needed = ["zwlr_layer_shell_v1", "zwp_pointer_constraints_v1", "zwp_relative_pointer_manager_v1", "ext_data_control_manager_v1",
              "zwlr_output_manager_v1", "zwlr_virtual_pointer_manager_v1", "zwp_virtual_keyboard_manager_v1"]
    with open(f"{EV}/wayland-info.txt", "w") as handle:
        handle.write(offered)
    missing = [name for name in needed if f"'{name}'" not in offered]
    check("setup", "this labwc offers every protocol the backend and the harness use", not missing, f"missing {missing}")
    ZONES = randr_zones()
    with open(f"{EV}/wlr-randr.txt", "w") as handle:
        handle.write(tool(["wlr-randr"]).stdout)
    vptr = VInput("pointer")
    vkbd = VInput("keyboard")
    goto(300, 300)
    spawn("window", [WLH, "window", "--keep-open"], CLIENT_ENV)
    if not wait_for(lambda: any(line.startswith("CONFIGURED") for line in window()), 5):
        raise RuntimeError("the probe window did not map")
    pump(0.3)
    check("setup", "the probe window is full-screen on the first output and receives local input", local_motion() and local_button() and local_key(), f"{window()[-6:]}")
    check("setup", "labwc was told not to update any activation environment, and did not", "Updating dbus execution environment" not in log_of("labwc"))
    meta = os.lstat(SWITCH)
    check("setup", "the sharing switch is on: root's regular file, 0644, saying on", stat.S_ISREG(meta.st_mode) and meta.st_uid == 0
          and stat.S_IMODE(meta.st_mode) == 0o644 and open(SWITCH).read() == "on\n")


def run(name, function, *args):
    try:
        return function(*args)
    except Exception as error:  # a broken test is a failed test, and the rest still runs
        check(name, "ran to its end", False, f"{type(error).__name__}: {error}")
        traceback.print_exc()
        return None


def main():
    def too_long(*_):
        raise TimeoutError("the harness ran into its own time limit")

    signal.signal(signal.SIGALRM, too_long)
    signal.alarm(780)
    code = 2
    try:
        setup()
        stranger = Bus("stranger-1")
        fe = Bus("frontend-1")
        fe.own_frontend()
        backend = start_backend(stranger)
        isolation_of_clients()
        if any(line.startswith("FAIL") for line in results):
            raise RuntimeError("the setup is not usable")

        for name, case, args in (
            ("test1", test1_zones, (fe,)),
            ("test2", test2_crossing, (fe,)),
            ("test3", test3_ways_out, (fe,)),
            ("test5", test5_clipboard, (fe,)),
        ):
            run(name, case, *args, backend)
            closed_backend(backend)
            backend = start_backend(stranger)
        run("test6", test6_refusals, fe, stranger, backend)
        backend = start_backend(stranger)
        run("review1-finding5", review5_pointer_device, fe, backend)
        closed_backend(backend)
        fe = run("test4", test4_teardown, fe, stranger, start_backend(stranger)) or fe
        run("test3", test3_kill_and_watchdog, fe, stranger, start_backend(stranger))
        run("test7", test7_logs, fe, stranger, stranger)
        run("test1", test1_output_off, fe, stranger)
        run("test8", test8_switch, fe, stranger)
        run("test9", test9_way_out, fe, stranger)
        run("test10", test10_shortcuts, fe, stranger)
        run("review1-finding2", review2_bus_loss, fe, stranger)
        run("review1-finding4", review4_signals)
        code = 1 if any(line.startswith("FAIL") for line in results) else 0
        # After the result is settled: it restarts labwc, and may see it abort.
        try:
            control_output_cycle()
        except Exception as error:
            info(f"control: could not be run: {type(error).__name__}: {error}")
    except Exception as error:
        traceback.print_exc()
        results.append(f"UNUSABLE {type(error).__name__}: {error}")
        print(results[-1], flush=True)
    finally:
        signal.alarm(0)
        # Only what this harness started: its own processes, and wl-copy's own background copies.
        for name in list(procs):
            stop(name, timeout=3)
        subprocess.run(["pkill", "-x", "wl-copy"], check=False)
        for bus in buses:
            with open(f"{EV}/signals-{bus.label}.json", "w") as handle:
                json.dump(bus.signals, handle, indent=1, default=str)
        passed = sum(1 for line in results if line.startswith("PASS"))
        failed = sum(1 for line in results if line.startswith("FAIL"))
        results.append(f"SUMMARY {passed} passed, {failed} failed, exit {code}")
        print(results[-1], flush=True)
        with open(f"{EV}/results.txt", "a") as handle:
            handle.write("\n".join(results) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
