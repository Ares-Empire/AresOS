"""Create VM-only credentials; neither credentials nor the disk are uploaded."""
import crypt
import json
import pathlib
import secrets

work = pathlib.Path('vm-work')
work.mkdir(exist_ok=True)
password = secrets.token_hex(24)
(work / 'credentials.json').write_text(json.dumps({'password': password}))
(work / 'credentials.json').chmod(0o600)
hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
(work / 'config.toml').write_text(f'''[[customizations.user]]
name = "root"
password = "{hashed}"

[customizations.kernel]
append = "console=tty0 console=ttyS0,115200n8 systemd.show_status=yes"

[[customizations.filesystem]]
mountpoint = "/"
minsize = "28 GiB"
''')
(work / 'config.toml').chmod(0o600)
