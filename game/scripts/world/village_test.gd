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


## Seconds between a call to headquarters and the reinforcements setting off up the street.
var reinforcement_delay := 40.0
var _wire_spans: Array[MeshInstance3D] = []


func _ready() -> void:
	add_to_group("level")
	reinforcement_delay = float(Debug.args.get("reinforce-delay", reinforcement_delay))
	Visibility.reset()
	Guard.reset_shared()
	# Mission start: blue hour. A restart after death begins the evening again.
	Game.set_clock(String(Debug.args.get("time", "17:40")))
	Visibility.ambient = 0.2          # blue hour under overcast
	Visibility.noise_floor_db = 34.0  # drizzle and wind
	var env_refs := DuskEnvironment.apply(self)
	var day_night := DayNight.new()
	day_night.name = "DayNight"
	day_night.env = env_refs["environment"]
	day_night.sun = env_refs["sun"]
	add_child(day_night)
	_build_ground()
	_build_street()
	_build_houses()
	_build_square()
	_build_checkpoint()
	_build_poles_and_wires()
	_build_window_lights()
	_build_reflection_probes()
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
	_setup_test_objective()
	_build_back_lanes()
	_place_options()
	_place_wireless()
	_build_atmosphere()
	print("LEVEL READY")


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
	sentry.checkpoint = true
	sentry.model_variant = "feldgendarm"
	sentry.phone_position = Vector3(3.7, 0.05, 45.2)
	sentry.challenge_zone = AABB(Vector3(-6.0, -1.0, 33.0), Vector3(12.0, 6.0, 8.0))
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
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/ground.gdshader")
	for set_name: String in ["mud", "grass"]:
		var files: String = "grass_winter" if set_name == "grass" else set_name
		mat.set_shader_parameter(set_name + "_albedo", _ground_tex(files, "albedo", Color(0.2, 0.17, 0.13) if set_name == "mud" else Color(0.22, 0.23, 0.14)))
		mat.set_shader_parameter(set_name + "_normal", _ground_tex(files, "normal", Color(0.5, 0.5, 1.0)))
		mat.set_shader_parameter(set_name + "_orm", _ground_tex(files, "orm", Color(1.0, 0.85, 0.0)))
	mat.set_shader_parameter("mask_scale", GroundMask.SCALE)
	var body := Terrain.build(self, mat)
	body.set_meta("surface_fn", GroundMask.surface_at)
	_build_water()
	_scatter_nature()


## The sea along the northern shore, and the river in its valley to the east.
func _build_water() -> void:
	var shader: Shader = load("res://shaders/water.gdshader")
	var sea := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(900.0, 500.0)
	sea.mesh = plane
	var sea_mat := ShaderMaterial.new()
	sea_mat.shader = shader
	sea.material_override = sea_mat
	sea.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(sea)
	sea.position = Vector3(0.0, Terrain.SEA_LEVEL, 330.0)

	var river_mat := ShaderMaterial.new()
	river_mat.shader = shader
	river_mat.set_shader_parameter("flow", Vector2(0.0, 0.06))
	river_mat.set_shader_parameter("wave_scale", 0.18)
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var z := -200.0
	while z < 120.0:
		var z1 := z + 4.0
		var w0 := lerpf(7.0, 22.0, smoothstep(-100.0, 100.0, z)) * 0.9
		var w1 := lerpf(7.0, 22.0, smoothstep(-100.0, 100.0, z1)) * 0.9
		var c0 := Terrain.river_center_x(z)
		var c1 := Terrain.river_center_x(z1)
		var y := -1.3
		var a := Vector3(c0 - w0, y, z)
		var b := Vector3(c0 + w0, y, z)
		var c := Vector3(c1 - w1, y, z1)
		var d := Vector3(c1 + w1, y, z1)
		for v in [a, c, b, b, c, d]:
			st.set_normal(Vector3.UP)
			st.add_vertex(v)
		z = z1
	var river := MeshInstance3D.new()
	river.mesh = st.commit()
	river.material_override = river_mat
	river.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(river)


## Thousands of grass tufts, rushes and dead ferns as one MultiMesh per kind: cheap to draw, no collision.
func _scatter_ground_cover(list: Array, total: int, rng: RandomNumberGenerator) -> void:
	if list.is_empty():
		return
	var per := total / list.size()
	for scene: PackedScene in list:
		var src := scene.instantiate()
		var mi := src.find_children("*", "MeshInstance3D", true, false)
		if mi.is_empty():
			src.free()
			continue
		var mesh: Mesh = (mi[0] as MeshInstance3D).mesh
		src.free()
		var mm := MultiMesh.new()
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.mesh = mesh
		var xforms: Array[Transform3D] = []
		var tries := 0
		while xforms.size() < per and tries < per * 5:
			tries += 1
			var x := rng.randf_range(-185.0, 185.0)
			var z := rng.randf_range(-185.0, 100.0)
			var vm := Terrain.village_mask(x, z)
			if vm > 0.5 or absf(x - Terrain.river_center_x(z)) < 14.0:
				continue
			# Tufts cluster where the ground is grassy rather than bare mud.
			if GroundMask.grassiness(Vector3(x, 0, z)) < 0.35 and rng.randf() < 0.7:
				continue
			var h := Terrain.height(x, z)
			if h < Terrain.SEA_LEVEL + 0.3:
				continue
			var s := rng.randf_range(0.7, 1.4)
			xforms.append(Transform3D(Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s, s)), Vector3(x, h - 0.03, z)))
		mm.instance_count = xforms.size()
		for k in xforms.size():
			mm.set_instance_transform(k, xforms[k])
		var mmi := MultiMeshInstance3D.new()
		mmi.multimesh = mm
		mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mmi.visibility_range_end = 70.0
		add_child(mmi)


## Trees, gorse, hedgerow banks, rocks and grass outside the village, placed by a seeded scatter that
## avoids the village, the street, the river and the sea. Only uses kit pieces that exist.
func _scatter_nature() -> void:
	const NATURE := "res://assets/models/nature/"
	var kinds := {
		"tree": ["tree_oak_a", "tree_oak_b", "tree_beech_a", "tree_beech_b", "tree_chestnut_a", "tree_ash_a", "tree_pine_a", "tree_pine_b"],
		"bush": ["gorse_a", "gorse_b", "gorse_c", "bramble_a", "bramble_b", "bracken_a", "bracken_b"],
		"rock": ["rock_small", "rock_medium", "rock_large", "rock_outcrop_moss"],
		"grass": ["grass_tuft_a", "grass_tuft_b", "grass_tuft_c", "rush_clump_a", "rush_clump_b", "fern_dead_a", "fern_dead_b"],
	}
	var scenes := {}
	for kind: String in kinds:
		scenes[kind] = []
		for asset: String in kinds[kind]:
			var path := NATURE + asset + ".glb"
			if ResourceLoader.exists(path):
				scenes[kind].append(load(path))
	var rng := RandomNumberGenerator.new()
	rng.seed = 1944
	var counts := {"tree": 260, "bush": 420, "rock": 90, "grass": 6000}
	_scatter_ground_cover(scenes["grass"], counts["grass"], rng)
	for kind: String in counts:
		var list: Array = scenes[kind]
		if list.is_empty() or kind == "grass":
			continue
		var placed := 0
		var tries := 0
		while placed < counts[kind] and tries < counts[kind] * 6:
			tries += 1
			var x := rng.randf_range(-185.0, 185.0)
			var z := rng.randf_range(-185.0, 105.0)
			if Terrain.village_mask(x, z) > 0.02 or absf(x - Terrain.river_center_x(z)) < 26.0:
				continue
			var h := Terrain.height(x, z)
			if h < Terrain.SEA_LEVEL + 0.4:
				continue
			# Trees cluster into copses and along field edges rather than spreading evenly.
			if kind == "tree" and GroundMask.fbm(Vector2(x, z) * 0.02) < 0.5:
				continue
			var node: Node3D = (list[rng.randi() % list.size()] as PackedScene).instantiate()
			add_child(node)
			node.position = Vector3(x, h - 0.05, z)
			node.rotation.y = rng.randf() * TAU
			var s := rng.randf_range(0.8, 1.25)
			node.scale = Vector3(s, s, s)
			_tag_surface(node, "wood" if kind == "tree" else ("stone" if kind == "rock" else "grass"))
			placed += 1
	# Hedgerow banks lining the lane south of the village.
	var bank := NATURE + "talus_bank_10m.glb"
	if ResourceLoader.exists(bank):
		var scene: PackedScene = load(bank)
		for side: float in [-1.0, 1.0]:
			for k in 9:
				var bz := -82.0 - k * 10.0
				var bx := side * 6.0
				var b := scene.instantiate() as Node3D
				add_child(b)
				b.position = Vector3(bx, Terrain.height(bx, bz), bz)
				_tag_surface(b, "mud")


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
		# Enterable variants (with coloured doors) are used where they've been built.
		if asset.ends_with("_int") and not ResourceLoader.exists(ENV + asset + ".glb"):
			asset = asset.trim_suffix("_int")
		var house := spawn(asset, Vector3.ZERO, facing, "stone", _fallback_house_size(asset))
		var fp := footprint(house)
		# Push the house back so its front sits on the street edge, and start it at the cursor.
		var front_x := fp.end.x if side < 0 else fp.position.x
		var x := -STREET_HALF - FRONT_SETBACK - front_x if side < 0 else STREET_HALF + FRONT_SETBACK - front_x
		house.position = Vector3(x, 0.0, z - fp.position.z)
		_houses.append(house)
		if asset.ends_with("_int"):
			_setup_interior(house)
		z += fp.size.z + randf_range(0.0, 1.2)


## Doors that swing (F), warm lamps inside, and an interior reflection probe.
func _setup_interior(house: Node3D) -> void:
	var door := house.find_child("Door", true, false) as Node3D
	if door:
		var it := Interactable.new()
		it.prompt = "open the door"
		it.radius = 1.3
		it.noise_db = 44.0
		add_child(it)
		it.global_position = door.global_position + house.global_basis.z * 0.5 + Vector3.UP * 1.0
		var closed_y := door.rotation.y
		var state := {"open": false}
		it.on_use = func(_p: Node3D) -> void:
			state["open"] = not state["open"]
			it.prompt = "close the door" if state["open"] else "open the door"
			var tw := create_tween()
			tw.tween_property(door, "rotation:y", closed_y + (deg_to_rad(90.0) if state["open"] else 0.0), 0.9) 				.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
			SoundLib.play_3d("impacts/impact_wood", door.global_position + Vector3.UP, -14.0, 25.0, 0.2, 2.0)
	# Lamp bodies mustn't shadow their own flames.
	for lamp in house.find_children("Lamp_*", "MeshInstance3D", true, false):
		(lamp as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	for n in house.find_children("LightSpot_*", "Node3D", true, false):
		var l := OmniLight3D.new()
		l.light_color = Color(1.0, 0.62, 0.32)
		l.light_energy = 1.2
		l.omni_range = 6.0
		l.shadow_enabled = true
		(n as Node3D).add_child(l)
		Visibility.register_light(l)
	var fp := footprint(house)
	var probe := ReflectionProbe.new()
	probe.interior = true
	probe.box_projection = true
	probe.size = fp.size * 0.95
	probe.update_mode = ReflectionProbe.UPDATE_ONCE
	add_child(probe)
	probe.global_position = house.global_position + fp.get_center()


func _fallback_house_size(asset: String) -> Vector3:
	match asset.trim_suffix("_int"):
		"house_longere":
			return Vector3(14.0, 5.5, 6.5)
		"house_cafe":
			return Vector3(7.0, 8.0, 8.0)
	return Vector3(8.0, 9.0, 7.0)


func _build_houses() -> void:
	seed(1943)
	_row(-1, -62.0, 52.0, ["house_bourg_int", "house_cafe_int", "house_bourg", "house_longere_int", "house_bourg"],
		[Vector2(-30.0, -26.0), Vector2(6.0, 9.0)])
	_row(1, -62.0, 40.0, ["house_longere", "house_bourg_int", "house_bourg", "house_cafe", "house_bourg_int"],
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
	_build_junction_box(_poles[1])
	var sentry_drop := Vector3(4.6, 2.35, 46.0)
	var last := _poles[_poles.size() - 1]
	var m := find_marker(last, "WireAttach_0")
	var from := m.global_position if m else last.global_position + Vector3.UP * 7.2
	add_child(WireSpan.build(from, sentry_drop, 0.5))


## A PTT junction box at the foot of a pole, where the line can be cut without climbing.
func _build_junction_box(pole: Node3D) -> void:
	var box := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.28, 0.38, 0.14)
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.17, 0.2, 0.17)
	m.roughness = 0.7
	m.metallic = 0.3
	bm.material = m
	box.mesh = bm
	add_child(box)
	box.global_position = pole.global_position + Vector3(-0.2, 1.25, 0.0)
	var cable := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.008
	cm.bottom_radius = 0.008
	cm.height = 5.8
	var cable_mat := StandardMaterial3D.new()
	cable_mat.albedo_color = Color(0.05, 0.05, 0.05)
	cable_mat.roughness = 0.5
	cm.material = cable_mat
	cable.mesh = cm
	add_child(cable)
	cable.global_position = pole.global_position + Vector3(-0.14, 4.3, 0.0)
	var it := Interactable.new()
	it.prompt = "cut the telephone line"
	it.busy_time = 2.5
	it.noise_db = 46.0
	it.on_use = func(_p: Node3D) -> void:
		Guard.phone_line_ok = false
		it.enabled = false
		SoundLib.play_3d("weapons/p38_dryfire", it.global_position, -4.0, 20.0, 0.2, 1.5)
		for w in _wire_spans.slice(0, 8):
			if is_instance_valid(w):
				w.rotation_degrees.z = randf_range(-4.0, 4.0)
				w.position.y -= randf_range(0.6, 1.4)   # the cut spans sag and hang
		player.note("Snip. The line goes slack.", 3.0)
	add_child(it)
	it.global_position = box.global_position


const NOTEBOOK := """Plouzennec. Février.

The harbour is past the north checkpoint,
inside the zone interdite. My carte d'identité
is good for town. I have no zone pass.

TO DO
  Get past the checkpoint and reach the
  shore beyond it. Don't get taken.

WHAT I KNOW
  - Sentry at the box, with a field telephone.
    A second man walks the street.
  - The PTT line runs up the east side on poles.
    Junction box at the foot of one of them.
    Cut it and he can't call anyone.
  - Fields and the river to the east and west.
    Dark out there, but the ground is open.
  - After 22:00 it's curfew. Anyone seen is shot.
  - Never stand against the sky.
  - Yann's café has a wireless. London speaks
    at 19:30 and 21:15. If they read "le chat
    de la voisine", the boat comes tonight.

Pistol: P.38, 8 rounds + 2 spare magazines.
Every shot carries a long way."""


func _setup_test_objective() -> void:
	player.overlay.notebook_text = NOTEBOOK
	var shore := Area3D.new()
	shore.name = "ShoreObjective"
	shore.collision_mask = Game.LAYER_PLAYER
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(400.0, 20.0, 30.0)
	cs.shape = box
	shore.add_child(cs)
	add_child(shore)
	shore.position = Vector3(0.0, 0.0, 104.0)
	shore.body_entered.connect(func(b: Node) -> void:
		if b == player and not player.dead:
			player.note("The sea. You made it past them, for now. (Test objective complete.)", 8.0)
			player.overlay.notebook_text = NOTEBOOK.replace("TO DO", "DONE: reached the shore at " + Game.clock_text() + ".

TO DO (next build)"))
	get_tree().create_timer(2.5, false).timeout.connect(func() -> void:
		player.note("Plouzennec, 17:40. Press J for your notebook.", 6.0))


func _notable(pos: Vector3, thought: String, lead := "", radius := 12.0) -> Notable:
	var n := Notable.new()
	n.thought = thought
	n.lead = lead
	n.radius = radius
	add_child(n)
	n.global_position = pos
	return n


func _cafe() -> Node3D:
	for h in _houses:
		if String(h.name).to_lower().contains("cafe"):
			return h
	return null


## Low garden walls behind both rows of houses, broken by gaps, with a lane beyond. You can climb them (Space).
func _build_back_lanes() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 77
	for side: float in [-1.0, 1.0]:
		var z := -58.0
		while z < 46.0:
			if rng.randf() > 0.22:
				spawn("stone_wall_low_4m", Vector3(side * 19.5, 0.0, z + 2.0), -90.0, "stone", Vector3(4.0, 1.1, 0.6))
			z += 4.0
		# Sheds, woodpiles and clutter in the gardens.
		for k in 7:
			var gz := rng.randf_range(-55.0, 40.0)
			var gx := side * rng.randf_range(13.0, 18.0)
			if rng.randf() < 0.5:
				spawn("crate_wood", Vector3(gx, 0, gz), rng.randf() * 360.0, "wood", Vector3(0.8, 0.6, 0.6))
			else:
				spawn("barrel_wood", Vector3(gx, 0, gz), rng.randf() * 360.0, "wood", Vector3(0.6, 0.9, 0.6))
	_notable(Vector3(-8.0, 1.0, -28.0), "An alley between the houses, toward the back gardens.",
		"Back lanes run behind both rows of houses: low walls, easy to climb (Space).", 14.0)


## The concrete ways past the checkpoint in this test level, each discoverable in the world.
func _place_options() -> void:
	# 1. The harbour master's satchel behind the café: a stamped zone pass.
	var cafe := _cafe()
	if cafe:
		var fp := footprint(cafe)
		var back_x := cafe.global_position.x + fp.position.x - 1.4
		var bz := cafe.global_position.z + fp.get_center().z
		spawn("crate_wood", Vector3(back_x, 0, bz), 15.0, "wood", Vector3(0.8, 0.6, 0.6))
		var satchel := MeshInstance3D.new()
		var sm := BoxMesh.new()
		sm.size = Vector3(0.38, 0.26, 0.12)
		var leather := StandardMaterial3D.new()
		leather.albedo_color = Color(0.22, 0.12, 0.06)
		leather.roughness = 0.55
		sm.material = leather
		satchel.mesh = sm
		add_child(satchel)
		satchel.global_position = Vector3(back_x, 0.75, bz)
		satchel.rotation_degrees.y = 30.0
		var it := Interactable.new()
		it.prompt = "search the satchel"
		it.busy_time = 2.0
		add_child(it)
		it.global_position = satchel.global_position
		it.on_use = func(_p: Node3D) -> void:
			player.papers["zone_pass"] = true
			it.enabled = false
			satchel.queue_free()
			player.note("Guégan's satchel: invoices, a bottle, and a stamped zone pass made out to his clerk. Close enough, in the dark.", 6.0)
			player.overlay.add_lead("I have a zone pass now (the clerk's). The sentry should let me through.")
		_notable(satchel.global_position, "A leather satchel left on a crate behind the café.",
			"The harbour master drinks at the café. His satchel is behind it.", 8.0)
		# Empty bottles by the café's back door.
		for k in 3:
			var bpos := Vector3(back_x + 0.9, 0.12, bz + 1.2 + k * 0.35)
			var b := MeshInstance3D.new()
			var bm := CylinderMesh.new()
			bm.top_radius = 0.012
			bm.bottom_radius = 0.035
			bm.height = 0.28
			var g := StandardMaterial3D.new()
			g.albedo_color = Color(0.08, 0.16, 0.08)
			g.roughness = 0.08
			bm.material = g
			b.mesh = bm
			add_child(b)
			b.global_position = bpos
			var bi := Interactable.new()
			bi.prompt = "take an empty bottle"
			bi.radius = 1.0
			add_child(bi)
			bi.global_position = bpos
			bi.on_use = func(_p: Node3D) -> void:
				player.items["bottle"] = int(player.items.get("bottle", 0)) + 1
				bi.enabled = false
				b.queue_free()
				player.note("An empty bottle. Thrown (G), it'll make a racket where it lands.", 3.5)
		_notable(Vector3(back_x + 0.9, 0.3, bz + 1.5), "Empty bottles by the back door.",
			"Bottles behind the café: throw one (G) to draw a guard away. A stone from the road works too, quieter.", 8.0)

	# 2. A Kriegsmarine greatcoat drying on a line in a back garden on the east side.
	var line_a := Vector3(14.0, 0.0, -14.0)
	var line_b := Vector3(14.0, 0.0, -8.0)
	for p in [line_a, line_b]:
		var post := MeshInstance3D.new()
		var pm := CylinderMesh.new()
		pm.top_radius = 0.04
		pm.bottom_radius = 0.05
		pm.height = 2.1
		var wood := StandardMaterial3D.new()
		wood.albedo_color = Color(0.25, 0.2, 0.15)
		pm.material = wood
		post.mesh = pm
		add_child(post)
		post.global_position = p + Vector3.UP * 1.05
	add_child(WireSpan.build(line_a + Vector3.UP * 2.0, line_b + Vector3.UP * 2.0, 0.12, 0.003))
	var cloth := StandardMaterial3D.new()
	cloth.albedo_color = Color(0.72, 0.7, 0.64)
	cloth.roughness = 0.9
	cloth.cull_mode = BaseMaterial3D.CULL_DISABLED
	for k in 3:
		var sheet := MeshInstance3D.new()
		var q := QuadMesh.new()
		q.size = Vector2(1.1, 1.2)
		q.material = cloth
		sheet.mesh = q
		add_child(sheet)
		sheet.global_position = line_a.lerp(line_b, 0.15 + k * 0.22) + Vector3.UP * 1.35
		sheet.rotation_degrees.y = 90.0
	var coat := MeshInstance3D.new()
	var cm := BoxMesh.new()
	cm.size = Vector3(0.06, 1.15, 0.62)
	var navy := StandardMaterial3D.new()
	navy.albedo_color = Color(0.05, 0.06, 0.11)
	navy.roughness = 0.95
	cm.material = navy
	coat.mesh = cm
	add_child(coat)
	coat.global_position = line_a.lerp(line_b, 0.82) + Vector3.UP * 1.38
	var ci := Interactable.new()
	ci.prompt = "take the navy greatcoat"
	ci.busy_time = 3.0
	ci.noise_db = 40.0
	add_child(ci)
	ci.global_position = coat.global_position + Vector3.DOWN * 0.6
	ci.on_use = func(_p: Node3D) -> void:
		player.disguise = "kriegsmarine"
		ci.enabled = false
		coat.queue_free()
		player.note("A Kriegsmarine greatcoat, still damp. At a distance you're one of them. Up close, in the light, your shoes and face will give you away.", 7.0)
		player.overlay.add_lead("Wearing the navy greatcoat. Keep out of the light and don't let anyone look closely.")
	_notable(coat.global_position, "Washing on a line. Among the sheets, a navy greatcoat.",
		"A navy greatcoat on a washing line behind the east houses. A disguise, from a distance.", 14.0)

	# 3. A ford across the river: stepping stones, and nobody watching.
	var fz := 24.0
	var fx := Terrain.river_center_x(fz)
	var stone_mat := StandardMaterial3D.new()
	stone_mat.albedo_color = Color(0.32, 0.31, 0.29)
	stone_mat.roughness = 0.7
	for k in 9:
		var sx := fx - 10.0 + k * 2.5
		var body := StaticBody3D.new()
		body.set_meta("surface", "stone")
		var mi := MeshInstance3D.new()
		var sm2 := CylinderMesh.new()
		sm2.top_radius = 0.45
		sm2.bottom_radius = 0.6
		sm2.height = 1.4
		sm2.material = stone_mat
		mi.mesh = sm2
		body.add_child(mi)
		var cs := CollisionShape3D.new()
		var cyl := CylinderShape3D.new()
		cyl.radius = 0.55
		cyl.height = 1.4
		cs.shape = cyl
		body.add_child(cs)
		add_child(body)
		var ground := Terrain.height(sx, fz)
		body.global_position = Vector3(sx, maxf(ground, -1.3) - 0.45 + 0.25, fz + sin(k * 1.7) * 0.4)
	_notable(Vector3(fx, -0.8, fz), "Stepping stones across the stream. Nobody watches this side.",
		"A ford across the river east of the village: a way round the checkpoint to the shore.", 30.0)

	# 4. Things to read and see at the checkpoint and on the PTT line.
	_notable(Vector3(-4.6, 1.4, 41.0), "BEKANNTMACHUNG / AVIS. Curfew 22h to 5h. The coastal zone: entry only with a valid Ausweis.",
		"Curfew 22:00-05:00. The coastal zone needs an Ausweis (zone pass).", 9.0)
	_notable(Vector3(4.6, 1.3, 46.0), "A sentry box with a field telephone. If he calls this in, more will come.",
		"The checkpoint sentry has a telephone. Cut the line first?", 22.0)
	for it2 in get_tree().get_nodes_in_group("interactables"):
		var ib := it2 as Interactable
		if ib and ib.prompt == "cut the telephone line":
			_notable(ib.global_position, "A PTT junction box. The checkpoint's telephone line runs through it.",
				"PTT junction box on a pole, east side of the street: cut it (F) and the sentry can't call for help.", 10.0)


## A wireless set inside the café, on whatever counter or table it finds at the right height.
func _place_wireless() -> void:
	var cafe := _cafe()
	if cafe == null:
		return
	var fp := footprint(cafe)
	var origin := cafe.global_position + fp.get_center()
	var space := get_world_3d().direct_space_state
	var best := Vector3.INF
	for i in 9:
		for j in 9:
			var p := origin + Vector3((i - 4) / 4.0 * fp.size.x * 0.32, 0.0, (j - 4) / 4.0 * fp.size.z * 0.32)
			var q := PhysicsRayQueryParameters3D.create(Vector3(p.x, 2.2, p.z), Vector3(p.x, 0.0, p.z), Game.LAYER_WORLD)
			var hit := space.intersect_ray(q)
			if hit.is_empty() or (hit.normal as Vector3).y < 0.9:
				continue
			var y: float = (hit.position as Vector3).y
			if y > 0.65 and y < 1.25:
				best = hit.position
				break
		if best != Vector3.INF:
			break
	if best == Vector3.INF:
		# No counter at the right height: stand it on a table from the props kit.
		best = Vector3(origin.x, 0.13, origin.z)
		var table_path := "res://assets/models/props/table_bench.glb"
		if ResourceLoader.exists(table_path):
			var table := (load(table_path) as PackedScene).instantiate() as Node3D
			add_child(table)
			table.global_position = best
			table.rotation.y = cafe.rotation.y
			_tag_surface(table, "wood")
			var tfp := footprint(table)
			best.y = table.global_position.y + tfp.end.y
	var w := Wireless.new()
	w.name = "Wireless"
	w.player = player
	add_child(w)
	w.global_position = best
	w.rotation.y = cafe.rotation.y
	w.message_heard.connect(func(_t: String) -> void:
		player.note("That's it. The boat comes tonight: 02:30, the Anse de Kerlo.", 6.0)
		player.overlay.add_lead("The BBC read our message. The boat comes at 02:30 to the Anse de Kerlo.")
		, CONNECT_ONE_SHOT)
	_notable(best + Vector3.UP * 0.2, "A wireless set, tuned to London by the look of the dial.",
		"Yann's wireless, inside the café. Turn it on at 19:30 or 21:15 for the BBC.", 6.0)


## Chimney smoke, mist lying in the river valley, and a few far-off farm lights.
func _build_atmosphere() -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = 404
	var smoke_mat := ParticleProcessMaterial.new()
	smoke_mat.direction = Vector3.UP
	smoke_mat.spread = 8.0
	smoke_mat.initial_velocity_min = 0.4
	smoke_mat.initial_velocity_max = 0.8
	smoke_mat.gravity = Vector3(0.35, 0.15, 0.1)
	smoke_mat.scale_min = 1.0
	smoke_mat.scale_max = 2.0
	var grow := Curve.new()
	grow.add_point(Vector2(0.0, 0.4))
	grow.add_point(Vector2(1.0, 3.0))
	var ct := CurveTexture.new()
	ct.curve = grow
	smoke_mat.scale_curve = ct
	var fade := Gradient.new()
	fade.set_color(0, Color(0.4, 0.4, 0.42, 0.0))
	fade.add_point(0.15, Color(0.42, 0.42, 0.44, 0.22))
	fade.set_color(fade.get_point_count() - 1, Color(0.45, 0.45, 0.47, 0.0))
	var gt := GradientTexture1D.new()
	gt.gradient = fade
	smoke_mat.color_ramp = gt
	var quad := QuadMesh.new()
	quad.size = Vector2(0.9, 0.9)
	var qm := StandardMaterial3D.new()
	qm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	qm.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	qm.vertex_color_use_as_albedo = true
	qm.albedo_texture = ProcTex.soft_dot()
	qm.shading_mode = BaseMaterial3D.SHADING_MODE_PER_VERTEX
	quad.material = qm
	for h in _houses:
		if rng.randf() < 0.4:
			continue
		var fp := footprint(h)
		var top := h.global_position + fp.get_center() + Vector3.UP * (fp.size.y * 0.5)
		var along := Vector3(0, 0, 1) if fp.size.z > fp.size.x else Vector3(1, 0, 0)
		var half := (fp.size.z if along.z > 0.5 else fp.size.x) * 0.5 - 0.6
		var p := GPUParticles3D.new()
		p.amount = 24
		p.lifetime = 9.0
		p.local_coords = false
		p.process_material = smoke_mat
		p.draw_pass_1 = quad
		p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		p.visibility_aabb = AABB(Vector3(-6, -1, -6), Vector3(16, 14, 12))
		add_child(p)
		p.global_position = top + along * half * (1.0 if rng.randf() < 0.5 else -1.0) - Vector3.UP * 0.6

	# Mist pooled along the river.
	var mist := FogMaterial.new()
	mist.density = 0.12
	mist.albedo = Color(0.7, 0.72, 0.76)
	mist.height_falloff = 0.6
	var z := -160.0
	while z < 100.0:
		var fv := FogVolume.new()
		fv.shape = RenderingServer.FOG_VOLUME_SHAPE_ELLIPSOID
		fv.size = Vector3(46.0, 5.0, 38.0)
		fv.material = mist
		add_child(fv)
		fv.global_position = Vector3(Terrain.river_center_x(z), -0.6, z)
		z += 26.0

	# Far-off farms with a lamp still burning behind a shutter.
	for k in 7:
		var a := rng.randf() * TAU
		var r := rng.randf_range(130.0, 185.0)
		var fx2 := cos(a) * r
		var fz2 := clampf(sin(a) * r, -185.0, 85.0)
		var y := Terrain.height(fx2, fz2) + 1.6
		var l := OmniLight3D.new()
		l.light_color = Color(1.0, 0.6, 0.3)
		l.light_energy = 0.8
		l.omni_range = 5.0
		add_child(l)
		l.global_position = Vector3(fx2, y, fz2)
		var w := MeshInstance3D.new()
		var wq := QuadMesh.new()
		wq.size = Vector2(0.5, 0.4)
		var wm := StandardMaterial3D.new()
		wm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		wm.albedo_color = Color(1.0, 0.65, 0.3)
		wm.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
		wq.material = wm
		w.mesh = wq
		add_child(w)
		w.global_position = l.global_position


func is_phone_line_ok() -> bool:
	return Guard.phone_line_ok


func call_reinforcements(where: Vector3) -> void:
	get_tree().create_timer(reinforcement_delay, false).timeout.connect(func() -> void:
		for i in 3:
			var g := Guard.new()
			g.name = "Reinforcement%d" % i
			g.patrol_points = PackedVector3Array([Vector3(1.0, 0.05, 30.0), Vector3(-1.0, 0.05, -10.0)])
			add_child(g)
			g.global_position = Vector3(-1.5 + i * 1.5, 0.05, -66.0 - i * 1.2)
			g.rotation.y = PI
			g.dispatch_to(where))


func _wire_between(a: Node3D, b: Node3D) -> void:
	for w in 4:
		var ma := find_marker(a, "WireAttach_%d" % w)
		var mb := find_marker(b, "WireAttach_%d" % w)
		var pa := ma.global_position if ma else a.global_position + Vector3(0, 7.2, (w - 1.5) * 0.3)
		var pb := mb.global_position if mb else b.global_position + Vector3(0, 7.2, (w - 1.5) * 0.3)
		if ma == null and w > 1:
			break
		var span := WireSpan.build(pa, pb, randf_range(0.3, 0.45))
		add_child(span)
		_wire_spans.append(span)


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


## Without probes every glossy surface reflects the open dusk sky, even deep in a street walled in by houses.
## That made blued steel look chrome and wet cobbles glare. Box-projected probes capture the real street.
func _build_reflection_probes() -> void:
	# One broad probe over the open country, so glossy things out there reflect dark fields, not only sky.
	var wide := ReflectionProbe.new()
	wide.size = Vector3(420.0, 60.0, 420.0)
	wide.update_mode = ReflectionProbe.UPDATE_ONCE
	wide.ambient_mode = ReflectionProbe.AMBIENT_DISABLED
	wide.max_distance = 400.0
	add_child(wide)
	wide.position = Vector3(0.0, 4.0, -40.0)
	for k in 7:
		var probe := ReflectionProbe.new()
		probe.size = Vector3(18.0, 12.0, 22.0)
		probe.box_projection = true
		probe.enable_shadows = true
		probe.update_mode = ReflectionProbe.UPDATE_ONCE
		probe.ambient_mode = ReflectionProbe.AMBIENT_DISABLED
		probe.blend_distance = 3.0
		add_child(probe)
		probe.position = Vector3(0.0, 4.0, -60.0 + k * 20.0)


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
