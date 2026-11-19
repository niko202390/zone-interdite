extends Node
## The first autoload. Loads downloaded patch packs before any other autoload or scene, so everything after it
## comes from the newest files. Patches live in user://patches as patch-<base>-<version>.pck and are applied in
## version order. Only patches made against this build's base version are used.
##
## What a patch can't change: project settings (project.godot), the autoload list and the engine itself.
## Those need a full build.

const PATCH_DIR := "user://patches"

## Version of the full build (application/config/version).
var base_version := "0.0.0"
## Version after applying patches.
var version := "0.0.0"
var applied: PackedStringArray = PackedStringArray()


func _init() -> void:
	base_version = String(ProjectSettings.get_setting("application/config/version", "0.0.0"))
	version = base_version
	# Patches are for exported builds. When running from source, the source is newer than any patch.
	if OS.has_feature("editor") or not DirAccess.dir_exists_absolute(PATCH_DIR):
		return
	var patches: Array = []
	for f in DirAccess.get_files_at(PATCH_DIR):
		var info := parse_patch_name(f)
		if info.is_empty() or info["base"] != base_version:
			continue
		patches.append(info)
	patches.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return compare_versions(a["version"], b["version"]) < 0)
	for p: Dictionary in patches:
		if ProjectSettings.load_resource_pack(PATCH_DIR.path_join(p["file"]), true):
			applied.append(p["file"])
			version = p["version"]
		else:
			push_warning("Boot: could not load patch " + p["file"])
	if not applied.is_empty():
		print("BOOT v%s (base %s) with patches %s" % [version, base_version, ", ".join(applied)])


## "patch-0.3.0-0.3.2.pck" -> {file, base: "0.3.0", version: "0.3.2"}; {} if it isn't a patch.
static func parse_patch_name(file: String) -> Dictionary:
	if not (file.begins_with("patch-") and file.ends_with(".pck")):
		return {}
	var parts := file.trim_prefix("patch-").trim_suffix(".pck").split("-")
	if parts.size() != 2:
		return {}
	return {"file": file, "base": parts[0], "version": parts[1]}


## -1, 0 or 1, comparing dotted version numbers numerically.
static func compare_versions(a: String, b: String) -> int:
	var pa := a.split(".")
	var pb := b.split(".")
	for i in maxi(pa.size(), pb.size()):
		var x := pa[i].to_int() if i < pa.size() else 0
		var y := pb[i].to_int() if i < pb.size() else 0
		if x != y:
			return -1 if x < y else 1
	return 0
