"""Install the unit tests' device fixtures in the container's own /usr/bin."""
from pathlib import Path
import sys

sys.path.insert(0, '/harness/os/tests')
from level_sandbox import BRIGHTNESSCTL, WPCTL

PW_DUMP = '''#!/usr/bin/python3 -IS
# ARESOS-TEST-STAND-IN: the test's snapshot of the PipeWire graph.
import os
from pathlib import Path
import sys
assert sys.argv[1:] == ['-N']
print((Path(os.environ['STANDIN_DIR']) / 'graph.json').read_text())
'''

for name, text in (('brightnessctl', BRIGHTNESSCTL), ('wpctl', WPCTL), ('pw-dump', PW_DUMP)):
    path = Path('/usr/bin') / name
    path.write_text(text)
    path.chmod(0o755)
