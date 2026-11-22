extends SceneTree
## Headless check of hotel_de_la_plage_int.glb (not part of the game):
##   Godot --headless --path game --script ../tools/blender/town/check_hotel_int.gd
## Prints the Godot-local position / yaw of every named marker and door, then swings every door open 90 deg and
## sweeps a player capsule (r 0.35, h 1.75) along walking routes through every room, reporting overlaps.

const GLB := "res://assets/models/town/hotel_de_la_plage_int.glb"
const XC := -1.5
const MARKERS := ["Door_Front", "Door_Kitchen", "Door_Signals", "Door_Brenner", "Door_Dorm", "Door_Mess",
	"Door_CoalStore", "Door_WC", "Door_Store", "Stairs_Bottom", "Stairs_Top", "Cabinet", "Desk_Signals",
	"CipherMachine", "RadioBench", "Brenner_Desk", "Brenner_Bed", "Brenner_Coat", "Kitchen_Stove", "Kitchen_Table",
	"Mess_Table", "Reception", "CoalStore_Floor", "Dorm_Bunks", "Door", "CoalChute"]

# Routes in Blender coordinates before the XC shift: [x, y, floor z]. Converted to Godot local below.
var ROUTES := {
	"front door -> hall -> stair -> landing": [[0, -7.25, 0.16], [0, -6.0, 0.16], [0, -3.0, 0.16],
		[1.0, -1.4, 0.16], [3.85, -1.4, 0.16], [3.85, -2.12, 0.16], [3.85, -5.2, 2.27], [3.85, -5.8, 2.27],
		[2.7, -5.8, 2.27], [2.7, -5.2, 2.27], [2.7, -2.4, 4.2], [2.7, -1.6, 4.2], [2.7, 0.5, 4.2]],
	"1F corridor -> signals": [[2.7, 0.5, 4.2], [5.75, 0.5, 4.2], [5.75, -1.3, 4.2], [7.0, -2.8, 4.2], [8.0, -4.5, 4.2],
		[6.0, -4.0, 4.2]],
	"1F corridor -> Brenner office -> bedroom": [[2.7, 0.5, 4.2], [-2.35, 0.5, 4.2], [-2.35, -1.3, 4.2],
		[-3.3, -1.8, 4.2], [-6.5, -1.6, 4.2], [-8.3, -1.6, 4.2], [-8.4, -3.5, 4.2]],
	"1F corridor -> dorm": [[-2.0, 0.5, 4.2], [1.05, 0.5, 4.2], [1.05, 2.5, 4.2], [3.0, 2.5, 4.2], [10.3, 2.5, 4.2],
		[10.3, 3.98, 4.2], [1.0, 3.98, 4.2]],
	"1F corridor -> WC": [[1.0, 0.5, 4.2], [-0.85, 0.5, 4.2], [-0.85, 2.5, 4.2], [-2.5, 4.5, 4.2]],
	"1F corridor -> store": [[-2.0, 0.5, 4.2], [-5.85, 0.5, 4.2], [-5.85, 2.5, 4.2], [-7.5, 3.5, 4.2], [-8.5, 4.8, 4.2]],
	"1F corridor west/east ends": [[-10.3, 0.5, 4.2], [10.3, 0.5, 4.2]],
	"hall -> kitchen -> back door -> quay": [[0, -1.0, 0.16], [0, 0.5, 0.16], [-2.0, 0.5, 0.16], [-2.0, 2.4, 0.16],
		[-0.15, 2.9, 0.16], [-0.15, 5.0, 0.16], [-0.15, 6.0, 0.16], [-0.15, 7.6, 0.16], [-0.15, 8.6, 0.0]],
	"kitchen -> pantry": [[-3.5, 2.5, 0.16], [-5.2, 2.55, 0.16], [-7.5, 3.2, 0.16]],
	"hall -> salon": [[-3.6, -1.3, 0.16], [-5.4, -1.3, 0.16], [-7.0, -1.3, 0.16], [-9.6, -1.6, 0.16], [-9.6, -5.5, 0.16]],
	"corridor -> mess": [[0.0, 0.5, 0.16], [5.75, 0.5, 0.16], [5.75, -1.3, 0.16], [6.4, -1.8, 0.16], [10.5, -1.8, 0.16],
		[10.5, -5.6, 0.16]],
	"corridor -> coal store -> floor": [[3.0, 0.5, 0.16], [5.25, 0.5, 0.16], [5.25, 2.1, 0.16], [5.9, 2.1, 0.16],
		[8.87, 2.1, -2.0], [9.2, 2.1, -2.0], [9.3, 3.2, -2.0], [9.5, 3.9, -2.0], [8.0, 4.0, -2.0], [7.0, 5.6, -2.0]],
	"coal store -> chute passage -> shaft": [[9.3, 3.0, -2.0], [9.6, 3.0, -1.95], [10.8, 3.0, -1.95],
		[11.5, 3.0, -1.98], [11.93, 3.0, -1.98]],
}
## Furniture markers people stand at: hotel_post.gd sends NPCs to marker + 0.7 m toward the building centre.
const STANDS := ["Brenner_Desk", "Brenner_Bed", "Mess_Table", "Desk_Signals", "Kitchen_Stove", "Dorm_Bunks", "Cabinet",
	"Reception", "RadioBench", "Kitchen_Table", "Brenner_Coat", "CoalStore_Floor", "Stairs_Bottom", "Stairs_Top"]
const LIFT := 0.12   # capsule bottom above the floor, as a character rides up ramps and steps

var _root: Node3D
var _frames := 0


func _initialize() -> void:
	var ps := load(GLB) as PackedScene
	_root = ps.instantiate() as Node3D
	get_root().add_child(_root)
	print("== markers (Godot local: position, yaw deg) ==")
	for n in MARKERS:
		var node := _root.find_child(n, true, false) as Node3D
		if node == null:
			print("  MISSING ", n)
			continue
		var t := _local(node)
		print("  %-16s pos=(%.3f, %.3f, %.3f)  rot=(%.1f, %.1f, %.1f)  class=%s" % [n, t.origin.x, t.origin.y, t.origin.z,
			rad_to_deg(t.basis.get_euler().x), rad_to_deg(t.basis.get_euler().y), rad_to_deg(t.basis.get_euler().z), node.get_class()])
	var lamps := _root.find_children("Lamp_*", "Node3D", true, false)
	lamps.sort_custom(func(a, b): return int(String(a.name).trim_prefix("Lamp_")) < int(String(b.name).trim_prefix("Lamp_")))
	print("== lamps: %d ==" % lamps.size())
	for l in lamps:
		var o := _local(l as Node3D).origin
		print("  %-8s (%.2f, %.2f, %.2f) %s" % [l.name, o.x, o.y, o.z, l.get_class()])
	var doors := _root.find_children("DoorNode_*", "Node3D", true, false)
	var front := _root.find_child("Door", true, false) as Node3D
	if front:
		doors.append(front)
	print("== doors: %d ==" % doors.size())
	for d in doors:
		var shapes := (d as Node).find_children("*", "CollisionShape3D", true, false)
		var o := _local(d as Node3D).origin
		print("  %-20s hinge=(%.3f, %.3f, %.3f) class=%s col_shapes=%d" % [d.name, o.x, o.y, o.z, d.get_class(), shapes.size()])
		(d as Node3D).rotation.y += PI * 0.5
	var bodies := _root.find_children("*", "StaticBody3D", true, false)
	print("== static bodies: %d ==" % bodies.size())
	var tris := 0
	for mi in _root.find_children("*", "MeshInstance3D", true, false):
		var m := (mi as MeshInstance3D).mesh
		for s in m.get_surface_count():
			var arr := m.surface_get_arrays(s)
			var idx = arr[Mesh.ARRAY_INDEX]
			tris += (idx.size() if idx != null else (arr[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()) / 3
	print("== render triangles: %d ==" % tris)


func _local(n: Node3D) -> Transform3D:
	var t := Transform3D.IDENTITY
	var c: Node = n
	while c != null and c != _root:
		if c is Node3D:
			t = (c as Node3D).transform * t
		c = c.get_parent()
	return t


func _g(p: Array) -> Vector3:
	return Vector3(float(p[0]) + XC, float(p[2]), -float(p[1]))


func _physics_process(_delta: float) -> bool:
	_frames += 1
	if _frames < 3:
		return false
	var space := _root.get_world_3d().direct_space_state
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.75
	var q := PhysicsShapeQueryParameters3D.new()
	q.shape = cap
	q.margin = 0.0
	var bad := 0
	print("== capsule sweeps (doors open) ==")
	for rname in ROUTES:
		var pts: Array = ROUTES[rname]
		var hits := {}
		var nfloor := 0
		var nsamp := 0
		for k in range(pts.size() - 1):
			var a := _g(pts[k])
			var b := _g(pts[k + 1])
			var n := maxi(2, int(a.distance_to(Vector3(b.x, a.y, b.z)) / 0.12))
			for i in range(n + 1):
				var p := a.lerp(b, float(i) / n)
				nsamp += 1
				var rq := PhysicsRayQueryParameters3D.create(p + Vector3.UP * 0.6, p + Vector3.DOWN * 0.7)
				var r := space.intersect_ray(rq)
				var floor_y := p.y
				if r.is_empty():
					nfloor += 1
				else:
					floor_y = (r["position"] as Vector3).y
				q.transform = Transform3D(Basis.IDENTITY, Vector3(p.x, floor_y + 0.875 + LIFT, p.z))
				for h in space.intersect_shape(q, 8):
					var col: Object = h["collider"]
					var nm := String((col as Node).name) if col is Node else "?"
					if not hits.has(nm):
						hits[nm] = "(%.2f, %.2f, %.2f)" % [p.x, floor_y, p.z]
		var status := "OK" if hits.is_empty() else "BLOCKED by %s" % [hits]
		if not hits.is_empty():
			bad += 1
		print("  %-44s samples=%d no_floor=%d %s" % [rname, nsamp, nfloor, status])
	print("== %d of %d routes blocked ==" % [bad, ROUTES.size()])
	print("== stand points (marker, and marker + 0.7 m toward the centre) ==")
	for n in STANDS:
		var m := _local(_root.find_child(n, true, false) as Node3D).origin
		var d := Vector3(-m.x, 0, -m.z)
		var s2 := m + d.normalized() * 0.7
		var res := []
		for p in [m, s2]:
			q.transform = Transform3D(Basis.IDENTITY, Vector3(p.x, p.y + 0.875 + LIFT, p.z))
			var names := []
			for h in space.intersect_shape(q, 8):
				names.append(String((h["collider"] as Node).name))
			res.append("clear" if names.is_empty() else str(names))
		print("  %-16s at marker: %s | stand point (%.2f, %.2f, %.2f): %s" % [n, res[0], s2.x, s2.y, s2.z, res[1]])
	return true
