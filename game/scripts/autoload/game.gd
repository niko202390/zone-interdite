extends Node
## Global setup: the input map, audio buses, and window toggles.
## It also acts as the world's noise bus, so AI can listen to everything that makes sound.

## position, loudness in dB SPL at 1 m, and the node that made it.
signal noise_emitted(position: Vector3, loudness_db: float, source: Node)

const BUS_WORLD := &"World"
const BUS_TINNITUS := &"Tinnitus"
const BUS_MUSIC := &"Music"

## Collision layers.
const LAYER_WORLD := 1
const LAYER_PLAYER := 2
const LAYER_DEBRIS := 4      # casings and similar small stuff
const LAYER_HITBOX := 8      # character hit zones (M2)

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


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_setup_input()
	_setup_audio_buses()


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
