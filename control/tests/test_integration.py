import asyncio
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from aresos_control.common import canonical
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

    def launch(self, uid, mode_args, input=None, env=None, cwd=None):
        return subprocess.run(["/usr/bin/python3", "-I", "-S", LAUNCH, *mode_args], preexec_fn=identity(uid),
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

    def test_cli_generated_help_admin_and_today_log(self):
        result = self.launch(OWNER, ["cli", "--help"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn((ROOT / "control/generated/cli-help.txt").read_text().strip(), result.stdout)
        detail = self.launch(OWNER, ["cli", "testapp", "send", "--help"])
        self.assertIn('"operation_id"', detail.stdout)
        listing = self.launch(OWNER, ["cli", "testapp", "list", "--json"])
        self.assertTrue(json.loads(listing.stdout)["ok"], listing.stderr)
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
                "/usr/bin/env", "-i", "PATH=/usr/bin:/bin", "LANG=C.UTF-8", "/usr/bin/python3", "-I", "-S", LAUNCH, "proxy", "testapp"])
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
                hook = self.launch(OWNER, ["hook"], input=canonical(hook_input))
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
        prompt = self.launch(OWNER, ["hook"], input=canonical(prompt_input))
        self.assertIn(prepared["operation_id"], json.loads(prompt.stdout)["hookSpecificOutput"]["additionalContext"])

    def test_proxy_isolated_from_planted_code_environment_and_pth(self):
        poison = self.home / "Documents/poison"
        poison.mkdir()
        os.chown(poison, OWNER, OWNER)
        marker = self.home / "executed.txt"
        payload = f"open({str(marker)!r},'w').write('EXECUTED')\n"
        for name in ("sitecustomize.py", "usercustomize.py", "json.py", "aresos_control.py"):
            (poison / name).write_text(payload)
        (poison / "attack.pth").write_text("import sitecustomize\n")
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
