extends SceneTree
## Headless test for the field telephone and the cuttable PTT line. Run:
##   godot --headless --path game --script ../tools/godot/test_wire.gd
## 1. A gunshot with the line intact: the sentry runs to his phone, calls it in, and reinforcements arrive.
## 2. Cut the line at the junction box first: the call fails and nobody comes.

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
	level.reinforcement_delay = 3.0
	root.add_child(level)
	current_scene = level
	player = level.get_node("Player")
	await _wait(3.0)


func _report(label: String, seconds: float) -> void:
	var sentry: Node = level.get_node("Sentry")
	var t := 0.0
	while t < seconds:
		await _wait(1.0)
		t += 1.0
		print("%s t=%4.1f  sentry=%-10s call=%-8s guards=%d  subtitle=%s" % [label, t, sentry.state_name(),
			sentry._call, get_nodes_in_group("guards").size(), player.overlay._subtitle.text.replace("\n", " ")])


func _run() -> void:
	await _load()
	player.debug_place(Vector3(-2.0, 0.05, -50.0), 90.0, 0.0)
	player.firearm.holstered = false
	player.debug_fire()
	await _report("INTACT", 14.0)

	await _load()
	var pole_box: Node3D = null
	for it in get_nodes_in_group("interactables"):
		if is_instance_valid(it) and level.is_ancestor_of(it):
			pole_box = it
	player.debug_place(pole_box.global_position + Vector3(-0.8, -1.2, 0.0), 90.0, 0.0)
	await _wait(0.3)
	player._refresh_interact()
	print("CUT option=", player._interact_kind, " prompt=", player._interactable.prompt if player._interactable else "-")
	player._interact()
	await _wait(3.0)
	print("line_ok=", level.call("is_phone_line_ok"))
	player.debug_place(Vector3(-2.0, 0.05, -50.0), 90.0, 0.0)
	player.debug_fire()
	await _report("CUT   ", 14.0)
	quit()
