extends SceneTree
## Headless test for this pass's rules: questions at the checkpoint, the password for uniforms, the town's alert
## closing the checkpoint, routines by the clock, bodies in water, and London's report.
##   godot --headless --path game --script ../tools/godot/test_social.gd

var level: Node
var player: Node
var game: Node


func _init() -> void:
	_run.call_deferred()


func _wait(seconds: float) -> void:
	await create_timer(seconds, true, true).timeout


func _load(clock := "17:40") -> void:
	if level:
		level.queue_free()
		await process_frame
	level = (load("res://scenes/levels/village_test.tscn") as PackedScene).instantiate()
	root.add_child(level)
	current_scene = level
	player = level.get_node("Player")
	game = root.get_node("Game")
	while not level.is_built:
		await process_frame
	game.set_clock(clock)
	player.health = 1.0e6
	player.firearm.holstered = true
	await _wait(1.0)


## Walk up to the sentry, get challenged, show papers, and answer `choice` (0-based) when asked.
func _papers(choice: int, label: String) -> void:
	var sentry: Node = level.get_node("Sentry")
	player.debug_place(Vector3(1.5, 0.05, 37.0), 180.0, 0.0)
	await _wait(2.5)
	player.debug_place(Vector3(2.2, 0.05, 44.3), 180.0, 0.0)
	await _wait(0.5)
	player._refresh_interact()
	var kind: String = player._interact_kind
	player._interact()
	await _wait(2.5)
	var asking: bool = player.overlay.is_asking()
	player.overlay._answer(choice)
	await _wait(4.5)
	print("%s option=%s asked=%s -> sentry=%s pass=%s subtitle=%s" % [label, kind, asking, sentry.state_name(),
		player.papers["zone_pass"], player.overlay._subtitle.text.replace("\n", " ")])


func _run() -> void:
	# 1. With the clerk's pass: the right answer, then a wrong one.
	await _load()
	player.papers["zone_pass"] = true
	await _papers(0, "PASS+RIGHT")
	await _load()
	player.papers["zone_pass"] = true
	await _papers(1, "PASS+WRONG")

	# 2. In uniform after dark: the password.
	for k in 2:
		await _load("20:30")
		player.wear("wehrmacht", 0.85)
		var sentry: Node = level.get_node("Sentry")
		player.debug_place(Vector3(1.5, 0.05, 38.5), 180.0, 0.0)
		await _wait(1.0)
		player.debug_place(Vector3(2.0, 0.05, 39.0), 180.0, 0.0)
		await _wait(2.5)
		var asking: bool = player.overlay.is_asking()
		player.overlay._answer(k)
		await _wait(3.0)
		print("PAROLE answer=%d asked=%s -> sentry=%s disguise=%s alert=%d subtitle=%s" % [k, asking, sentry.state_name(),
			player.disguise, sentry.town_alert, player.overlay._subtitle.text.replace("\n", " ")])

	# 3. A body found puts the town on alert, and the checkpoint closes even with a pass.
	await _load()
	var patrol: Node = level.get_node("Patrol")
	patrol.silent_kill(player)
	var sentry2: Node = level.get_node("Sentry")
	patrol.global_position = sentry2.global_position + Vector3(-2.0, 0, -1.6)
	await _wait(3.0)
	print("BODY alert=%d intel_last=%s" % [sentry2.town_alert, player.overlay.journal.intel[player.overlay.journal.intel.size() - 1]])
	await _wait(25.0)
	player.papers["zone_pass"] = true
	await _papers(0, "CLOSED")

	# 4. Routines: the patrol's smoke at the café, the sentry's walk down at ten.
	await _load("19:31")
	await _wait(25.0)
	var p2: Node = level.get_node("Patrol")
	print("ROUTINE 19:31 patrol on_routine=%s dist_to_cafe=%.1f" % [p2.on_routine(), p2.global_position.distance_to(Vector3(-2.3, 0.05, -48.6))])
	await _load("22:00")
	await _wait(20.0)
	var s3: Node = level.get_node("Sentry")
	print("ROUTINE 22:00 sentry on_routine=%s dist_from_post=%.1f" % [s3.on_routine(), s3.global_position.distance_to(Vector3(2.4, 0.05, 46.6))])

	# 5. A body put in the river is never found, and the report counts it.
	await _load()
	var p4: Node = level.get_node("Patrol")
	p4.silent_kill(player)
	await _wait(1.5)
	var rx: float = level.call("_ground_at", 60.0, -40.0).x
	p4.global_position = Vector3(Terrain_river_x(), -1.6, -40.0)
	await _wait(2.0)
	var r: Array = level._report("cove")
	print("REPORT hidden=%d verdict=%s" % [level.stats["hidden"], r[1]])
	print(r[0])
	quit()


func Terrain_river_x() -> float:
	return level.call("cove_position").x * 0.0 + 62.0 + sin(-40.0 * 0.021) * 9.0 + sin(-40.0 * 0.057) * 3.0
