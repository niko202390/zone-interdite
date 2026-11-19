class_name Player
extends CharacterBody3D
## The first-person body. It's slow and deliberate: the scroll wheel sets walking pace, sprinting costs
## stamina, crouch is a toggle and lean is held. Footsteps depend on the surface and are loud enough for AI to hear.

@export_group("Movement")
## Walking paces in m/s, chosen with the mouse wheel. A careful creep through to a brisk walk.
@export var paces: PackedFloat32Array = PackedFloat32Array([0.55, 0.95, 1.35, 1.75])
@export var start_pace := 2
@export var sprint_speed := 5.4
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
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
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


func note(text: String, seconds := 3.0) -> void:
	if overlay and overlay.has_method("note"):
		overlay.note(text, seconds)


# --- simulation --------------------------------------------------------------------------------

func _physics_process(delta: float) -> void:
	var on_floor := is_on_floor()
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		input = Vector2.ZERO
	var wish := global_basis * Vector3(input.x, 0.0, input.y)
	wish.y = 0.0
	wish = wish.normalized() * minf(input.length(), 1.0)

	sprinting = Input.is_action_pressed("sprint") and input.y < -0.3 and stamina > 0.04 \
		and on_floor and not is_aiming() and input != Vector2.ZERO
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

	var horiz := Vector3(velocity.x, 0.0, velocity.z)
	var k := 1.0 - exp(-(ground_accel if on_floor else air_accel) * delta)
	horiz = horiz.lerp(wish * speed, k)
	velocity.x = horiz.x
	velocity.z = horiz.z

	if not on_floor:
		velocity.y -= _gravity * delta
		_fall_speed = maxf(_fall_speed, -velocity.y)
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
