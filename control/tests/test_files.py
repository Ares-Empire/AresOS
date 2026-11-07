import base64
import json
import os
from pathlib import Path
import stat
from unittest.mock import patch

from aresos_control.common import FILE_LIMIT, Refused, digest, sha256
from aresos_control.files import FilePolicy
from support import EngineCase, ROOT


class Files(EngineCase):
    def setUp(self):
        super().setUp()
        self.home = self.root / "home"
        self.allowed = self.home / "Documents"
        self.allowed.mkdir(parents=True)
        self.policy = FilePolicy(str(self.home), [str(self.allowed)])

    def test_file_limit_defaults_agree_and_configuration_can_raise_them(self):
        self.assertEqual(FILE_LIMIT, 26214400)
        self.assertEqual(self.policy.limit, FILE_LIMIT)
        self.assertEqual(self.engine.blobs.limit, FILE_LIMIT)
        for setting in ("proxy", "service"):
            self.assertEqual(json.loads((ROOT / f"control/settings/{setting}.json").read_text())["file_limit"], FILE_LIMIT)
        file = self.allowed / "raised-limit.bin"
        with file.open("wb") as stream:
            stream.truncate(FILE_LIMIT + 1)
        policy = FilePolicy(str(self.home), [str(self.allowed)], limit=FILE_LIMIT + 1)
        data, ref = policy.read(str(file))
        self.assertEqual(len(data), FILE_LIMIT + 1)
        from aresos_control.blobs import Blobs
        blobs = Blobs(self.root / "raised-blobs", limit=FILE_LIMIT + 1)
        self.assertEqual(blobs.put(data), ref["sha256"])
        self.assertEqual(blobs.read(ref["sha256"]), data)

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
        imported = self.upload(data, ref)
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

        with self.assertRaises(Refused) as linked_error:
            self.policy.save(str(self.allowed), "linked.txt", data, key, link_published)
        self.assertEqual((self.allowed / "linked.txt").read_bytes(), b"")
        self.assertEqual((self.allowed / "alias.txt").read_bytes(), b"")
        self.assertIn("0 bytes, 2 remaining links", str(linked_error.exception))
        self.assertIn(str(self.allowed / "linked.txt"), str(linked_error.exception))

        def swap_after_publish(point):
            if point == "published":
                self.allowed.rename(self.home / "MovedAgain")
                self.allowed.mkdir()

        with self.assertRaises(Refused) as moved_error:
            self.policy.save(str(self.allowed), "moved.txt", data, key, swap_after_publish)
        moved = self.home / "MovedAgain/moved.txt"
        self.assertEqual(moved.read_bytes(), b"")
        self.assertIn(str(moved.parent), str(moved_error.exception))
        self.assertIn("No directory entries removed", str(moved_error.exception))

    def test_download_hash_and_private_transfer_metadata_checks(self):
        blob = self.engine.blobs.put(b"bytes", origin="export")
        result = self.engine.request({"v": 1, "method": "download", "app": "testapp", "sha256": blob})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"], {"sha256": blob, "size": 5})
        self.assertEqual(self.engine.blobs.read(blob), b"bytes")
        invalid = self.engine.request({"v": 1, "method": "upload", "app": "testapp", "file": {"sha256": blob, "size": 5, "name": "file", "real_path": "/fixture/path"}, "bytes": base64.b64encode(b"wrong").decode()})
        self.assertFalse(invalid["ok"])
        self.assertFalse(self.engine.request({"v": 1, "method": "download", "app": "testapp", "sha256": "../control.sqlite"})["ok"])

    def test_failed_save_cleanup_preserves_a_racing_replacement(self):
        saved = self.allowed / "race.txt"
        moved = self.home / "moved-export.txt"
        original_stat, original_truncate = os.stat, os.ftruncate
        replacement = None

        def replace():
            nonlocal replacement
            if replacement is None:
                saved.rename(moved)
                saved.write_bytes(b"unrelated replacement")
                saved.chmod(0o640)
                replacement = saved.stat()

        def checked_then_replaced(path, *args, **kwargs):
            result = original_stat(path, *args, **kwargs)
            if path == saved.name and kwargs.get("dir_fd") is not None:
                replace()
            return result

        def truncate_pinned(fd, size):
            replace()
            return original_truncate(fd, size)

        def fail(point):
            if point == "published":
                raise Refused("file_refused", "fixture: reject after publication")

        with patch("aresos_control.files.os.stat", side_effect=checked_then_replaced), \
             patch("aresos_control.files.os.ftruncate", side_effect=truncate_pinned), self.assertRaises(Refused):
            self.policy.save(str(self.allowed), saved.name, b"exported", sha256(b"exported"), fail)
        self.assertIsNotNone(replacement)
        self.assertTrue(saved.exists(), "cleanup deleted the replacement")
        self.assertEqual(saved.stat(), replacement)
        self.assertEqual(saved.read_bytes(), b"unrelated replacement")
        self.assertEqual(moved.read_bytes(), b"")

    def test_failed_save_clears_hardlink_alias_outside_allowed_folders(self):
        saved, alias = self.allowed / "linked.txt", self.home / "outside-alias.txt"

        def link(point):
            if point == "published":
                os.link(saved, alias)

        with self.assertRaises(Refused):
            self.policy.save(str(self.allowed), saved.name, b"exported", sha256(b"exported"), link)
        self.assertEqual(alias.read_bytes(), b"", "refused save left readable exported bytes in an alias")

    def test_failed_save_reports_rollback_storage_failures_honestly(self):
        for fault in ("truncate", "sync"):
            with self.subTest(fault=fault):
                saved, alias = self.allowed / (fault + ".txt"), self.home / (fault + "-alias.txt")
                published = False
                original_sync = os.fsync

                def fail(point):
                    nonlocal published
                    if point == "published":
                        published = True
                        os.link(saved, alias)
                        raise Refused("file_refused", "fixture: fail after publication")

                def sync(fd):
                    if published and fault == "sync":
                        raise OSError("fixture: sync failed")
                    return original_sync(fd)

                truncate = (patch("aresos_control.files.os.ftruncate", side_effect=OSError("fixture: truncate failed"))
                            if fault == "truncate" else patch("aresos_control.files.os.ftruncate", wraps=os.ftruncate))
                with patch("aresos_control.files.os.fsync", side_effect=sync), truncate:
                    with self.assertRaises(Refused) as error:
                        self.policy.save(str(self.allowed), saved.name, b"exported", sha256(b"exported"), fail)
                self.assertEqual(error.exception.code, "save_incomplete")
                self.assertIn(str(saved), str(error.exception))
                self.assertIn("inode " + str(alias.stat().st_ino), str(error.exception))
                self.assertIn("bytes may remain readable", str(error.exception))
                self.assertEqual(alias.read_bytes(), b"exported" if fault == "truncate" else b"")
