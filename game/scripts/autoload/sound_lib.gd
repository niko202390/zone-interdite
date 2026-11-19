extends Node
## Resolves sound keys like "weapons/p38_shot" to streams under res://assets/audio/.
## "weapons/p38_shot" matches p38_shot.wav or p38_shot_01.wav … p38_shot_NN.wav, and one
## variation is picked at random (never the same one twice in a row).
## When a sound is missing, a generated placeholder is used so the game keeps running.
## Each file's base mix level comes from assets/audio/manifest.json (suggested_gain_db), so the
## volume_db values callers pass are adjustments on top of that mix.

const ROOT := "res://assets/audio/"
const MANIFEST := "res://assets/audio/manifest.json"

var _cache := {}        # key -> Array[AudioStream]
var _last_pick := {}    # key -> int
var _placeholders := {} # key -> AudioStream
var _gains := {}        # key (without _NN) -> suggested gain dB


func _ready() -> void:
	if not FileAccess.file_exists(MANIFEST):
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
	if parsed is Dictionary and parsed.get("sounds") is Array:
		var variant_suffix := RegEx.create_from_string("_\\d+$")
		for entry: Dictionary in parsed["sounds"]:
			var key := String(entry.get("file", "")).get_basename()
			var m := variant_suffix.search(key)
			if m:
				key = key.substr(0, m.get_start())
			if not _gains.has(key):
				_gains[key] = float(entry.get("suggested_gain_db", 0.0))


## Base mix level for a sound key, in dB.
func gain(key: String) -> float:
	return _gains.get(key, 0.0)


func variants(key: String) -> Array:
	if _cache.has(key):
		return _cache[key]
	var found: Array = []
	var dir := ROOT.path_join(key.get_base_dir())
	var base := key.get_file()
	var files: Array = Array(_list_dir(dir))
	files.sort()
	for f: String in files:
		var stem := f.get_basename()
		var is_variant := stem.begins_with(base + "_") and stem.substr(base.length() + 1).is_valid_int()
		if stem == base or is_variant:
			var stream := load(dir.path_join(f))
			if stream is AudioStream:
				found.append(stream)
	_cache[key] = found
	return found


func has_sound(key: String) -> bool:
	return not variants(key).is_empty()


func pick(key: String) -> AudioStream:
	var v := variants(key)
	if v.is_empty():
		return _placeholder(key)
	if v.size() == 1:
		return v[0]
	var i := randi() % v.size()
	if i == _last_pick.get(key, -1):
		i = (i + 1) % v.size()
	_last_pick[key] = i
	return v[i]


## Fire-and-forget positional sound. Returns the player so callers can tweak it.
func play_3d(key: String, pos: Vector3, volume_db := 0.0, max_distance := 120.0,
		pitch_jitter := 0.05, unit_size := 4.0) -> AudioStreamPlayer3D:
	var p := AudioStreamPlayer3D.new()
	p.stream = pick(key)
	p.bus = Game.BUS_WORLD
	p.volume_db = volume_db + gain(key)
	p.unit_size = unit_size
	p.max_distance = max_distance
	p.attenuation_model = AudioStreamPlayer3D.ATTENUATION_INVERSE_DISTANCE
	# Air absorption: the further away a sound is, the more of its high end the air eats.
	p.attenuation_filter_cutoff_hz = 6500.0
	p.attenuation_filter_db = -18.0
	p.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	_scene_root().add_child(p)
	p.global_position = pos
	p.finished.connect(p.queue_free)
	p.play()
	return p


## Fire-and-forget non-positional sound (player's own body/weapon, stereo tails).
func play_2d(key: String, volume_db := 0.0, bus: StringName = Game.BUS_WORLD,
		pitch_jitter := 0.03) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.stream = pick(key)
	p.bus = bus
	p.volume_db = volume_db + gain(key)
	p.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	_scene_root().add_child(p)
	p.finished.connect(p.queue_free)
	p.play()
	return p


func _scene_root() -> Node:
	var scene := get_tree().current_scene
	return scene if scene else get_tree().root


func _list_dir(dir: String) -> PackedStringArray:
	# list_directory sees through the .import/.remap indirection in exported builds.
	var out := PackedStringArray()
	if not DirAccess.dir_exists_absolute(dir):
		return out
	for f in ResourceLoader.list_directory(dir):
		if not f.ends_with("/"):
			out.append(f)
	return out


func _placeholder(key: String) -> AudioStream:
	if _placeholders.has(key):
		return _placeholders[key]
	var rate := 22050
	var looping := key.contains("loop")
	var length := 1.0 if looping else 0.12
	var n := int(rate * length)
	var data := PackedByteArray()
	data.resize(n * 2)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(key)
	for i in n:
		var t := float(i) / n
		var v: float
		if key.contains("tinnitus"):
			v = sin(TAU * 4400.0 * float(i) / rate) * 0.3
		elif looping:
			v = rng.randf_range(-1.0, 1.0) * 0.05
		else:
			v = rng.randf_range(-1.0, 1.0) * pow(1.0 - t, 4.0) * 0.6
		data.encode_s16(i * 2, int(clampf(v, -1.0, 1.0) * 32767.0))
	var s := AudioStreamWAV.new()
	s.format = AudioStreamWAV.FORMAT_16_BITS
	s.mix_rate = rate
	s.stereo = false
	s.data = data
	if looping:
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_begin = 0
		s.loop_end = n
	_placeholders[key] = s
	push_warning("SoundLib: missing sound '%s', using placeholder" % key)
	return s
