extends Node
## Global setup: the input map, audio buses, and window toggles.
## It also acts as the world's noise bus, so AI can listen to everything that makes sound.

## position, loudness in dB SPL at 1 m, and the node that made it.
signal noise_emitted(position: Vector3, loudness_db: float, source: Node)
## Emitted on the hour (0-23), so the church bell can strike it.
signal hour_struck(hour: int)

## Curfew in the occupied zone, 22:00 to 05:00.
const CURFEW_START := 22 * 60
const CURFEW_END := 5 * 60

const BUS_WORLD := &"World"
const BUS_TINNITUS := &"Tinnitus"
const BUS_MUSIC := &"Music"
## A wartime wireless: narrow band, a little overdriven. Sends into World, so hearing loss and distance apply.
const BUS_RADIO := &"Radio"

## Collision layers.
const LAYER_WORLD := 1
const LAYER_PLAYER := 2
const LAYER_DEBRIS := 4      # casings and similar small stuff
const LAYER_HITBOX := 8      # things bullets can hit that take damage (characters)
const LAYER_CHARACTER := 16  # NPC bodies, for movement collision

const KEY_ACTIONS := {
	"move_forward": [KEY_W],
	"move_back": [KEY_S],
	"move_left": [KEY_A],
	"move_right": [KEY_D],
	"sprint": [KEY_SHIFT],
	"crouch": [KEY_C, KEY_CTRL],
	"jump": [KEY_SPACE],
	"lean_left": [KEY_Q],
	"lean_right": [KEY_E],
	"interact": [KEY_F],
	"reload": [KEY_R],
	"check_ammo": [KEY_T],
	"safety": [KEY_B],
	"holster": [KEY_H],
	"pause": [KEY_ESCAPE],
	"fullscreen": [KEY_F11],
	"help": [KEY_F1],
	"watch": [KEY_X],
	"notebook": [KEY_J],
	"throw": [KEY_G],
	"weapon_1": [KEY_1],
	"weapon_2": [KEY_2],
	"quit": [KEY_F10],
}
const MOUSE_ACTIONS := {
	"fire": MOUSE_BUTTON_LEFT,
	"aim": MOUSE_BUTTON_RIGHT,
	"pace_up": MOUSE_BUTTON_WHEEL_UP,
	"pace_down": MOUSE_BUTTON_WHEEL_DOWN,
}

## Radians of view rotation per pixel of mouse motion.
var mouse_sensitivity := 0.0022
## Time of day in minutes since midnight. Mission 1 begins at blue hour.
var clock_minutes := 17.0 * 60.0 + 40.0
## Game minutes per real second. At 5x, an hour of play covers five hours of the night.
var clock_rate := 5.0 / 60.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_setup_input()
	_setup_audio_buses()


func _process(delta: float) -> void:
	if get_tree().paused:
		return
	var before := clock_minutes
	clock_minutes = fposmod(clock_minutes + delta * clock_rate, 1440.0)
	if int(before / 60.0) != int(clock_minutes / 60.0):
		hour_struck.emit(int(clock_minutes / 60.0))


func set_clock(text: String) -> void:
	var parts := text.split(":")
	if parts.size() == 2:
		clock_minutes = parts[0].to_float() * 60.0 + parts[1].to_float()


func clock_text() -> String:
	return "%02d:%02d" % [int(clock_minutes / 60.0), int(fmod(clock_minutes, 60.0))]


func curfew_active() -> bool:
	return clock_minutes >= CURFEW_START or clock_minutes < CURFEW_END


func emit_noise(position: Vector3, loudness_db: float, source: Node = null) -> void:
	noise_emitted.emit(position, loudness_db, source)


func _setup_input() -> void:
	for action: String in KEY_ACTIONS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key: Key in KEY_ACTIONS[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = key
			InputMap.action_add_event(action, ev)
	for action: String in MOUSE_ACTIONS:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		var mev := InputEventMouseButton.new()
		mev.button_index = MOUSE_ACTIONS[action]
		InputMap.action_add_event(action, mev)


func _setup_audio_buses() -> void:
	var world := _ensure_bus(BUS_WORLD)
	_ensure_bus(BUS_TINNITUS)
	_ensure_bus(BUS_MUSIC)
	var radio := _ensure_bus(BUS_RADIO, BUS_WORLD)
	if AudioServer.get_bus_effect_count(radio) == 0:
		var hp := AudioEffectHighPassFilter.new()
		hp.cutoff_hz = 320.0
		AudioServer.add_bus_effect(radio, hp, 0)
		var lp2 := AudioEffectLowPassFilter.new()
		lp2.cutoff_hz = 3300.0
		AudioServer.add_bus_effect(radio, lp2, 1)
		var dist := AudioEffectDistortion.new()
		dist.mode = AudioEffectDistortion.MODE_OVERDRIVE
		dist.drive = 0.35
		dist.post_gain = -4.0
		AudioServer.add_bus_effect(radio, dist, 2)
	# World sounds pass through a low-pass filter that the Hearing system closes down after loud exposure.
	if AudioServer.get_bus_effect_count(world) == 0:
		var lp := AudioEffectLowPassFilter.new()
		lp.cutoff_hz = 20000.0
		lp.db = AudioEffectFilter.FILTER_12DB
		AudioServer.add_bus_effect(world, lp, 0)
	# Gunshots are mixed hot; stop the master from clipping.
	var master := AudioServer.get_bus_index(&"Master")
	if AudioServer.get_bus_effect_count(master) == 0:
		var limiter := AudioEffectHardLimiter.new()
		limiter.ceiling_db = -0.3
		AudioServer.add_bus_effect(master, limiter, 0)


func _ensure_bus(bus_name: StringName, send: StringName = &"Master") -> int:
	var idx := AudioServer.get_bus_index(bus_name)
	if idx == -1:
		AudioServer.add_bus()
		idx = AudioServer.bus_count - 1
		AudioServer.set_bus_name(idx, bus_name)
		AudioServer.set_bus_send(idx, send)
	return idx


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("fullscreen"):
		var mode := DisplayServer.window_get_mode()
		if mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
		else:
			DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	elif event.is_action_pressed("quit"):
		get_tree().quit()
