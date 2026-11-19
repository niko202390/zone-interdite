extends SceneTree
## Headless test for the ways past the checkpoint. Run:
##   godot --headless --path game --script ../tools/godot/test_options.gd

var level: Node
var player: Node


func _init() -> void:
	_run.call_deferred()


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
	player.health = 1.0e6
	player.firearm.holstered = true
	await _wait(3.0)


func _interactable(prompt: String) -> Node3D:
	for it in get_nodes_in_group("interactables"):
		if is_instance_valid(it) and level.is_ancestor_of(it) and it.prompt == prompt:
			return it
	return null


func _run() -> void:
	await _load()
	var sentry: Node = level.get_node("Sentry")

	# Vault: face a garden wall on the east side and press jump.
	player.debug_place(Vector3(18.4, 0.05, -21.0), -90.0, 0.0)
	await _wait(0.3)
	player._jump_requested = true
	await _wait(1.2)
	print("VAULT  x before=18.4 after=%.2f  (wall at 19.5)" % player.global_position.x)

	# Satchel: get the zone pass, then present it at the checkpoint and walk through.
	var satchel := _interactable("search the satchel")
	print("SATCHEL found=", satchel != null)
	if satchel:
		player.debug_place(satchel.global_position + Vector3(0.6, -0.7, 0.0), 90.0, 0.0)
		await _wait(0.3)
		player._refresh_interact()
		player._interact()
		await _wait(2.5)
		print("SATCHEL zone_pass=", player.papers["zone_pass"])
	player.debug_place(Vector3(1.5, 0.05, 37.0), 180.0, 0.0)
	await _wait(2.0)
	player.debug_place(Vector3(2.2, 0.05, 44.3), 180.0, 0.0)
	await _wait(0.4)
	player._refresh_interact()
	player._interact()
	await _wait(4.5)
	print("PASS   sentry=%s  subtitle=%s" % [sentry.state_name(), player.overlay._subtitle.text.replace("\n", " ")])
	player.debug_place(Vector3(1.0, 0.05, 52.0), 0.0, 0.0)
	await _wait(4.0)
	print("PASS   walked through: sentry=%s susp=%.2f" % [sentry.state_name(), sentry.suspicion])

	# Disguise: greatcoat on, walk past at a distance at dusk; then step close into the brazier's light.
	await _load()
	sentry = level.get_node("Sentry")
	var coat := _interactable("take the navy greatcoat")
	print("COAT   found=", coat != null)
	if coat:
		player.debug_place(coat.global_position + Vector3(-0.7, -0.8, 0.0), -90.0, 0.0)
		await _wait(0.3)
		player._refresh_interact()
		player._interact()
		await _wait(3.5)
	print("COAT   disguise=", player.disguise)
	player.debug_place(Vector3(-2.5, 0.05, 38.0), 180.0, 0.0)
	await _wait(5.0)
	print("COAT   at 9 m: sentry=%s susp=%.2f disguise=%s" % [sentry.state_name(), sentry.suspicion, player.disguise])
	player.debug_place(Vector3(2.9, 0.05, 45.6), 180.0, 0.0)
	await _wait(5.0)
	print("COAT   at 1.5 m in light: sentry=%s disguise=%s subtitle=%s" % [sentry.state_name(), player.disguise, player.overlay._subtitle.text.replace("\n", " ")])

	# Throw: a bottle smashing near the sentry draws him off.
	await _load()
	sentry = level.get_node("Sentry")
	player.items["bottle"] = 1
	player.debug_place(Vector3(-2.0, 0.05, 14.0), 180.0, -12.0)
	await _wait(0.5)
	player._throw()
	await _wait(3.0)
	print("THROW  sentry=%s  target=%s" % [sentry.state_name(), str(sentry.target_pos)])
	quit()
