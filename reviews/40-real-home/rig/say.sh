#!/bin/bash
# Rig tool: type a chat line or command into the game. usage: say.sh <rig> <text>
echo "key t" > "$1/vin"; sleep 0.4; echo "type $2" > "$1/vin"; sleep 0.3; echo "key enter" > "$1/vin"; sleep 0.5
