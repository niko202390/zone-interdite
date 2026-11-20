extends SceneTree
## Headless test for the café wireless and the BBC broadcast. Run:
##   godot --headless --path game --script ../tools/godot/test_radio.gd

func _init() -> void:
	_run.call_deferred()


func _wait(seconds: float) -> void:
	await create_timer(seconds, true, true).timeout


func _run() -> void:
	var level: Node = (load("res://scenes/levels/village_test.tscn") as PackedScene).instantiate()
	root.add_child(level)
	current_scene = level
	var player: Node = level.get_node("Player")
	player.health = 1.0e6
	while not level.is_built:
		await process_frame
	await _wait(1.0)
	var w: Node3D = level.get_node_or_null("Wireless")
	print("RADIO found=", w != null, " at ", w.global_position if w else Vector3.ZERO)
	if w == null:
		quit()
		return
	root.get_node("Game").set_clock("19:29")
	player.debug_place(w.global_position + Vector3(0.0, -w.global_position.y + 0.15, 1.2), 0.0, -25.0)
	await _wait(0.5)
	player._refresh_interact()
	print("RADIO option=", player._interact_kind, " prompt=", player._interactable.prompt if player._interactable else "-")
	player._interact()
	var last := ""
	for i in 40:
		await _wait(2.0)
		var sub: String = player.overlay._subtitle.text.replace("\n", " ")
		if sub != last:
			print("RADIO t=%3d %s  %s" % [i * 2, root.get_node("Game").clock_text(), sub])
			last = sub
	print("RADIO intel: ", player.overlay.journal.intel, " bbc done=", player.overlay.journal.is_done("bbc"))
	quit()
