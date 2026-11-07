import base64
import json
import os
from pathlib import Path
import stat

from aresos_control.common import FILE_LIMIT, Refused, digest, sha256
from aresos_control.files import FilePolicy
from support import EngineCase


class Files(EngineCase):
    def setUp(self):
        super().setUp()
        self.home = self.root / "home"
        self.allowed = self.home / "Documents"
        self.allowed.mkdir(parents=True)
        self.policy = FilePolicy(str(self.home), [str(self.allowed)])

    def test_read_regular_real_path_size_and_opened_descriptor(self):
        file = self.allowed / "notes.txt"
        file.write_bytes(b"snapshot")
        data, ref = self.policy.read(str(file))
        self.assertEqual(ref, {"sha256": sha256(b"snapshot"), "size": 8, "name": "notes.txt", "real_path": str(file)})
        self.assertEqual(data, b"snapshot")
        file.write_bytes(b"x" * (FILE_LIMIT + 1))
        with self.assertRaises(Refused):
            self.policy.read(str(file))
        file.write_bytes(b"before")

        def replace(_):
            file.rename(self.allowed / "old.txt")
            file.write_bytes(b"new secret")

        # A renamed original changes ctime: fail closed while the read is in progress.
        with self.assertRaises(Refused):
            self.policy.read(str(file), replace)

    def test_read_refuses_traversal_dotfiles_credentials_links_nonregular(self):
        file = self.allowed / "good.txt"
        file.write_bytes(b"good")
        secret = self.home / ".ssh"
        secret.mkdir()
        (secret / "id_rsa").write_bytes(b"fixture secret")
        os.symlink(file, self.allowed / "symlink.txt")
        os.symlink(secret, self.allowed / "linked-dir")
        os.link(secret / "id_rsa", self.allowed / "hardlink.txt")
        os.mkfifo(self.allowed / "fifo")
        (self.allowed / "folder").mkdir()
        bad = ["../.ssh/id_rsa", "folder/../good.txt", "./good.txt", ".hidden", "config/token", "browser/Profile 1/Cookies",
               "credentials.json", "symlink.txt", "linked-dir/id_rsa", "hardlink.txt", "fifo", "folder", "a//b", "bad\\name"]
        for name in bad:
            with self.subTest(name=name), self.assertRaises(Refused):
                self.policy.read(str(self.allowed) + "/" + name)
        with self.assertRaises(Refused):
            self.policy.read(str(secret / "id_rsa"))
        # Reject configured roots which themselves traverse symlinks.
        alias = self.home / "Alias"
        os.symlink(self.allowed, alias)
        with self.assertRaises(Refused):
            FilePolicy(str(self.home), [str(alias)]).read(str(alias / "good.txt"))

    def test_source_content_and_parent_races_refused(self):
        file = self.allowed / "race.txt"
        file.write_bytes(b"safe")
        with self.assertRaises(Refused):
            self.policy.read(str(file), lambda _: file.write_bytes(b"different"))
        file.write_bytes(b"safe")

        def swap_parent(_):
            self.allowed.rename(self.home / "Moved")
            self.allowed.mkdir()
            (self.allowed / "race.txt").write_bytes(b"other")

        with self.assertRaises(Refused):
            self.policy.read(str(file), swap_parent)

    def test_import_immutable_hash_bytes_even_after_source_replacement(self):
        file = self.allowed / "attachment.txt"
        file.write_bytes(b"approved bytes")
        data, ref = self.policy.read(str(file))
        imported = self.engine.request({"v": 1, "method": "upload", "app": "testapp", "file": ref, "bytes": base64.b64encode(data).decode()})
        self.assertTrue(imported["ok"], imported)
        self.assertEqual(stat.S_IMODE((self.root / "state/blobs" / ref["sha256"]).stat().st_mode), 0o400)
        approval = self.reserve(attachments=[ref])
        self.assertEqual(approval["description"]["attachments"][0]["real_path"], str(file))
        file.unlink()
        file.write_bytes(b"replacement bytes")
        self.data("testapp_send", approval)
        payload = json.loads(self.engine.receiver.db.execute("SELECT payload FROM arrivals WHERE op=? LIMIT 1", (approval["operation_id"],)).fetchone()[0])
        self.assertEqual(bytes.fromhex(payload["attachment_bytes"][0]), b"approved bytes")
        self.assertEqual(payload["attachments"][0]["sha256"], sha256(b"approved bytes"))
        changed_ref = {**ref, "name": "misleading.txt"}
        from support import message
        self.assertFalse(self.call("testapp_prepare_send", message(attachments=[changed_ref]))["ok"])
        # Corruption of the service blob must refuse BEFORE submitting.
        approval2 = self.reserve(attachments=[ref])
        blob = self.root / "state/blobs" / ref["sha256"]
        blob.chmod(0o600)
        blob.write_bytes(b"corrupt")
        self.assertFalse(self.call("testapp_send", approval2)["ok"])
        self.assertEqual(self.engine.receiver.evidence(approval2["operation_id"])["arrivals"], [])

    def test_save_exclusive_no_traversal_config_symlink_or_hardlink(self):
        data, key = b"download", sha256(b"download")
        result = self.policy.save(str(self.allowed), "saved.txt", data, key)
        saved = self.allowed / "saved.txt"
        self.assertEqual(saved.read_bytes(), data)
        self.assertEqual(saved.stat().st_nlink, 1)
        self.assertEqual(result["path"], str(saved))
        secret = self.home / "secret.txt"
        secret.write_bytes(b"never overwrite")
        os.symlink(secret, self.allowed / "link.txt")
        os.link(secret, self.allowed / "hard.txt")
        for name in ["saved.txt", "link.txt", "hard.txt", "../escape.txt", ".bashrc", "authorized_keys", "run.desktop", "x.pth", "config/file", "a/b", "bad\\name", "bad\nname"]:
            with self.subTest(name=name), self.assertRaises(Refused):
                self.policy.save(str(self.allowed), name, data, key)
        for folder in [self.home / ".config", self.allowed / "autostart", self.home]:
            folder.mkdir(exist_ok=True)
            with self.subTest(folder=folder), self.assertRaises(Refused):
                self.policy.save(str(folder), "x.txt", data, key)
        self.assertEqual(secret.read_bytes(), b"never overwrite")
        with self.assertRaises(Refused):
            self.policy.save(str(self.allowed), "bad-hash.txt", data, "0" * 64)
        with self.assertRaises(Refused):
            self.policy.save(str(self.allowed), "oversize.txt", b"x" * (FILE_LIMIT + 1), "0" * 64)

    def test_save_destination_swaps_and_link_races_fail_closed(self):
        data, key = b"snapshot", sha256(b"snapshot")

        def swap_before_publish(_):
            self.allowed.rename(self.home / "Moved")
            os.symlink(self.home / "Moved", self.allowed)

        with self.assertRaises(Refused):
            self.policy.save(str(self.allowed), "never.txt", data, key, swap_before_publish)
        self.assertFalse((self.home / "Moved/never.txt").exists())
        self.allowed.unlink()
        (self.home / "Moved").rename(self.allowed)

        def collide(_):
            (self.allowed / "collision.txt").write_bytes(b"winner")

        with self.assertRaises(Refused):
            self.policy.save(str(self.allowed), "collision.txt", data, key, collide)
        self.assertEqual((self.allowed / "collision.txt").read_bytes(), b"winner")

        def link_published(point):
            if point == "published":
                os.link(self.allowed / "linked.txt", self.allowed / "alias.txt")

        with self.assertRaises(Refused):
            self.policy.save(str(self.allowed), "linked.txt", data, key, link_published)
        self.assertFalse((self.allowed / "linked.txt").exists())

        def swap_after_publish(point):
            if point == "published":
                self.allowed.rename(self.home / "MovedAgain")
                self.allowed.mkdir()

        with self.assertRaises(Refused):
            self.policy.save(str(self.allowed), "moved.txt", data, key, swap_after_publish)
        self.assertFalse((self.home / "MovedAgain/moved.txt").exists())

    def test_download_hash_and_private_transfer_metadata_checks(self):
        blob = self.engine.blobs.put(b"bytes")
        result = self.engine.request({"v": 1, "method": "download", "app": "testapp", "sha256": blob})
        self.assertTrue(result["ok"], result)
        self.assertEqual(base64.b64decode(result["data"]["bytes"]), b"bytes")
        invalid = self.engine.request({"v": 1, "method": "upload", "app": "testapp", "file": {"sha256": blob, "size": 5, "name": "file", "real_path": "/fixture/path"}, "bytes": base64.b64encode(b"wrong").decode()})
        self.assertFalse(invalid["ok"])
        self.assertFalse(self.engine.request({"v": 1, "method": "download", "app": "testapp", "sha256": "../control.sqlite"})["ok"])
