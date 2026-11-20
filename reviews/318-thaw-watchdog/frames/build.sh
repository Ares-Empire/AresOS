#!/usr/bin/bash
# DEVELOPMENT AID of package 318 (copied from packages 49b and 41) (measurement only, never shipped): builds the frame recorder, a tiny Fabric mod
# that the rig adds to the development client with -Dfabric.addMods. Plain javac against Gradle's cached jars
# (Minecraft 26.2 has no obfuscation, so no remapping); writes only $1 (default: build/pkg41-frames.jar here).
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
out=${1:-$here/build/pkg41-frames.jar}
jdk=${JAVA_HOME:-$HOME/.local/opt/jdk-25}
cache=$HOME/.gradle/caches
cp="$cache/fabric-loom/26.2/minecraft-client-only.jar:$cache/fabric-loom/26.2/minecraft-common.jar"
cp+=":$(ls "$cache"/modules-2/files-2.1/net.fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/*/sponge-mixin-0.17.4+mixin.0.8.7.jar | grep -v sources)"
# Component's displayed button text implements Minecraft 26.2's Brigadier Message interface.
cp+=":$(ls "$cache"/modules-2/files-2.1/com.mojang/brigadier/1.3.10/*/brigadier-1.3.10.jar)"
mkdir -p "$here/../../../.work/pkg318"
work=$(mktemp -d "$here/../../../.work/pkg318/frames.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
"$jdk/bin/javac" --release 25 -proc:none -nowarn -cp "$cp" -d "$work" $(find "$here/src" -name '*.java')
cp -- "$here/fabric.mod.json" "$here/pkg41frames.mixins.json" "$work/"
mkdir -p -- "$(dirname -- "$out")"
rm -f -- "$out"
(cd -- "$work" && "$jdk/bin/jar" --create --file "$out" .)
echo "$out"
