#!/usr/bin/bash
# Package 328 rig: stops every scope the rig started (pkg328-*) and nothing else; run-hub.sh, stopped with them, stops
# its own aresos-dev-run-hub-* scopes. The owner's session and other builders' runs are in scopes of other names.
units=$(systemctl --user list-units --all --no-legend --plain 'pkg328-*' | /usr/bin/awk '{print $1}')
[[ -z $units ]] || systemctl --user stop $units
systemctl --user list-units --all --no-legend --plain 'pkg328-*'
