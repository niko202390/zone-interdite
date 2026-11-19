class_name Ambience
extends Node3D
## The soundscape of the test level: wind, drizzle, the distant sea, a church bell, engines far off,
## sparse dread music, and now and then hobnailed boots passing behind the houses with nobody in sight.

var player: Node3D
var _music: AudioStreamPlayer
var _music_state := "idle"
var _music_timer := 75.0
var _music_vol := 0.0
var _bell_timer := 35.0
var _engine_timer := 140.0
var _dog_timer := 95.0
var _patrol_timer := 150.0
var _patrol: Node3D
var _patrol_path: Array[Vector3] = []
var _patrol_t := 0.0
var _patrol_step := 0.0


func _ready() -> void:
	_bed("ambience/wind_gusts_loop", -13.0)
	_bed("ambience/rain_light_loop", -12.0)
	_bed("ambience/distant_sea_loop", -21.0)
	_bed("ambience/drips_loop", -19.0)
	_music = AudioStreamPlayer.new()
	_music.bus = Game.BUS_MUSIC
	_music.stream = SoundLib.pick("music/drone_dread_loop")
	_music.volume_db = -80.0
	add_child(_music)


func _bed(key: String, vol: float) -> void:
	if not SoundLib.has_sound(key):
		return
	var p := AudioStreamPlayer.new()
	p.stream = SoundLib.pick(key)
	p.bus = Game.BUS_WORLD
	p.volume_db = vol
	add_child(p)
	p.play(randf() * 10.0)


func _listener_pos() -> Vector3:
	return player.global_position if player else Vector3.ZERO


func _process(delta: float) -> void:
	var lp := _listener_pos()

	_bell_timer -= delta
	if _bell_timer <= 0.0:
		_bell_timer = randf_range(200.0, 360.0)
		_toll_bell(randi_range(1, 3))

	_engine_timer -= delta
	if _engine_timer <= 0.0:
		_engine_timer = randf_range(120.0, 260.0)
		var side := Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)).normalized()
		SoundLib.play_3d("ambience/distant_engine_pass", lp + side * 160.0 + Vector3.UP * 3.0, 6.0, 600.0, 0.05, 40.0)

	_dog_timer -= delta
	if _dog_timer <= 0.0:
		_dog_timer = randf_range(80.0, 200.0)
		if SoundLib.has_sound("alarm/dog_bark_distant"):
			var dir := Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)).normalized()
			for i in randi_range(2, 5):
				get_tree().create_timer(i * randf_range(0.5, 0.9), false).timeout.connect(
					SoundLib.play_3d.bind("alarm/dog_bark_distant", lp + dir * 220.0, 4.0, 700.0, 0.06, 40.0))

	_update_patrol(delta)
	_update_music(delta)


func _toll_bell(count: int) -> void:
	var church := Vector3(-140.0, 25.0, 190.0)
	for i in count:
		get_tree().create_timer(i * 3.2, false).timeout.connect(
			SoundLib.play_3d.bind("ambience/church_bell_toll", church, 10.0, 900.0, 0.0, 60.0))


## Unseen boots on the cobbles behind the houses. No patrol is there yet (AI comes in M2), only the sound.
func _update_patrol(delta: float) -> void:
	if _patrol == null:
		_patrol_timer -= delta
		if _patrol_timer <= 0.0 and SoundLib.has_sound("footsteps/npc_hobnail_cobble"):
			_patrol_timer = randf_range(180.0, 320.0)
			_patrol = Node3D.new()
			add_child(_patrol)
			var x := 17.0 if randf() < 0.5 else -17.0
			var z0 := clampf(_listener_pos().z - 30.0, -70.0, 40.0)
			_patrol_path = [Vector3(x, 0.1, z0), Vector3(x, 0.1, z0 + 60.0)]
			if randf() < 0.5:
				_patrol_path.reverse()
			_patrol_t = 0.0
		return
	_patrol_t += delta / 38.0
	_patrol.global_position = _patrol_path[0].lerp(_patrol_path[1], _patrol_t)
	# Two men marching out of step, at about 1.8 steps per second each.
	_patrol_step += delta * 3.6
	if _patrol_step >= 1.0:
		_patrol_step -= randf_range(0.85, 1.0)
		SoundLib.play_3d("footsteps/npc_hobnail_cobble", _patrol.global_position + Vector3(randf_range(-0.6, 0.6), 0, 0), 2.0, 70.0, 0.08, 5.0)
	if _patrol_t >= 1.0:
		_patrol.queue_free()
		_patrol = null


## Music is rare. It swells up out of silence, lingers, and goes away again.
func _update_music(delta: float) -> void:
	match _music_state:
		"idle":
			_music_timer -= delta
			if _music_timer <= 0.0:
				_music_state = "in"
				_music.play(randf() * 30.0)
		"in":
			_music_vol = move_toward(_music_vol, 1.0, delta / 12.0)
			if _music_vol >= 1.0:
				_music_state = "hold"
				_music_timer = randf_range(60.0, 110.0)
		"hold":
			_music_timer -= delta
			if _music_timer <= 0.0:
				_music_state = "out"
		"out":
			_music_vol = move_toward(_music_vol, 0.0, delta / 15.0)
			if _music_vol <= 0.0:
				_music.stop()
				_music_state = "idle"
				_music_timer = randf_range(200.0, 420.0)
	_music.volume_db = linear_to_db(maxf(_music_vol, 0.0001)) - 12.0
