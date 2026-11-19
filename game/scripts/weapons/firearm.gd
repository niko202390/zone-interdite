class_name Firearm
extends Node3D
## A first-person firearm. Shooting is hitscan with CS-style first-shot accuracy, bloom and recoil,
## on top of a real pistol's mechanics: chamber, magazine, slide lock, double/single-action hammer
## and a decocking safety. There's no ammo HUD; press T to check the magazine by feel.

signal fired(origin: Vector3, direction: Vector3)

## The FOV the weapon data was tuned at; the aimed FOV scales with the player's setting.
const REFERENCE_FOV := 62.0
const VIEWMODEL_LAYER := 1 << 1
const PART_NAMES := ["Frame", "Slide", "Barrel", "Hammer", "Trigger", "Magazine", "Decocker",
	"Hand_R", "Hand_L", "Muzzle", "EjectPort", "SightRear", "SightFront"]

@export var data: WeaponData

var player: Player
var camera: Camera3D

# Mechanical state.
var mag_inserted := true
var mag_rounds := 0
var chambered := true
var hammer_cocked := false      # false = hammer down, so the next pull is double action
var safety_on := false
var slide_locked := false
var spare_mags: Array[int] = []

# Presentation state.
var holstered := false
var ads := 0.0

var _model: Node3D
var _parts := {}
var _rest := {}
var _hip_xform := Transform3D.IDENTITY
var _ads_xform := Transform3D.IDENTITY
var _slide := 0.0
var _hammer := 0.0
var _trigger := 0.0
var _safety_amt := 0.0
var _mag_out := 0.0
var _hand_l := 0.0
var _kick := 0.0
var _kick_rot := Vector3.ZERO
var _bloom := 0.0
var _last_shot := -10.0
var _pending_da := -1.0
var _lower := 0.0
var _holster_amt := 0.0
var _retract := 0.0
var _sway := Vector3.ZERO
var _busy := ""
var _busy_t := 0.0
var _busy_len := 0.0
var _busy_done := {}
var _reload_from := -1
var _reload_empty := false
var _flash_light: OmniLight3D
var _flash_mesh: MeshInstance3D
var _flash_t := 0.0
var _casings: Array = []


func _ready() -> void:
	player = _find_player()
	# Children are ready before parents, so walk up for the camera rather than asking the player.
	var n := get_parent()
	while n and not (n is Camera3D):
		n = n.get_parent()
	camera = n as Camera3D if n else get_viewport().get_camera_3d()
	if data == null:
		data = WeaponData.new()
	mag_rounds = data.magazine_capacity
	spare_mags = [data.magazine_capacity, data.magazine_capacity]
	chambered = true
	hammer_cocked = false   # carried hammer-down on a loaded chamber, the way the P38 was designed to be
	_build_model()
	_build_flash()


func _find_player() -> Player:
	var n := get_parent()
	while n:
		if n is Player:
			return n
		n = n.get_parent()
	return null


# --- model -------------------------------------------------------------------------------------

func _build_model() -> void:
	if data.model_path != "" and ResourceLoader.exists(data.model_path):
		_model = (load(data.model_path) as PackedScene).instantiate()
	else:
		_model = _placeholder_model()
	add_child(_model)
	for n: String in PART_NAMES:
		var node := _model.find_child(n, true, false) as Node3D
		if node:
			_parts[n] = node
			_rest[n] = node.transform
	_prepare_meshes(_model)
	_compute_poses()
	if _parts.has("Hand_L"):
		_parts["Hand_L"].visible = false


## Viewmodel materials draw squashed toward the camera (no clipping into walls) with their own FOV,
## and don't cast shadows into the world.
func _prepare_meshes(node: Node) -> void:
	if node is MeshInstance3D:
		var mi := node as MeshInstance3D
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.layers = VIEWMODEL_LAYER
		if mi.mesh:
			for i in mi.mesh.get_surface_count():
				var mat := mi.get_active_material(i)
				if mat is BaseMaterial3D:
					var m := (mat as BaseMaterial3D).duplicate() as BaseMaterial3D
					m.use_z_clip_scale = true
					m.z_clip_scale = data.z_clip_scale
					m.use_fov_override = true
					m.fov_override = data.viewmodel_fov
					mi.set_surface_override_material(i, m)
	for c in node.get_children():
		_prepare_meshes(c)


func _compute_poses() -> void:
	_hip_xform = Transform3D(Basis.from_euler(data.hip_rotation_deg * (PI / 180.0)), data.hip_position)
	# Aiming: put the rear sight on the eye line at arm's length, with the sight line pointing straight ahead.
	var r: Vector3 = _model_space(_parts.get("SightRear"), Vector3(0, 0.02, 0.08))
	var f: Vector3 = _model_space(_parts.get("SightFront"), Vector3(0, 0.02, -0.12))
	var sight_dir := (f - r).normalized()
	var basis := Basis(Quaternion(sight_dir, Vector3.FORWARD))
	_ads_xform = Transform3D(basis, Vector3(0, 0, -data.ads_eye_relief) - basis * r)


func _model_space(node: Node3D, fallback: Vector3) -> Vector3:
	if node == null:
		return fallback
	return (_model.global_transform.affine_inverse() * node.global_transform).origin


func _placeholder_model() -> Node3D:
	# Rough P38 proportions so the game is playable before the real model exists.
	var root := Node3D.new()
	root.name = "P38Placeholder"
	var steel := StandardMaterial3D.new()
	steel.albedo_color = Color(0.08, 0.08, 0.09)
	steel.metallic = 0.9
	steel.roughness = 0.4
	var grip := StandardMaterial3D.new()
	grip.albedo_color = Color(0.12, 0.07, 0.04)
	grip.roughness = 0.6
	var specs := [
		["Frame", Vector3(0.028, 0.035, 0.17), Vector3(0, -0.018, -0.03), steel],
		["Slide", Vector3(0.03, 0.026, 0.19), Vector3(0, 0.012, -0.005), steel],
		["Barrel", Vector3(0.018, 0.018, 0.13), Vector3(0, 0.004, -0.06), steel],
		["Magazine", Vector3(0.024, 0.11, 0.045), Vector3(0, -0.085, 0.045), grip],
		["Hammer", Vector3(0.01, 0.018, 0.01), Vector3(0, 0.024, 0.093), steel],
		["Trigger", Vector3(0.006, 0.02, 0.008), Vector3(0, -0.04, 0.0), steel],
	]
	for s in specs:
		var mi := MeshInstance3D.new()
		mi.name = s[0]
		var box := BoxMesh.new()
		box.size = s[1]
		box.material = s[3]
		mi.mesh = box
		mi.position = s[2]
		root.add_child(mi)
	for e in [["Muzzle", Vector3(0, 0.004, -0.125)], ["EjectPort", Vector3(0.016, 0.02, 0.02)],
			["SightRear", Vector3(0, 0.027, 0.085)], ["SightFront", Vector3(0, 0.029, -0.095)]]:
		var n := Node3D.new()
		n.name = e[0]
		n.position = e[1]
		root.add_child(n)
	return root


func _build_flash() -> void:
	var muzzle: Node3D = _parts.get("Muzzle", _model)
	_flash_light = OmniLight3D.new()
	_flash_light.light_color = Color(1.0, 0.72, 0.42)
	_flash_light.omni_range = 7.0
	_flash_light.light_energy = 0.0
	_flash_light.shadow_enabled = true
	_flash_light.visible = false
	muzzle.add_child(_flash_light)
	Visibility.register_light(_flash_light)
	_flash_light.position = Vector3(0, 0, -0.05)

	_flash_mesh = MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(0.16, 0.16)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	m.albedo_texture = ProcTex.flash_star()
	m.albedo_color = Color(1.0, 0.8, 0.55)
	m.use_z_clip_scale = true
	m.z_clip_scale = data.z_clip_scale
	m.use_fov_override = true
	m.fov_override = data.viewmodel_fov
	quad.material = m
	_flash_mesh.mesh = quad
	_flash_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_flash_mesh.layers = VIEWMODEL_LAYER
	_flash_mesh.visible = false
	muzzle.add_child(_flash_mesh)
	_flash_mesh.position = Vector3(0, 0, -0.04)


# --- input and actions -------------------------------------------------------------------------

func _process(delta: float) -> void:
	if player == null:
		return
	_handle_input()
	_update_busy(delta)
	_update_mechanics(delta)
	_update_pose(delta)
	_update_flash(delta)
	_bloom = maxf(_bloom - delta * data.bloom_recovery, 0.0)


func _handle_input() -> void:
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED or get_tree().paused or player.dead:
		return
	if Input.is_action_just_pressed("holster") and _busy == "":
		_toggle_holster()
	if holstered or _busy != "":
		return
	if Input.is_action_just_pressed("reload"):
		_start_reload()
	elif Input.is_action_just_pressed("check_ammo"):
		_begin_busy("check", 1.5)
	elif Input.is_action_just_pressed("safety") and data.has_decocker:
		_toggle_safety()
	elif data.automatic and Input.is_action_pressed("fire"):
		_pull_trigger()
	elif Input.is_action_just_pressed("fire"):
		_pull_trigger()


func _now() -> float:
	return Time.get_ticks_msec() / 1000.0


func _pull_trigger() -> void:
	var now := _now()
	if player.sprinting or _lower > 0.5 or _retract > 0.6 or _holster_amt > 0.1:
		return
	if now - _last_shot < data.min_shot_interval or _pending_da >= 0.0:
		return
	_trigger = 1.0
	if safety_on:
		# With the P38's safety on, the trigger is disconnected. It moves, but nothing happens.
		_last_shot = now
		return
	if not hammer_cocked and data.double_action:
		_pending_da = data.double_action_delay
		return
	_hammer_fall(0.0)


func _hammer_fall(extra_spread_deg: float) -> void:
	_last_shot = _now()
	hammer_cocked = false
	if not chambered:
		SoundLib.play_2d(data.sound_dry, 0.0)
		return
	_discharge(extra_spread_deg)


func _discharge(extra_spread_deg: float) -> void:
	chambered = false
	var origin := camera.global_position
	var dir := _spread_direction(_current_spread_deg() + extra_spread_deg)
	_hitscan(origin, dir)
	fired.emit(origin, dir)

	# The slide cycles: it ejects, cocks the hammer, and strips the next round if there is one.
	_slide = 1.0
	hammer_cocked = true
	if mag_inserted and mag_rounds > 0:
		mag_rounds -= 1
		chambered = true
	else:
		# The slide stop is worked by the magazine follower, so it only holds open with a magazine in.
		slide_locked = mag_inserted and data.holds_open_on_empty

	_bloom += data.bloom_per_shot
	_kick = 1.0
	_kick_rot = Vector3(deg_to_rad(randf_range(7.0, 10.0)), deg_to_rad(randf_range(-2.0, 2.0)),
		deg_to_rad(randf_range(-3.0, 3.0)))
	player.add_recoil(deg_to_rad(data.recoil_pitch_deg * randf_range(0.85, 1.15)),
		deg_to_rad(data.recoil_yaw_deg * randf_range(-1.0, 1.0)), data.recoil_recovery, data.recoil_stick)
	_flash_t = 0.055
	var muzzle_node: Node3D = _parts.get("Muzzle", _model)
	ImpactFX.spawn_muzzle_smoke(get_tree().current_scene, muzzle_node.global_position, -camera.global_basis.z, player.velocity)
	_flash_mesh.rotation.z = randf() * TAU
	_flash_mesh.scale = Vector3.ONE * randf_range(0.8, 1.25)
	_eject_casing()

	var enclosed := _is_enclosed()
	SoundLib.play_2d(data.sound_shot, 0.0, Game.BUS_WORLD, 0.02)
	SoundLib.play_2d(data.sound_tail_interior if enclosed else data.sound_tail_exterior, 0.0, Game.BUS_WORLD, 0.03)
	Hearing.expose(data.loudness_db, 0.45, enclosed)
	Game.emit_noise(origin, data.loudness_db, player)


func _current_spread_deg() -> float:
	var base := lerpf(data.hip_spread_deg, data.ads_spread_deg, ads)
	var move := clampf(player.horizontal_speed() / 4.0, 0.0, 1.0) * data.move_spread_deg
	var air := 0.0 if player.is_on_floor() else data.move_spread_deg * 1.5
	var fatigue := player.exhaustion * data.fatigue_spread_deg
	var stance := 0.82 if player.crouching else 1.0
	return (base + move + air + fatigue + _bloom) * stance


func _spread_direction(spread_deg: float) -> Vector3:
	var a := deg_to_rad(spread_deg) * sqrt(randf())
	var phi := randf() * TAU
	var local := Vector3(sin(a) * cos(phi), sin(a) * sin(phi), -cos(a))
	return (camera.global_basis * local).normalized()


func _hitscan(origin: Vector3, dir: Vector3) -> void:
	var space := player.get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(origin, origin + dir * data.range_m,
		Game.LAYER_WORLD | Game.LAYER_HITBOX, [player.get_rid()])
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		return
	var col: Object = hit.collider
	var surface := "flesh" if col.has_method("take_hit") else ImpactFX.surface_of(col, hit.position)
	ImpactFX.spawn(get_tree().current_scene, hit.position, hit.normal, dir, surface)
	if col.has_method("take_hit"):
		col.take_hit(data.damage, hit.position, dir, player)
	elif col is RigidBody3D:
		var rb := col as RigidBody3D
		rb.apply_impulse(dir * data.impulse, hit.position - rb.global_position)


## Indoors, or boxed in by walls: there's a roof overhead and walls on most sides.
func _is_enclosed() -> bool:
	var space := player.get_world_3d().direct_space_state
	var o := camera.global_position
	var hits := 0
	for d in [Vector3.UP * 8.0, Vector3.LEFT * 5.0, Vector3.RIGHT * 5.0, Vector3.FORWARD * 5.0, Vector3.BACK * 5.0]:
		var q := PhysicsRayQueryParameters3D.create(o, o + d, Game.LAYER_WORLD, [player.get_rid()])
		if not space.intersect_ray(q).is_empty():
			hits += 1
		elif d.y > 0.0:
			return false
	return hits >= 4


func _eject_casing() -> void:
	var port: Node3D = _parts.get("EjectPort", _model)
	var c := RigidBody3D.new()
	c.collision_layer = Game.LAYER_DEBRIS
	c.collision_mask = Game.LAYER_WORLD
	c.mass = 0.008
	c.continuous_cd = true
	c.contact_monitor = true
	c.max_contacts_reported = 2
	var shape := CollisionShape3D.new()
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.005
	cyl.height = 0.019
	shape.shape = cyl
	c.add_child(shape)
	var mesh := MeshInstance3D.new()
	mesh.mesh = ProcTex.casing_mesh()
	c.add_child(mesh)
	get_tree().current_scene.add_child(c)
	c.global_position = port.global_position
	c.global_basis = camera.global_basis * Basis.from_euler(Vector3(PI * 0.5, 0, 0))
	var b := camera.global_basis
	c.linear_velocity = player.velocity + b * Vector3(randf_range(1.6, 2.4), randf_range(1.3, 2.1), randf_range(-0.1, 0.6))
	c.angular_velocity = Vector3(randf_range(-30, 30), randf_range(-30, 30), randf_range(-30, 30))
	var bounces := [0]
	var key := data.sound_casing
	c.body_entered.connect(func(_body: Node) -> void:
		if bounces[0] < 3 and c.linear_velocity.length() > 0.35:
			bounces[0] += 1
			SoundLib.play_3d(key, c.global_position, -bounces[0] * 5.0, 25.0, 0.12, 1.5))
	_casings.append(c)
	while _casings.size() > 40:
		var old: Node = _casings.pop_front()
		if is_instance_valid(old):
			old.queue_free()


func _toggle_safety() -> void:
	safety_on = not safety_on
	if safety_on:
		hammer_cocked = false   # the lever decocks, dropping the hammer safely onto a blocked firing pin
	SoundLib.play_2d(data.sound_safety, 0.0)
	player.note("Safety on. Hammer down." if safety_on else "Safety off.", 1.6)


func _toggle_holster() -> void:
	holstered = not holstered
	_begin_busy("holster" if holstered else "draw", 0.55)
	SoundLib.play_2d("player/cloth_wool_move", 0.0)


func _start_reload() -> void:
	var best := -1
	_reload_from = -1
	for i in spare_mags.size():
		if spare_mags[i] > best:
			best = spare_mags[i]
			_reload_from = i
	if _reload_from == -1:
		player.note("No spare magazine.", 2.0)
		return
	if best <= 0:
		player.note("Your spare magazines are empty.", 2.0)
		return
	if mag_inserted and mag_rounds >= best and chambered:
		return
	_reload_empty = slide_locked or not chambered
	_begin_busy("reload", data.reload_empty_time if _reload_empty else data.reload_time)


func _begin_busy(kind: String, length: float) -> void:
	_busy = kind
	_busy_t = 0.0
	_busy_len = length
	_busy_done.clear()


func _busy_event(id: String, at: float) -> bool:
	if _busy_t / _busy_len >= at and not _busy_done.has(id):
		_busy_done[id] = true
		return true
	return false


func _update_busy(delta: float) -> void:
	if _busy == "":
		return
	_busy_t += delta
	var f := _busy_t / _busy_len
	match _busy:
		"reload":
			if _busy_event("out", 0.18):
				SoundLib.play_2d(data.sound_mag_out, 0.0)
			if _busy_event("swap", 0.6):
				var old := mag_rounds if mag_inserted else 0
				mag_rounds = spare_mags[_reload_from]
				spare_mags[_reload_from] = old   # the old magazine goes back in your pocket
				mag_inserted = true
				SoundLib.play_2d(data.sound_mag_in, 0.0)
			if _reload_empty and _busy_event("release", 0.78):
				slide_locked = false
				if not chambered and mag_rounds > 0:
					mag_rounds -= 1
					chambered = true
					hammer_cocked = true
				SoundLib.play_2d(data.sound_slide_forward, 0.0)
			_mag_out = _bump(f, 0.18, 0.3, 0.52, 0.62)
			_hand_l = _bump(f, 0.08, 0.3, 0.7, 0.92)
		"check":
			if _busy_event("out", 0.2):
				SoundLib.play_2d(data.sound_mag_out, -8.0)
			if _busy_event("note", 0.45):
				player.note(_ammo_estimate(), 3.2)
			if _busy_event("in", 0.68):
				SoundLib.play_2d(data.sound_mag_in, -6.0)
			_mag_out = _bump(f, 0.2, 0.32, 0.56, 0.68) * 0.45
			_hand_l = _bump(f, 0.05, 0.25, 0.75, 0.95)
	if _busy_t >= _busy_len:
		_busy = ""
		_mag_out = 0.0
		_hand_l = 0.0


## Smooth 0 → 1 → 0 envelope across the four fractions.
func _bump(f: float, a: float, b: float, c: float, d: float) -> float:
	if f <= a or f >= d:
		return 0.0
	if f < b:
		return smoothstep(a, b, f)
	if f > c:
		return 1.0 - smoothstep(c, d, f)
	return 1.0


func _ammo_estimate() -> String:
	if not mag_inserted:
		return "No magazine."
	var frac := float(mag_rounds) / float(data.magazine_capacity)
	var m: String
	if frac >= 1.0:
		m = "Magazine full."
	elif frac >= 0.7:
		m = "Magazine nearly full."
	elif frac >= 0.4:
		m = "About half a magazine."
	elif frac > 0.0:
		m = "Only a few rounds left."
	else:
		m = "Magazine empty."
	# The P38's loaded-chamber indicator pin can be felt at the back of the slide.
	var c := " A round in the chamber." if chambered else " The chamber is empty."
	var spares := 0
	for r in spare_mags:
		if r > 0:
			spares += 1
	var s := "  %d loaded spare%s in your coat." % [spares, "" if spares == 1 else "s"]
	return m + c + s


# --- presentation ------------------------------------------------------------------------------

func is_aiming() -> bool:
	return ads > 0.5


func _update_mechanics(delta: float) -> void:
	if _pending_da >= 0.0:
		_pending_da -= delta
		_hammer = 1.0 - clampf(_pending_da / data.double_action_delay, 0.0, 1.0)
		if _pending_da < 0.0:
			_pending_da = -1.0
			_hammer_fall(data.double_action_spread_deg)
	else:
		_hammer = move_toward(_hammer, 1.0 if hammer_cocked else 0.0, delta * 25.0)

	if slide_locked:
		_slide = move_toward(_slide, 1.0, delta / 0.03)
	else:
		_slide = move_toward(_slide, 0.0, delta / 0.05)
	_trigger = move_toward(_trigger, 0.0, delta * 7.0)
	_safety_amt = move_toward(_safety_amt, 1.0 if safety_on else 0.0, delta * 8.0)
	_kick = move_toward(_kick, 0.0, delta * 9.0)

	_pose_part("Slide", Vector3(0, 0, data.slide_travel * _slide), Vector3.ZERO)
	_pose_part("Barrel", Vector3(0, 0, minf(data.slide_travel * _slide, data.barrel_travel)), Vector3.ZERO)
	_pose_part("Hammer", Vector3.ZERO, Vector3(deg_to_rad(data.hammer_cock_angle_deg) * _hammer, 0, 0))
	_pose_part("Trigger", Vector3.ZERO, Vector3(deg_to_rad(data.trigger_pull_angle_deg) * _trigger, 0, 0))
	_pose_part("Decocker", Vector3(0, 0, data.slide_travel * _slide), Vector3(0, 0, deg_to_rad(data.safety_angle_deg) * _safety_amt))
	_pose_part("Magazine", Vector3(0, -data.mag_drop * _mag_out, 0.01 * _mag_out), Vector3.ZERO)
	if _parts.has("Magazine"):
		_parts["Magazine"].visible = _mag_out < 0.97
	if _parts.has("Hand_L"):
		_parts["Hand_L"].visible = _hand_l > 0.01
		_pose_part("Hand_L", Vector3(-0.06, -0.22, 0.12) * (1.0 - _hand_l), Vector3.ZERO)


func _pose_part(part: String, offset: Vector3, euler: Vector3) -> void:
	if not _parts.has(part):
		return
	var rest: Transform3D = _rest[part]
	_parts[part].transform = rest.translated(offset).rotated_local(Vector3.RIGHT, euler.x) \
		.rotated_local(Vector3.UP, euler.y).rotated_local(Vector3.BACK, euler.z)


func _update_pose(delta: float) -> void:
	var want_ads := (Input.is_action_pressed("aim") and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED) \
		or player.debug_force_ads
	want_ads = want_ads and not holstered and not player.sprinting and _busy == "" and _retract < 0.5
	ads = move_toward(ads, 1.0 if want_ads else 0.0, delta / data.ads_time)
	var a := smoothstep(0.0, 1.0, ads)
	var base_fov: float = Settings.fov
	camera.fov = lerpf(base_fov, base_fov * data.ads_fov / REFERENCE_FOV, a)

	_lower = move_toward(_lower, 1.0 if player.sprinting else 0.0, delta * 4.0)
	_holster_amt = move_toward(_holster_amt, 1.0 if holstered else 0.0, delta / 0.5)
	_model.visible = _holster_amt < 0.99

	# Pull the gun back and up when the muzzle would be inside a wall.
	var space := player.get_world_3d().direct_space_state
	var o := camera.global_position
	var fwd := -camera.global_basis.z
	var q := PhysicsRayQueryParameters3D.create(o, o + fwd * 0.8, Game.LAYER_WORLD, [player.get_rid()])
	var hit := space.intersect_ray(q)
	var retract_target := 0.0
	if not hit.is_empty():
		retract_target = clampf((0.8 - o.distance_to(hit.position)) / 0.45, 0.0, 1.0)
	_retract = move_toward(_retract, retract_target, delta * 5.0)

	# Inertia sway: the gun lags behind the view.
	var md := player.mouse_motion
	player.mouse_motion = Vector2.ZERO
	var sway_target := Vector3(clampf(md.y * 0.0009, -0.06, 0.06), clampf(md.x * 0.0009, -0.06, 0.06), 0.0) * (1.0 - 0.75 * a)
	_sway = _sway.lerp(sway_target, 1.0 - exp(-10.0 * delta))

	# Walk bob, in step with the head bob.
	var ph := player.stride_phase * PI
	var amt := clampf(player.horizontal_speed() / 1.6, 0.0, 1.0) * (1.0 - 0.8 * a)
	var bob := Vector3(sin(ph) * 0.007, -absf(sin(ph)) * 0.009, 0.0) * amt

	var busy_tilt := 0.0
	if _busy == "reload" or _busy == "check":
		busy_tilt = _bump(_busy_t / _busy_len, 0.0, 0.18, 0.82, 1.0)
	var draw := 0.0
	if _busy == "draw":
		draw = 1.0 - _busy_t / _busy_len

	var view_rot := Vector3(
		-deg_to_rad(32.0) * _lower - deg_to_rad(55.0) * maxf(_holster_amt, draw) + _sway.x,
		deg_to_rad(18.0) * _lower + _sway.y,
		0.0)
	var view_pos := bob + Vector3(-0.03 * _lower, -0.05 * _lower - 0.3 * maxf(_holster_amt, draw), 0.0)
	var local_rot := Vector3(
		_kick_rot.x * _kick + deg_to_rad(38.0) * _retract + deg_to_rad(14.0) * busy_tilt,
		_kick_rot.y * _kick,
		_kick_rot.z * _kick + deg_to_rad(28.0) * busy_tilt)
	var local_pos := Vector3(-0.03 * busy_tilt, 0.04 * busy_tilt, 0.035 * _kick + 0.09 * _retract)

	var base := _hip_xform.interpolate_with(_ads_xform, a)
	_model.transform = Transform3D(Basis.from_euler(view_rot), view_pos) * base \
		* Transform3D(Basis.from_euler(local_rot), local_pos)


func _update_flash(delta: float) -> void:
	_flash_t -= delta
	var on := _flash_t > 0.0
	_flash_light.visible = on
	_flash_light.light_energy = randf_range(5.0, 8.0) * clampf(_flash_t / 0.055, 0.0, 1.0) if on else 0.0
	_flash_mesh.visible = _flash_t > 0.03


func debug_fire() -> void:
	safety_on = false
	hammer_cocked = true
	_hammer_fall(0.0)
