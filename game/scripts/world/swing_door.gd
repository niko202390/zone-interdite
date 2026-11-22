class_name SwingDoor
extends Node3D
## A door that swings on its hinge. The player opens and closes it with F; guards open it as they come through
## and pull it shut behind them. A door the player leaves open is evidence: a guard who sees it standing open
## gets suspicious, comes over and closes it.
##
## Collision on the leaf is switched off while the navigation mesh bakes, so patrols can path through doorways.

var door: Node3D
var room := ""
var is_open := false
var left_open_by_player := false
## Set by a guard who has noticed it open; he closes it when he gets there.
var noticed_by: Node3D = null
## Optional check before the player may open it (returns "" to allow, or a reason to show).
var lock_check: Callable
var _closed_y := 0.0
var _it: Interactable
var _guard_opened := false
var _clear_t := 0.0
var _check_t := 0.0


static func make(parent: Node, door_node: Node3D, room_name := "") -> SwingDoor:
	var d := SwingDoor.new()
	d.door = door_node
	d.room = room_name
	parent.add_child(d)
	return d


func _ready() -> void:
	add_to_group("swing_doors")
	_closed_y = door.rotation.y
	_it = Interactable.new()
	_it.prompt = "open the door"
	_it.radius = 1.2
	_it.noise_db = 42.0
	add_child(_it)
	global_position = center()
	_it.global_position = global_position
	_it.on_use = func(p: Node3D) -> void:
		if not is_open and lock_check.is_valid():
			var why: String = lock_check.call()
			if why != "":
				if p.has_method("note"):
					p.note(why, 2.5)
				SoundLib.play_3d("impacts/impact_wood", global_position, -16.0, 15.0, 0.1, 1.5)
				return
		set_open(not is_open, true)


## The middle of the leaf, where you'd reach for the handle.
func center() -> Vector3:
	for mi in door.find_children("*", "MeshInstance3D", true, false) + ([door] if door is MeshInstance3D else []):
		var m := mi as MeshInstance3D
		return m.global_transform * m.get_aabb().get_center()
	return door.global_position + Vector3.UP


func set_open(open: bool, by_player := false) -> void:
	if open == is_open:
		return
	is_open = open
	left_open_by_player = open and by_player
	if not open:
		noticed_by = null
		_guard_opened = false
	_it.prompt = "close the door" if open else "open the door"
	var tw := create_tween()
	tw.tween_property(door, "rotation:y", _closed_y + (deg_to_rad(90.0) if open else 0.0), 0.8 if by_player else 0.6) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	SoundLib.play_3d("impacts/impact_wood", global_position, -14.0, 25.0, 0.2, 2.0)


func set_collision(on: bool) -> void:
	for b in door.find_children("*", "CollisionShape3D", true, false):
		(b as CollisionShape3D).disabled = not on


func _physics_process(delta: float) -> void:
	_check_t -= delta
	if _check_t > 0.0:
		return
	_check_t = 0.2
	var near_guard := false
	for n in get_tree().get_nodes_in_group("guards"):
		var g := n as Guard
		if g == null or g.is_dead() or g.asleep:
			continue
		var d := Vector2(g.global_position.x - global_position.x, g.global_position.z - global_position.z).length()
		if d < (2.1 if g == noticed_by else 1.7):
			near_guard = true
			if not is_open:
				# A guard walking up to it opens it.
				set_open(true)
				_guard_opened = true
			elif g == noticed_by:
				# The one who saw it open shuts it.
				set_open(false)
	if _guard_opened and is_open:
		_clear_t = 0.0 if near_guard else _clear_t + 0.2
		if _clear_t > 1.6:
			set_open(false)
