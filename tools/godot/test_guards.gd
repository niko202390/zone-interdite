extends SceneTree
## Headless behaviour test for guards. Run:
##   godot --headless --path game --script ../tools/godot/test_guards.gd
## Scenarios: (1) armed in plain view of the sentry, (2) unarmed in plain view, (3) gunshot out of sight.

var level: Node
var player: Node


func _init() -> void:
	_run.call_deferred()


func _wait(seconds: float) -> void:
	var t := 0.0
	while t < seconds:
		await process_frame
		t += 1.0 / 60.0


func _load() -> void:
	if level:
		level.queue_free()
		await process_frame
	level = (load("res://scenes/levels/village_test.tscn") as PackedScene).instantiate()
	root.add_child(level)
	current_scene = level
	player = level.get_node("Player")
	await _wait(3.0)


func _log(label: String, seconds: float) -> void:
	var sentry: Node = level.get_node("Sentry")
	var patrol: Node = level.get_node("Patrol")
	var t := 0.0
	while t < seconds:
		await _wait(0.5)
		t += 0.5
		print("%s t=%4.1f  sentry=%-10s susp=%.2f vis=%.2f  patrol=%-10s  player_hp=%5.1f" % [label, t,
			sentry.state_name(), sentry.suspicion, sentry._visibility, patrol.state_name(), player.health])


func _run() -> void:
	await _load()
	print("nav_ready=", Visibility.nav_ready)
	# 1: armed, standing 14 m in front of the sentry, beyond the brazier light.
	player.debug_place(Vector3(0.5, 0.05, 32.0), 180.0, 0.0)
	player.firearm.holstered = false
	await _log("ARMED  ", 4.0)

	await _load()
	# 1b: armed, 7 m from the sentry, inside the brazier's light.
	player.debug_place(Vector3(0.5, 0.05, 40.0), 180.0, 0.0)
	player.firearm.holstered = false
	await _log("ARMED7m", 8.0)

	await _load()
	# 2: unarmed (holstered), same spot, standing still.
	player.firearm.holstered = true
	player.debug_place(Vector3(0.5, 0.05, 32.0), 180.0, 0.0)
	await _log("UNARMED", 6.0)

	await _load()
	# 3: out of sight at the south end; fire a shot into a wall.
	player.debug_place(Vector3(-2.0, 0.05, -50.0), 90.0, 0.0)
	player.firearm.holstered = false
	await _wait(0.5)
	player.debug_fire()
	await _log("GUNSHOT", 5.0)
	quit()
