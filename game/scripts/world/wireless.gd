class_name Wireless
extends Node3D
## A wireless set tuned to London. Listening to the BBC was forbidden under the occupation, and the sound carries.
## At 19:30 and 21:15 the French service is on: « Ici Londres », the news, then the messages personnels that
## London uses to talk to its agents. Tonight one of them is yours. At other times there's only static and the
## German jamming.

signal message_heard(text: String)

## Game-time minutes when the French service broadcasts, and how long each window lasts.
const BROADCASTS := [1170.0, 1275.0]   # 19:30, 21:15
const WINDOW := 15.0
const OUR_MESSAGE := "Le chat de la voisine a mangé les pommes."

## The programme: [seconds from start, French, English]. A line with French "" is the V-signal drum.
const PROGRAMME := [
	[0.0, "", ""],
	[6.0, "Ici Londres ! Les Français parlent aux Français.", "This is London! The French speaking to the French."],
	[11.0, "Voici d'abord les nouvelles.", "First, the news."],
	[15.0, "Sur le front de l'Est, l'Armée rouge poursuit son offensive en Ukraine.", "On the Eastern Front, the Red Army presses its offensive in Ukraine."],
	[22.0, "En Italie, de durs combats continuent autour de la tête de pont d'Anzio et devant Cassino.", "In Italy, hard fighting continues around the Anzio beachhead and before Cassino."],
	[29.5, "Cette nuit encore, la Royal Air Force a bombardé Berlin.", "Again last night, the Royal Air Force bombed Berlin."],
	[35.0, "Et maintenant, voici quelques messages personnels.", "And now, some personal messages."],
	[40.0, "Jean-Pierre n'aime pas les épinards.", "Jean-Pierre doesn't like spinach."],
	[45.0, "La lune est pleine d'éléphants verts.", "The moon is full of green elephants."],
	[50.0, "Le facteur s'est endormi sur son vélo.", "The postman fell asleep on his bicycle."],
	[55.0, OUR_MESSAGE, "The neighbour's cat has eaten the apples."],
	[60.5, "Je répète : le chat de la voisine a mangé les pommes.", "I repeat: the neighbour's cat has eaten the apples."],
	[66.0, "Les sabots de Lucien sont trop petits.", "Lucien's clogs are too small."],
	[71.0, "", ""],
]

var on := false
var player: Node3D
var _static: AudioStreamPlayer3D
var _jam: AudioStreamPlayer3D
var _dial: StandardMaterial3D
var _running := -1.0
var _next_line := 0
var _done := {}
var _noise_t := 0.0
var _switch: Interactable


func _ready() -> void:
	_build_mesh()
	_static = _loop("radio/static_loop", -10.0)
	_jam = _loop("radio/jamming_loop", -16.0)
	_switch = Interactable.new()
	_switch.prompt = "turn on the wireless"
	_switch.radius = 1.3
	add_child(_switch)
	_switch.position = Vector3(0, 0.1, 0)
	_switch.on_use = func(_p: Node3D) -> void: _toggle()


func _build_mesh() -> void:
	var wood := StandardMaterial3D.new()
	wood.albedo_color = Color(0.2, 0.11, 0.06)
	wood.roughness = 0.45
	var cabinet := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.44, 0.36, 0.24)
	bm.material = wood
	cabinet.mesh = bm
	add_child(cabinet)
	cabinet.position.y = 0.18
	var cloth := MeshInstance3D.new()
	var cm := QuadMesh.new()
	cm.size = Vector2(0.22, 0.2)
	var cmat := StandardMaterial3D.new()
	cmat.albedo_color = Color(0.32, 0.26, 0.18)
	cmat.roughness = 1.0
	cm.material = cmat
	cloth.mesh = cm
	add_child(cloth)
	cloth.position = Vector3(-0.07, 0.2, 0.121)
	var dial := MeshInstance3D.new()
	var dm := QuadMesh.new()
	dm.size = Vector2(0.12, 0.05)
	_dial = StandardMaterial3D.new()
	_dial.albedo_color = Color(0.5, 0.42, 0.25)
	_dial.emission_enabled = true
	_dial.emission = Color(1.0, 0.7, 0.3)
	_dial.emission_energy_multiplier = 0.0
	dm.material = _dial
	dial.mesh = dm
	add_child(dial)
	dial.position = Vector3(0.12, 0.24, 0.121)


func _loop(key: String, vol: float) -> AudioStreamPlayer3D:
	var p := AudioStreamPlayer3D.new()
	p.stream = SoundLib.pick(key)
	p.bus = Game.BUS_RADIO
	p.volume_db = vol
	p.unit_size = 2.0
	p.max_distance = 30.0
	add_child(p)
	p.position.y = 0.2
	return p


func _toggle() -> void:
	on = not on
	_switch.prompt = "turn off the wireless" if on else "turn on the wireless"
	_dial.emission_energy_multiplier = 1.4 if on else 0.0
	if on:
		SoundLib.play_3d("radio/tuning_sweep", global_position, -6.0, 20.0, 0.05, 2.0)
		_static.play(randf() * 10.0)
		_jam.play(randf() * 8.0)
		if _current_broadcast() < 0.0 and player and player.has_method("note"):
			player.note("Static, and the German jamming. London speaks at 19:30 and 21:15.", 4.0)
	else:
		_static.stop()
		_jam.stop()
		_running = -1.0


## The broadcast whose window is open now, or -1.
func _current_broadcast() -> float:
	for b: float in BROADCASTS:
		if Game.clock_minutes >= b and Game.clock_minutes < b + WINDOW:
			return b
	return -1.0


func _process(delta: float) -> void:
	if not on:
		return
	# The sound carries. Listening to London was a crime.
	_noise_t -= delta
	if _noise_t <= 0.0:
		_noise_t = 2.0
		Game.emit_noise(global_position + Vector3.UP * 0.3, 60.0, self)
	var b := _current_broadcast()
	if _running < 0.0 and b >= 0.0 and not _done.has(b):
		_done[b] = true
		_running = 0.0
		_next_line = 0
		_jam.volume_db = -26.0   # the signal comes through over the jamming
	if _running < 0.0:
		return
	_running += delta
	while _next_line < PROGRAMME.size() and _running >= float(PROGRAMME[_next_line][0]):
		_speak(PROGRAMME[_next_line])
		_next_line += 1
	if _next_line >= PROGRAMME.size() and _running > float(PROGRAMME[PROGRAMME.size() - 1][0]) + 8.0:
		_running = -1.0
		_jam.volume_db = -16.0


func _speak(line: Array) -> void:
	var fr: String = line[1]
	if fr == "":
		_play_on_set("radio/bbc_v_signal", 0.0)
		return
	var bucket := "s" if fr.length() < 18 else ("m" if fr.length() < 46 else "l")
	_play_on_set("voice/fr_talk_" + bucket, -2.0)
	var close := player != null and player.global_position.distance_to(global_position) < 7.0
	if close and player.get("overlay") and player.overlay.has_method("subtitle"):
		player.overlay.subtitle(fr, line[2], Hearing.loss() > 0.5)
		player.overlay.subtitle_t_override(5.0)
	if close and fr.contains(OUR_MESSAGE):
		message_heard.emit(fr)


func _play_on_set(key: String, vol: float) -> void:
	if not SoundLib.has_sound(key):
		return
	var p := AudioStreamPlayer3D.new()
	p.stream = SoundLib.pick(key)
	p.bus = Game.BUS_RADIO
	p.volume_db = vol + SoundLib.gain(key)
	p.unit_size = 2.5
	p.max_distance = 30.0
	add_child(p)
	p.position.y = 0.2
	p.finished.connect(p.queue_free)
	p.play()
