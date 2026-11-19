class_name Updater
extends Node
## Checks the GitHub releases for patches newer than what's installed, downloads them into user://patches,
## verifies each one's SHA-256 against the release notes, then asks to restart so Boot can load them.
##
## The repository is public, so no login is needed. An optional GitHub token (user://github_token) only raises
## the API rate limit.
##
## It lives on the scene tree's root, so a download carries on if you start playing. It shows its own status
## line in the bottom-left corner. If a patch finishes while you're on the title screen the game restarts to
## apply it; mid-mission it waits, and the patch is applied the next time the game starts.

signal status(text: String)
signal restart_ready

const REPO := "niko202390/zone-interdite"
const TOKEN_PATH := "user://github_token"

var token := ""
var busy := false
## Restart the game as soon as an update is installed (only while on the title screen).
var title_scene := ""
var _label: Label
var _label_t := 0.0


func _ready() -> void:
	if FileAccess.file_exists(TOKEN_PATH):
		token = FileAccess.get_file_as_string(TOKEN_PATH).strip_edges()
	var layer := CanvasLayer.new()
	layer.layer = 90
	add_child(layer)
	_label = Label.new()
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["Courier New", "Courier", "monospace"])
	_label.add_theme_font_override("font", font)
	_label.add_theme_font_size_override("font_size", 14)
	_label.add_theme_color_override("font_color", Color(0.6, 0.57, 0.5))
	_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	_label.offset_left = 24
	_label.offset_top = -40
	_label.offset_right = 900
	_label.offset_bottom = -16
	_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_label)
	status.connect(_show)


func _show(text: String) -> void:
	_label.text = text
	_label.modulate.a = 1.0
	_label_t = 0.0 if text.begins_with("Downloading") or text.begins_with("Checking") else 8.0


func _process(delta: float) -> void:
	# Finished messages fade out after a while; progress stays up.
	if _label_t > 0.0:
		_label_t -= delta
		if _label_t <= 0.0:
			_label.modulate.a = 0.0


func _on_title() -> bool:
	var cur := get_tree().current_scene
	return cur != null and title_scene != "" and cur.scene_file_path == title_scene


func save_token(t: String) -> void:
	token = t.strip_edges()
	var f := FileAccess.open(TOKEN_PATH, FileAccess.WRITE)
	f.store_string(token)
	f.close()


func _headers(accept: String, auth := true) -> PackedStringArray:
	var h := PackedStringArray(["Accept: " + accept, "User-Agent: ZoneInterdite-Updater", "X-GitHub-Api-Version: 2022-11-28"])
	if auth and token != "":
		h.append("Authorization: Bearer " + token)
	return h


func _fetch(url: String, headers: PackedStringArray, to_file := "", redirects := 0, progress_label := "") -> Array:
	var http := HTTPRequest.new()
	http.max_redirects = redirects
	http.download_file = to_file
	http.use_threads = true
	http.download_chunk_size = 1 << 20
	add_child(http)
	var err := http.request(url, headers)
	if err != OK:
		http.queue_free()
		return [err, 0, PackedStringArray(), PackedByteArray()]
	var out: Array = []
	http.request_completed.connect(func(r: int, code: int, h: PackedStringArray, b: PackedByteArray) -> void:
		out.append_array([r, code, h, b]))
	while out.is_empty():
		await get_tree().create_timer(0.5, true, false, true).timeout
		if progress_label != "":
			var total := http.get_body_size()
			var got := http.get_downloaded_bytes()
			if total > 0:
				status.emit("%s %d%%  (%.0f of %.0f MB)" % [progress_label, int(100.0 * got / total), got / 1.0e6, total / 1.0e6])
	http.queue_free()
	return out


func check_and_install() -> void:
	if busy:
		return
	busy = true
	status.emit("Checking for updates...")
	var res := await _fetch("https://api.github.com/repos/%s/releases?per_page=50" % REPO, _headers("application/vnd.github+json"))
	if res[1] != 200:
		status.emit("Couldn't check for updates (HTTP %d). Offline?" % res[1])
		busy = false
		return
	var releases: Variant = JSON.parse_string((res[3] as PackedByteArray).get_string_from_utf8())
	if not (releases is Array):
		status.emit("Couldn't read the release list.")
		busy = false
		return
	var todo: Array = []
	for r: Dictionary in releases:
		var info := Boot.parse_patch_name(String(r.get("tag_name", "")) + ".pck")
		if info.is_empty() or info["base"] != Boot.base_version:
			continue
		if Boot.compare_versions(info["version"], Boot.version) <= 0:
			continue
		info["release"] = r
		todo.append(info)
	todo.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return Boot.compare_versions(a["version"], b["version"]) < 0)
	if todo.is_empty():
		status.emit("Up to date (v%s)." % Boot.version)
		busy = false
		return
	DirAccess.make_dir_recursive_absolute(Boot.PATCH_DIR)
	for p: Dictionary in todo:
		if not await _install(p):
			busy = false
			return
	busy = false
	var v: String = todo[todo.size() - 1]["version"]
	if _on_title():
		status.emit("Update v%s installed. Restarting..." % v)
		restart_ready.emit()
		await get_tree().create_timer(1.5).timeout
		OS.set_restart_on_exit(true, OS.get_cmdline_args())
		get_tree().quit()
	else:
		status.emit("Update v%s downloaded. It applies the next time you start the game." % v)


func _install(p: Dictionary) -> bool:
	var rel: Dictionary = p["release"]
	var asset: Dictionary = {}
	for a: Dictionary in rel.get("assets", []):
		if String(a.get("name", "")).ends_with(".pck"):
			asset = a
	if asset.is_empty():
		status.emit("Release %s has no patch file." % rel.get("tag_name", "?"))
		return false
	var expected := ""
	var m := RegEx.create_from_string("sha256:\\s*([0-9a-fA-F]{64})").search(String(rel.get("body", "")))
	if m:
		expected = m.get_string(1).to_lower()
	status.emit("Downloading v%s (%.1f MB)..." % [p["version"], float(asset.get("size", 0)) / 1.0e6])
	var tmp := Boot.PATCH_DIR.path_join(p["file"] + ".part")
	# GitHub answers with a redirect to a pre-signed storage URL, which must be fetched without our token.
	var first := await _fetch(String(asset["url"]), _headers("application/octet-stream"), "", 0)
	var location := ""
	for h: String in first[2]:
		if h.to_lower().begins_with("location:"):
			location = h.substr(9).strip_edges()
	var got: Array
	if first[1] == 200:
		got = await _fetch(String(asset["url"]), _headers("application/octet-stream"), tmp, 0,
			"Downloading update v%s:" % p["version"])
	elif location != "":
		got = await _fetch(location, PackedStringArray(["User-Agent: ZoneInterdite-Updater"]), tmp, 0,
			"Downloading update v%s:" % p["version"])
	else:
		status.emit("Download of v%s failed (HTTP %d)." % [p["version"], first[1]])
		return false
	if got[1] != 200:
		status.emit("Download of v%s failed (HTTP %d)." % [p["version"], got[1]])
		DirAccess.remove_absolute(tmp)
		return false
	if expected != "" and _sha256(tmp) != expected:
		status.emit("v%s failed its checksum. Not installed." % p["version"])
		DirAccess.remove_absolute(tmp)
		return false
	DirAccess.rename_absolute(tmp, Boot.PATCH_DIR.path_join(p["file"]))
	return true


func _sha256(path: String) -> String:
	var ctx := HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	var f := FileAccess.open(path, FileAccess.READ)
	while f.get_position() < f.get_length():
		ctx.update(f.get_buffer(1 << 20))
	f.close()
	return ctx.finish().hex_encode()
