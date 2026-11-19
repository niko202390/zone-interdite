extends Node3D
## M1 "First Night" test level: a short Breton village street at blue hour in drizzle, with a German
## checkpoint at the north end. It's built at runtime from the generated kit in res://assets/models/env/.
## Anything not generated yet falls back to grey boxes, so the level always runs.
##
## Layout: the street runs along Z from z = -60 (south, where the player starts) to z = +60 (north, the checkpoint).
## The carriageway spans x = -3.5..3.5. Houses line both sides and face the street.

const ENV := "res://assets/models/env/"
const GROUND := "res://assets/textures/ground/"
const STREET_HALF := 3.5
const FRONT_SETBACK := 0.15

@onready var player: Player = $Player

var _houses: Array[Node3D] = []
var _poles: Array[Node3D] = []
var _flames: Array = []
var _rain: GPUParticles3D


func _ready() -> void:
	Visibility.reset()
	Visibility.ambient = 0.2          # blue hour under overcast
	Visibility.noise_floor_db = 34.0  # drizzle and wind
	DuskEnvironment.apply(self)
	_build_ground()
	_build_street()
	_build_houses()
	_build_square()
	_build_checkpoint()
	_build_poles_and_wires()
	_build_window_lights()
	_build_rain()
	_build_bounds()
	var amb := Ambience.new()
	amb.name = "Ambience"
	amb.player = player
	add_child(amb)
	# The checkpoint: just being seen here unchallenged is enough to get you stopped.
	Visibility.restricted_zones.append(AABB(Vector3(-6.0, -1.0, 41.0), Vector3(12.0, 6.0, 12.0)))
	_build_navigation()
	_spawn_guards()


func _build_navigation() -> void:
	add_to_group("navmesh_source")
	var region := NavigationRegion3D.new()
	region.name = "Navigation"
	var nm := NavigationMesh.new()
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nm.geometry_collision_mask = Game.LAYER_WORLD
	nm.geometry_source_geometry_mode = NavigationMesh.SOURCE_GEOMETRY_GROUPS_WITH_CHILDREN
	nm.geometry_source_group_name = &"navmesh_source"
	nm.cell_size = 0.25
	nm.cell_height = 0.25
	nm.agent_radius = 0.5
	nm.agent_height = 1.75
	nm.agent_max_climb = 0.5
	nm.filter_baking_aabb = AABB(Vector3(-60.0, -2.0, -80.0), Vector3(120.0, 14.0, 160.0))
	region.navigation_mesh = nm
	add_child(region)
	region.bake_finished.connect(func() -> void: Visibility.nav_ready = true)
	region.bake_navigation_mesh(true)


func _spawn_guards() -> void:
	# A sentry at the checkpoint, watching the street, and a patrol walking it.
	var sentry := Guard.new()
	sentry.name = "Sentry"
	sentry.patrol_points = PackedVector3Array([Vector3(2.4, 0.05, 46.6)])
	add_child(sentry)
	sentry.global_position = Vector3(2.4, 0.05, 46.6)
	sentry.rotation.y = deg_to_rad(8.0)

	var patrol := Guard.new()
	patrol.name = "Patrol"
	patrol.patrol_points = PackedVector3Array([Vector3(1.2, 0.05, 38.0), Vector3(-1.0, 0.05, 2.0),
		Vector3(1.0, 0.05, -44.0), Vector3(-1.0, 0.05, 2.0)])
	add_child(patrol)
	patrol.global_position = Vector3(1.2, 0.05, 30.0)
	patrol.rotation.y = 0.0


# --- asset helpers -----------------------------------------------------------------------------

## Places a kit asset with its front facing `facing_deg` (0 = +Z, 90 = +X, -90 = -X, 180 = -Z).
## Tags every collider with `surface`. If the .glb doesn't exist, a box of `fallback_size` is used instead.
func spawn(asset: String, pos: Vector3, facing_deg: float, surface: String, fallback_size: Vector3) -> Node3D:
	var path := ENV + asset + ".glb"
	var node: Node3D
	if ResourceLoader.exists(path):
		node = (load(path) as PackedScene).instantiate()
	else:
		node = _fallback_box(fallback_size, surface)
	node.name = asset.capitalize().replace(" ", "")
	add_child(node)
	node.position = pos
	node.rotation.y = deg_to_rad(facing_deg)
	_tag_surface(node, surface)
	return node


func _fallback_box(size: Vector3, surface: String) -> Node3D:
	var body := StaticBody3D.new()
	var mi := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.42, 0.41, 0.4) if surface != "wood" else Color(0.32, 0.25, 0.18)
	m.roughness = 0.9
	box.material = m
	mi.mesh = box
	mi.position.y = size.y * 0.5
	body.add_child(mi)
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = size
	cs.shape = shape
	cs.position.y = size.y * 0.5
	body.add_child(cs)
	return body


func _tag_surface(node: Node, surface: String) -> void:
	if node is CollisionObject3D:
		node.set_meta("surface", surface)
	for c in node.get_children():
		_tag_surface(c, surface)


## Bounding box of everything visible under `node`, in the node's parent space (so it includes the node's rotation).
func footprint(node: Node3D) -> AABB:
	var box := AABB()
	var first := true
	var inv := node.global_transform.affine_inverse()
	for vi in node.find_children("*", "VisualInstance3D", true, false):
		var local: AABB = (inv * (vi as VisualInstance3D).global_transform) * (vi as VisualInstance3D).get_aabb()
		box = local if first else box.merge(local)
		first = false
	return Transform3D(node.basis, Vector3.ZERO) * box


func find_marker(root: Node, marker: String) -> Node3D:
	return root.find_child(marker, true, false) as Node3D


# --- ground and street -------------------------------------------------------------------------

func _build_ground() -> void:
	var size := 420.0
	var mi := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(size, size)
	plane.subdivide_width = 1
	plane.subdivide_depth = 1
	mi.mesh = plane
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/ground.gdshader")
	for set_name in ["mud", "grass"]:
		mat.set_shader_parameter(set_name + "_albedo", _ground_tex(set_name, "albedo", Color(0.2, 0.17, 0.13) if set_name == "mud" else Color(0.22, 0.23, 0.14)))
		mat.set_shader_parameter(set_name + "_normal", _ground_tex(set_name, "normal", Color(0.5, 0.5, 1.0)))
		mat.set_shader_parameter(set_name + "_orm", _ground_tex(set_name, "orm", Color(1.0, 0.85, 0.0)))
	mat.set_shader_parameter("mask_scale", GroundMask.SCALE)
	mi.material_override = mat
	mi.position.y = -0.005
	add_child(mi)

	var body := StaticBody3D.new()
	body.name = "Ground"
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(size, 1.0, size)
	cs.shape = shape
	cs.position.y = -0.5
	body.add_child(cs)
	body.set_meta("surface_fn", GroundMask.surface_at)
	add_child(body)


func _ground_tex(set_name: String, channel: String, fallback: Color) -> Texture2D:
	var path := GROUND + "%s_%s.png" % [set_name, channel]
	return load(path) if ResourceLoader.exists(path) else ProcTex.flat(fallback)


func _build_street() -> void:
	for i in 12:
		var z := -55.0 + i * 10.0
		spawn("street_pave_10m", Vector3(0, 0, z), 0.0, "cobble", Vector3(7.0, 0.05, 10.0))


# --- houses ------------------------------------------------------------------------------------

## Lines one side of the street with houses from z_from to z_to, leaving the given gaps empty.
func _row(side: int, z_from: float, z_to: float, order: Array, gaps: Array) -> void:
	var z := z_from
	var i := 0
	var facing := 90.0 if side < 0 else -90.0
	while z < z_to:
		var skip := false
		for g in gaps:
			if z >= g.x and z < g.y:
				z = g.y
				skip = true
		if skip:
			continue
		var asset: String = order[i % order.size()]
		i += 1
		var house := spawn(asset, Vector3.ZERO, facing, "stone", _fallback_house_size(asset))
		var fp := footprint(house)
		# Push the house back so its front sits on the street edge, and start it at the cursor.
		var front_x := fp.end.x if side < 0 else fp.position.x
		var x := -STREET_HALF - FRONT_SETBACK - front_x if side < 0 else STREET_HALF + FRONT_SETBACK - front_x
		house.position = Vector3(x, 0.0, z - fp.position.z)
		_houses.append(house)
		z += fp.size.z + randf_range(0.0, 1.2)


func _fallback_house_size(asset: String) -> Vector3:
	match asset:
		"house_longere":
			return Vector3(14.0, 5.5, 6.5)
		"house_cafe":
			return Vector3(7.0, 8.0, 8.0)
	return Vector3(8.0, 9.0, 7.0)


func _build_houses() -> void:
	seed(1943)
	_row(-1, -62.0, 52.0, ["house_bourg", "house_cafe", "house_bourg", "house_longere", "house_bourg"],
		[Vector2(-30.0, -26.0), Vector2(6.0, 9.0)])
	_row(1, -62.0, 40.0, ["house_longere", "house_bourg", "house_bourg", "house_cafe", "house_bourg"],
		[Vector2(-6.0, 12.0), Vector2(26.0, 29.0)])


# --- set dressing ------------------------------------------------------------------------------

func _build_square() -> void:
	# The little square on the east side, around a granite wayside cross.
	spawn("wayside_cross", Vector3(9.5, 0, 3.0), -90.0, "stone", Vector3(1.4, 3.2, 1.4))
	spawn("cart_charrette", Vector3(6.2, 0, -2.5), -60.0, "wood", Vector3(1.6, 1.2, 3.2))
	spawn("barrel_wood", Vector3(5.2, 0, 8.6), 0.0, "wood", Vector3(0.6, 0.9, 0.6))
	spawn("barrel_wood", Vector3(5.9, 0, 9.3), 40.0, "wood", Vector3(0.6, 0.9, 0.6))
	spawn("crate_wood", Vector3(-4.3, 0, -18.0), 10.0, "wood", Vector3(0.8, 0.6, 0.6))
	spawn("crate_wood", Vector3(-4.2, 0.62, -18.1), 25.0, "wood", Vector3(0.8, 0.6, 0.6))
	for k in 4:
		spawn("stone_wall_low_4m", Vector3(13.5, 0, -5.0 + k * 4.0), -90.0, "stone", Vector3(4.0, 1.1, 0.6))


func _build_checkpoint() -> void:
	# A German control post at the north end: sentry box, sandbags, a knife-rest roadblock half across the road,
	# the curfew notice, a brazier, and a blue blackout lamp.
	spawn("sentry_box", Vector3(4.6, 0, 46.0), -90.0, "wood", Vector3(1.1, 2.4, 1.1))
	spawn("sandbag_wall_2m", Vector3(2.6, 0, 43.5), 0.0, "sand", Vector3(2.0, 1.1, 0.6))
	spawn("sandbag_wall_2m", Vector3(4.6, 0, 43.5), 0.0, "sand", Vector3(2.0, 1.1, 0.6))
	spawn("knife_rest_roadblock", Vector3(-1.0, 0, 47.5), 0.0, "wood", Vector3(3.0, 1.2, 1.2))
	spawn("notice_board", Vector3(-4.6, 0, 41.0), 90.0, "wood", Vector3(0.2, 2.0, 1.2))
	_brazier(Vector3(3.2, 0, 47.4))
	var lamp := spawn("wall_lantern", Vector3(4.3, 2.6, 44.9), -90.0, "metal", Vector3(0.25, 0.4, 0.25))
	var blue := OmniLight3D.new()
	blue.light_color = Color(0.38, 0.5, 1.0)
	blue.light_energy = 0.7
	blue.omni_range = 7.0
	blue.shadow_enabled = true
	lamp.add_child(blue)
	Visibility.register_light(blue)
	blue.position = Vector3(0, -0.15, 0.25)


func _brazier(pos: Vector3) -> void:
	var body := StaticBody3D.new()
	body.set_meta("surface", "metal")
	add_child(body)
	body.position = pos
	var drum := MeshInstance3D.new()
	var cyl := CylinderMesh.new()
	cyl.top_radius = 0.28
	cyl.bottom_radius = 0.28
	cyl.height = 0.75
	var rust := StandardMaterial3D.new()
	rust.albedo_color = Color(0.22, 0.12, 0.07)
	rust.roughness = 0.85
	rust.metallic = 0.4
	cyl.material = rust
	drum.mesh = cyl
	drum.position.y = 0.375
	body.add_child(drum)
	var cs := CollisionShape3D.new()
	var shape := CylinderShape3D.new()
	shape.radius = 0.3
	shape.height = 0.75
	cs.shape = shape
	cs.position.y = 0.375
	body.add_child(cs)

	var fire := GPUParticles3D.new()
	fire.amount = 70
	fire.lifetime = 0.9
	fire.local_coords = false
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	pm.emission_sphere_radius = 0.16
	pm.direction = Vector3.UP
	pm.spread = 12.0
	pm.initial_velocity_min = 0.5
	pm.initial_velocity_max = 1.3
	pm.gravity = Vector3(0, 0.8, 0)
	pm.scale_min = 0.6
	pm.scale_max = 1.4
	var g := Gradient.new()
	g.set_color(0, Color(1.0, 0.75, 0.35, 1.0))
	g.set_color(1, Color(0.6, 0.12, 0.02, 0.0))
	var gt := GradientTexture1D.new()
	gt.gradient = g
	pm.color_ramp = gt
	fire.process_material = pm
	var quad := QuadMesh.new()
	quad.size = Vector2(0.22, 0.3)
	var fm := StandardMaterial3D.new()
	fm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	fm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	fm.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	fm.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	fm.vertex_color_use_as_albedo = true
	fm.albedo_texture = ProcTex.soft_dot()
	fm.emission_enabled = true
	fm.emission = Color(1.0, 0.5, 0.15)
	fm.emission_energy_multiplier = 2.5
	quad.material = fm
	fire.draw_pass_1 = quad
	fire.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	body.add_child(fire)
	fire.position.y = 0.78

	var light := OmniLight3D.new()
	light.light_color = Color(1.0, 0.55, 0.24)
	light.light_energy = 2.4
	light.omni_range = 10.0
	light.shadow_enabled = true
	light.light_volumetric_fog_energy = 1.5
	body.add_child(light)
	light.position.y = 1.05
	_flames.append(light)
	Visibility.register_light(light)

	if SoundLib.has_sound("ambience/fire_crackle_loop"):
		var crackle := AudioStreamPlayer3D.new()
		crackle.stream = SoundLib.pick("ambience/fire_crackle_loop")
		crackle.bus = Game.BUS_WORLD
		crackle.unit_size = 2.0
		crackle.volume_db = SoundLib.gain("ambience/fire_crackle_loop")
		body.add_child(crackle)
		crackle.position.y = 0.8
		crackle.play()


func _build_poles_and_wires() -> void:
	# A PTT line runs up the east side of the street, with a drop to the checkpoint's field telephone.
	for k in 5:
		var z := -52.0 + k * 24.0
		if z > -8.0 and z < 14.0:
			z = 15.0
		_poles.append(spawn("telegraph_pole", Vector3(STREET_HALF + 0.6, 0, z), -90.0, "wood", Vector3(0.25, 7.5, 0.25)))
	for k in _poles.size() - 1:
		_wire_between(_poles[k], _poles[k + 1])
	var sentry_drop := Vector3(4.6, 2.35, 46.0)
	var last := _poles[_poles.size() - 1]
	var m := find_marker(last, "WireAttach_0")
	var from := m.global_position if m else last.global_position + Vector3.UP * 7.2
	add_child(WireSpan.build(from, sentry_drop, 0.5))


func _wire_between(a: Node3D, b: Node3D) -> void:
	for w in 4:
		var ma := find_marker(a, "WireAttach_%d" % w)
		var mb := find_marker(b, "WireAttach_%d" % w)
		var pa := ma.global_position if ma else a.global_position + Vector3(0, 7.2, (w - 1.5) * 0.3)
		var pb := mb.global_position if mb else b.global_position + Vector3(0, 7.2, (w - 1.5) * 0.3)
		if ma == null and w > 1:
			break
		add_child(WireSpan.build(pa, pb, randf_range(0.3, 0.45)))


## Blackout rules: almost every window is dark. The few marked WindowGlow leak a little warm light.
func _build_window_lights() -> void:
	for house in _houses:
		for mi_node in house.find_children("*", "MeshInstance3D", true, false):
			var mi := mi_node as MeshInstance3D
			if mi.mesh == null:
				continue
			for s in mi.mesh.get_surface_count():
				var mat := mi.get_active_material(s)
				if mat == null or not mat.resource_name.to_lower().contains("windowglow"):
					continue
				var arrays := mi.mesh.surface_get_arrays(s)
				var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
				var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
				if verts.is_empty():
					continue
				var center := Vector3.ZERO
				var normal := Vector3.ZERO
				for v in verts:
					center += v
				for n in normals:
					normal += n
				center /= verts.size()
				normal = (mi.global_basis * normal.normalized()).normalized() if normal.length() > 0.01 else house.global_basis.z
				var light := OmniLight3D.new()
				light.light_color = Color(1.0, 0.6, 0.3)
				light.light_energy = 0.9
				light.omni_range = 5.0
				light.shadow_enabled = true
				add_child(light)
				light.global_position = mi.global_transform * center + normal * 0.45
				Visibility.register_light(light)


func _build_rain() -> void:
	var rain := GPUParticles3D.new()
	rain.name = "Rain"
	rain.amount = 7000
	rain.lifetime = 1.3
	rain.local_coords = false
	rain.visibility_aabb = AABB(Vector3(-20, -14, -20), Vector3(40, 18, 40))
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(16, 0.5, 16)
	pm.direction = Vector3(0.08, -1, 0.03)
	pm.spread = 3.0
	pm.initial_velocity_min = 8.0
	pm.initial_velocity_max = 9.5
	pm.gravity = Vector3(0, -2.0, 0)
	pm.particle_flag_align_y = true
	rain.process_material = pm
	var quad := QuadMesh.new()
	quad.size = Vector2(0.006, 0.32)
	var m := StandardMaterial3D.new()
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = Color(0.62, 0.66, 0.74, 0.13)
	# Fade streaks in with distance so drops right in front of the eye don't read as thick white bars.
	m.distance_fade_mode = BaseMaterial3D.DISTANCE_FADE_PIXEL_ALPHA
	m.distance_fade_min_distance = 0.6
	m.distance_fade_max_distance = 3.5
	m.billboard_mode = BaseMaterial3D.BILLBOARD_FIXED_Y
	m.billboard_keep_scale = true
	quad.material = m
	rain.draw_pass_1 = quad
	rain.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(rain)
	_rain = rain


func _build_bounds() -> void:
	# Invisible edges well inside the fog.
	for spec in [[Vector3(0, 5, 120), Vector3(260, 10, 1)], [Vector3(0, 5, -120), Vector3(260, 10, 1)],
			[Vector3(120, 5, 0), Vector3(1, 10, 260)], [Vector3(-120, 5, 0), Vector3(1, 10, 260)]]:
		var body := StaticBody3D.new()
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = spec[1]
		cs.shape = shape
		body.add_child(cs)
		add_child(body)
		body.position = spec[0]


func _process(_delta: float) -> void:
	if _rain and player:
		_rain.global_position = player.global_position + Vector3(0, 11, 0) + player.velocity * 0.6
	var t := Time.get_ticks_msec() / 1000.0
	for i in _flames.size():
		var l: OmniLight3D = _flames[i]
		l.light_energy = 2.4 * (0.82 + 0.1 * sin(t * 11.0 + i) + 0.08 * sin(t * 23.0 + i * 2.0))
