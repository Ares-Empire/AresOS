import os
from pathlib import Path
import tempfile
import unittest

from aresos_control.engine import Engine
from aresos_control.definitions import BY_NAME
from response_checks import check_responses

check_responses()

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "control" / "test-work"
WORK.mkdir(parents=True, exist_ok=True)


def message(**changes):
    return {"account": "fixture", "to": ["alpha", "beta"], "cc": [], "bcc": ["hidden"],
            "subject": "Fixture message", "text": "Written in full", "attachments": [], **changes}


class EngineCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temp.name)
        self.engine = Engine(self.root / "state", self.root / "independent")

    def tearDown(self):
        self.engine.close()
        self.temp.cleanup()

    def restart(self):
        self.engine.close()
        self.engine = Engine(self.root / "state", self.root / "independent")

    def call(self, name, args=None, admin=False):
        return self.engine.request({"v": 1, "method": "call", "action": name, "arguments": args or {}}, admin)

    def data(self, name, args=None, admin=False):
        result = self.call(name, args, admin)
        self.assertTrue(result["ok"], result)
        from jsonschema import Draft202012Validator
        Draft202012Validator(BY_NAME[name].tool()["outputSchema"]).validate(result)
        return result["data"]

    def reserve(self, **changes):
        return self.data("testapp_prepare_send", message(**changes))["approval"]

    def upload(self, data, file_ref):
        import base64
        from concurrent.futures import ThreadPoolExecutor
        import socket
        from aresos_control.common import CHUNK_SIZE
        from aresos_control.protocol import receive, send
        caller, service = socket.socketpair()

        def client():
            with caller:
                ready = receive(caller)
                if not ready["ok"]:
                    return ready
                for offset in range(0, len(data), CHUNK_SIZE):
                    send(caller, {"offset": offset, "bytes": base64.b64encode(data[offset:offset + CHUNK_SIZE]).decode()})
                    response = receive(caller)
                    if not response["ok"]:
                        return response
                send(caller, {"end": True, "offset": len(data)})
                return receive(caller)

        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(client)
            with service:
                self.engine.transfer(service, {"v": 1, "method": "upload", "app": "testapp", "file": file_ref})
            return result.result(timeout=10)

    def configure(self, failure="none", refuse=None):
        return self.data("testapp_fixture_configure", {"failure": failure, "refuse": refuse or []}, admin=True)
