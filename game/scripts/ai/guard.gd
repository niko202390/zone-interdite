class_name Guard
extends CharacterBody3D
## A German soldier on sentry or patrol duty. M2 stand-in: a simple body built from primitives with
## procedural walking, a Kar98k, and a button-on chest torch.
##
## Perception: sight depends on light level, distance, angle, posture, movement and how much of the
## player is visible. Hearing listens to Game.noise_emitted, minus distance, walls and the rain's noise floor.
## Suspicion fills up while he can see you and drains slowly when he can't.
##
## Social stealth: an unarmed civilian walking normally at dusk is only watched. He becomes hostile if
## you're armed, sneaking, sprinting, in a restricted zone, near recent gunfire, or if he's been shot at.

enum State { PATROL, CURIOUS, SUSPICIOUS, SEARCH, ALERTED, DEAD }

const STATE_NAMES := ["patrol", "curious", "suspicious", "search", "alerted", "dead"]
const FELDGRAU := Color(0.29, 0.31, 0.27)

@export var patrol_points: PackedVector3Array = PackedVector3Array()
@export var walk_speed := 1.25
@export var run_speed := 4.0
@export var view_distance := 48.0
@export var fov_deg := 120.0
@export var torch_on := true
@export var health := 100.0
@export var rifle_damage := 72.0
## A Kar98k is a bolt action: one aimed shot every couple of seconds at best.
@export var fire_interval := Vector2(2.1, 2.9)

var state := State.PATROL
var suspicion := 0.0
## Long-term wariness after incidents. It makes him quicker to notice things for the rest of the night.
var alertness := 0.0
var target_pos := Vector3.ZERO

var _player: Player
var _nav: NavigationAgent3D
var _patrol_i := 0
var _wait := 0.0
var _state_t := 0.0
var _perceive_t := 0.0
var _visibility := 0.0
var _can_see_player := false
var _last_seen_t := 100.0
var _combat_t := 100.0       # time since he last heard gunfire or was shot at
var _fire_t := 0.0
var _whistle_cd := 0.0
var _look_yaw := 0.0
var _home_yaw := 0.0
var _walk_phase := 0.0
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _death_t := 0.0

# Body parts.
var _body: Node3D
var _leg_l: Node3D
var _leg_r: Node3D
var _arm_l: Node3D
var _arm_r: Node3D
var _head: Node3D
var _rifle: Node3D
var _torch: SpotLight3D


func _ready() -> void:
	add_to_group("guards")
	collision_layer = Game.LAYER_HITBOX | Game.LAYER_CHARACTER
	collision_mask = Game.LAYER_WORLD | Game.LAYER_PLAYER
	var cs := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.32
	cap.height = 1.82
	cs.shape = cap
	cs.position.y = 0.91
	add_child(cs)
	_build_body()
	_nav = NavigationAgent3D.new()
	_nav.radius = 0.35
	_nav.height = 1.8
	_nav.path_desired_distance = 0.7
	_nav.target_desired_distance = 0.9
	add_child(_nav)
	_home_yaw = rotation.y
	_perceive_t = randf() * 0.1
	Game.noise_emitted.connect(_on_noise)
	_player = get_tree().get_first_node_in_group("player") as Player


# --- body --------------------------------------------------------------------------------------

func _mat(color: Color, rough := 0.9, metal := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = rough
	m.metallic = metal
	return m


func _part(parent: Node3D, mesh: Mesh, mat: Material, pos: Vector3, rot_deg := Vector3.ZERO, scl := Vector3.ONE) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.rotation_degrees = rot_deg
	mi.scale = scl
	parent.add_child(mi)
	return mi


func _cyl(top: float, bottom: float, h: float) -> CylinderMesh:
	var c := CylinderMesh.new()
	c.top_radius = top
	c.bottom_radius = bottom
	c.height = h
	c.radial_segments = 16
	return c


func _build_body() -> void:
	var wool := _mat(FELDGRAU, 0.95)
	var leather := _mat(Color(0.05, 0.045, 0.04), 0.45)
	var belt := _mat(Color(0.08, 0.06, 0.045), 0.6)
	var skin := _mat(Color(0.6, 0.46, 0.38), 0.7)
	var steel := _mat(Color(0.23, 0.25, 0.22), 0.65, 0.3)
	var wood := _mat(Color(0.3, 0.18, 0.1), 0.6)
	var gunmetal := _mat(Color(0.06, 0.06, 0.065), 0.4, 0.8)

	_body = Node3D.new()
	add_child(_body)

	for side in [-1, 1]:
		var leg := Node3D.new()
		leg.position = Vector3(0.1 * side, 0.9, 0)
		_body.add_child(leg)
		_part(leg, _cyl(0.075, 0.07, 0.5), wool, Vector3(0, -0.3, 0))
		_part(leg, _cyl(0.07, 0.075, 0.36), leather, Vector3(0, -0.72, 0.0))
		_part(leg, BoxMesh.new(), leather, Vector3(0, -0.88, -0.05), Vector3.ZERO, Vector3(0.1, 0.06, 0.24))
		if side < 0:
			_leg_l = leg
		else:
			_leg_r = leg

	# Greatcoat: torso, a long skirt to below the knee, collar, belt with buckle and ammunition pouches.
	_part(_body, _cyl(0.2, 0.235, 0.62), wool, Vector3(0, 1.2, 0), Vector3.ZERO, Vector3(1.1, 1, 0.78))
	_part(_body, _cyl(0.235, 0.33, 0.55), wool, Vector3(0, 0.68, 0), Vector3.ZERO, Vector3(1.05, 1, 0.85))
	_part(_body, _cyl(0.12, 0.15, 0.09), wool, Vector3(0, 1.53, 0), Vector3.ZERO, Vector3(1.1, 1, 1))
	_part(_body, _cyl(0.245, 0.245, 0.055), belt, Vector3(0, 0.98, 0), Vector3.ZERO, Vector3(1.1, 1, 0.8))
	_part(_body, BoxMesh.new(), steel, Vector3(0, 0.98, -0.2), Vector3.ZERO, Vector3(0.07, 0.05, 0.02))
	for side in [-1, 1]:
		_part(_body, BoxMesh.new(), leather, Vector3(0.12 * side, 0.99, -0.19), Vector3.ZERO, Vector3(0.1, 0.08, 0.05))

	for side in [-1, 1]:
		var arm := Node3D.new()
		arm.position = Vector3(0.25 * side, 1.46, 0)
		_body.add_child(arm)
		var sleeve := CapsuleMesh.new()
		sleeve.radius = 0.06
		sleeve.height = 0.62
		_part(arm, sleeve, wool, Vector3(0, -0.29, 0))
		var hand := SphereMesh.new()
		hand.radius = 0.045
		hand.height = 0.09
		_part(arm, hand, skin, Vector3(0, -0.62, 0))
		if side < 0:
			_arm_l = arm
		else:
			_arm_r = arm

	# Head and M35 helmet: a deep dome with the flared skirt that gives the unmistakable silhouette.
	_head = Node3D.new()
	_head.position = Vector3(0, 1.62, 0)
	_body.add_child(_head)
	var face := SphereMesh.new()
	face.radius = 0.105
	face.height = 0.24
	_part(_head, face, skin, Vector3(0, 0.0, -0.01))
	var dome := SphereMesh.new()
	dome.radius = 0.145
	dome.height = 0.145
	dome.is_hemisphere = true
	_part(_head, dome, steel, Vector3(0, 0.03, 0.005), Vector3.ZERO, Vector3(1.0, 1.05, 1.12))
	_part(_head, _cyl(0.145, 0.168, 0.07), steel, Vector3(0, -0.005, 0.012), Vector3(-6, 0, 0), Vector3(1.0, 1.0, 1.12))

	# Kar98k slung on the right shoulder, muzzle up.
	_rifle = Node3D.new()
	_rifle.position = Vector3(0.2, 1.15, 0.1)
	_rifle.rotation_degrees = Vector3(-8, 0, -6)
	_body.add_child(_rifle)
	_part(_rifle, BoxMesh.new(), wood, Vector3(0, -0.15, 0), Vector3.ZERO, Vector3(0.045, 0.75, 0.06))
	_part(_rifle, _cyl(0.011, 0.011, 0.6), gunmetal, Vector3(0, 0.45, -0.01))
	_part(_rifle, BoxMesh.new(), wood, Vector3(0, -0.6, 0.02), Vector3(8, 0, 0), Vector3(0.045, 0.28, 0.11))

	# Button-on chest torch, with a beam that shows up in the fog.
	_part(_body, BoxMesh.new(), _mat(Color(0.12, 0.12, 0.1), 0.5, 0.4), Vector3(-0.1, 1.32, -0.2), Vector3.ZERO, Vector3(0.065, 0.1, 0.04))
	_torch = SpotLight3D.new()
	_torch.light_color = Color(1.0, 0.92, 0.76)
	_torch.light_energy = 3.2
	_torch.spot_range = 24.0
	_torch.spot_angle = 17.0
	_torch.spot_attenuation = 1.2
	_torch.shadow_enabled = true
	_torch.light_volumetric_fog_energy = 2.0
	_torch.position = Vector3(-0.1, 1.32, -0.23)
	_torch.rotation_degrees = Vector3(-12, 0, 0)
	_torch.visible = torch_on
	_body.add_child(_torch)
	Visibility.register_light(_torch)

	for mi in _body.find_children("*", "MeshInstance3D", true, false):
		(mi as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON


# --- perception --------------------------------------------------------------------------------

func _eye_pos() -> Vector3:
	return global_position + Vector3.UP * 1.62


## How hostile what he sees is. 1 or more means "enemy", below 1 means "a civilian worth watching".
func _hostility() -> float:
	var h := 0.0
	if _player.firearm and not _player.firearm.holstered:
		h += 1.0
	if _player.crouching:
		h += 0.45
	if _player.sprinting:
		h += 0.45
	if Visibility.in_restricted_zone(_player.global_position):
		h += 1.0
	if _combat_t < 90.0:
		h += 1.0
	return h


func _perceive() -> void:
	_can_see_player = false
	_visibility = 0.0
	if _player == null or _player.dead or Debug.peaceful():
		return
	var eye := _eye_pos()
	var chest := _player.global_position + Vector3.UP * (0.6 if _player.crouching else 1.15)
	var head := _player.head.global_position
	var to := chest - eye
	var dist := to.length()
	var light := Visibility.light_level(get_world_3d(), chest, [_player.get_rid()])
	var light_f := clampf(light / 0.5, 0.12, 2.5)
	var effective_range := view_distance * clampf(light_f, 0.25, 1.0)
	if dist > effective_range:
		return
	var facing := -global_basis.z
	var look := facing.rotated(Vector3.UP, _look_yaw)
	var flat := Vector3(to.x, 0.0, to.z).normalized()
	var ang := rad_to_deg(look.angle_to(flat))
	if ang > fov_deg * 0.5:
		return
	var space := get_world_3d().direct_space_state
	var seen_points := 0
	for p in [chest, head]:
		var q := PhysicsRayQueryParameters3D.create(eye, p, Game.LAYER_WORLD, [get_rid()])
		if space.intersect_ray(q).is_empty():
			seen_points += 1
	if seen_points == 0:
		return
	_can_see_player = true
	var dist_f := pow(clampf(1.0 - dist / effective_range, 0.0, 1.0), 1.3)
	var angle_f := lerpf(1.0, 0.3, ang / (fov_deg * 0.5))
	var posture_f := 0.55 if _player.crouching else 1.0
	var speed := _player.horizontal_speed()
	var motion_f := 0.45 if speed < 0.2 else (1.6 if speed > 3.0 else 1.0)
	_visibility = light_f * dist_f * angle_f * posture_f * motion_f * (seen_points * 0.5) * (1.0 + alertness)
	if dist < 2.5:
		_visibility = maxf(_visibility, 2.0)


func _on_noise(pos: Vector3, loudness: float, source: Node) -> void:
	if state == State.DEAD or source == self or Debug.peaceful():
		return
	var d := global_position.distance_to(pos)
	var received := loudness + linear_to_db(1.0 / maxf(d, 1.0))
	var q := PhysicsRayQueryParameters3D.create(_eye_pos(), pos + Vector3.UP * 0.3, Game.LAYER_WORLD, [get_rid()])
	if not get_world_3d().direct_space_state.intersect_ray(q).is_empty():
		received -= 14.0
	var perceived := received - Visibility.noise_floor_db
	if perceived <= 4.0:
		return
	# Hearing gives only a rough location, and the further away the worse it is.
	var err := clampf(d * 0.12, 0.5, 12.0)
	var guess := pos + Vector3(randf_range(-err, err), 0, randf_range(-err, err))
	if loudness >= 110.0:
		# A gunshot or a whistle. Something is wrong; go and find out, fast.
		_combat_t = 0.0
		alertness = minf(alertness + 0.5, 1.5)
		if state != State.ALERTED:
			target_pos = guess
			_enter(State.SEARCH)
	elif state == State.PATROL or state == State.CURIOUS:
		suspicion = maxf(suspicion, clampf(0.25 + perceived * 0.025, 0.25, 0.65))
		target_pos = guess
		_enter(State.SUSPICIOUS if suspicion >= 0.5 else State.CURIOUS)


# --- decisions ---------------------------------------------------------------------------------

func _enter(s: State) -> void:
	if state == s or state == State.DEAD:
		return
	state = s
	_state_t = 0.0
	match s:
		State.ALERTED:
			_fire_t = randf_range(0.55, 0.95)   # reaction time before the first aimed shot
			_raise_alarm()
		State.SEARCH:
			_wait = randf_range(18.0, 32.0)
		State.CURIOUS:
			_wait = randf_range(2.5, 4.5)


func _raise_alarm() -> void:
	if _whistle_cd > 0.0:
		return
	_whistle_cd = 25.0
	SoundLib.play_3d("alarm/whistle_trill", _eye_pos(), 6.0, 300.0, 0.04, 12.0)
	Game.emit_noise(_eye_pos(), 115.0, self)


func _think(delta: float) -> void:
	var hostile := _hostility() >= 1.0
	if _can_see_player:
		_last_seen_t = 0.0
		var cap := 1.3 if hostile else 0.7
		suspicion = minf(suspicion + _visibility * delta * 1.4, cap)
		if suspicion > 0.2:
			target_pos = _player.global_position
	else:
		_last_seen_t += delta
		suspicion = maxf(suspicion - delta * (0.05 if state == State.SEARCH else 0.09), 0.0)

	match state:
		State.PATROL:
			if suspicion >= 0.25:
				_enter(State.CURIOUS)
		State.CURIOUS:
			if suspicion >= 0.6:
				_enter(State.SUSPICIOUS)
			elif _state_t > _wait and suspicion < 0.2:
				_enter(State.PATROL)
		State.SUSPICIOUS:
			if hostile and suspicion >= 1.0:
				_enter(State.ALERTED)
			elif _state_t > 14.0 and suspicion < 0.3:
				alertness = minf(alertness + 0.15, 1.5)
				_enter(State.PATROL)
		State.SEARCH:
			if _can_see_player and hostile and suspicion >= 0.5:
				_enter(State.ALERTED)
			elif _state_t > _wait:
				alertness = minf(alertness + 0.25, 1.5)
				suspicion = 0.0
				_enter(State.PATROL)
		State.ALERTED:
			if _player.dead:
				_enter(State.SEARCH)
			elif _last_seen_t > 4.0:
				target_pos = _player.global_position if _last_seen_t < 4.5 else target_pos
				_enter(State.SEARCH)
	if state != State.ALERTED and _can_see_player and hostile and suspicion >= 1.0:
		_enter(State.ALERTED)


func _physics_process(delta: float) -> void:
	if state == State.DEAD:
		_update_death(delta)
		return
	_state_t += delta
	_combat_t += delta
	_whistle_cd = maxf(_whistle_cd - delta, 0.0)
	_perceive_t -= delta
	if _perceive_t <= 0.0:
		_perceive_t = 0.1
		_perceive()
	_think(delta)

	var desired_speed := 0.0
	var face_dir := Vector3.ZERO
	match state:
		State.PATROL:
			_look_yaw = sin(_state_t * 0.35) * 0.45 if _wait > 0.0 else move_toward(_look_yaw, 0.0, delta)
			if patrol_points.is_empty():
				pass
			elif _wait > 0.0:
				_wait -= delta
			elif _move_toward_point(patrol_points[_patrol_i], walk_speed, delta):
				_patrol_i = (_patrol_i + 1) % patrol_points.size()
				_wait = randf_range(3.0, 7.0) if patrol_points.size() > 1 else 9999.0
			if patrol_points.size() <= 1 and _wait > 0.0:
				face_dir = Vector3.FORWARD.rotated(Vector3.UP, _home_yaw)
		State.CURIOUS:
			_look_yaw = move_toward(_look_yaw, 0.0, delta * 2.0)
			face_dir = target_pos - global_position
		State.SUSPICIOUS:
			_look_yaw = move_toward(_look_yaw, 0.0, delta * 2.0)
			if _can_see_player and global_position.distance_to(_player.global_position) < 6.0:
				face_dir = _player.global_position - global_position
			elif _move_toward_point(target_pos, walk_speed * 0.9, delta):
				face_dir = target_pos - global_position
		State.SEARCH:
			if global_position.distance_to(target_pos) > 1.2 and _state_t < _wait * 0.6:
				_move_toward_point(target_pos, run_speed * (0.75 if _state_t > 6.0 else 1.0), delta)
				_look_yaw = move_toward(_look_yaw, 0.0, delta * 2.0)
			else:
				_look_yaw = sin(_state_t * 0.8) * 1.1
		State.ALERTED:
			_look_yaw = move_toward(_look_yaw, 0.0, delta * 4.0)
			face_dir = _player.global_position - global_position
			if _can_see_player:
				_fire_t -= delta
				if _fire_t <= 0.0:
					_fire_t = randf_range(fire_interval.x, fire_interval.y)
					_fire_at_player()
			else:
				_move_toward_point(target_pos, run_speed, delta)

	if face_dir != Vector3.ZERO:
		_face(face_dir, delta, 3.0)
	if desired_speed == 0.0 and _not_moving_state():
		velocity.x = move_toward(velocity.x, 0.0, delta * 6.0)
		velocity.z = move_toward(velocity.z, 0.0, delta * 6.0)
	if not is_on_floor():
		velocity.y -= _gravity * delta
	else:
		velocity.y = 0.0
	move_and_slide()
	_animate(delta)


var _moving_this_frame := false


func _not_moving_state() -> bool:
	var moving := _moving_this_frame
	_moving_this_frame = false
	return not moving


## Walks toward a point (with the navmesh if ready). Returns true on arrival.
func _move_toward_point(point: Vector3, speed: float, delta: float) -> bool:
	var to := point - global_position
	to.y = 0.0
	if to.length() < 0.9:
		return true
	var next := point
	if Visibility.nav_ready:
		if _nav.target_position.distance_to(point) > 0.5:
			_nav.target_position = point
		var n := _nav.get_next_path_position()
		if n.distance_to(global_position) > 0.05:
			next = n
	var dir := next - global_position
	dir.y = 0.0
	dir = dir.normalized()
	var k := 1.0 - exp(-6.0 * delta)
	velocity.x = lerpf(velocity.x, dir.x * speed, k)
	velocity.z = lerpf(velocity.z, dir.z * speed, k)
	_face(dir, delta, 4.0)
	_moving_this_frame = true
	return false


func _face(dir: Vector3, delta: float, rate: float) -> void:
	dir.y = 0.0
	if dir.length() < 0.01:
		return
	var target := atan2(-dir.x, -dir.z)
	rotation.y = rotate_toward(rotation.y, target, rate * delta)


func _fire_at_player() -> void:
	var eye := _eye_pos() + Vector3.UP * -0.05
	var aim_point := _player.global_position + Vector3.UP * (0.7 if _player.crouching else 1.2)
	var dist := eye.distance_to(aim_point)
	var light := Visibility.light_level(get_world_3d(), aim_point, [_player.get_rid()])
	var spread := 0.5 + dist * 0.025 + _player.horizontal_speed() * 0.45 + (1.2 if light < 0.35 else 0.0)
	var dir := (aim_point - eye).normalized()
	var a := deg_to_rad(spread) * sqrt(randf())
	var phi := randf() * TAU
	var basis := Basis.looking_at(dir)
	var shot := (basis * Vector3(sin(a) * cos(phi), sin(a) * sin(phi), -cos(a))).normalized()

	var muzzle := eye + dir * 0.9
	var bang := SoundLib.play_3d("weapons/p38_shot", muzzle, 6.0, 900.0, 0.03, 18.0)
	bang.pitch_scale = 0.72
	var tail := SoundLib.play_3d("weapons/tail_street", muzzle, 2.0, 900.0, 0.03, 18.0)
	tail.pitch_scale = 0.8
	Hearing.expose(167.0, _player.camera.global_position.distance_to(muzzle), false)
	Game.emit_noise(muzzle, 167.0, self)
	_flash(muzzle)

	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(eye, eye + shot * 400.0, Game.LAYER_WORLD | Game.LAYER_PLAYER, [get_rid()])
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		return
	if hit.collider == _player:
		var head_h := _player.head.global_position.y
		var dmg := rifle_damage * (5.0 if hit.position.y > head_h - 0.14 else 1.0)
		_player.take_hit(dmg, hit.position, shot, self)
	else:
		ImpactFX.spawn(get_tree().current_scene, hit.position, hit.normal, shot, ImpactFX.surface_of(hit.collider, hit.position))


func _flash(pos: Vector3) -> void:
	var l := OmniLight3D.new()
	l.light_color = Color(1.0, 0.7, 0.4)
	l.light_energy = 9.0
	l.omni_range = 9.0
	get_tree().current_scene.add_child(l)
	l.global_position = pos
	get_tree().create_timer(0.06, false).timeout.connect(l.queue_free)


func take_hit(damage: float, pos: Vector3, _dir: Vector3, attacker: Node) -> void:
	if state == State.DEAD:
		return
	var local_y := pos.y - global_position.y
	health -= damage * (4.0 if local_y > 1.5 else 1.0)
	SoundLib.play_3d("impacts/impact_dirt", pos, -2.0, 40.0, 0.1, 3.0)
	if health <= 0.0:
		_die()
		return
	_combat_t = 0.0
	alertness = 1.5
	suspicion = 1.3
	if attacker is Node3D:
		target_pos = (attacker as Node3D).global_position
	_enter(State.ALERTED)


func _die() -> void:
	state = State.DEAD
	_state_t = 0.0
	collision_layer = 0
	collision_mask = Game.LAYER_WORLD
	velocity = Vector3.ZERO
	add_to_group("bodies")
	SoundLib.play_3d("footsteps/cobble_run", global_position, 6.0, 40.0, 0.1, 3.0)


func _update_death(delta: float) -> void:
	_death_t += delta
	var t := clampf(_death_t / 0.8, 0.0, 1.0)
	var e := t * t
	_body.rotation.x = lerpf(0.0, deg_to_rad(84.0), e)
	_body.position.y = lerpf(0.0, 0.12, e)
	_body.position.z = lerpf(0.0, 0.9, e)
	if not is_on_floor():
		velocity.y -= _gravity * delta
		move_and_slide()


# --- animation ---------------------------------------------------------------------------------

func _animate(delta: float) -> void:
	var spd := Vector2(velocity.x, velocity.z).length()
	_walk_phase += spd * delta * 2.4
	var amt := clampf(spd / 1.3, 0.0, 1.6)
	var swing := sin(_walk_phase) * 0.42 * amt
	_leg_l.rotation.x = swing
	_leg_r.rotation.x = -swing
	_body.position.y = absf(sin(_walk_phase)) * 0.025 * amt
	_head.rotation.y = lerp_angle(_head.rotation.y, _look_yaw, 1.0 - exp(-5.0 * delta))
	var aiming := state == State.ALERTED and _can_see_player
	if aiming:
		_arm_r.rotation.x = lerp_angle(_arm_r.rotation.x, deg_to_rad(-80.0), 1.0 - exp(-10.0 * delta))
		_arm_l.rotation.x = lerp_angle(_arm_l.rotation.x, deg_to_rad(-85.0), 1.0 - exp(-10.0 * delta))
		_arm_l.rotation.y = lerp_angle(_arm_l.rotation.y, deg_to_rad(-35.0), 1.0 - exp(-10.0 * delta))
		_rifle.position = _rifle.position.lerp(Vector3(0.12, 1.42, -0.35), 1.0 - exp(-10.0 * delta))
		_rifle.rotation = _rifle.rotation.lerp(Vector3(deg_to_rad(-90.0), 0.0, 0.0), 1.0 - exp(-10.0 * delta))
	else:
		_arm_l.rotation.x = -swing * 0.5
		_arm_l.rotation.y = 0.0
		_arm_r.rotation.x = lerp_angle(_arm_r.rotation.x, deg_to_rad(-25.0), 1.0 - exp(-6.0 * delta))
		_rifle.position = _rifle.position.lerp(Vector3(0.2, 1.15, 0.1), 1.0 - exp(-6.0 * delta))
		_rifle.rotation = _rifle.rotation.lerp(Vector3(deg_to_rad(-8.0), 0.0, deg_to_rad(-6.0)), 1.0 - exp(-6.0 * delta))
	# The torch points where he's looking, and at you once he's interested.
	var torch_target := 0.0
	if state in [State.CURIOUS, State.SUSPICIOUS, State.ALERTED] and _player:
		var to_p := _player.global_position + Vector3.UP - _torch.global_position
		var local := global_basis.inverse() * to_p
		_torch.rotation.x = lerp_angle(_torch.rotation.x, atan2(local.y, Vector2(local.x, local.z).length()), 1.0 - exp(-4.0 * delta))
		torch_target = atan2(-local.x, -local.z)
	else:
		_torch.rotation.x = lerp_angle(_torch.rotation.x, deg_to_rad(-12.0), 1.0 - exp(-3.0 * delta))
		torch_target = _look_yaw
	_torch.rotation.y = lerp_angle(_torch.rotation.y, torch_target, 1.0 - exp(-4.0 * delta))


func state_name() -> String:
	return STATE_NAMES[state]
