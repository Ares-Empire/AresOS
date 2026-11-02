"""Verify retained version evidence using an extracted ISO SQLite RPM database.

Read-only ordinary files only. No rpm executable, package installation, mount,
network, firmware, host database or privileged operation is used.
"""
import hashlib
import json
import pathlib
import sqlite3
import struct
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
expected = json.loads((ROOT/'os/manifest/ci/14/parser-sources/packages.json').read_text())
path = pathlib.Path(sys.argv[1]).resolve()
assert path.is_relative_to(ROOT.resolve()), 'Use an extracted ordinary file inside this worktree'
assert not path.is_symlink() and path.is_file()
assert hashlib.sha256(path.read_bytes()).hexdigest() == expected['rpmdb']['sha256'], 'RPM database differs from pinned extraction'
database = sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True)
for package in expected['packages']:
    matches = []
    for blob, in database.execute('SELECT blob FROM Packages JOIN Name USING(hnum) WHERE key=?', (package['name'],)):
        count, size = struct.unpack('>II', blob[:8])
        data = blob[8+16*count:]
        assert len(data) == size
        tags = {}
        for offset in range(count):
            tag, kind, start, number = struct.unpack('>IIII', blob[8+16*offset:24+16*offset])
            if tag in (1000,1001,1002,1022,1044):
                assert kind == 6
                tags[tag] = data[start:].split(b'\0',1)[0].decode()
        if tags[1022] == package['arch']:
            matches.append(dict(name=tags[1000],version=tags[1001],release=tags[1002],arch=tags[1022],source_rpm=tags[1044]))
    assert matches == [package], 'Pinned RPM header missing, duplicated or changed: '+package['name']
database.close()
print('PASS', len(expected['packages']), 'exact pinned ISO RPM headers; SQLite read-only/immutable')
