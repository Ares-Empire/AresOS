"""Check documentation mechanics only; never execute an installation command."""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[2]
files = [root / name for name in (
    'README.md', 'docs/INSTALL.md', 'docs/INSTALL-RECORD.md',
    'docs/design/OS-BASE.md', 'reviews/councils/2026-10-21-dual-boot/CHANGES.md',
    'reviews/05b-dual-boot-fixes/REPORT.md',
)]

def anchors(path):
    result, seen = set(), {}
    for heading in re.findall(r'^#{1,6} (.+)$', path.read_text(encoding='utf-8'), re.M):
        slug = re.sub(r'[^\w\- ]', '', heading.lower()).replace(' ', '-')
        suffix = seen.get(slug, 0)
        seen[slug] = suffix + 1
        result.add(f'{slug}-{suffix}' if suffix else slug)
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
    if path.name == 'INSTALL-RECORD.md':
        linux_blocks = re.findall(r'^```bash\n(.*?)^```', content, re.M | re.S)

scratch = root / '.work' / '05b-linux-syntax.sh'
scratch.parent.mkdir(exist_ok=True)
scratch.write_bytes(('\n'.join(linux_blocks) + '\n').encode())
subprocess.run(['bash', '-n', scratch.relative_to(root).as_posix()], cwd=root, check=True)
print(f'PASS: {len(files)} Markdown files; {links} local links/anchors; balanced fences; {len(linux_blocks)} Linux blocks pass bash -n (not executed).')
