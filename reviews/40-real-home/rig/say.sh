#!/bin/bash
# DEVELOPMENT AID of package 40, headless use only: this rig calls Gradle directly (inner.sh runs gradlew runClient).
# Rig tool: type a chat line or command into the game. usage: say.sh <rig> <text>
echo "key t" > "$1/vin"; sleep 0.4; echo "type $2" > "$1/vin"; sleep 0.3; echo "key enter" > "$1/vin"; sleep 0.5
