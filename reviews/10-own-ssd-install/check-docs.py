"""Check links and shell syntax without executing any installation command."""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[2]
files = [root / name for name in (
    'README.md', 'docs/INSTALL.md', 'docs/INSTALL-RECORD.md',
    'docs/INSTALL-SAME-DRIVE.md', 'docs/INSTALL-RECORD-SAME-DRIVE.md',
    'docs/design/OS-BASE.md',
)]
for name in (
    'reviews/10-own-ssd-install/REPORT.md',
    'reviews/10b-own-ssd-fixes/REPORT.md',
    'reviews/councils/2026-10-22-own-ssd/CHANGES.md',
):
    report = root / name
    if report.exists():
        files.append(report)


def anchors(path):
    result, seen = set(), {}
    for heading in re.findall(r'^#{1,6} (.+)$', path.read_text(encoding='utf-8'), re.M):
        slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        suffix = seen.get(slug, 0)
        seen[slug] = suffix + 1
        result.add(f'{slug}-{suffix}' if suffix else slug)
    result.update(re.findall(r'<a id="([^"]+)"', path.read_text(encoding='utf-8')))
    return result


links = 0
linux_blocks = []
for path in files:
    content = path.read_text(encoding='utf-8')
    assert len(re.findall(r'^[ \t]*```', content, re.M)) % 2 == 0, path
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if '://' in target:
            continue
        name, _, anchor = target.partition('#')
        destination = (path.parent / name).resolve() if name else path
        assert destination.exists(), (path, target)
        if anchor:
            assert anchor in anchors(destination), (path, target)
        links += 1
    refs = set(re.findall(r'^\[([^\]]+)\]:', content, re.M))
    prose = re.sub(r'^[ \t]*```.*?^[ \t]*```', '', content, flags=re.M | re.S)
    prose = re.sub(r'`[^`]*`', '', prose)
    used = set(re.findall(r'\[([A-Z][A-Z0-9]*)\](?![(:])', prose))
    assert used <= refs, (path, used - refs)
    linux_blocks.extend(re.findall(r'^[ \t]*```bash\n(.*?)^[ \t]*```', content, re.M | re.S))

scratch = root / '.work' / '10-linux-syntax.sh'
scratch.parent.mkdir(exist_ok=True)
scratch.write_bytes(('\n'.join(linux_blocks) + '\n').encode())
subprocess.run(['bash', '-n', scratch.relative_to(root).as_posix()], cwd=root, check=True)
print(f'PASS: {len(files)} Markdown files; {links} local links/anchors; reference labels and fences; {len(linux_blocks)} Linux blocks pass bash -n (not executed).')
