extends Node
## Player settings, saved to user://settings.cfg: mouse sensitivity, field of view, volumes,
## a graphics quality preset, and display options.
## Quality presets scale the expensive features (GI, volumetric fog, reflections, shadows, render scale).

signal changed

const PATH := "user://settings.cfg"
const PRESETS := ["Low", "Medium", "High", "Ultra"]

## Mouse sensitivity, in radians per pixel.
var sensitivity := 0.0022
## Vertical field of view in degrees. The menu shows the 16:9 horizontal equivalent.
var fov := 62.0
var master_volume := 1.0
var effects_volume := 1.0
var music_volume := 0.8
var quality := 2
var fullscreen := false
var vsync := true

var _cfg := ConfigFile.new()


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	load_settings()
	apply_all.call_deferred()
	get_tree().node_added.connect(_on_node_added)


func load_settings() -> void:
	if _cfg.load(PATH) != OK:
		return
	sensitivity = _cfg.get_value("input", "sensitivity", sensitivity)
	fov = _cfg.get_value("view", "fov", fov)
	master_volume = _cfg.get_value("audio", "master", master_volume)
	effects_volume = _cfg.get_value("audio", "effects", effects_volume)
	music_volume = _cfg.get_value("audio", "music", music_volume)
	quality = _cfg.get_value("graphics", "quality", quality)
	fullscreen = _cfg.get_value("display", "fullscreen", fullscreen)
	vsync = _cfg.get_value("display", "vsync", vsync)


func save_settings() -> void:
	_cfg.set_value("input", "sensitivity", sensitivity)
	_cfg.set_value("view", "fov", fov)
	_cfg.set_value("audio", "master", master_volume)
	_cfg.set_value("audio", "effects", effects_volume)
	_cfg.set_value("audio", "music", music_volume)
	_cfg.set_value("graphics", "quality", quality)
	_cfg.set_value("display", "fullscreen", fullscreen)
	_cfg.set_value("display", "vsync", vsync)
	_cfg.save(PATH)


func apply_all() -> void:
	Game.mouse_sensitivity = sensitivity
	_apply_audio()
	_apply_display()
	_apply_quality()
	changed.emit()


func set_value(key: String, value: Variant) -> void:
	set(key, value)
	apply_all()
	save_settings()


## Horizontal FOV at 16:9 for a vertical FOV, which is what players usually mean by "FOV".
static func horizontal_fov(vertical_deg: float) -> float:
	return rad_to_deg(2.0 * atan(tan(deg_to_rad(vertical_deg) * 0.5) * 16.0 / 9.0))


func _apply_audio() -> void:
	AudioServer.set_bus_volume_db(AudioServer.get_bus_index(&"Master"), linear_to_db(maxf(master_volume, 0.0001)))
	var music := AudioServer.get_bus_index(Game.BUS_MUSIC)
	if music >= 0:
		AudioServer.set_bus_volume_db(music, linear_to_db(maxf(music_volume, 0.0001)))
	# World and Tinnitus volumes are driven by the Hearing system, so the effects level lives in Hearing.effects_gain_db.
	Hearing.effects_gain_db = linear_to_db(maxf(effects_volume, 0.0001))


func _apply_display() -> void:
	if DisplayServer.get_name() == "headless":
		return
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if vsync else DisplayServer.VSYNC_DISABLED)
	var mode := DisplayServer.window_get_mode()
	var is_full := mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN
	if fullscreen != is_full:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED)


func _apply_quality() -> void:
	var vp := get_viewport()
	match quality:
		0:
			vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR2
			vp.scaling_3d_scale = 0.67
			RenderingServer.directional_shadow_atlas_set_size(2048, true)
			RenderingServer.gi_set_use_half_resolution(true)
		1:
			vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_FSR2
			vp.scaling_3d_scale = 0.8
			RenderingServer.directional_shadow_atlas_set_size(4096, true)
			RenderingServer.gi_set_use_half_resolution(true)
		2:
			vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
			vp.scaling_3d_scale = 1.0
			RenderingServer.directional_shadow_atlas_set_size(4096, true)
			RenderingServer.gi_set_use_half_resolution(false)
		_:
			vp.scaling_3d_mode = Viewport.SCALING_3D_MODE_BILINEAR
			vp.scaling_3d_scale = 1.0
			RenderingServer.directional_shadow_atlas_set_size(8192, true)
			RenderingServer.gi_set_use_half_resolution(false)
	vp.use_taa = vp.scaling_3d_mode != Viewport.SCALING_3D_MODE_FSR2
	for we in get_tree().root.find_children("*", "WorldEnvironment", true, false):
		_apply_environment((we as WorldEnvironment).environment)


func _apply_environment(env: Environment) -> void:
	if env == null:
		return
	env.sdfgi_enabled = quality >= 1
	env.volumetric_fog_enabled = quality >= 1
	env.ssr_enabled = quality >= 2 and not Debug.args.has("no-ssr")
	env.ssil_enabled = quality >= 2
	env.ssao_enabled = true
	env.sdfgi_cascades = 4 if quality <= 1 else (5 if quality == 2 else 6)


## Levels build their WorldEnvironment at runtime, so apply quality whenever one appears.
func _on_node_added(node: Node) -> void:
	if node is WorldEnvironment:
		(func() -> void: _apply_environment((node as WorldEnvironment).environment)).call_deferred()
