class_name WireSpan
extends RefCounted
## Builds a sagging telephone/telegraph wire between two points as a thin tube mesh.
## The PTT lines matter later: cutting them stops alerts from travelling (see docs/DESIGN.md).

static var _material: StandardMaterial3D


static func build(a: Vector3, b: Vector3, sag := 0.35, radius := 0.0035, segments := 28) -> MeshInstance3D:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var sides := 5
	var pts: Array[Vector3] = []
	for i in segments + 1:
		var t := float(i) / segments
		pts.append(a.lerp(b, t) + Vector3.DOWN * (4.0 * sag * t * (1.0 - t)))
	for i in segments:
		var p0 := pts[i]
		var p1 := pts[i + 1]
		var tangent := (p1 - p0).normalized()
		var n := tangent.cross(Vector3.UP).normalized()
		if n.length() < 0.5:
			n = Vector3.RIGHT
		var bn := tangent.cross(n).normalized()
		for s in sides:
			var a0 := TAU * s / sides
			var a1 := TAU * (s + 1) / sides
			var o0 := (n * cos(a0) + bn * sin(a0)) * radius
			var o1 := (n * cos(a1) + bn * sin(a1)) * radius
			st.set_normal(o0.normalized())
			st.add_vertex(p0 + o0)
			st.set_normal(o1.normalized())
			st.add_vertex(p0 + o1)
			st.set_normal(o1.normalized())
			st.add_vertex(p1 + o1)
			st.set_normal(o0.normalized())
			st.add_vertex(p0 + o0)
			st.set_normal(o1.normalized())
			st.add_vertex(p1 + o1)
			st.set_normal(o0.normalized())
			st.add_vertex(p1 + o0)
	var mi := MeshInstance3D.new()
	mi.mesh = st.commit()
	if _material == null:
		_material = StandardMaterial3D.new()
		_material.albedo_color = Color(0.05, 0.05, 0.05)
		_material.roughness = 0.45
		_material.metallic = 0.6
		_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	mi.material_override = _material
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi
