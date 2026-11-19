# Releases and updates

## For players
1. Download the latest **full build** (`base-X.Y.Z`) from the [releases page](https://github.com/niko202390/zone-interdite/releases) once. Unzip it and keep `ZoneInterdite.exe` and `ZoneInterdite.pck` together.
2. From then on, the title screen checks for **patches** and installs them by itself. They're usually kilobytes to a few MB. The game restarts once to apply them, and the version shows in the bottom-right corner.
3. Patches are stored in `%APPDATA%\Godot\app_userdata\Zone Interdite\patches`. Deleting that folder returns you to the base build.

## For us
- `tools/release.sh patch <version> "notes"` is the normal case. It exports only the files changed since the base build and every earlier patch, then publishes them as `patch-<base>-<version>` with the SHA-256 in the notes.
- `tools/release.sh full <version> "notes"` is needed when a patch can't carry the change: an engine upgrade, edits to `project.godot` (settings, the autoload list, input defaults), or the size of the patch chain growing big. Players then download one new full build.
- Keep `build/base/` and `build/patches/`. Every new patch is diffed against them, and they're gitignored.
- Patches load only in exported builds. Running from source ignores them.
