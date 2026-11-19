#!/usr/bin/env bash
# Build and publish Zone Interdite releases on GitHub.
#
#   tools/release.sh full <version> ["notes"]   Full Windows build (exe + pck), zipped, released as base-<version>.
#                                                Sets application/config/version. Players download this once.
#   tools/release.sh patch <version> ["notes"]  A patch .pck with only the files changed since the base build and
#                                                every earlier patch, released as patch-<base>-<version>. The game
#                                                downloads it from the title screen and restarts to apply it.
#
# Base packs and patches are kept in build/base/<base>/ and build/patches/<base>/ (gitignored), because each new
# patch is diffed against them. Don't delete them.
set -euo pipefail
cd "$(dirname "$0")/.."
GODOT="${GODOT:-$USERPROFILE/Downloads/Godot_v4.7.2-stable_win64.exe/Godot_v4.7.2-stable_win64_console.exe}"
REPO="niko202390/zone-interdite"
mode="${1:?full|patch}"; ver="${2:?version}"; notes="${3:-}"

base_version() { sed -n 's/^config\/version="\(.*\)"$/\1/p' game/project.godot; }

case "$mode" in
full)
  sed -i "s/^config\/version=\".*\"$/config\/version=\"$ver\"/" game/project.godot
  rm -rf build/windows && mkdir -p build/windows "build/base/$ver"
  "$GODOT" --headless --path game --export-release "Windows Desktop" "../build/windows/ZoneInterdite.exe"
  cp build/windows/ZoneInterdite.pck "build/base/$ver/ZoneInterdite.pck"
  zip="build/ZoneInterdite-$ver.zip"
  rm -f "$zip"
  powershell.exe -NoProfile -Command "Compress-Archive -Path 'build\\windows\\*' -DestinationPath '${zip//\//\\}' -CompressionLevel Fastest -Force"
  gh release create "base-$ver" "$zip" --repo "$REPO" --prerelease --title "Zone Interdite $ver (full build)" \
    --notes "Full Windows build $ver. Unzip, keep ZoneInterdite.exe and ZoneInterdite.pck together, and run the exe. Later updates download themselves from the title screen.

$notes"
  ;;
patch)
  base="$(base_version)"
  [ -f "build/base/$base/ZoneInterdite.pck" ] || { echo "No base pack for $base in build/base/$base"; exit 1; }
  mkdir -p "build/patches/$base"
  packs="build/base/$base/ZoneInterdite.pck"
  for p in $(ls "build/patches/$base"/patch-*.pck 2>/dev/null | sort -V); do packs="$packs,$p"; done
  abs=""
  IFS=',' read -ra arr <<< "$packs"
  for p in "${arr[@]}"; do abs="$abs,$(cd "$(dirname "$p")" && pwd -W)/$(basename "$p")"; done
  out="build/patches/$base/patch-$base-$ver.pck"
  "$GODOT" --headless --path game --export-patch "Windows Desktop" "../$out" --patches "${abs#,}"
  sha=$(sha256sum "$out" | cut -d' ' -f1)
  size=$(stat -c %s "$out")
  echo "patch $ver: $size bytes, sha256 $sha"
  gh release create "patch-$base-$ver" "$out" --repo "$REPO" --prerelease --title "Patch $ver (for $base)" \
    --notes "Patch $ver for base $base. Installed automatically from the title screen.

sha256: $sha

$notes"
  ;;
*) echo "usage: tools/release.sh full|patch <version> [notes]"; exit 1 ;;
esac
