"""Physical QMP positions from the exact ISO maps and pinned QEMU key database.

Only printable ASCII, Return and the qualification's umlaut are admitted.
Dead-key symbols are never treated as emitted characters. No typed secret or
its key sequence is retained by this module.
"""
import csv
import hashlib
import json
import io
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
_MAPS = None


def maps():
    global _MAPS
    if _MAPS is not None:
        return _MAPS
    folder = ROOT / 'os/manifest/ci/14/keyboard-sources'
    index = json.loads((folder / 'index.json').read_text())
    csv_path = ROOT / 'os/manifest/ci/13/13f-zero-cost/qemu-keymap.csv'
    source, = [row for row in json.loads(csv_path.with_name('sources.json').read_text()) if row['file'] == csv_path.name]
    assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == source['sha256']
    codes = {}
    for row in csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8'))):
        if row['Linux Keycode'] and row['QEMU QKeyCode']:
            code = int(row['Linux Keycode'], 0)
            if code not in (*range(1, 55), 56, 57, 58, 86):
                continue
            if code in codes:
                assert codes[code] == row['QEMU QKeyCode']
            codes[code] = row['QEMU QKeyCode']
    result = {}
    for source in index:
        data = (folder / source['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == source['sha256']
        profile = source['file'].removesuffix('.map')
        table = {'\n': [codes[28]]}
        # Prefer base/Shift over AltGr. These columns share the XKB modifier
        # semantics; all three actual ISO maps explicitly declare 0-127.
        rows = re.findall(r'^keycode (\d+) = (.+)$', data.decode(), re.M)
        for column, modifiers in ((0, []), (1, ['shift']), (2, ['alt_r']), (3, ['shift', 'alt_r'])):
            for code, symbols in rows:
                token = symbols.split()[column].removeprefix('+')
                if not re.fullmatch(r'U\+[0-9a-fA-F]{4,6}', token):
                    continue
                char = chr(int(token[2:], 16))
                if (32 <= ord(char) <= 126 or char == 'ü') and int(code) in codes:
                    table.setdefault(char, [*modifiers, codes[int(code)]])
        result[profile] = table
    assert result['de']['y'] == ['z'] and result['de']['z'] == ['y']
    assert result['de']['ü'] == ['bracket_left']
    assert result['us-intl']['ü'] == ['alt_r', 'y']
    assert 'ü' not in result['us']
    _MAPS = result
    return result


def physical_keys(char, profile):
    assert isinstance(char, str) and len(char) == 1 and profile in ('de', 'us', 'us-intl')
    assert char in maps()[profile], 'Unknown or untypeable physical character'
    return maps()[profile][char]


def at_keycodes():
    """Static evdev keymap indices, not observed or typed input events."""
    keys = {key for profile in maps().values() for chord in profile.values() for key in chord}
    keys.update(('ctrl', 'alt', 'f2', 'f3', 'f4', 'u', 'd'))
    path = ROOT / 'os/manifest/ci/13/13f-zero-cost/qemu-keymap.csv'
    # maps() already verifies this exact pinned keycodemapdb file's SHA-256.
    rows = {r['QEMU QKeyCode']: r for r in csv.DictReader(io.StringIO(path.read_text()))
            if r['Linux Keycode'] and r['AT set1 keycode']}
    result = {}
    for key in keys:
        # The selected name is AT *Translated*: atkbd_set_keycode_table
        # indexes set1 and untranslates to its set2 defaults internally.
        scan = int(rows[key]['AT set1 keycode'], 0)
        index = (scan & 0x7f) | (0x80 if scan >> 8 == 0xe0 else 0)
        code = int(rows[key]['Linux Keycode'], 0)
        assert index not in result or result[index] == code, 'Ambiguous AT keymap'
        result[index] = code
    return dict(sorted(result.items()))
