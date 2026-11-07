import asyncio
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from aresos_control.common import FILE_LIMIT, WIRE_LIMIT, canonical, sha256
from aresos_control.protocol import Client, receive, send
from support import ROOT, WORK, message

OWNER, SERVICE, OTHER = 23101, 23102, 23103
LAUNCH = "/usr/libexec/aresos-control/launch.py"
VENDOR = "/usr/lib/aresos-control/vendor"


def identity(uid):
    def enter():
        os.setgroups([])
        os.setgid(uid)
        os.setuid(uid)
    return enter


class Integration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temp.name)
        self.root.chmod(0o711)
        self.home = self.root / "home"
        self.home.mkdir(mode=0o700)
        os.chown(self.home, OWNER, OWNER)
        for name in ("Documents", "Downloads", "Desktop"):
            path = self.home / name
            path.mkdir(mode=0o700)
            os.chown(path, OWNER, OWNER)
        for name in ("state", "independent", "sockets"):
            path = self.root / name
            path.mkdir(mode=0o711 if name == "sockets" else 0o700)
            os.chown(path, SERVICE, SERVICE)
        self.service_config = {"owner_uid": OWNER, "state_dir": str(self.root / "state"),
                               "evidence_dir": str(self.root / "independent"), "socket_dir": str(self.root / "sockets"), "approval_ttl": 120}
        self.proxy_config = {"act_socket": str(self.root / "sockets/act.sock"), "admin_socket": str(self.root / "sockets/admin.sock"),
                             "home": str(self.home), "folders": [str(self.home / name) for name in ("Documents", "Downloads", "Desktop")]}
        Path("/etc/aresos-control/service.json").write_text(canonical(self.service_config))
        Path("/etc/aresos-control/proxy.json").write_text(canonical(self.proxy_config))
        self.output = open(self.root / "daemon-output.txt", "w+")
        self.daemon = subprocess.Popen(["/usr/bin/python3", "-I", "-S", LAUNCH, "service"],
                                       preexec_fn=identity(SERVICE), stdout=self.output, stderr=subprocess.STDOUT)
        for _ in range(100):
            if (self.root / "sockets/act.sock").exists():
                break
            if self.daemon.poll() is not None:
                self.output.seek(0)
                self.fail("Daemon failed: " + self.output.read())
            time.sleep(0.03)
        else:
            self.fail("Service did not start")

    def tearDown(self):
        if hasattr(self, "daemon"):
            self.daemon.terminate()
            self.daemon.wait(timeout=8)
        if hasattr(self, "output"):
            self.output.close()
        self.temp.cleanup()

    def run_user(self, uid, code, *arguments, env=None, cwd=None):
        result = subprocess.run([sys.executable, "-c", code, *arguments], env=env,
                                cwd=cwd, preexec_fn=identity(uid), capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def request(self, uid, kind, request):
        # An independent client process provides genuine kernel peer credentials.
        code = "import json,socket,sys; s=socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); s.sendall((sys.argv[2]+'\\n').encode()); f=s.makefile(); print(f.readline())"
        return self.run_user(uid, code, str(self.root / ("sockets/" + kind + ".sock")), canonical({"v": 1, **request}))

    def call(self, uid, action, args, kind="act"):
        return self.request(uid, kind, {"method": "call", "action": action, "arguments": args})

    def hook_command(self, name):
        settings = json.loads((ROOT / "control/settings/managed-hooks.json").read_text())
        return shlex.split(settings["hooks"][name][0]["hooks"][0]["command"])

    def launch(self, uid, mode_args, input=None, env=None, cwd=None):
        command = (self.hook_command(mode_args[1]) if mode_args[0] == "hook" else
                   ["/usr/bin/python3", "-I", "-S", LAUNCH, *mode_args])
        return subprocess.run(command, preexec_fn=identity(uid),
                              input=input, env=env, cwd=cwd, capture_output=True, text=True, timeout=25)

    def test_all_socket_peer_credentials_even_permissive_modes(self):
        # Opening the mode bits deliberately proves that SO_PEERCRED is the gate.
        for path in (self.root / "sockets").glob("*.sock"):
            path.chmod(0o666)
        for uid in (OWNER, OTHER, 0, SERVICE):
            for kind in ("act", "admin", "chrome"):
                with self.subTest(uid=uid, socket=kind):
                    result = self.request(uid, kind, {"method": "tools", "app": "testapp"})
                    self.assertEqual(result["ok"], (kind == "act" and uid == OWNER) or (kind == "admin" and uid == 0), result)
                    if not result["ok"]:
                        self.assertEqual(result["error"]["code"], "permission_denied")
        settings = {"refuse": [], "failure": "none"}
        self.assertFalse(self.call(OWNER, "testapp_fixture_configure", settings)["ok"])
        self.assertFalse(self.call(OWNER, "control_restore_confirm", {"confirm": "invalidate earlier approvals"})["ok"])
        self.assertTrue(self.call(0, "testapp_fixture_configure", settings, "admin")["ok"])
        self.assertFalse(self.call(0, "testapp_list", {}, "admin")["ok"])

    def test_25_mib_file_uses_chunks_and_receiver_gets_hashed_snapshot(self):
        source = self.home / "Documents/large.bin"
        original = (b"fixture snapshot bytes " * (FILE_LIMIT // 23 + 1))[:FILE_LIMIT - 1]
        self.assertEqual(len(original), FILE_LIMIT - 1)
        source.write_bytes(original)
        os.chown(source, OWNER, OWNER)
        code = r"""
import json, os, sys
from pathlib import Path
from unittest.mock import patch
from aresos_control import protocol
from aresos_control.common import WIRE_LIMIT, canonical, sha256
from aresos_control.proxy import Proxy
from support import message
config, path = json.loads(sys.argv[1]), Path(sys.argv[2])
proxy = Proxy("testapp", config)
read = proxy.files.read
sizes = []
original_send, original_receive = protocol.send, protocol.receive

def send(connection, value):
    sizes.append(len(canonical(value).encode()) + 1)
    return original_send(connection, value)

def receive(connection):
    value = original_receive(connection)
    sizes.append(len(canonical(value).encode()) + 1)
    return value

def snapshot(name):
    data, ref = read(name)
    path.unlink()
    path.write_bytes(b"replacement after reading")
    return data, ref

with patch.object(proxy.files, "read", side_effect=snapshot), patch.object(protocol, "send", side_effect=send), patch.object(protocol, "receive", side_effect=receive):
    imported = proxy.call("file_import", {"path": str(path)})
    assert imported["ok"], imported
    ref = imported["data"]["file"]
    prepared = proxy.call("prepare_send", message(attachments=[ref], to=["alpha"], bcc=[]))
    assert prepared["ok"], prepared
    sent = proxy.call("send", prepared["data"]["approval"])
    assert sent["ok"] and sent["data"]["operation"]["state"] == "done", sent
    saved = proxy.call("file_save", {"sha256": ref["sha256"], "folder": str(path.parent.parent / "Downloads"), "name": "large-saved.bin"})
    assert saved["ok"], saved
assert max(sizes) <= WIRE_LIMIT
print(canonical({"ref": ref, "id": prepared["data"]["approval"]["operation_id"], "frames": len(sizes), "largest": max(sizes)}))
"""
        # support is test-only; the actual proxy and service use their production paths.
        env = {**os.environ, "PYTHONPATH": str(ROOT / "control/tests") + os.pathsep + os.environ["PYTHONPATH"]}
        result = self.run_user(OWNER, code, canonical(self.proxy_config), str(source), env=env)
        self.assertEqual(result["ref"]["size"], FILE_LIMIT - 1)
        self.assertEqual(result["ref"]["sha256"], sha256(original))
        self.assertGreater(result["frames"], 100)
        self.assertLessEqual(result["largest"], WIRE_LIMIT)
        self.assertEqual((self.home / "Downloads/large-saved.bin").read_bytes(), original)
        self.assertEqual(source.read_bytes(), b"replacement after reading")
        import sqlite3
        receiver = sqlite3.connect(self.root / "independent/receiver.sqlite")
        try:
            payload, = receiver.execute("SELECT payload FROM arrivals WHERE op=?", (result["id"],)).fetchone()
        finally:
            receiver.close()
        payload = json.loads(payload)
        self.assertEqual(bytes.fromhex(payload["attachment_bytes"][0]), original)
        self.assertEqual(payload["attachments"][0]["sha256"], sha256(original))
        print(f"25 MiB transfer: {result['frames']} frames, largest={result['largest']} bytes (wire limit={WIRE_LIMIT})")

    def test_oversize_file_refused_by_real_proxy_and_service(self):
        source = self.home / "Documents/too-large.bin"
        with source.open("wb") as stream:
            stream.truncate(FILE_LIMIT + 1)
        os.chown(source, OWNER, OWNER)
        code = """
import json, sys
from aresos_control.proxy import Proxy
proxy = Proxy("testapp", json.loads(sys.argv[1]))
print(json.dumps(proxy.call("file_import", {"path": sys.argv[2]})))
"""
        self.assertFalse(self.run_user(OWNER, code, canonical(self.proxy_config), str(source))["ok"])
        result = self.request(OWNER, "act", {"method": "upload", "app": "testapp", "file": {
            "sha256": "0" * 64, "size": FILE_LIMIT + 1, "name": "large.bin", "real_path": str(source)}})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "file_refused")
        self.assertEqual(list((self.root / "state/blobs").iterdir()), [])

    def test_configured_file_limits_are_enforced_by_both_processes(self):
        source = self.home / "Documents/configured.bin"
        source.write_bytes(b"x" * 129)
        os.chown(source, OWNER, OWNER)
        code = """
import json, sys
from aresos_control.proxy import Proxy
proxy = Proxy("testapp", json.loads(sys.argv[1]))
print(json.dumps(proxy.call("file_import", {"path": sys.argv[2]})))
"""
        limited_proxy = {**self.proxy_config, "file_limit": 128}
        result = self.run_user(OWNER, code, canonical(limited_proxy), str(source))
        self.assertFalse(result["ok"])
        self.daemon.terminate()
        self.daemon.wait(timeout=8)
        for path in (self.root / "sockets").glob("*.sock"):
            path.unlink()
        self.service_config["file_limit"] = 128
        Path("/etc/aresos-control/service.json").write_text(canonical(self.service_config))
        self.daemon = subprocess.Popen(["/usr/bin/python3", "-I", "-S", LAUNCH, "service"],
                                       preexec_fn=identity(SERVICE), stdout=self.output, stderr=subprocess.STDOUT)
        for _ in range(100):
            if (self.root / "sockets/act.sock").exists():
                break
            time.sleep(0.03)
        result = self.run_user(OWNER, code, canonical(self.proxy_config), str(source))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "file_refused")
        source.write_bytes(b"x" * 128)
        result = self.run_user(OWNER, code, canonical(limited_proxy), str(source))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["file"]["size"], 128)

    def test_invalid_upload_streams_leave_no_blob_or_staging_file(self):
        code = r"""
import base64, json, socket, sys
from aresos_control.common import CHUNK_SIZE, sha256
from aresos_control.protocol import receive, send
results = []
for fault in ("cut-off", "incomplete", "reordered", "wrong-hash", "extra-bytes", "large-chunk", "bad-base64"):
    data = b"fixture-chunk" * 512
    key = "0" * 64 if fault == "wrong-hash" else sha256(data)
    with socket.socket(socket.AF_UNIX) as connection:
        connection.connect(sys.argv[1])
        send(connection, {"v": 1, "method": "upload", "app": "testapp", "file": {
            "sha256": key, "size": len(data), "name": "fixture.bin", "real_path": "/fixture/source"}})
        ready = receive(connection)
        assert ready["ok"], ready
        chunk = data[:100] if fault in {"cut-off", "incomplete"} else data + b"extra" if fault == "extra-bytes" else b"x" * (CHUNK_SIZE + 1) if fault == "large-chunk" else data
        send(connection, {"offset": 100 if fault == "reordered" else 0,
                          "bytes": "invalid!" if fault == "bad-base64" else base64.b64encode(chunk).decode()})
        response = receive(connection)
        if response["ok"]:
            if fault == "cut-off":
                connection.shutdown(socket.SHUT_WR)
            else:
                send(connection, {"end": True, "offset": len(chunk)})
            response = receive(connection)
        assert not response["ok"], (fault, response)
        results.append(fault)
print(json.dumps(results))
"""
        results = self.run_user(OWNER, code, str(self.root / "sockets/act.sock"))
        self.assertEqual(len(results), 7)
        self.assertEqual(list((self.root / "state/blobs").iterdir()), [])

    def test_cli_generated_help_admin_and_today_log(self):
        result = self.launch(OWNER, ["cli", "--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn((ROOT / "control/generated/cli-help.txt").read_text().strip(), result.stdout)
        detail = self.launch(OWNER, ["cli", "testapp", "send", "--help"])
        self.assertIn('"operation_id"', detail.stdout)
        listing = self.launch(OWNER, ["cli", "testapp", "list", "--json"])
        self.assertTrue(json.loads(listing.stdout)["ok"], listing.stderr)
        wrapped = subprocess.run(["/usr/bin/aresos", "testapp", "list"], preexec_fn=identity(OWNER), capture_output=True, text=True, timeout=10)
        self.assertTrue(json.loads(wrapped.stdout)["ok"], wrapped.stderr)
        admin = self.launch(0, ["cli", "admin", "testapp", "fixture_configure", "--input", canonical({"failure": "none", "refuse": []})])
        self.assertTrue(json.loads(admin.stdout)["ok"], admin.stderr)
        log = self.launch(OWNER, ["cli", "log", "--json"])
        self.assertTrue(json.loads(log.stdout)["ok"], log.stderr)
        self.assertTrue(any(i["action"] == "testapp_fixture_configure" for i in json.loads(log.stdout)["data"]["items"]))
        rejected = self.launch(OWNER, ["cli", "admin", "testapp", "fixture_configure", "--input", canonical({"failure": "none", "refuse": []})])
        self.assertEqual(rejected.returncode, 1)

    def test_real_mcp_stdio_list_prepare_send_attachment_save_and_hooks(self):
        async def conversation():
            from mcp import Client as MCPClient, StdioServerParameters
            source = self.home / "Documents/fixture.txt"
            source.write_bytes(b"fixture attachment bytes")
            os.chown(source, OWNER, OWNER)
            parameters = StdioServerParameters(command="/usr/bin/setpriv", args=["--reuid", str(OWNER), "--regid", str(OWNER), "--clear-groups",
                "/usr/bin/aresos-mcp", "testapp"])
            async with MCPClient(parameters) as client:
                tools = await client.list_tools()
                names = {tool.name for tool in tools.tools}
                self.assertIn("send", names)
                self.assertNotIn("fixture_configure", names)
                imported = (await client.call_tool("file_import", {"path": str(source)})).structured_content
                self.assertTrue(imported["ok"], imported)
                prepared = (await client.call_tool("prepare_send", message(attachments=[imported["data"]["file"]]))).structured_content
                self.assertTrue(prepared["ok"], prepared)
                approval = prepared["data"]["approval"]
                # A hook sees a held operation via act.sock, with documented I/O.
                hook_input = {"hook_event_name": "Stop", "session_id": "fixture-session", "transcript_path": "/unused", "cwd": str(self.home), "permission_mode": "default", "stop_hook_active": False}
                hook = self.launch(OWNER, ["hook", "Stop"], input=canonical(hook_input))
                self.assertEqual(json.loads(hook.stdout)["decision"], "block", hook.stderr)
                source.write_bytes(b"changed after import")
                sent = (await client.call_tool("send", approval)).structured_content
                self.assertTrue(sent["ok"], sent)
                self.assertEqual(sent["data"]["operation"]["state"], "done")
                repeat = (await client.call_tool("send", approval)).structured_content
                self.assertEqual(repeat["data"], sent["data"])
                saved = (await client.call_tool("file_save", {"sha256": imported["data"]["file"]["sha256"], "folder": str(self.home / "Downloads"), "name": "saved.txt"})).structured_content
                self.assertTrue(saved["ok"], saved)
                self.assertEqual((self.home / "Downloads/saved.txt").read_bytes(), b"fixture attachment bytes")
                collision = (await client.call_tool("file_save", {"sha256": imported["data"]["file"]["sha256"], "folder": str(self.home / "Downloads"), "name": "saved.txt"})).structured_content
                self.assertFalse(collision["ok"], collision)
                return approval["operation_id"]
        op_id = asyncio.run(conversation())
        status = self.call(OWNER, "testapp_operation_status", {"operation_id": op_id})
        self.assertEqual(status["data"]["evidence"]["arrivals"], ["alpha", "beta", "hidden"])
        # Reload a short TTL only for the independent expiry check, so normal
        # end-to-end work does not race a two-second approval on a slow runner.
        self.daemon.terminate()
        self.daemon.wait(timeout=8)
        self.service_config["approval_ttl"] = 0.2
        Path("/etc/aresos-control/service.json").write_text(canonical(self.service_config))
        self.daemon = subprocess.Popen(["/usr/bin/python3", "-I", "-S", LAUNCH, "service"],
                                       preexec_fn=identity(SERVICE), stdout=self.output, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 8
        while True:
            try:
                prepared_result = self.call(OWNER, "testapp_prepare_send", message())
                break
            except AssertionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.03)
        self.assertTrue(prepared_result["ok"], prepared_result)
        prepared = prepared_result["data"]["approval"]
        time.sleep(0.4)
        status = self.call(OWNER, "testapp_operation_status", {"operation_id": prepared["operation_id"]})
        self.assertEqual(status["data"]["operation"]["state"], "failed")
        prompt_input = {"hook_event_name": "UserPromptSubmit", "session_id": "fixture-session", "prompt": "owner message", "cwd": str(self.home)}
        prompt = self.launch(OWNER, ["hook", "UserPromptSubmit"], input=canonical(prompt_input))
        self.assertIn(prepared["operation_id"], json.loads(prompt.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_large_hook_inputs_still_remind_about_pending_work(self):
        prepared = self.call(OWNER, "testapp_prepare_send", message())
        self.assertTrue(prepared["ok"], prepared)
        op_id = prepared["data"]["approval"]["operation_id"]
        for name, field in (("Stop", "last_assistant_message"), ("UserPromptSubmit", "prompt")):
            with self.subTest(event=name):
                event = {"hook_event_name": name, "session_id": "fixture-session", "transcript_path": "/unused",
                         "cwd": str(self.home), "permission_mode": "default", "stop_hook_active": False,
                         field: "long pasted content " * 10000}
                wire = canonical(event)
                self.assertGreater(len(wire.encode()), 65536)
                hook = self.launch(OWNER, ["hook", name], input=wire)
                self.assertEqual(hook.returncode, 0, hook.stderr)
                result = json.loads(hook.stdout)
                if name == "Stop":
                    self.assertEqual(result["decision"], "block")
                    self.assertIn(op_id, result["reason"])
                else:
                    self.assertEqual(result["hookSpecificOutput"]["hookEventName"], name)
                    self.assertIn(op_id, result["hookSpecificOutput"]["additionalContext"])
                self.assertEqual(hook.stderr, "")

    def test_malformed_hook_input_gives_explicit_failure_feedback(self):
        for name in ("Stop", "UserPromptSubmit"):
            for wire in ('{"hook_event_name":"' + name + '","prompt":', '[]',
                         canonical({"hook_event_name": "Stop" if name == "UserPromptSubmit" else "UserPromptSubmit"})):
                with self.subTest(event=name, input=wire):
                    hook = self.launch(OWNER, ["hook", name], input=wire)
                    self.assertEqual(hook.stdout, "")
                    if name == "Stop":
                        self.assertEqual(hook.returncode, 2)
                        self.assertIn("AresOS hook failed; inspect pending work", hook.stderr)
                    else:
                        self.assertEqual(hook.returncode, 0)
                        self.assertEqual(hook.stderr, "")
                    self.assertNotIn("Traceback", hook.stderr)

    def test_prompt_hook_installation_and_service_failures_are_quiet(self):
        fd = os.open(self.home, os.O_RDONLY | os.O_DIRECTORY)
        try:
            hook = subprocess.run(self.hook_command("UserPromptSubmit"),
                                  preexec_fn=identity(OWNER), stdin=fd, capture_output=True, text=True, timeout=15)
            self.assertEqual((hook.returncode, hook.stdout, hook.stderr), (0, "", ""))
        finally:
            os.close(fd)
        config = Path("/etc/aresos-control/proxy.json")
        original = config.read_bytes()
        try:
            config.write_bytes(b"malformed configuration")
            hook = self.launch(OWNER, ["hook", "UserPromptSubmit"], input='{}')
            self.assertEqual((hook.returncode, hook.stdout, hook.stderr), (0, "", ""))
        finally:
            config.write_bytes(original)
        self.daemon.terminate()
        self.daemon.wait(timeout=8)
        hook = self.launch(OWNER, ["hook", "UserPromptSubmit"], input=canonical({"hook_event_name": "UserPromptSubmit"}))
        self.assertEqual((hook.returncode, hook.stdout, hook.stderr), (0, "", ""))

    def test_proxy_isolated_from_planted_code_environment_and_pth(self):
        poison = self.home / "Documents/poison"
        poison.mkdir()
        os.chown(poison, OWNER, OWNER)
        marker = self.home / "executed.txt"
        payload = f"open({str(marker)!r},'w').write('EXECUTED')\n"
        for name in ("sitecustomize.py", "usercustomize.py", "json.py", "aresos_control.py"):
            (poison / name).write_text(payload)
        (poison / "attack.pth").write_text("import sitecustomize\n")
        user_site = self.home / f".local/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
        user_site.mkdir(parents=True)
        (user_site / "sitecustomize.py").write_text(payload)
        (user_site / "planted.pth").write_text("import sitecustomize\n")
        # Even a .pth in the trusted vendor tree must not be processed by site.
        planted_pth = Path(VENDOR) / "aresos-test.pth"
        planted_pth.write_text("import builtins; " + payload)
        env = {"PATH": str(poison), "PYTHONPATH": str(poison), "PYTHONHOME": str(poison),
               "PYTHONSTARTUP": str(poison / "sitecustomize.py"), "HOME": str(self.home)}
        try:
            result = self.launch(OWNER, ["cli", "testapp", "list"], env=env, cwd=poison)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["ok"])
            self.assertFalse(marker.exists())
            # Exercise the MCP launcher too, without executing Claude Code.
            process = subprocess.Popen(["/usr/bin/python3", "-I", "-S", LAUNCH, "proxy", "testapp"],
                                       preexec_fn=identity(OWNER), env=env, cwd=poison,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            initialize = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "fixture", "version": "1"}}}
            process.stdin.write(canonical(initialize) + "\n")
            process.stdin.flush()
            response = json.loads(process.stdout.readline())
            self.assertIn("result", response)
            process.terminate()
            process.communicate(timeout=10)
            self.assertFalse(marker.exists())
        finally:
            planted_pth.unlink()
        bad_mode = subprocess.run(["/usr/bin/python3", "-I", LAUNCH, "cli", "--help"], capture_output=True, text=True)
        self.assertNotEqual(bad_mode.returncode, 0)
        self.assertIn("isolated launcher", bad_mode.stderr)

    def test_simultaneous_same_id_calls_submit_once(self):
        from concurrent.futures import ThreadPoolExecutor
        prepared = self.call(OWNER, "testapp_prepare_send", message())
        self.assertTrue(prepared["ok"], prepared)
        approval = prepared["data"]["approval"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.call(OWNER, "testapp_send", approval), range(2)))
        self.assertTrue(all(r["ok"] for r in results), results)
        self.assertEqual(results[0]["data"], results[1]["data"])
        status = self.call(OWNER, "testapp_operation_status", {"operation_id": approval["operation_id"]})
        self.assertEqual(status["data"]["evidence"]["arrivals"], ["alpha", "beta", "hidden"])

    def test_writable_executable_chain_refused(self):
        prefix_file = Path("/usr/libexec/aresos-control/aresos_control/__init__.py")
        mode = prefix_file.stat().st_mode & 0o777
        try:
            prefix_file.chmod(0o666)
            result = self.launch(OWNER, ["cli", "--help"])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("root-owned", result.stderr)
        finally:
            prefix_file.chmod(mode)

    def test_protocol_bad_version_and_malformed_frame(self):
        self.assertFalse(self.request(OWNER, "act", {"v": 7, "method": "tools", "app": "testapp"})["ok"])
        def raw(code):
            return self.run_user(OWNER, "import socket,sys,json; s=socket.socket(socket.AF_UNIX); s.connect(sys.argv[1]); s.sendall(sys.argv[2].encode()); print(s.makefile().readline())",
                                 str(self.root / "sockets/act.sock"), code)
        self.assertFalse(raw("not json\n")["ok"])
        self.assertFalse(raw('{}\n{}\n')["ok"])
