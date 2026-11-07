"""Maintainer helper: resolve ONLY, no installation; run inside a Linux container.

python3 control/ci/lock.py VERSION DIR
Then review the lock diff. Production supports x86_64 CPython 3.14 and 3.15.
"""
import email
import hashlib
from pathlib import Path
import subprocess
import sys
import zipfile

version, directory = sys.argv[1:]
work = Path(directory)
work.mkdir(parents=True, exist_ok=True)
for python in ("314", "315"):
    subprocess.run([sys.executable, "-m", "pip", "download", "--no-cache-dir", "--platform", "manylinux2014_x86_64",
                    "--python-version", python, "--only-binary=:all:", "--dest", str(work), "mcp==" + version], check=True)
entries = {}
for path in work.glob("*.whl"):
    with zipfile.ZipFile(path) as archive:
        meta = email.message_from_bytes(archive.read(next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))))
    key = meta["Name"].lower().replace("_", "-"), meta["Version"]
    entries.setdefault(key, set()).add(hashlib.sha256(path.read_bytes()).hexdigest())
print("# Linux x86_64 CPython 3.14/3.15; official MCP SDK and transitive dependencies.")
for (name, version), hashes in sorted(entries.items()):
    print(name + "==" + version + " \\\n" + " \\\n".join("    --hash=sha256:" + h for h in sorted(hashes)))
