class_name ImpactFX
extends RefCounted
## Bullet impacts: a decal, a puff of debris and dust, and a sound, chosen by surface.
## Also decides which surface a collider is made of, for footsteps and impacts alike.

const MAX_DECALS := 128
const DECAL_CULL := 0xFFFFF & ~(1 << 1)   # never project onto the viewmodel layer

const SURFACES := {
	"stone": {"dust": Color(0.6, 0.58, 0.55), "sound": "impacts/impact_stone", "ricochet": 0.18, "hole": "stone"},
	"cobble": {"dust": Color(0.55, 0.54, 0.52), "sound": "impacts/impact_stone", "ricochet": 0.25, "hole": "stone"},
	"gravel": {"dust": Color(0.5, 0.48, 0.45), "sound": "impacts/impact_dirt", "ricochet": 0.1, "hole": "mud"},
	"wood": {"dust": Color(0.4, 0.31, 0.22), "sound": "impacts/impact_wood", "ricochet": 0.0, "hole": "wood"},
	"mud": {"dust": Color(0.22, 0.18, 0.14), "sound": "impacts/impact_dirt", "ricochet": 0.0, "hole": "mud"},
	"grass": {"dust": Color(0.24, 0.22, 0.15), "sound": "impacts/impact_dirt", "ricochet": 0.0, "hole": "grass"},
	"metal": {"dust": Color(1.0, 0.7, 0.35), "sound": "impacts/ricochet", "ricochet": 0.6, "hole": "stone", "sparks": true},
	"sand": {"dust": Color(0.5, 0.44, 0.34), "sound": "impacts/impact_dirt", "ricochet": 0.0, "hole": "mud"},
	"flesh": {"dust": Color(0.22, 0.02, 0.02), "sound": "impacts/impact_dirt", "ricochet": 0.0, "hole": ""},
}

static var _decals: Array = []
static var _process_mats := {}
static var _draw_mesh: QuadMesh


static func surface_of(collider: Object, pos: Vector3) -> String:
	if collider == null:
		return "stone"
	if collider.has_meta("surface_fn"):
		return String((collider.get_meta("surface_fn") as Callable).call(pos))
	if collider.has_meta("surface"):
		return String(collider.get_meta("surface"))
	return "stone"


static func spawn(root: Node, pos: Vector3, normal: Vector3, dir: Vector3, surface: String) -> void:
	var fx: Dictionary = SURFACES.get(surface, SURFACES["stone"])
	if fx["hole"] != "":
		_spawn_decal(root, pos, normal, fx["hole"])
	_spawn_puff(root, pos, normal.lerp(-dir, 0.25).normalized(), fx["dust"], fx.get("sparks", false))
	SoundLib.play_3d(fx["sound"], pos, 0.0, 90.0, 0.08, 3.0)
	if randf() < float(fx["ricochet"]):
		SoundLib.play_3d("impacts/ricochet", pos, 0.0, 140.0, 0.12, 4.0)
	Game.emit_noise(pos, 92.0, null)


static func basis_from_up(up: Vector3) -> Basis:
	up = up.normalized()
	var ref := Vector3.FORWARD if absf(up.dot(Vector3.UP)) > 0.95 else Vector3.UP
	var x := ref.cross(up).normalized()
	var z := x.cross(up).normalized()
	return Basis(x, up, z)


static func _spawn_decal(root: Node, pos: Vector3, normal: Vector3, hole: String) -> void:
	var d := Decal.new()
	d.texture_albedo = ProcTex.bullet_hole(hole)
	var s := randf_range(0.055, 0.075)
	d.size = Vector3(s, 0.06, s)
	d.cull_mask = DECAL_CULL
	d.normal_fade = 0.3
	root.add_child(d)
	d.global_transform = Transform3D(basis_from_up(normal).rotated(normal.normalized(), randf() * TAU), pos)
	_decals.append(d)
	while _decals.size() > MAX_DECALS:
		var old: Node = _decals.pop_front()
		if is_instance_valid(old):
			old.queue_free()


static func _spawn_puff(root: Node, pos: Vector3, out: Vector3, color: Color, sparks: bool) -> void:
	var p := GPUParticles3D.new()
	p.one_shot = true
	p.explosiveness = 0.95
	p.amount = 18
	p.lifetime = 2.2
	p.local_coords = false
	p.process_material = _process_material(color, sparks)
	p.draw_pass_1 = _quad()
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	root.add_child(p)
	p.global_transform = Transform3D(basis_from_up(out), pos + out * 0.02)
	p.emitting = true
	p.get_tree().create_timer(p.lifetime + 0.5, false).timeout.connect(p.queue_free)


static func _process_material(color: Color, sparks: bool) -> ParticleProcessMaterial:
	var key := color.to_html() + str(sparks)
	if _process_mats.has(key):
		return _process_mats[key]
	var m := ParticleProcessMaterial.new()
	m.direction = Vector3.UP
	m.spread = 38.0
	m.initial_velocity_min = 0.6
	m.initial_velocity_max = 4.5 if sparks else 3.0
	m.gravity = Vector3(0, -2.2, 0)
	m.damping_min = 2.5
	m.damping_max = 5.0
	m.scale_min = 0.25
	m.scale_max = 1.6
	var grow := Curve.new()
	grow.add_point(Vector2(0.0, 0.3))
	grow.add_point(Vector2(0.25, 0.8))
	grow.add_point(Vector2(1.0, 1.6))
	var ct := CurveTexture.new()
	ct.curve = grow
	m.scale_curve = ct
	var fade := Gradient.new()
	fade.set_color(0, Color(color, 0.85))
	fade.set_color(1, Color(color, 0.0))
	var gt := GradientTexture1D.new()
	gt.gradient = fade
	m.color_ramp = gt
	_process_mats[key] = m
	return m


static func _quad() -> QuadMesh:
	if _draw_mesh:
		return _draw_mesh
	_draw_mesh = QuadMesh.new()
	_draw_mesh.size = Vector2(0.09, 0.09)
	var mat := StandardMaterial3D.new()
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	mat.vertex_color_use_as_albedo = true
	mat.albedo_texture = ProcTex.soft_dot()
	mat.shading_mode = BaseMaterial3D.SHADING_MODE_PER_VERTEX
	mat.roughness = 1.0
	_draw_mesh.material = mat
	return _draw_mesh
