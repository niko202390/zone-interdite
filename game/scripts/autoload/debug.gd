extends Node
## Command-line harness for automated visual checks. Pass the arguments after "--":
##   --views=street:0,0,-40,180,-3;aim:0,0,-40,180,0,ads,fire
##        Each view is name:x,y,z,yaw_deg,pitch_deg, optionally followed by ads and/or fire.
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


func active() -> bool:
	return args.has("views")


func _run_views() -> void:
	var outdir: String = args.get("outdir", OS.get_user_data_dir().path_join("shots"))
	DirAccess.make_dir_recursive_absolute(outdir)
	await _frames(int(args.get("warm", "240")))
	var player := get_tree().get_first_node_in_group("player") as Player
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
		var img := get_viewport().get_texture().get_image()
		var path := outdir.path_join(view_name + ".png")
		img.save_png(path)
		print("SCREENSHOT ", path)
	get_tree().quit()


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame
