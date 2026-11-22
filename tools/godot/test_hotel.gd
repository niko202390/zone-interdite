extends SceneTree
## Headless test for the signals post: the coal chute, Brenner asleep and his key, copying the monthly sheets,
## putting the key back, today's strip during the operator's break, and London's verdict.
##   godot --headless --path game --script ../tools/godot/test_hotel.gd

var level: Node
var player: Node
var game: Node
var post: Node


func _init() -> void:
	_run.call_deferred()


func _wait(seconds: float) -> void:
	await create_timer(seconds, true, true).timeout


func _load(clock: String) -> void:
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
	post = level.hotel_post
	await _wait(1.0)


func _use_nearest(prompt_part: String) -> String:
	while player.busy > 0.0:
		await process_frame
	player._refresh_interact()
	var it: Node = player._interactable
	var got: String = it.prompt if it else "-"
	if it and got.contains(prompt_part):
		player._interact()
	return got


func _run() -> void:
	await _load("19:00")
	if post == null:
		print("HOTEL no interior model yet; nothing to test.")
		quit()
		return
	print("MARKERS cabinet=%s desk=%s bed=%s chute=%s" % [post.mpos("Cabinet"), post.mpos("Desk_Signals"),
		post.mpos("Brenner_Bed"), post.hotel.find_child("CoalChute", true, false) != null])

	# The coal chute.
	var chute: Node3D = post.hotel.find_child("CoalChute", true, false)
	var outward: Vector3 = chute.global_position - post.hotel.global_position
	outward.y = 0.0
	player.debug_place(chute.global_position + outward.normalized() * 1.0, 0.0, -30.0)
	player.look_at(chute.global_position, Vector3.UP)
	await _wait(0.3)
	print("CHUTE prompt=%s" % await _use_nearest("coal"))
	await _wait(3.0)
	print("CHUTE inside=%s pos=%s" % [post.player_inside(), player.global_position])

	# Brenner asleep: take his key.
	await _load("23:50")
	await _wait(60.0)
	var b: Node3D = post.brenner
	print("BRENNER asleep=%s at_bed=%.1f" % [b.asleep, b.global_position.distance_to(post.mpos("Brenner_Bed"))])
	if not b.asleep:
		# Put him to bed directly so the rest can be tested.
		b.global_position = post.mpos("Brenner_Bed")
		b._set_asleep(true)
	player.debug_place(b.global_position + Vector3(0.8, 0.1, 0.0), 0.0, -40.0)
	await _wait(0.4)
	print("KEY prompt=%s" % await _use_nearest("key"))
	await _wait(3.0)
	print("KEY has=%s brenner_asleep=%s" % [player.items.get("cabinet_key", false), b.asleep])

	# The cabinet: copy by hand, standing still, with the operator away from his desk.
	post.operator.global_position = post.stand_at("Dorm_Bunks")
	post.operator.patrol_points = PackedVector3Array([post.stand_at("Dorm_Bunks")])
	var cab: Vector3 = post.mpos("Cabinet")
	player.debug_place(post.stand_at("Cabinet", 0.8), 0.0, -10.0)
	player.look_at(cab + Vector3.UP * 1.2, Vector3.UP)
	await _wait(0.4)
	print("CABINET prompt=%s" % await _use_nearest("cabinet"))
	await _wait(1.0)
	print("CABINET open=%s asking=%s key=%s busy=%.1f" % [post.cabinet_open, player.overlay.is_asking(), player.items.get("cabinet_key", false), player.busy])
	player.overlay._answer(0)
	await _wait(2.0)
	print("COPYING %s anchor_d=%.2f" % [post._copying, player.global_position.distance_to(post._copy_anchor)])
	await _wait(post.COPY_TIME + 3.0)
	print("COPY monthly=%s cabinet_open=%s" % [post.monthly, post.cabinet_open])

	# Put the key back.
	player.debug_place(b.global_position + Vector3(0.8, 0.1, 0.0), 0.0, -40.0)
	await _wait(0.4)
	print("RETURN prompt=%s" % await _use_nearest("put the key"))
	await _wait(3.0)
	print("RETURN returned=%s trace=%d line=%s" % [post.key_returned, post.trace(), post.report_line()])
	var r: Array = level._report("cove")
	print("VERDICT %s" % r[1])

	# The operator's coffee at nine leaves today's strip on the desk.
	await _load("21:00")
	await _wait(30.0)
	print("STRIP operator_away=%.1f enabled=%s" % [post.operator.global_position.distance_to(post.mpos("Desk_Signals")), post._strip_it.enabled])
	quit()
