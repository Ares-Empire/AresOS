"""Caller-side descriptor-relative Linux file transfers. No home path reaches toold."""
import os
from pathlib import Path
import re
import stat

from .common import FILE_LIMIT, Refused, sha256

# Dot components are always blocked. These catch non-dot credential/profile and
# executable configuration directories, including aliases under an allowed root.
FORBIDDEN = {"ssh", "gnupg", "config", "credentials", "secrets", "autostart", "startup", "systemd",
             "google-chrome", "chromium", "firefox", "mozilla", "bravesoftware", "browser", "profiles",
             "default", "appdata", "library", "applications", "login data", "cookies", "authorized_keys",
             "id_rsa", "id_ed25519", "credentials.json", "credentials.db", "netrc"}


def safe_parts(path):
    parts = path.split("/")
    if any(not p or p.startswith(".") or p.casefold() in FORBIDDEN or
           p.casefold().startswith("profile ") or "\\" in p or
           any(ord(c) < 32 or ord(c) == 127 for c in p) for p in parts):
        raise Refused("file_refused", "Dotfiles, traversal, credential/configuration places and unsafe names are refused; choose a file in an allowed folder.")
    return parts


def safe_name(name):
    safe_parts(name)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _().-]{0,127}", name) or "/" in name or name.lower().endswith((".desktop", ".service", ".socket", ".timer", ".pth")):
        raise Refused("file_refused", "Use a simple file name of at most 128 characters; configuration/start-up file types are refused.")
    return name


class FilePolicy:
    def __init__(self, home, folders, limit=FILE_LIMIT):
        self.home = Path(home)
        self.roots = sorted([Path(p) for p in folders], key=lambda p: len(str(p)), reverse=True)
        self.limit = min(limit, FILE_LIMIT)
        if not self.home.is_absolute():
            raise ValueError("Home must be absolute")
        for root in self.roots:
            if not root.is_absolute() or root == self.home or not root.is_relative_to(self.home):
                raise ValueError("Allowed folders must be specific folders beneath the configured home")
            safe_parts(str(root).lstrip("/"))

    def locate(self, path):
        if not isinstance(path, str) or not path.startswith("/"):
            raise Refused("file_refused", "Use an absolute path in an allowed folder.")
        # Validate the original string BEFORE Path can normalize '.' or '//'.
        safe_parts(path[1:])
        target = Path(path)
        for root in self.roots:
            if target.is_relative_to(root):
                return root, list(target.relative_to(root).parts)
        raise Refused("file_refused", "Path is outside configured folders; choose Documents, Downloads, Desktop or an owner-configured folder.")

    def directory(self, path):
        # Opening from '/' protects the configured root itself as well as children.
        fd = os.open("/", os.O_PATH | os.O_DIRECTORY)
        try:
            parts = safe_parts(str(path).lstrip("/"))
            for index, part in enumerate(parts):
                access = os.O_RDONLY if index == len(parts) - 1 else os.O_PATH
                new_fd = os.open(part, access | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = new_fd
            return fd
        except BaseException:
            os.close(fd)
            raise

    def real_directory(self, fd, expected):
        actual = os.readlink(f"/proc/self/fd/{fd}")
        if actual != str(expected):
            raise Refused("file_refused", "Folder moved during transfer; nothing published, choose the folder again.")
        # Check the live path still names the pinned inode, without following links.
        other = self.directory(expected)
        try:
            a, b = os.fstat(fd), os.fstat(other)
            if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino):
                raise Refused("file_refused", "Destination or source folder was swapped during transfer; try again after it is stable.")
        finally:
            os.close(other)

    def read(self, path, checkpoint=lambda _: None):
        _, relative = self.locate(path)
        if not relative:
            raise Refused("file_refused", "Choose a regular file inside the folder.")
        parent = Path(path).parent
        parent_fd = fd = None
        try:
            parent_fd = self.directory(parent)
            fd = os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > self.limit:
                raise Refused("file_refused", "Only single-link regular files up to the configured size are allowed.")
            real_path = os.readlink(f"/proc/self/fd/{fd}")
            if real_path != path:
                raise Refused("file_refused", "File moved while opening; choose it again.")
            checkpoint("opened")
            data = bytearray()
            while len(data) <= self.limit:
                block = os.read(fd, min(65536, self.limit + 1 - len(data)))
                if not block:
                    break
                data.extend(block)
            after = os.fstat(fd)
            fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_nlink")
            if len(data) > self.limit or any(getattr(before, k) != getattr(after, k) for k in fields):
                raise Refused("file_refused", "File changed during import; import again when stable.")
            self.real_directory(parent_fd, parent)
            # A replacement after this point is harmless: all subsequent use is these bytes.
            return bytes(data), {"sha256": sha256(data), "size": len(data), "name": Path(path).name, "real_path": real_path}
        except OSError as exc:
            raise Refused("file_refused", "File path contains a link, missing or non-regular component, or is inaccessible; choose a safe regular file.") from exc
        finally:
            if fd is not None:
                os.close(fd)
            if parent_fd is not None:
                os.close(parent_fd)

    def save(self, folder, name, data, expected_hash, checkpoint=lambda _: None):
        self.locate(folder)
        safe_name(name)
        if len(data) > self.limit or sha256(data) != expected_hash:
            raise Refused("file_refused", "Download bytes exceed the limit or differ from their hash; save refused.")
        parent_fd, published, completed = None, False, False
        fd = None
        try:
            parent_fd = self.directory(Path(folder))
            # An unnamed inode cannot be substituted by another owner process.
            fd = os.open(".", os.O_WRONLY | os.O_TMPFILE, 0o600, dir_fd=parent_fd)
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(data)
                stream.flush()
            os.fsync(fd)
            checkpoint("written")
            self.real_directory(parent_fd, Path(folder))
            # link() publishes atomically without overwriting any file, symlink or hard link.
            os.link(f"/proc/self/fd/{fd}", name, dst_dir_fd=parent_fd, follow_symlinks=True)
            published = True
            checkpoint("published")
            self.real_directory(parent_fd, Path(folder))
            check = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            own = os.fstat(fd)
            if (check.st_dev, check.st_ino, check.st_nlink) != (own.st_dev, own.st_ino, 1):
                raise Refused("file_refused", "Published destination was replaced or linked; save refused.")
            os.fsync(parent_fd)
            completed = True
            return {"path": str(Path(folder) / name), "sha256": expected_hash, "size": len(data)}
        except OSError as exc:
            raise Refused("file_refused", "Destination already exists, is linked, moved or inaccessible; choose a new safe file name.") from exc
        finally:
            if published and not completed and parent_fd is not None and fd is not None:
                # Remove only our inode. A racing caller's replacement is never overwritten/unlinked.
                try:
                    current, own = os.stat(name, dir_fd=parent_fd, follow_symlinks=False), os.fstat(fd)
                    if (current.st_dev, current.st_ino) == (own.st_dev, own.st_ino):
                        os.unlink(name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
            if fd is not None:
                os.close(fd)
            if parent_fd is not None:
                os.close(parent_fd)
