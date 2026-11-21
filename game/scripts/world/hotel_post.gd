class_name HotelPost
extends Node3D
## The Kriegsmarine signals post in the Hôtel de la Plage: the goal of the mission.
##
## The monthly key sheets are in the steel cabinet in the signals room, locked with a key Oberleutnant Brenner
## keeps on his watch chain. Today's strip lies on the operator's desk while he's on watch. The player can copy
## by hand (slow, and only while standing still at it), photograph with the dead operator's camera, or simply
## take them. London wants it done so the enemy never knows: key back on the chain, cabinet locked, nothing
## missing. Everything here hangs off named markers in hotel_de_la_plage_int.glb.

signal sheets_obtained(kind: String)

const COPY_TIME := 40.0          # seconds of standing at the cabinet to copy the monthly sheets by hand
const STRIP_TIME := 14.0         # seconds to copy today's strip off the desk
const PHOTO_TIME := 4.0
const LOCK_KITCHEN_AT := 21.0 * 60.0 + 30.0   # the cook leaves and locks the back door

var level: Node3D
var hotel: Node3D
var player: Player
var brenner: Guard
var operator: Guard

## Results, read by London's report.
var monthly := ""                # "", "copied", "photographed", "taken"
var strip := false
var key_taken := false
var key_returned := false
var cabinet_open := false
var cabinet_seen_open := false
var camera_found := false
var exposures := 3
var was_inside := false

var _cabinet: Node3D
var _desk: Node3D
var _copy := 0.0                 # progress 0..1 of the monthly copy
var _strip_copy := 0.0
var _copying := ""               # "", "monthly", "strip"
var _copy_anchor := Vector3.ZERO
var _copy_note_t := 0.0
var _scratch: AudioStreamPlayer
var _pick: Interactable
var _return_key: Interactable
var _strip_it: Interactable


static func available(h: Node3D) -> bool:
	return h != null and h.find_child("Cabinet", true, false) != null


func marker(n: String) -> Node3D:
	return hotel.find_child(n, true, false) as Node3D


func mpos(n: String, fallback := Vector3.INF) -> Vector3:
	var m := marker(n)
	return m.global_position if m else fallback


func setup(lvl: Node3D, h: Node3D, p: Player) -> void:
	level = lvl
	hotel = h
	player = p
	_cabinet = marker("Cabinet")
	_desk = marker("Desk_Signals")
	_scratch = AudioStreamPlayer.new()
	_scratch.stream = SoundLib.pick("ui/pen_scratch_loop")
	_scratch.volume_db = -12.0
	add_child(_scratch)
	_setup_doors()
	_setup_lamps()
	_setup_cabinet()
	_setup_strip()
	_setup_coal_chute()


# --- the building --------------------------------------------------------------------------------

func _setup_doors() -> void:
	for d in hotel.find_children("DoorNode_*", "Node3D", true, false):
		_door(d as Node3D, String(d.name).trim_prefix("DoorNode_"))
	var front := hotel.find_child("Door", true, false) as Node3D
	if front and front.find_children("*", "MeshInstance3D", true, false).size() + int(front is MeshInstance3D) > 0:
		_door(front, "Front")


func _door(door: Node3D, room: String) -> void:
	var it := Interactable.new()
	it.prompt = "open the door"
	it.radius = 1.2
	it.noise_db = 42.0
	add_child(it)
	# Stand the prompt a little out from the hinge along the door's width.
	var leaf := AABB()
	for mi in door.find_children("*", "MeshInstance3D", true, false):
		leaf = (door.global_transform.affine_inverse() * (mi as MeshInstance3D).global_transform) * (mi as MeshInstance3D).get_aabb()
		break
	it.global_position = door.global_transform * (leaf.get_center() if leaf.size != Vector3.ZERO else Vector3(0.5, 1.0, 0.0))
	var closed_y := door.rotation.y
	var st := {"open": false}
	it.on_use = func(_p: Node3D) -> void:
		if room == "Kitchen" and not st["open"] and fposmod(Game.clock_minutes, 1440.0) >= LOCK_KITCHEN_AT \
				and fposmod(Game.clock_minutes, 1440.0) < 6.0 * 60.0:
			player.note("Locked. The cook has gone home for the night.", 2.5)
			SoundLib.play_3d("impacts/impact_wood", it.global_position, -16.0, 15.0, 0.1, 1.5)
			return
		st["open"] = not st["open"]
		it.prompt = "close the door" if st["open"] else "open the door"
		var tw := create_tween()
		tw.tween_property(door, "rotation:y", closed_y + (deg_to_rad(90.0) if st["open"] else 0.0), 0.9) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		SoundLib.play_3d("impacts/impact_wood", door.global_position + Vector3.UP, -14.0, 25.0, 0.2, 2.0)


func _setup_lamps() -> void:
	for n in hotel.find_children("Lamp_*", "Node3D", true, false):
		if n is MeshInstance3D:
			(n as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			continue
		var l := OmniLight3D.new()
		l.light_color = Color(1.0, 0.64, 0.36)
		l.light_energy = 1.0
		l.omni_range = 5.5
		l.shadow_enabled = true
		(n as Node3D).add_child(l)
		Visibility.register_light(l)


## Is the player inside the building (either floor)?
func player_inside() -> bool:
	var lp := hotel.global_transform.affine_inverse() * player.global_position
	return lp.x > -12.8 and lp.x < 12.8 and lp.z > -7.0 and lp.z < 6.6 and lp.y > -0.5 and lp.y < 8.0


# --- the cabinet, the strip, the copying ---------------------------------------------------------

func _setup_cabinet() -> void:
	var it := Interactable.new()
	it.prompt = "the steel cabinet"
	it.radius = 1.2
	add_child(it)
	it.global_position = _cabinet.global_position + Vector3.UP * 1.0
	it.on_use = func(_p: Node3D) -> void:
		if monthly != "" and not cabinet_open:
			player.note("Locked again, as you found it.", 2.0)
			return
		if not player.items.get("cabinet_key", false) and not cabinet_open:
			player.note("A Panzerschrank, locked. Brenner keeps the key on his watch chain.", 3.5)
			level.player.overlay.add_lead("The key sheets are in a steel cabinet in the signals room. Brenner has the key on his watch chain.")
			return
		if not cabinet_open:
			cabinet_open = true
			SoundLib.play_3d("weapons/p38_decocker", it.global_position, -4.0, 20.0, 0.05, 2.0)
			Game.emit_noise(it.global_position, 40.0, player)
		var opts := ["Copy the sheets by hand. Slow, and you must stay put.",
			"Photograph them. %d exposure%s left." % [exposures, "" if exposures == 1 else "s"] if camera_found and exposures > 0 else "(No camera.)",
			"Take them."]
		if _copy > 0.0:
			opts[0] = "Go on copying (%d%% done)." % int(_copy * 100.0)
		player.overlay.ask(opts, 12.0, func(i: int) -> void: _cabinet_choice(i))


func _cabinet_choice(i: int) -> void:
	match i:
		0:
			_copying = "monthly"
			_copy_anchor = player.global_position
			player.note("February and March, four columns of trigrams a day. Pencil, and no mistakes.", 4.0)
		1:
			if not camera_found or exposures <= 0:
				player.note("You have no camera.", 2.0)
				return
			exposures -= 1
			player.busy = PHOTO_TIME
			SoundLib.play_2d("ui/lighter_close", -4.0)
			get_tree().create_timer(PHOTO_TIME * 0.5, false).timeout.connect(func() -> void: SoundLib.play_2d("ui/lighter_close", -6.0))
			get_tree().create_timer(PHOTO_TIME, false).timeout.connect(func() -> void:
				_finish_monthly("photographed"))
		2:
			_finish_monthly("taken")


func _finish_monthly(how: String) -> void:
	monthly = how
	_copying = ""
	_scratch.stop()
	if how != "taken":
		cabinet_open = false
		SoundLib.play_3d("weapons/p38_decocker", _cabinet.global_position + Vector3.UP, -4.0, 20.0, 0.05, 2.0)
	match how:
		"copied":
			player.note("Done. Every sheet back in its place, the cabinet locked. Now the key.", 5.0)
		"photographed":
			player.note("Click. Wind on. The sheets go back in order, the cabinet locked. Now the key.", 5.0)
		"taken":
			player.note("You stuff the sheets inside your coat. In the morning they'll know.", 5.0)
	player.overlay.add_lead({"copied": "I have the February and March key sheets, copied by hand.",
		"photographed": "I photographed the February and March key sheets.",
		"taken": "I took the key sheets. The Germans will know by morning and change everything."}[how])
	sheets_obtained.emit(how)


func _setup_strip() -> void:
	if _desk == null:
		return
	_strip_it = Interactable.new()
	_strip_it.prompt = "copy today's key strip"
	_strip_it.radius = 1.1
	add_child(_strip_it)
	_strip_it.global_position = _desk.global_position + Vector3.UP * 0.85
	_strip_it.on_use = func(_p: Node3D) -> void:
		_copying = "strip"
		_copy_anchor = player.global_position
		player.note("Today's settings, clipped by the machine. A quick copy.", 3.0)


func _process(delta: float) -> void:
	if player == null or player.dead:
		return
	if player_inside() and not was_inside:
		was_inside = true
		level.call("_task_done", "hotel")
	# The strip is only there to copy while the operator's away from his desk.
	if _strip_it:
		var op_away := operator == null or operator.is_dead() or operator.global_position.distance_to(_desk.global_position) > 3.0
		_strip_it.enabled = not strip and op_away
	_update_copy(delta)
	_update_key_actions()
	# The operator coming back to an open cabinet: the game is up.
	if cabinet_open and not cabinet_seen_open and operator and not operator.is_dead() \
			and operator.global_position.distance_to(_cabinet.global_position) < 4.0 and operator.state != Guard.State.DEAD:
		cabinet_seen_open = true
		operator.raise_town(2, "cabinet")
		operator.bark("alerted")


func _update_copy(delta: float) -> void:
	if _copying == "":
		if _scratch.playing:
			_scratch.stop()
		return
	var moved := player.global_position.distance_to(_copy_anchor) > 0.6
	if moved or player.is_aiming() or player.dragging:
		player.note("You stop copying. %d%% done." % int((_copy if _copying == "monthly" else _strip_copy) * 100.0), 2.5)
		_copying = ""
		return
	if not _scratch.playing:
		_scratch.play()
	_copy_note_t -= delta
	if _copying == "monthly":
		_copy = minf(_copy + delta / COPY_TIME, 1.0)
		if _copy_note_t <= 0.0:
			_copy_note_t = 8.0
			player.note("Copying... %d%%" % int(_copy * 100.0), 2.0)
		if _copy >= 1.0:
			_finish_monthly("copied")
	else:
		_strip_copy = minf(_strip_copy + delta / STRIP_TIME, 1.0)
		if _strip_copy >= 1.0:
			_copying = ""
			_scratch.stop()
			strip = true
			player.note("Today's strip, copied. Good, but London wants the month.", 4.0)
			player.overlay.add_lead("I have today's key strip from the operator's desk.")
			sheets_obtained.emit("strip")


# --- Brenner and his key -------------------------------------------------------------------------

func _update_key_actions() -> void:
	if player.items.get("cabinet_key", false) and not key_taken:
		key_taken = true   # off his body, by searching it
	if brenner == null or _pick == null:
		return
	var near := player.global_position.distance_to(brenner.global_position) < 1.8
	var helpless := brenner.asleep or brenner.is_dead()
	_pick.enabled = near and helpless and not key_taken and not brenner.searched
	_pick.global_position = brenner.global_position + Vector3.UP * 0.7
	_return_key.enabled = near and brenner.asleep and key_taken and not key_returned and not cabinet_open \
		and player.items.get("cabinet_key", false)
	_return_key.global_position = _pick.global_position


func spawn_people() -> void:
	var rnd := func(n: String) -> Vector3:
		var v := mpos(n)
		return v + Vector3.UP * 0.05 if v != Vector3.INF else Vector3.INF
	var desk_b: Vector3 = rnd.call("Brenner_Desk")
	var bed: Vector3 = rnd.call("Brenner_Bed")
	var mess: Vector3 = rnd.call("Mess_Table")
	var desk_s: Vector3 = rnd.call("Desk_Signals")
	var stove: Vector3 = rnd.call("Kitchen_Stove")
	var bunks: Vector3 = rnd.call("Dorm_Bunks")
	var kitchen_door: Vector3 = rnd.call("Door_Kitchen")
	if desk_b != Vector3.INF:
		brenner = Guard.new()
		brenner.name = "Brenner"
		brenner.model_variant = "feldgendarm"
		brenner.carries_key = true
		brenner.patrol_points = PackedVector3Array([desk_b + _toward_room(desk_b)])
		var sched: Array = []
		if mess != Vector3.INF:
			sched.append({"from": 20.0 * 60.0, "to": 20.0 * 60.0 + 45.0, "pos": mess + _toward_room(mess), "yaw": 0.0})
		if kitchen_door != Vector3.INF:
			sched.append({"from": 22.0 * 60.0 + 30.0, "to": 22.0 * 60.0 + 50.0, "pos": kitchen_door + hotel.global_basis.z * -2.5, "yaw": 0.0})
		if bed != Vector3.INF:
			sched.append({"from": 23.0 * 60.0 + 45.0, "to": 24.0 * 60.0, "pos": bed, "yaw": 0.0, "sleep": true})
			sched.append({"from": 0.0, "to": 6.0 * 60.0, "pos": bed, "yaw": 0.0, "sleep": true})
		brenner.schedule = sched
		level.add_child(brenner)
		brenner.global_position = brenner.patrol_points[0]
	if desk_s != Vector3.INF:
		operator = Guard.new()
		operator.name = "RadioOperator"
		operator.patrol_points = PackedVector3Array([desk_s + _toward_room(desk_s)])
		var s2: Array = []
		if stove != Vector3.INF:
			s2.append({"from": 21.0 * 60.0, "to": 21.0 * 60.0 + 10.0, "pos": stove + _toward_room(stove), "yaw": 0.0})
		if bunks != Vector3.INF:
			s2.append({"from": 0.0, "to": 4.0, "pos": bunks + _toward_room(bunks), "yaw": 0.0})
		operator.schedule = s2
		level.add_child(operator)
		operator.global_position = operator.patrol_points[0]
	_pick = Interactable.new()
	_pick.prompt = "take the cabinet key from his watch chain"
	_pick.radius = 1.3
	_pick.busy_time = 2.5
	_pick.noise_db = 22.0
	add_child(_pick)
	_pick.on_use = func(_p: Node3D) -> void:
		key_taken = true
		player.items["cabinet_key"] = true
		if brenner.is_dead():
			player.note("A small steel key on his watch chain. He won't miss it now.", 3.5)
		else:
			player.note("Slowly... the chain, the clip, the key. He breathes on. Put it back before he wakes.", 5.0)
		player.overlay.add_lead("I have Brenner's cabinet key. It must be back on his chain by morning.")
	_return_key = Interactable.new()
	_return_key.prompt = "put the key back on his chain"
	_return_key.radius = 1.3
	_return_key.busy_time = 2.5
	_return_key.noise_db = 22.0
	_return_key.enabled = false
	add_child(_return_key)
	_return_key.on_use = func(_p: Node3D) -> void:
		key_returned = true
		player.items["cabinet_key"] = false
		player.note("Back on the chain. He'll never know it went anywhere.", 4.0)


## A step in from a furniture marker toward the middle of the building, so people stand beside it, not in it.
func _toward_room(p: Vector3) -> Vector3:
	var c := hotel.global_position + Vector3.UP * (p.y - hotel.global_position.y)
	var d := c - p
	d.y = 0.0
	return d.normalized() * 0.7 if d.length() > 0.01 else Vector3.ZERO


# --- the coal chute ------------------------------------------------------------------------------

func _setup_coal_chute() -> void:
	var chute := hotel.find_child("CoalChute", true, false) as Node3D
	var inside := mpos("CoalStore_Floor")
	if chute == null or inside == Vector3.INF:
		return
	var it := Interactable.new()
	it.prompt = "lift the coal hatch and climb down"
	it.radius = 1.4
	it.busy_time = 2.2
	it.noise_db = 58.0
	add_child(it)
	var outward := (chute.global_position - hotel.global_position)
	outward.y = 0.0
	it.global_position = chute.global_position + outward.normalized() * 0.6 + Vector3.UP * 0.4
	it.on_use = func(_p: Node3D) -> void:
		var tw := create_tween()
		tw.tween_property(chute, "rotation:z", chute.rotation.z - deg_to_rad(80.0), 0.5)
		tw.tween_interval(1.2)
		tw.tween_callback(func() -> void:
			player.debug_place(inside + Vector3.UP * 0.3, rad_to_deg(player.yaw), 0.0)
			SoundLib.play_2d("footsteps/gravel_run", 2.0)
			player.note("Down the chute onto the coal, filthy and loud. Inside.", 3.0))
		tw.tween_property(chute, "rotation:z", chute.rotation.z, 0.6)


# --- the report ----------------------------------------------------------------------------------

func report_line() -> String:
	var parts := PackedStringArray()
	match monthly:
		"copied":
			parts.append("February and March sheets copied by hand")
		"photographed":
			parts.append("February and March sheets photographed")
		"taken":
			parts.append("February and March sheets TAKEN")
	if strip:
		parts.append("today's strip copied")
	if parts.is_empty():
		return "not obtained"
	var key := ""
	if key_taken and not key_returned and monthly != "taken":
		key = "  The cabinet key was not returned."
	return ", ".join(parts) + "." + key


## 0 = they never knew, 1 = they suspect, 2 = they know.
func trace() -> int:
	if monthly == "taken" or cabinet_seen_open:
		return 2
	if key_taken and not key_returned:
		return 1
	if cabinet_open:
		return 1
	return 0
