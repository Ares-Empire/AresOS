"""Create VM-only credentials; neither credentials nor the disk are uploaded."""
import crypt
import json
import pathlib
import secrets
import sys

stock = '--stock' in sys.argv
work = pathlib.Path('switch-work' if stock else 'vm-work')
work.mkdir(exist_ok=True)
password = secrets.token_hex(24)
(work / 'credentials.json').write_text(json.dumps({'password': password}))
(work / 'credentials.json').chmod(0o600)
hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
# The image builder logs user customization, including the password hash.
# Register both forms before its output can reach GitHub's retained logs.
print(f'::add-mask::{password}', flush=True)
print(f'::add-mask::{hashed}', flush=True)
(work / 'config.toml').write_text(f'''[[customizations.user]]
name = "{'ares-recovery' if stock else 'root'}"
password = "{hashed}"
{('groups = ["wheel"]' if stock else '')}

[customizations.kernel]
append = "console=tty0 console=ttyS0,115200n8 systemd.show_status=yes"

[[customizations.filesystem]]
mountpoint = "/"
minsize = "{'48 GiB' if stock else '28 GiB'}"
''')
(work / 'config.toml').chmod(0o600)
