class_name Player
extends CharacterBody3D
## The first-person body. It's slow and deliberate: the scroll wheel sets walking pace, sprinting costs
## stamina, crouch is a toggle and lean is held. Footsteps depend on the surface and are loud enough for AI to hear.

@export_group("Movement")
## Walking paces in m/s, chosen with the mouse wheel. A careful creep through to a brisk walk.
@export var paces: PackedFloat32Array = PackedFloat32Array([0.75, 1.2, 1.65, 2.1])
@export var start_pace := 2
@export var sprint_speed := 4.9
@export var crouch_mult := 0.55
@export var ground_accel := 8.0
@export var air_accel := 0.8
@export var jump_velocity := 3.3

@export_group("Body")
@export var stand_height := 1.78
@export var crouch_height := 1.12
@export var stand_eye := 1.64
@export var crouch_eye := 1.0
@export var lean_max_offset := 0.34
@export var lean_max_roll_deg := 12.0

## How loud footsteps are for AI on each surface, relative to cobbles (dB).
const SURFACE_LOUDNESS := {"cobble": 4.0, "stone": 4.0, "gravel": 6.0, "wood": 3.0, "mud": -3.0, "grass": -6.0}

@onready var collision: CollisionShape3D = $Collision
@onready var head: Node3D = $Head
@onready var lean_pivot: Node3D = $Head/LeanPivot
@onready var camera: Camera3D = $Head/LeanPivot/Camera
@onready var firearm: Firearm = $Head/LeanPivot/Camera/Viewmodel/Firearm
@onready var overlay: Node = $Overlay

var pace := 2
var yaw := 0.0
var pitch := 0.0
var crouching := false
var sprinting := false
var stamina := 1.0
## 0..1 heavy breathing. It lags behind stamina and drives sway, breath sounds and heartbeat.
var exhaustion := 0.0
var lean := 0.0
## Counts footsteps. The fractional part is how far through the current stride we are.
var stride_phase := 0.0
## Look motion accumulated this frame (pixels). The weapon consumes it for sway.
var mouse_motion := Vector2.ZERO
var debug_force_ads := false
var health := 100.0
var dead := false
## Your forged documents. Mission 1 starts with a good carte d'identité but no pass for the coastal zone.
var papers := {"identity": true, "zone_pass": false}
## Things in your coat pockets.
var items := {"bottle": 0}
## "" for your own clothes, "kriegsmarine" for a stolen navy greatcoat.
var disguise := ""
var _gaze := {}
var _notice_t := 0.0
var _vault_t := -1.0
var _vault_from := Vector3.ZERO
var _vault_to := Vector3.ZERO
var _vault_peak := 0.0
## Seconds the body is locked into an action, such as a takedown.
var busy := 0.0
## The body being dragged, if any.
var dragging: Guard = null
var _interact_t := 0.0
var _interact_target: Guard = null
var _interact_kind := ""
var _interactable: Interactable = null

var _eye := 1.64
var _recoil := Vector2.ZERO          # (yaw, pitch) offset that recovers toward zero
var _recoil_recovery := 7.0
var _aim_sway := Vector2.ZERO
var _stamina_delay := 0.0
var _jump_requested := false
var _was_on_floor := true
var _fall_speed := 0.0
var _landing_dip := 0.0
var _lean_clearance := 1.0
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _breath_calm: AudioStreamPlayer
var _breath_hard: AudioStreamPlayer
var _heart: AudioStreamPlayer


func _ready() -> void:
	add_to_group("player")
	pace = clampi(start_pace, 0, paces.size() - 1)
	_eye = stand_eye
	yaw = rotation.y
	(collision.shape as CapsuleShape3D).height = stand_height
	collision.position.y = stand_height * 0.5
	if not Debug.active():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_breath_calm = _make_loop("player/breath_calm_loop")
	_breath_hard = _make_loop("player/breath_exhausted_loop")
	_heart = _make_loop("player/heartbeat_loop")


func _make_loop(key: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.stream = SoundLib.pick(key)
	p.bus = Game.BUS_WORLD
	p.volume_db = -80.0
	add_child(p)
	p.play()
	return p


# --- input -------------------------------------------------------------------------------------

func _unhandled_input(event: InputEvent) -> void:
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED or dead:
		return
	if event is InputEventMouseMotion:
		var motion: Vector2 = event.relative
		var s := Game.mouse_sensitivity * (0.55 if is_aiming() else 1.0)
		yaw -= motion.x * s
		pitch = clampf(pitch - motion.y * s, deg_to_rad(-86.0), deg_to_rad(86.0))
		mouse_motion += motion
	elif event.is_action_pressed("pace_up"):
		pace = mini(pace + 1, paces.size() - 1)
	elif event.is_action_pressed("pace_down"):
		pace = maxi(pace - 1, 0)
	elif event.is_action_pressed("crouch"):
		if not crouching:
			crouching = true
		elif _can_stand():
			crouching = false
	elif event.is_action_pressed("jump"):
		_jump_requested = true
	elif event.is_action_pressed("throw"):
		_throw()
	elif event.is_action_pressed("interact"):
		_interact()
	elif event.is_action_pressed("watch"):
		var t := Game.clock_text()
		if Game.curfew_active():
			note("Your watch: %s. Curfew." % t, 3.0)
		elif Game.clock_minutes >= Game.CURFEW_START - 30:
			note("Your watch: %s. Curfew soon." % t, 3.0)
		else:
			note("Your watch: %s." % t, 2.5)


## Recoil from the weapon. A share of it ("stick") moves the aim permanently, like CS spray climb.
## The rest kicks the view and recovers.
func add_recoil(pitch_rad: float, yaw_rad: float, recovery: float, stick := 0.25) -> void:
	pitch = clampf(pitch + pitch_rad * stick, deg_to_rad(-86.0), deg_to_rad(86.0))
	yaw += yaw_rad * stick
	_recoil += Vector2(yaw_rad, pitch_rad) * (1.0 - stick)
	_recoil_recovery = recovery


func is_aiming() -> bool:
	return firearm != null and firearm.ads > 0.5


func horizontal_speed() -> float:
	return Vector2(velocity.x, velocity.z).length()


# --- vaulting, throwing, noticing -------------------------------------------------------------

## Space in front of a low wall, fence or crate climbs over it (or onto it, if there's room on top).
func _try_vault() -> bool:
	if dragging or busy > 0.0 or crouching:
		return false
	var fwd := -global_basis.z
	fwd.y = 0.0
	fwd = fwd.normalized()
	var space := get_world_3d().direct_space_state
	var base := global_position
	var low := PhysicsRayQueryParameters3D.create(base + Vector3.UP * 0.45, base + Vector3.UP * 0.45 + fwd * 0.9, Game.LAYER_WORLD, [get_rid()])
	var low_hit := space.intersect_ray(low)
	if low_hit.is_empty():
		return false
	var reach := Vector2(low_hit.position.x - base.x, low_hit.position.z - base.z).length()
	var high := PhysicsRayQueryParameters3D.create(base + Vector3.UP * 1.55, base + Vector3.UP * 1.55 + fwd * 1.1, Game.LAYER_WORLD, [get_rid()])
	if not space.intersect_ray(high).is_empty():
		return false
	# Probe the top just beyond where the forward ray met the obstacle's face.
	var probe := base + fwd * (reach + 0.12)
	var top_q := PhysicsRayQueryParameters3D.create(probe + Vector3.UP * 1.6, probe + Vector3.UP * 0.2, Game.LAYER_WORLD, [get_rid()])
	var top := space.intersect_ray(top_q)
	if top.is_empty():
		return false
	var top_y: float = top.position.y
	if top_y - base.y < 0.35 or top_y - base.y > 1.4:
		return false
	var far := base + fwd * (reach + 1.0)
	var far_q := PhysicsRayQueryParameters3D.create(far + Vector3.UP * 1.8, far + Vector3.DOWN * 2.0, Game.LAYER_WORLD, [get_rid()])
	var far_hit := space.intersect_ray(far_q)
	if far_hit.is_empty():
		return false
	_vault_from = base
	_vault_to = Vector3(far.x, (far_hit.position as Vector3).y + 0.02, far.z)
	_vault_peak = top_y + 0.3
	_vault_t = 0.0
	velocity = Vector3.ZERO
	stamina = maxf(stamina - 0.08, 0.0)
	SoundLib.play_2d("player/cloth_wool_move", 0.0)
	Game.emit_noise(global_position, 52.0, self)
	return true


func _update_vault(delta: float) -> void:
	_vault_t += delta / 0.6
	var t := clampf(_vault_t, 0.0, 1.0)
	var p := _vault_from.lerp(_vault_to, smoothstep(0.0, 1.0, t))
	var lift := maxf(_vault_peak - _vault_from.y, 0.0)
	p.y = lerpf(_vault_from.y, _vault_to.y, t) + sin(t * PI) * lift
	global_position = p
	if _vault_t >= 1.0:
		_vault_t = -1.0
		_footstep(1.4, 2.0)


## G throws an empty bottle if you have one, or a stone from the road if you don't. Either way it makes a
## noise where it lands, and a bottle shatters much louder.
func _throw() -> void:
	if dead or busy > 0.0 or dragging:
		return
	var t := Throwable.new()
	if items.get("bottle", 0) > 0:
		items["bottle"] -= 1
	else:
		t.loudness = 64.0
		t.breaks = false
		t.sound_key = "impacts/impact_dirt"
	get_tree().current_scene.add_child(t)
	var fwd := -camera.global_basis.z
	t.global_position = camera.global_position + fwd * 0.5 + Vector3.DOWN * 0.1
	t.linear_velocity = fwd * 11.0 + Vector3.UP * 2.5 + velocity
	t.angular_velocity = Vector3(randf_range(-8, 8), randf_range(-8, 8), randf_range(-8, 8))
	SoundLib.play_2d("player/cloth_wool_move", -4.0)


## Looking at something notable for a moment makes the character notice it.
func _update_noticing(delta: float) -> void:
	_notice_t -= delta
	if _notice_t > 0.0:
		return
	_notice_t = 0.15
	var eye := camera.global_position
	var fwd := -camera.global_basis.z
	var space := get_world_3d().direct_space_state
	for n in get_tree().get_nodes_in_group("notables"):
		var nb := n as Notable
		if nb == null or nb.noticed:
			continue
		var to := nb.global_position - eye
		var d := to.length()
		if d > nb.radius or rad_to_deg(fwd.angle_to(to)) > 15.0:
			_gaze.erase(nb)
			continue
		var q := PhysicsRayQueryParameters3D.create(eye, nb.global_position, Game.LAYER_WORLD, [get_rid()])
		var hit := space.intersect_ray(q)
		if not hit.is_empty() and (hit.position as Vector3).distance_to(nb.global_position) > 0.8:
			continue
		_gaze[nb] = float(_gaze.get(nb, 0.0)) + 0.15
		if _gaze[nb] >= nb.look_time:
			nb.noticed = true
			note(nb.thought, 5.5)
			if overlay and overlay.has_method("add_lead"):
				overlay.add_lead(nb.lead)


# --- interaction: takedowns and bodies ---------------------------------------------------------

func _interact() -> void:
	if dead or busy > 0.0:
		return
	if dragging:
		dragging.dragged_by = null
		dragging = null
		SoundLib.play_2d("player/cloth_wool_move", -2.0)
		return
	_refresh_interact()
	if _interact_kind == "object" and _interactable:
		busy = _interactable.busy_time
		_interactable.interact(self)
		return
	if _interact_kind == "papers":
		_interact_target.present_papers(self)
		SoundLib.play_2d("player/cloth_wool_move", -4.0)
		return
	if _interact_kind == "takedown":
		busy = 1.1
		_interact_target.silent_kill(self)
		SoundLib.play_2d("player/cloth_wool_move", 2.0)
		SoundLib.play_3d("impacts/impact_dirt", _interact_target.global_position + Vector3.UP, -10.0, 15.0, 0.1, 1.0)
		stamina = maxf(stamina - 0.15, 0.0)
		add_recoil(deg_to_rad(-3.0), deg_to_rad(randf_range(-2.0, 2.0)), 4.0, 0.0)
	elif _interact_kind == "drag":
		dragging = _interact_target
		dragging.dragged_by = self
		SoundLib.play_2d("player/cloth_wool_move", 0.0)


func _refresh_interact() -> void:
	_interact_target = null
	_interact_kind = ""
	_interactable = null
	var best := 9999.0
	for n in get_tree().get_nodes_in_group("interactables"):
		var it := n as Interactable
		if it and it.can_interact(self):
			var d0 := global_position.distance_to(it.global_position)
			if d0 < best:
				best = d0
				_interactable = it
				_interact_kind = "object"
	for n in get_tree().get_nodes_in_group("guards"):
		var g := n as Guard
		if g == null:
			continue
		if g.is_dead():
			var d := global_position.distance_to(g.body_center())
			if d < 1.7 and d < best:
				best = d
				_interact_target = g
				_interact_kind = "drag"
		elif g.wants_papers_from(self):
			_interact_target = g
			_interact_kind = "papers"
			return
		elif g.can_be_taken_down_by(self):
			var d2 := global_position.distance_to(g.global_position)
			if d2 < best + 0.5:
				best = d2
				_interact_target = g
				_interact_kind = "takedown"


func _update_interaction(delta: float) -> void:
	busy = maxf(busy - delta, 0.0)
	if dragging:
		var fwd := -global_basis.z
		fwd.y = 0.0
		dragging.drag_toward(global_position + fwd.normalized() * 0.95, global_position, delta)
		if horizontal_speed() > 0.2:
			Game.emit_noise(dragging.global_position, 42.0, self)
		if overlay and overlay.has_method("hint"):
			overlay.hint("[F]  let go")
		return
	_interact_t -= delta
	if _interact_t <= 0.0:
		_interact_t = 0.1
		_refresh_interact()
	if overlay and overlay.has_method("hint"):
		match _interact_kind:
			"takedown":
				overlay.hint("[F]  take him down")
			"drag":
				overlay.hint("[F]  drag the body")
			"papers":
				overlay.hint("[F]  show your papers")
			"object":
				overlay.hint("[F]  " + _interactable.prompt)
			_:
				overlay.hint("")


## Hit by a bullet. There's no health bar: you feel it in the jolt, your breathing, and how slowly you move.
func take_hit(damage: float, _pos: Vector3, _dir: Vector3, _attacker: Node) -> void:
	if dead:
		return
	health -= damage
	add_recoil(deg_to_rad(randf_range(5.0, 9.0)), deg_to_rad(randf_range(-7.0, 7.0)), 2.5, 0.45)
	SoundLib.play_2d("impacts/impact_dirt", 3.0)
	stamina *= 0.5
	exhaustion = 1.0
	if health <= 0.0:
		_die()
	else:
		note("You're hit." if health > 40.0 else "You're badly hurt.", 2.5)


func _die() -> void:
	dead = true
	print("PLAYER DIED at ", Game.clock_text(), " pos ", global_position)
	if overlay:
		overlay.fade_to(1.0)
	note("You were killed.", 9.0)
	get_tree().create_timer(7.0, false).timeout.connect(get_tree().reload_current_scene)


func note(text: String, seconds := 3.0) -> void:
	if overlay and overlay.has_method("note"):
		overlay.note(text, seconds)


# --- simulation --------------------------------------------------------------------------------

func _physics_process(delta: float) -> void:
	var on_floor := is_on_floor()
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED or dead or busy > 0.0:
		input = Vector2.ZERO
	var wish := global_basis * Vector3(input.x, 0.0, input.y)
	wish.y = 0.0
	wish = wish.normalized() * minf(input.length(), 1.0)

	sprinting = Input.is_action_pressed("sprint") and input.y < -0.3 and stamina > 0.04 \
		and on_floor and not is_aiming() and input != Vector2.ZERO and dragging == null
	if sprinting and crouching:
		if _can_stand():
			crouching = false
		else:
			sprinting = false

	var speed := paces[pace]
	if sprinting:
		speed = sprint_speed * lerpf(1.0, 0.78, exhaustion)
	if crouching:
		speed *= crouch_mult
	if is_aiming():
		speed = minf(speed, 0.9)
	if health < 50.0:
		speed *= 0.75   # wounded
	if dragging:
		speed = minf(speed, 0.85)

	var horiz := Vector3(velocity.x, 0.0, velocity.z)
	var k := 1.0 - exp(-(ground_accel if on_floor else air_accel) * delta)
	horiz = horiz.lerp(wish * speed, k)
	velocity.x = horiz.x
	velocity.z = horiz.z

	if not on_floor:
		velocity.y -= _gravity * delta
		_fall_speed = maxf(_fall_speed, -velocity.y)
	if _vault_t >= 0.0:
		_update_vault(delta)
		return
	if _jump_requested and on_floor and _try_vault():
		_jump_requested = false
		return
	if _jump_requested:
		_jump_requested = false
		if on_floor and stamina > 0.12 and not crouching:
			velocity.y = jump_velocity
			stamina -= 0.1
			_stamina_delay = 1.2

	move_and_slide()

	var now_floor := is_on_floor()
	if now_floor and not _was_on_floor:
		_on_land(_fall_speed)
	if now_floor:
		_fall_speed = 0.0
	_was_on_floor = now_floor

	_update_stamina(delta)
	_update_crouch(delta)
	_update_steps(delta)
	_update_lean_clearance()


func _update_stamina(delta: float) -> void:
	var hspeed := horizontal_speed()
	if sprinting and hspeed > 2.5:
		stamina = maxf(stamina - delta / 13.0, 0.0)
		_stamina_delay = 1.6
	else:
		_stamina_delay -= delta
		if _stamina_delay <= 0.0:
			var rate := (1.0 / 16.0) * (0.45 if hspeed > 1.2 else 1.0) * (1.25 if crouching else 1.0)
			stamina = minf(stamina + delta * rate, 1.0)
	var target := clampf((0.7 - stamina) / 0.7, 0.0, 1.0)
	if health < 50.0:
		target = maxf(target, 0.45)
	exhaustion = move_toward(exhaustion, target, delta * (0.5 if target > exhaustion else 0.1))


func _update_crouch(delta: float) -> void:
	var cap := collision.shape as CapsuleShape3D
	cap.height = move_toward(cap.height, crouch_height if crouching else stand_height, delta * 3.0)
	collision.position.y = cap.height * 0.5
	_eye = move_toward(_eye, crouch_eye if crouching else stand_eye, delta * 2.8)


func _can_stand() -> bool:
	var params := PhysicsShapeQueryParameters3D.new()
	var shape := CapsuleShape3D.new()
	shape.radius = 0.28
	shape.height = stand_height - 0.06
	params.shape = shape
	params.transform = Transform3D(Basis(), global_position + Vector3.UP * (stand_height * 0.5 + 0.04))
	params.exclude = [get_rid()]
	params.collision_mask = Game.LAYER_WORLD
	return get_world_3d().direct_space_state.intersect_shape(params, 1).is_empty()


func _update_steps(delta: float) -> void:
	var hspeed := horizontal_speed()
	if is_on_floor() and hspeed > 0.15:
		var stride := lerpf(0.62, 1.45, clampf((hspeed - 1.0) / 4.4, 0.0, 1.0)) * (0.75 if crouching else 1.0)
		var before := floorf(stride_phase)
		stride_phase += hspeed * delta / stride
		if floorf(stride_phase) != before:
			_footstep(hspeed)
	else:
		# Settle the stride when standing still so the bob doesn't freeze mid-step.
		var base := floorf(stride_phase)
		var frac := stride_phase - base
		stride_phase = base + move_toward(frac, 0.0 if frac < 0.5 else 0.999, delta * 2.0)


func _footstep(hspeed: float, extra_db := 0.0) -> void:
	var surface := surface_below()
	var running := hspeed > 3.0
	var key := "footsteps/%s_%s" % [surface, "run" if running else "walk"]
	if not SoundLib.has_sound(key):
		key = "footsteps/cobble_%s" % ("run" if running else "walk")
	var pace_t := clampf(hspeed / 1.8, 0.0, 1.0)
	var vol := lerpf(-7.0, 3.0, pace_t) + (4.0 if running else 0.0) - (6.0 if crouching else 0.0) + extra_db
	SoundLib.play_3d(key, global_position + Vector3.UP * 0.05, vol, 40.0, 0.06, 2.0)
	# Loudness for AI, in dB SPL at 1 m: a creep is about 38, a normal walk about 58, a sprint on cobbles about 75.
	var loud := lerpf(38.0, 58.0, pace_t) + (13.0 if running else 0.0) - (8.0 if crouching else 0.0) \
		+ float(SURFACE_LOUDNESS.get(surface, 0.0)) + extra_db
	Game.emit_noise(global_position, loud, self)


func _on_land(fall_speed: float) -> void:
	if fall_speed > 2.2:
		_landing_dip = clampf(fall_speed * 0.018, 0.0, 0.12)
		_footstep(4.0, clampf((fall_speed - 2.0) * 2.0, 0.0, 10.0))


func surface_below() -> String:
	var from := global_position + Vector3.UP * 0.3
	var q := PhysicsRayQueryParameters3D.create(from, from + Vector3.DOWN * 0.8, Game.LAYER_WORLD, [get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return "mud"
	return ImpactFX.surface_of(hit.collider, hit.position)


func _update_lean_clearance() -> void:
	if absf(lean) < 0.01:
		_lean_clearance = 1.0
		return
	var side := global_basis.x * signf(lean)
	var from := head.global_position
	var reach := lean_max_offset + 0.22
	var q := PhysicsRayQueryParameters3D.create(from, from + side * reach, Game.LAYER_WORLD, [get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	var target := 1.0
	if not hit.is_empty():
		target = clampf((from.distance_to(hit.position) - 0.22) / lean_max_offset, 0.0, 1.0)
	_lean_clearance = minf(target, move_toward(_lean_clearance, target, 0.1))


# --- presentation ------------------------------------------------------------------------------

func _process(delta: float) -> void:
	_recoil = _recoil.lerp(Vector2.ZERO, 1.0 - exp(-_recoil_recovery * delta))
	if not dead:
		_update_interaction(delta)
		_update_noticing(delta)

	# Breathing sway: always slightly there, much worse when winded, and strongest while aiming.
	var t := Time.get_ticks_msec() / 1000.0
	var rate := 1.0 + exhaustion * 1.6
	var amp := deg_to_rad(lerpf(0.1, 0.85, exhaustion)) * (1.0 if is_aiming() else 0.3)
	var target_sway := Vector2(
		sin(t * 0.83 * rate) * 0.6 + sin(t * 2.1 * rate) * 0.15,
		sin(t * 1.66 * rate + 1.0) * 0.5 + sin(t * 0.61) * 0.3) * amp
	_aim_sway = _aim_sway.lerp(target_sway, 1.0 - exp(-6.0 * delta))

	rotation.y = yaw
	head.rotation.x = pitch
	camera.rotation = Vector3(_recoil.y + _aim_sway.y, _recoil.x + _aim_sway.x, 0.0)

	# Lean: shift sideways and roll, limited by walls.
	var lean_input := 0.0
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and not sprinting:
		lean_input = Input.get_action_strength("lean_right") - Input.get_action_strength("lean_left")
	lean = move_toward(lean, lean_input, delta * 3.5)
	lean_pivot.position = Vector3(lean * lean_max_offset * _lean_clearance, -absf(lean) * 0.06, 0.0)
	lean_pivot.rotation.z = -lean * deg_to_rad(lean_max_roll_deg)

	# Head bob: highest mid-stride, swaying side to side every other step.
	var amt := clampf(horizontal_speed() / 1.6, 0.0, 1.0) * (1.0 if is_on_floor() else 0.0)
	var ph := stride_phase * PI
	var strength := 1.7 if sprinting else 1.0
	var bob_y := (absf(sin(ph)) - 0.5) * 0.028 * amt * strength
	var bob_x := sin(ph) * 0.012 * amt * strength
	_landing_dip = move_toward(_landing_dip, 0.0, delta * 0.5)
	head.position = Vector3(bob_x, _eye + bob_y - _landing_dip, 0.0)
	if dead:
		# Collapse: the view drops to the cobbles and rolls.
		_eye = move_toward(_eye, 0.22, delta * 2.2)
		lean_pivot.rotation.z = move_toward(lean_pivot.rotation.z, deg_to_rad(72.0), delta * 1.6)
		head.position = Vector3(0, _eye, 0)

	# Body sounds.
	_breath_calm.volume_db = linear_to_db(maxf((1.0 - exhaustion) * 0.3, 0.0001)) - 6.0 + SoundLib.gain("player/breath_calm_loop")
	_breath_hard.volume_db = linear_to_db(maxf(exhaustion, 0.0001)) + SoundLib.gain("player/breath_exhausted_loop")
	_heart.volume_db = linear_to_db(maxf(exhaustion * 0.8, 0.0001)) - 2.0 + SoundLib.gain("player/heartbeat_loop")


# --- debug harness -----------------------------------------------------------------------------

func debug_place(pos: Vector3, yaw_deg: float, pitch_deg: float) -> void:
	global_position = pos
	velocity = Vector3.ZERO
	yaw = deg_to_rad(yaw_deg)
	pitch = deg_to_rad(pitch_deg)
	rotation.y = yaw


func debug_fire() -> void:
	if firearm:
		firearm.debug_fire()
