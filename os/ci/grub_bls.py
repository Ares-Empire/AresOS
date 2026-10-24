"""The pinned OSTree/Fedora blscfg rule, checked against actual entries and status."""
import pathlib
import re


class StockSelectionError(ValueError):
    pass


def deployment_checksum(path):
    match = re.fullmatch(r'([0-9a-f]{64})\.[0-9]+', pathlib.PurePosixPath(path).name)
    return match[1] if match else None


def stock_bls_entry(entries, stock, deployments=None):
    matches = [e for e in entries if deployment_checksum(e['deployment']) == stock]
    if not matches:
        raise StockSelectionError('No BLS entry resolves to the recorded stock checksum')
    if len(matches) != 1:
        raise StockSelectionError('Several BLS entries resolve to the recorded stock checksum')
    # 2026.4 writes reverse-index bare filenames; Fedora 2.12-66 compares those
    # filenames numerically, descending, ignoring the BLS version field.
    checked = []
    for entry in entries:
        filename = re.fullmatch(r'ostree-([1-9][0-9]*)', entry['id'])
        title = re.fullmatch(r'.+ \(ostree:([0-9]+)\)', entry['title'])
        versions = re.findall(r'^version ([1-9][0-9]*)$', entry['content'], re.M)
        titles = re.findall(r'^title (.+)$', entry['content'], re.M)
        if not filename or not title or len(versions) != 1 or titles != [entry['title']]:
            raise StockSelectionError('BLS position disagreement: entry is outside the verified pinned naming/title/version rule')
        checked.append((int(filename[1]), int(title[1]), int(versions[0]), entry))
    ordered = sorted(checked, reverse=True, key=lambda item: item[0])
    if deployments is not None and len(deployments) != len(ordered):
        raise StockSelectionError('BLS position disagreement: deployment and entry counts differ')
    for index, (filename, title, version, entry) in enumerate(ordered):
        if filename != len(ordered) - index or version != filename or title != index:
            raise StockSelectionError('BLS position disagreement: filename order, title index and version do not agree')
        if deployments is not None and deployment_checksum(entry['deployment']) != deployments[index]['checksum']:
            raise StockSelectionError('BLS position disagreement: rpm-ostree deployment index differs')
    position = next(i for i, item in enumerate(ordered) if item[3] is matches[0])
    if position == 0:
        raise StockSelectionError('BLS position disagreement: stock is already the default, not the previous entry')
    return dict(matches[0], menu_index=position, menu_titles=[item[3]['title'] for item in ordered],
                menu_ids=[item[3]['id'] for item in ordered], rule='11l-pinned-ostree-blscfg-order')


def confirm_menu_ocr(text, backup):
    # Check ordered entry lines, not title occurrences anywhere in a frame.
    normalize = lambda value: re.sub(r'[^a-z0-9]', '', value.lower())
    observed = []
    for line in text.splitlines():
        match = re.search(r'(Bazzite(?: [^()]*)?\s*\(\s*ostree\s*:\s*[0-9]+\s*\))', line, re.I)
        if match:
            observed.append(normalize(match[1]))
    if observed != [normalize(title) for title in backup['menu_titles']] or backup['menu_index'] <= 0:
        raise StockSelectionError('GRUB OCR position disagreement: stock title/line and AresOS line 0 do not match the verified order')
    return dict(status='passed', menu_titles=backup['menu_titles'], stock_position=backup['menu_index'],
                stock_title=backup['title'], aresos_title=backup['menu_titles'][0], before_any_selection_key=True)
