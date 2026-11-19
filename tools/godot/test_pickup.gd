extends SceneTree
## Headless test for enemy weapons and uniforms. Run:
##   godot --headless --path game --script ../tools/godot/test_pickup.gd
## Knife the patrol, take his rifle, fire it (the bolt cycles), search him for clips, take his greatcoat,
## reload from pocket ammunition, switch back to the pistol, and check how the sentry reads you.

var level: Node
var player: Node


func _init() -> void:
	_run.call_deferred()


func _wait(seconds: float) -> void:
	await create_timer(seconds, true, true).timeout


func _gun() -> String:
	var f: Node = player.firearm
	return "%s mag=%d ch=%s busy=%s pool=%d" % [f.data.id, f.mag_rounds, f.chambered, f.busy_kind(), player.ammo["7.92x57"]]


func _run() -> void:
	level = (load("res://scenes/levels/village_test.tscn") as PackedScene).instantiate()
	root.add_child(level)
	current_scene = level
	player = level.get_node("Player")
	player.health = 1.0e6
	await _wait(3.0)
	var g: Node = level.get_node("Patrol")
	player.debug_place(g.global_position + g.global_basis.z * 1.2, rad_to_deg(g.rotation.y), -20.0)
	g.silent_kill(player)
	await _wait(2.5)
	var rifles := get_nodes_in_group("dropped_weapons")
	print("DROPPED rifles=", rifles.size())
	var rb: Node3D = rifles[0]
	player.debug_place(rb.global_position + Vector3(0, 0.05, 1.0), 0.0, -50.0)
	await _wait(0.3)
	player._refresh_interact()
	print("PICKUP option=", player._interact_kind)
	player._interact()
	await _wait(1.4)
	print("TAKEN weapons=", player.weapons.size(), "  ", _gun())
	var before: int = player.firearm.mag_rounds
	player.firearm.holstered = false
	player.debug_fire()
	await _wait(0.1)
	print("FIRED  ", _gun())
	await _wait(1.3)
	print("BOLTED ", _gun(), "  (mag was ", before, ")")

	player.debug_place(g.body_center() + Vector3(0, -0.2, 1.0), 0.0, -60.0)
	await _wait(0.3)
	player._refresh_interact()
	print("BODY option=", player._interact_kind, " action=", player._body_action(g))
	player._interact()
	await _wait(2.6)
	print("SEARCHED ", g.searched, "  ", _gun())
	player._refresh_interact()
	print("BODY option=", player._interact_kind, " action=", player._body_action(g))
	player._interact()
	await _wait(5.0)
	print("COAT disguise=", player.disguise, " q=", player.disguise_quality, " tint=", player.firearm.sleeve_tint)

	var sentry: Node = level.get_node("Sentry")
	sentry._player = player
	player.firearm.holstered = true
	print("HOSTILITY disguised, rifle slung = %.2f" % sentry._hostility())
	player.firearm.holstered = false
	print("HOSTILITY disguised, rifle at ready = %.2f" % sentry._hostility())

	# Empty the rifle and reload from pockets.
	while player.firearm.mag_rounds > 0 or player.firearm.chambered:
		player.debug_fire()
		await _wait(1.3)
	print("EMPTY  ", _gun())
	player.firearm._start_reload()
	await _wait(0.2)
	print("RELOADING ", _gun())
	await _wait(3.2)
	print("RELOADED  ", _gun())
	player.firearm._start_reload()
	await _wait(0.1)
	print("TOP-UP (full) ", _gun())

	player.select_weapon(0)
	await _wait(1.2)
	print("SWITCHED ", player.firearm.data.id, " mag=", player.firearm.mag_rounds, " spares=", player.firearm.spare_mags)
	player.select_weapon(1)
	await _wait(1.2)
	print("BACK     ", _gun())
	player.wear("", 0.0)
	player.firearm.holstered = true
	print("HOSTILITY civilian, rifle slung = %.2f" % sentry._hostility())
	quit()
