import os
from pathlib import Path
import tempfile
import unittest

from aresos_control.engine import Engine
from aresos_control.definitions import BY_NAME

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

    def configure(self, failure="none", refuse=None):
        return self.data("testapp_fixture_configure", {"failure": failure, "refuse": refuse or []}, admin=True)
