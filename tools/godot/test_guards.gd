extends SceneTree
## Headless behaviour test for guards. Run:
##   godot --headless --path game --script ../tools/godot/test_guards.gd
## Scenarios: armed far off in the dark, unarmed in plain view, gunshot out of sight, and (last,
## because it kills the player and triggers a level reload) armed close to the sentry.

var level: Node
var player: Node


func _init() -> void:
	_run.call_deferred()


## Waits in game time (timers follow the same clock the guards use), not in frames.
func _wait(seconds: float) -> void:
	await create_timer(seconds, true, true).timeout


func _load() -> void:
	if level:
		level.queue_free()
		await process_frame
	level = (load("res://scenes/levels/village_test.tscn") as PackedScene).instantiate()
	root.add_child(level)
	current_scene = level
	player = level.get_node("Player")
	while not level.is_built:
		await process_frame
	await _wait(1.0)


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

	await _load()
	# Takedown: step in close behind the patrol, take him down, and see whether the sentry finds the body.
	var patrol: Node = level.get_node("Patrol")
	player.firearm.holstered = true
	player.debug_place(patrol.global_position + patrol.global_basis.z * 1.0, rad_to_deg(patrol.rotation.y), 0.0)
	await _wait(0.2)
	player._refresh_interact()
	print("TAKEDOWN option=", player._interact_kind)
	player._interact()
	await _wait(0.5)
	player.debug_place(Vector3(-3.0, 0.05, 10.0), 180.0, 0.0)
	await _log("BODY   ", 5.0)

	await _load()
	# Papers: walk up unarmed, get challenged, show papers (no zone pass), get turned back, then push past.
	var sentry: Node = level.get_node("Sentry")
	player.firearm.holstered = true
	player.debug_place(Vector3(1.5, 0.05, 37.0), 180.0, 0.0)
	await _log("CHALLNG", 2.0)
	print("  subtitle: ", player.overlay._subtitle.text.replace("
", " "))
	player.debug_place(Vector3(2.2, 0.05, 44.3), 180.0, 0.0)
	await _wait(0.4)
	player._refresh_interact()
	print("PAPERS option=", player._interact_kind)
	player._interact()
	await _log("INSPECT", 4.5)
	print("  subtitle: ", player.overlay._subtitle.text.replace("
", " "))
	# Comply: walk back out of the zone during the grace period.
	player.debug_place(Vector3(1.0, 0.05, 36.0), 180.0, 0.0)
	await _log("LEAVE  ", 10.0)

	await _load()
	# Defy: get turned back, then stay in the zone past the grace period.
	player.firearm.holstered = true
	player.health = 100000.0
	player.debug_place(Vector3(1.5, 0.05, 37.0), 180.0, 0.0)
	await _wait(2.0)
	player.debug_place(Vector3(2.2, 0.05, 44.3), 180.0, 0.0)
	await _wait(0.4)
	player._refresh_interact()
	player._interact()
	await _wait(4.0)
	await _log("LINGER ", 10.0)

	await _load()
	# Curfew: unarmed, walking normally, in view of the sentry at 22:30.
	root.get_node("Game").set_clock("22:30")
	player.health = 100000.0
	player.firearm.holstered = true
	player.debug_place(Vector3(0.5, 0.05, 40.0), 180.0, 0.0)
	await _log("CURFEW ", 4.0)
	root.get_node("Game").set_clock("17:40")

	await _load()
	# 1b: armed, 7 m from the sentry, inside the brazier's light.
	player.debug_place(Vector3(0.5, 0.05, 40.0), 180.0, 0.0)
	player.firearm.holstered = false
	await _log("ARMED7m", 8.0)
	quit()
