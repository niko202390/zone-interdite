extends Node
## Command-line harness for automated visual checks. Pass the arguments after "--":
##   --views=street:0,0,-40,180,-3;aim:0,0,-40,180,0,ads,fire
##        Each view is name:x,y,z,yaw_deg,pitch_deg, optionally followed by ads, fire and/or pause.
##        x,y,z is where the player's feet go.
##   --outdir=C:/some/folder   --warm=240 (frames before the first view)   --settle=60 (frames per view)
## For each view the harness places the player, waits, saves <outdir>/<name>.png, and quits at the end.

var args := {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--"):
			var kv := a.substr(2).split("=", true, 1)
			args[kv[0]] = kv[1] if kv.size() > 1 else "true"
	if args.has("views"):
		_run_views.call_deferred()
	if args.has("time"):
		Game.set_clock(String(args["time"]))
	if args.has("audio-probe"):
		var at := Timer.new()
		at.wait_time = 1.0
		at.autostart = true
		at.timeout.connect(func() -> void:
			var parts := PackedStringArray()
			for i in AudioServer.bus_count:
				parts.append("%s vol=%.0f peak=%.0f mute=%s" % [AudioServer.get_bus_name(i), AudioServer.get_bus_volume_db(i),
					AudioServer.get_bus_peak_volume_left_db(i, 0), AudioServer.is_bus_mute(i)])
			print("AUDIO ", " | ".join(parts), " | driver=", AudioServer.get_driver_name(), " out=", AudioServer.output_device))
		add_child(at)
	if args.has("fps-log"):
		var t := Timer.new()
		t.wait_time = 2.0
		t.autostart = true
		t.timeout.connect(func() -> void:
			print("FPS %d  frame %.1f ms  process %.1f ms  physics %.1f ms  guards %d" % [Engine.get_frames_per_second(),
				1000.0 / maxf(Engine.get_frames_per_second(), 1.0),
				Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
				Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
				get_tree().get_nodes_in_group("guards").size()]))
		add_child(t)
	if args.has("fire-after"):
		get_tree().create_timer(float(args["fire-after"])).timeout.connect(func() -> void:
			var p := get_tree().get_first_node_in_group("player") as Player
			if p:
				p.debug_fire())
	if args.has("kill-after"):
		get_tree().create_timer(float(args["kill-after"])).timeout.connect(func() -> void:
			var p := get_tree().get_first_node_in_group("player") as Player
			if p:
				p.take_hit(999.0, p.global_position, Vector3.FORWARD, null))


func active() -> bool:
	return args.has("views")


## Screenshot runs leave the AI blind and deaf unless --ai is passed, so the camera isn't shot mid-shoot.
func peaceful() -> bool:
	return active() and not args.has("ai")


func _run_views() -> void:
	var outdir: String = args.get("outdir", OS.get_user_data_dir().path_join("shots"))
	DirAccess.make_dir_recursive_absolute(outdir)
	# Wait for the level to exist and finish building (it builds over many frames).
	var level := get_tree().get_first_node_in_group("level")
	while level == null or not level.get("is_built"):
		await get_tree().process_frame
		level = get_tree().get_first_node_in_group("level")
	await _frames(int(args.get("warm", "240")))
	var player := get_tree().get_first_node_in_group("player") as Player
	if player and args.has("rifle"):
		player.weapons.append(Player.KAR98K)
		player.firearm.equip(Player.KAR98K)
		if args.has("disguise"):
			player.wear(String(args["disguise"]), 0.85)
	if player and args.has("journal"):
		player.overlay.journal.complete("checkpoint")
		player.overlay.journal.complete("bbc")
		player.overlay.add_lead("The harbour master drinks at the café. His satchel is behind it.")
		player.overlay.journal.toggle()
	if player and args.has("tools"):
		player.overlay.instruments.force = true
	for spec: String in String(args["views"]).split(";", false):
		var parts := spec.split(":")
		var view_name := parts[0]
		var v := parts[1].split(",")
		if player:
			player.debug_place(Vector3(v[0].to_float(), v[1].to_float(), v[2].to_float()),
				v[3].to_float(), v[4].to_float())
			player.debug_force_ads = v.has("ads")
		await _frames(int(args.get("settle", "60")))
		if player and v.has("fire"):
			player.debug_fire()
			await _frames(2)
		if player and v.has("reload"):
			player.firearm.mag_rounds = 2
			player.firearm._start_reload()
			await get_tree().create_timer(1.25).timeout
		if player and v.has("pause"):
			player.overlay._set_paused(true)
			await _frames(3)
		var img := get_viewport().get_texture().get_image()
		if player and v.has("pause"):
			player.overlay._set_paused(false)
		var path := outdir.path_join(view_name + ".png")
		img.save_png(path)
		print("SCREENSHOT ", path)
	get_tree().quit()


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame
