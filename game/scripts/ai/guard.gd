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

enum State { PATROL, CURIOUS, SUSPICIOUS, SEARCH, ALERTED, DEAD, CHALLENGE, INSPECT }

const STATE_NAMES := ["patrol", "curious", "suspicious", "search", "alerted", "dead", "challenge", "inspect"]

## What German soldiers shout, with translations. [german, english]. Placeholder text until voice acting exists.
const BARKS := {
	"curious": [["Hm?", "Hm?"], ["Wer da?", "Who's there?"], ["Was war das?", "What was that?"]],
	"suspicious": [["Hallo? Ist da jemand?", "Hello? Is someone there?"], ["Ich seh' mal nach.", "I'll take a look."]],
	"suspicious_seen": [["Sie da! Was machen Sie da?", "You there! What are you doing?"], ["Moment mal...", "Wait a moment..."]],
	"search": [["Da drüben!", "Over there!"], ["Wo ist er hin?", "Where did he go?"], ["Ausschwärmen!", "Spread out!"]],
	"alerted": [["Halt! Stehenbleiben!", "Halt! Stand still!"], ["Alarm! Alarm!", "Alarm! Alarm!"], ["Da ist er!", "There he is!"]],
	"calm": [["Nichts. Wahrscheinlich eine Katze.", "Nothing. Probably a cat."], ["Hab' mich wohl geirrt.", "Must have been mistaken."]],
	"body": [["Mein Gott... Alarm!", "My God... Alarm!"], ["Hier liegt einer!", "There's a man down here!"]],
	"challenge": [["Halt! Ausweis, bitte.", "Halt! Papers, please."], ["Halt! Papiere!", "Halt! Papers!"]],
	"inspect": [["Zeigen Sie mal her.", "Let's have a look."]],
	"pass": [["Gut. Weitergehen.", "Fine. Move along."]],
	"no_pass": [["Kein Passierschein für die Sperrzone. Zurück!", "No pass for the restricted zone. Go back!"]],
	"closed": [["Heute Nacht kommt hier keiner durch. Alarm. Zurück!", "Nobody gets through tonight. There's an alert. Go back!"]],
	"where": [["Wohin wollen Sie?", "Where are you going?"]],
	"pass_q": [["Und Ihr Passierschein für die Zone?", "And your pass for the zone?"]],
	"parole": [["Halt! Parole?", "Halt! Password?"]],
	"liar": [["Das ist der Schein von Guégans Schreiber! Sie lügen! Hände hoch!", "That's Guégan's clerk's pass! You're lying! Hands up!"]],
	"parole_ok": [["Gut. Weiter, Kamerad.", "Good. Carry on, mate."]],
	"parole_bad": [["Falsche Parole! Stehenbleiben!", "Wrong password! Stand still!"]],
	"parole_forgot": [["Vergessen? Dann bleiben Sie draußen, bis Ihr Unteroffizier Sie holt.", "Forgot it? Then you stay out until your sergeant comes for you."]],
	"silent": [["Na? Hat's Ihnen die Sprache verschlagen?", "Well? Cat got your tongue?"]],
	"curfew": [["Sperrstunde! Was machen Sie hier draußen?", "Curfew! What are you doing out here?"]],
	"wounded": [["Was ist mit Ihnen passiert? Mitkommen!", "What happened to you? Come with me!"]],
	"warning": [["Halt! Oder ich schieße!", "Halt! Or I shoot!"]],
	"phone": [["Posten Nord an Kommandantur! Alarm!", "North post to HQ! Alarm!"]],
	"phone_ok": [["Jawohl. Verstärkung ist unterwegs.", "Understood. Reinforcements are on the way."]],
	"phone_dead": [["Die Leitung ist tot! Verdammt!", "The line's dead! Damn it!"]],
	"greet": [["'n Abend, Kamerad.", "Evening, mate."], ["Na, Matrose? Auch noch unterwegs?", "Out late too, sailor?"]],
	"unmasked": [["Moment... Sie sind kein Matrose! Halt!", "Wait... you're no sailor! Halt!"]],
	"greet_army": [["'n Abend, Kamerad.", "Evening, mate."], ["Na? Auch Wache gehabt?", "You been on watch too?"],
		["Kalt heute, was?", "Cold tonight, eh?"]],
	"unmasked_army": [["Moment... welche Einheit? Sie sind nicht von uns! Halt!", "Wait... what unit? You're not one of ours! Halt!"]],
}

## Small talk at the checkpoint, [sentry line, patrol reply]. Some of it is useful to an eavesdropper.
## Tonight's password for anyone in uniform after dark at the harbour checkpoint.
const PAROLE := "Seeadler"
const CHATS := [
	[["Die Leitung zum Hafen spinnt schon wieder.", "The line to the harbour's playing up again."],
	 ["Solange sie bis zur Kommandantur geht, ist mir das egal.", "As long as it reaches HQ, I don't care."],
	 "The checkpoint phone line runs to HQ. Cut it and the sentry can't call."],
	[["Wie war die Parole heute Nacht nochmal?", "What was tonight's password again?"],
	 ["Seeadler. Und frag nicht nochmal, sonst lass ich dich draußen stehen.", "Seeadler. Don't ask again or I'll leave you standing outside."],
	 "Tonight's password at the checkpoint, for anyone in uniform: SEEADLER."],
	[["Halb acht, Zigarette beim Café?", "Half seven, a smoke by the café?"],
	 ["Wie jeden Abend. Bis viertel vor acht.", "Same as every night. Till quarter to eight."],
	 "The street patrol stops for a cigarette outside the café from 19:30 to about 19:45."],
	[["Um zehn werd' ich abgelöst. Bis Müller vom Hafen hochkommt, steht der Posten leer.", "I'm relieved at ten. Till Müller comes up from the harbour, the post stands empty."],
	 ["Lass das bloß nicht den Leutnant hören.", "Don't let the lieutenant hear that."],
	 "At 22:00 the checkpoint sentry walks down to the harbour for his relief. The post is empty for a few minutes."],
	[["Guégan hat seine Tasche schon wieder hinterm Café liegen lassen.", "Guégan's left his satchel behind the café again."],
	 ["Der säuft sich noch um seinen Posten. Mit Passierschein und allem.", "He'll drink himself out of his job. Pass and all."]],
	[["Hast du die Mäntel der Marine auf der Leine gesehen? Hinter den Häusern.", "Seen the navy coats on the washing line? Behind the houses."],
	 ["Bei dem Wetter werden die nie trocken.", "In this weather they'll never dry."]],
	[["Am Bach kommt man an der Furt fast trockenen Fußes rüber.", "You can cross the stream at the ford with nearly dry feet."],
	 ["Da unten patrouilliert keiner. Zu nass.", "Nobody patrols down there. Too wet."]],
	[["Bei dem Regen hört man keinen kommen.", "In this rain you can't hear anyone coming."],
	 ["Deshalb schaust du ja auch hin.", "That's why you keep your eyes open."]],
	[["Noch drei Stunden bis zur Ablösung.", "Three more hours until we're relieved."],
	 ["Und dann Sperrstunde. Dann schießen wir wenigstens auf was.", "Then curfew. At least then we get to shoot at something."]],
]
static var _chat_index := 0
## The town's alert level tonight: 0 calm, 1 local (shots heard), 2 town (a body, an intruder seen for what he
## is), 3 regional (a call got through to HQ). It only ever goes up.
static var town_alert := 0
## Seconds a turned-back civilian has to leave the restricted zone before the sentry treats them as hostile.
const TURN_BACK_GRACE := 8.0

## Barks that are shouted loud enough for other soldiers to hear and come.
const LOUD_BARKS := ["alerted", "body", "search", "warning", "challenge"]
const FELDGRAU := Color(0.29, 0.31, 0.27)

@export var patrol_points: PackedVector3Array = PackedVector3Array()
## Routines by the clock: [{"from": minutes, "to": minutes, "pos": Vector3, "yaw": degrees}]. While one is on, a
## calm guard goes there and stays, then goes back to his rounds.
var schedule: Array = []
## Asleep in his bed: blind, hard of hearing, and helpless. Set by a routine with "sleep": true.
var asleep := false
## Oberleutnant Brenner carries the key to the signals-room cabinet on his watch chain.
var carries_key := false
var _answer := -1
var _question := ""
@export var walk_speed := 1.25
@export var run_speed := 4.0
@export var view_distance := 48.0
@export var fov_deg := 120.0
@export var torch_on := true
@export var health := 100.0
@export var rifle_damage := 72.0
## A Kar98k is a bolt action: one aimed shot every couple of seconds at best.
@export var fire_interval := Vector2(2.1, 2.9)
## A checkpoint sentry challenges people for their papers instead of treating the restricted zone as hostile outright.
@export var checkpoint := false
## Where his field telephone is. Vector3.INF means no telephone. When trouble starts and he can't see
## its cause, he runs to it and calls it in, unless someone has cut the line.
@export var phone_position := Vector3.INF
## Which soldier model to wear: "rifleman" or "feldgendarm".
@export var model_variant := "rifleman"
## Set once his body has been gone through, and once his greatcoat has been taken.
var searched := false
var coat_taken := false
var _died_quietly := false
## The approach in front of a checkpoint, where the sentry calls you over.
@export var challenge_zone := AABB()

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
var _shape: CollisionShape3D
var _body_check_t := 0.0
## For bodies: whether another guard has already found this one.
var discovered := false
## For bodies: the player dragging this one, if any.
var dragged_by: Node3D = null
## Checkpoint sentries currently checking the player's papers. While someone is, other soldiers
## leave you to him rather than treating the restricted zone as hostile.
static var _papers_checkers: Array = []
## Shared by all soldiers: a checkpoint's verdict on your papers stands for everyone.
static var _cleared_until := -1.0   # game minute until which your papers have been accepted
static var _grace_until_ms := 0     # wall-clock ms until which a turned-back civilian is let walk away
## The PTT line from this post to headquarters. Shared by everyone on the line.
static var phone_line_ok := true
var _bark_cd := 0.0
var _call := ""          # "", "going", "calling", "done"
var _chat_cd := 20.0
## Each soldier has his own voice.
var _voice_pitch := randf_range(0.9, 1.1)
var _call_t := 0.0
var _turned_away_t := 999.0    # seconds since the player was turned back from this checkpoint
var _warned := false
var _warn_t := 0.0

# Body parts.
var _body: Node3D
var _leg_l: Node3D
var _leg_r: Node3D
var _arm_l: Node3D
var _arm_r: Node3D
var _head: Node3D
var _rifle: Node3D
var _torch: SpotLight3D
## The rigged soldier model, when it exists (otherwise the primitive stand-in is built).
var _model: Node3D
var _anim: AnimationPlayer
var _anim_current := ""
var _torch_mount: Node3D


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
	_shape = cs
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


## The rigged soldier from tools/blender/characters: skinned, animated, with rifle and torch sockets.
func _build_model() -> bool:
	var path := "res://assets/models/characters/soldier_%s.glb" % model_variant
	if not ResourceLoader.exists(path):
		return false
	_body = Node3D.new()
	add_child(_body)
	_model = (load(path) as PackedScene).instantiate()
	_body.add_child(_model)
	_model.rotation.y = PI   # the model faces +Z; a guard looks down -Z
	_anim = _model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if _anim:
		for n: String in ["Idle", "Walk", "Run", "AimRifle", "LookAround"]:
			if _anim.has_animation(n):
				_anim.get_animation(n).loop_mode = Animation.LOOP_LINEAR
		_play("Idle", 0.0)
		_anim.seek(randf() * 3.0, true)
	for gi in _model.find_children("*", "GeometryInstance3D", true, false):
		(gi as GeometryInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	var shoulder := _model.find_child("RifleSocket_Shoulder", true, false) as Node3D
	var rifle_path := "res://assets/models/weapons/kar98k.glb"
	if shoulder and ResourceLoader.exists(rifle_path):
		_rifle = (load(rifle_path) as PackedScene).instantiate()
		shoulder.add_child(_rifle)
	_torch = SpotLight3D.new()
	_torch.light_color = Color(1.0, 0.92, 0.76)
	_torch.light_energy = 3.2
	_torch.spot_range = 24.0
	_torch.spot_angle = 17.0
	_torch.spot_attenuation = 1.2
	_torch.shadow_enabled = true
	_torch.light_volumetric_fog_energy = 2.0
	_torch.rotation_degrees = Vector3(-12, 0, 0)
	_torch.visible = torch_on
	_body.add_child(_torch)
	_torch.position = Vector3(-0.1, 1.32, -0.23)
	_torch_mount = _model.find_child("TorchMount", true, false) as Node3D
	Visibility.register_light(_torch)
	return true


func _play(anim_name: String, blend: float) -> void:
	if _anim == null or _anim_current == anim_name or not _anim.has_animation(anim_name):
		return
	_anim_current = anim_name
	_anim.play(anim_name, blend)


func _build_body() -> void:
	if _build_model():
		return
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
	var gun_out: bool = _player.firearm != null and not _player.firearm.holstered
	if _player.disguise != "":
		# A man in uniform on the street is one of their own, unless he's waving a pistol about or
		# aiming a rifle. Carrying a rifle at the ready is only a little odd.
		if gun_out:
			var rifle: bool = _player.firearm.data.action == "bolt"
			h += 0.25 if rifle and not _player.is_aiming() else 1.0
		if _combat_t < 90.0:
			h += 1.0
		return h
	if gun_out:
		h += 1.0
	elif _player.has_long_gun():
		# A civilian with a Mauser slung on his back.
		h += 1.0
	if _player.crouching:
		h += 0.45
	if _player.sprinting:
		h += 0.45
	if _zone_violation():
		if checkpoint:
			# Turned back: you get a few seconds to walk away before lingering becomes defiance.
			if _warned or (_turned_away_t > TURN_BACK_GRACE and _turned_away_t < 90.0):
				h += 1.0
		elif not _someone_checking_papers() and Time.get_ticks_msec() > _grace_until_ms:
			h += 1.0
	if Game.curfew_active():
		h += 1.0
	if _player.dragging != null:
		h += 1.5
	if _combat_t < 90.0:
		h += 1.0
	return h


## Called by the level on load so one run's paperwork doesn't leak into the next.
static func reset_shared() -> void:
	phone_line_ok = true
	town_alert = 0
	_chat_index = 0
	_papers_checkers.clear()
	_cleared_until = -1.0
	_grace_until_ms = 0


static func _someone_checking_papers() -> bool:
	_papers_checkers = _papers_checkers.filter(func(g: Variant) -> bool: return is_instance_valid(g))
	return not _papers_checkers.is_empty()


func _zone_violation() -> bool:
	return Visibility.in_restricted_zone(_player.global_position) and Game.clock_minutes > _cleared_until


func _player_in_challenge_zone() -> bool:
	return challenge_zone.has_volume() and challenge_zone.has_point(_player.global_position)


## The voice itself: German-flavoured babble from his mouth, short/medium/long to fit the line.
## The subtitle carries the meaning; distance, walls and your hearing shape how it sounds.
func _voice(text: String, shout: bool) -> void:
	var bucket := "s" if text.length() < 18 else ("m" if text.length() < 46 else "l")
	var key := "voice/de_%s_%s" % ["shout" if shout else "talk", bucket]
	if not SoundLib.has_sound(key):
		return
	var p := SoundLib.play_3d(key, _eye_pos(), 4.0 if shout else -6.0, 90.0 if shout else 30.0, 0.04, 6.0 if shout else 2.0)
	p.pitch_scale = _voice_pitch


## Quiet talk shown as a subtitle if the player is close enough to overhear. No noise; it's just talk.
func say(line: Array) -> void:
	if state == State.DEAD or _player == null:
		return
	_voice(line[0], false)
	var d := _player.global_position.distance_to(global_position)
	if d < 22.0 and _player.overlay and _player.overlay.has_method("subtitle"):
		_player.overlay.subtitle(line[0], line[1], Hearing.loss() > 0.4 or d > 15.0)
		_player.overlay.subtitle_t_override(4.5)


## The sentry and a passing patrol pass the time. Eavesdroppers learn things.
func _update_chat(delta: float) -> void:
	if not checkpoint or state != State.PATROL:
		return
	_chat_cd -= delta
	if _chat_cd > 0.0:
		return
	for n in get_tree().get_nodes_in_group("guards"):
		var g := n as Guard
		if g == null or g == self or g.checkpoint or g.state != State.PATROL:
			continue
		if g.global_position.distance_to(global_position) > 8.0:
			continue
		_chat_cd = randf_range(35.0, 55.0)
		var pair: Array = CHATS[_chat_index % CHATS.size()]
		_chat_index += 1
		say(pair[0])
		var other := g
		var intel: String = pair[2] if pair.size() > 2 else ""
		get_tree().create_timer(3.2, false).timeout.connect(func() -> void:
			if is_instance_valid(other):
				other.say(pair[1])
				# Close enough to follow it, and something worth remembering.
				if intel != "" and _player and _player.global_position.distance_to(global_position) < 16.0 and _player.overlay:
					_player.overlay.add_lead(intel))
		return
	_chat_cd = 2.0


## Say something out loud. Loud barks carry, and other soldiers who hear them come to look.
func bark(kind: String) -> void:
	if _bark_cd > 0.0 or state == State.DEAD or _player == null:
		return
	var lines: Array = BARKS.get(kind, [])
	if lines.is_empty():
		return
	_bark_cd = 2.5
	var line: Array = lines[randi() % lines.size()]
	var loud: bool = kind in LOUD_BARKS or kind in ["alerted", "unmasked", "curfew", "wounded", "phone", "phone_dead"]
	_voice(line[0], loud)
	if kind in LOUD_BARKS:
		Game.emit_noise(_eye_pos(), 76.0, self)
	var d := _player.global_position.distance_to(global_position)
	if d < 40.0 and _player.overlay and _player.overlay.has_method("subtitle"):
		_player.overlay.subtitle(line[0], line[1], Hearing.loss() > 0.55 or d > 28.0)


func wants_papers_from(p: Node3D) -> bool:
	return state == State.CHALLENGE and global_position.distance_to(p.global_position) < 2.8


func present_papers(p: Node3D) -> void:
	if state != State.CHALLENGE:
		return
	_enter(State.INSPECT)
	if p is Player:
		(p as Player).busy = 14.0


## He looks at the papers, then asks a question. The answer decides it: the right one gets you through,
## a wrong one is worse than saying nothing.
func _ask(kind: String) -> void:
	_question = kind
	_answer = -1
	if _player == null or _player.overlay == null:
		return
	var opts: Array = []
	var bark_kind := ""
	match kind:
		"where":
			bark_kind = "where"
			opts = ["Au bureau du port. Je travaille pour M. Guégan.", "Chez ma tante, près du quai.", "(Say nothing)"]
		"pass_q":
			bark_kind = "pass_q"
			opts = ["Je l'ai oublié chez moi, monsieur.", "Je suis d'ici. Je n'en ai pas besoin.", "(Say nothing)"]
		"parole":
			bark_kind = "parole"
			opts = ["Seeadler.", "Edelweiss.", "Hab' ich vergessen, Kamerad."]
	get_tree().create_timer(0.9, false).timeout.connect(func() -> void:
		_bark_cd = 0.0
		bark(bark_kind)
		_player.overlay.ask(opts, 9.0, func(i: int) -> void: _answer = i))


func _papers_verdict() -> void:
	if _player.busy > 0.0:
		_player.busy = 0.6
	if _question == "parole":
		_question = ""
		_bark_cd = 0.0
		if _answer == 0:
			bark("parole_ok")
			_cleared_until = Game.clock_minutes + 60.0
			suspicion = 0.0
			_enter(State.PATROL)
		elif _answer == 1:
			bark("parole_bad")
			_player.wear("", 0.0)
			raise_town(2, "unmasked")
			_combat_t = 0.0
			suspicion = 1.3
			_enter(State.ALERTED)
		else:
			bark("parole_forgot")
			_turned_away_t = 0.0
			_grace_until_ms = Time.get_ticks_msec() + int(TURN_BACK_GRACE * 1000.0)
			suspicion = 0.5
			_enter(State.PATROL)
		return
	var q := _question
	_question = ""
	if q == "where" and _answer == 1:
		# The pass is made out to Guégan's clerk. Any other story gives it away.
		_bark_cd = 0.0
		bark("liar")
		_player.papers["zone_pass"] = false
		_combat_t = 0.0
		suspicion = 1.3
		_enter(State.ALERTED)
		return
	if q == "where" and _answer == 2 and randf() < 0.5:
		_bark_cd = 0.0
		bark("silent")
		_player.papers["zone_pass"] = false
		_turned_away_t = 0.0
		_grace_until_ms = Time.get_ticks_msec() + int(TURN_BACK_GRACE * 1000.0)
		suspicion = 0.5
		_enter(State.PATROL)
		return
	_papers_judge(q)


func _papers_judge(q: String) -> void:
	_bark_cd = 0.0
	if town_alert >= 2:
		bark("closed")
		_turned_away_t = 0.0
		_grace_until_ms = Time.get_ticks_msec() + int(TURN_BACK_GRACE * 1000.0)
		suspicion = 0.6
		_enter(State.PATROL)
		return
	if q == "pass_q" and _answer == 1:
		suspicion = 0.7   # a smart answer: he'll remember your face
	if _player.health < 60.0:
		bark("wounded")
		_combat_t = 0.0
		alertness = 1.5
		suspicion = 1.3
		_enter(State.ALERTED)
	elif Game.curfew_active():
		bark("curfew")
		_combat_t = 0.0
		suspicion = 1.3
		_enter(State.ALERTED)
	elif _player.papers.get("zone_pass", false):
		bark("pass")
		_cleared_until = Game.clock_minutes + 30.0
		suspicion = 0.0
		_enter(State.PATROL)
	else:
		bark("no_pass")
		_turned_away_t = 0.0
		_grace_until_ms = Time.get_ticks_msec() + int(TURN_BACK_GRACE * 1000.0)
		suspicion = maxf(suspicion, 0.3)
		_enter(State.PATROL)


func _perceive() -> void:
	_can_see_player = false
	_visibility = 0.0
	if _player == null or _player.dead or Debug.peaceful() or asleep:
		return
	var eye := _eye_pos()
	var chest := _player.global_position + Vector3.UP * (0.6 if _player.crouching else 1.15)
	var head := _player.head.global_position
	var to := chest - eye
	var dist := to.length()
	var light := Visibility.light_level(get_world_3d(), chest, [_player.get_rid()])
	var light_f := clampf(light / 0.5, 0.12, 2.5)
	var effective_range := view_distance * clampf(light_f, 0.25, 1.0)
	if dist > view_distance:
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
	# Skylining: with nothing behind your head but open sky, you're a black cut-out against the glow.
	# It matters most when the ground is dark, so it scales up as the ambient light falls.
	var beyond := head + (head - eye).normalized() * 70.0
	var sky_q := PhysicsRayQueryParameters3D.create(head, beyond, Game.LAYER_WORLD, [get_rid(), _player.get_rid()])
	if space.intersect_ray(sky_q).is_empty():
		light_f = maxf(light_f, 0.45) * lerpf(2.2, 1.3, clampf(Visibility.ambient / 0.25, 0.0, 1.0))
		effective_range = maxf(effective_range, view_distance * 0.7)
	if dist > effective_range:
		_can_see_player = false
		return
	var dist_f := pow(clampf(1.0 - dist / effective_range, 0.0, 1.0), 1.3)
	var angle_f := lerpf(1.0, 0.3, ang / (fov_deg * 0.5))
	var posture_f := 0.55 if _player.crouching else 1.0
	var speed := _player.horizontal_speed()
	var motion_f := 0.45 if speed < 0.2 else (1.6 if speed > 3.0 else 1.0)
	_visibility = light_f * dist_f * angle_f * posture_f * motion_f * (seen_points * 0.5) * (1.0 + alertness)
	if dist < 2.5:
		_visibility = maxf(_visibility, 2.0)
	if _player.disguise != "":
		# Seen clearly up close, the civilian shoes and the wrong face give it away. A good disguise
		# (a clean coat, the right cap) has to be looked at from nearer.
		var q: float = _player.disguise_quality
		if dist < lerpf(6.5, 2.0, q) and light_f > 0.8 and suspicion > 0.45:
			var navy: bool = _player.disguise == "kriegsmarine"
			_player.wear("", 0.0)
			_player.note("He's seen through the coat.", 3.0)
			raise_town(2, "unmasked")
			_bark_cd = 0.0
			bark("unmasked" if navy else "unmasked_army")
			_combat_t = 0.0
			suspicion = 1.3
			_enter(State.ALERTED)
		else:
			_visibility *= 1.0 - 0.6 * _player.disguise_quality


func _on_noise(pos: Vector3, loudness: float, source: Node) -> void:
	if state == State.DEAD or source == self or Debug.peaceful():
		return
	var d := global_position.distance_to(pos)
	var received := loudness + linear_to_db(1.0 / maxf(d, 1.0))
	var q := PhysicsRayQueryParameters3D.create(_eye_pos(), pos + Vector3.UP * 0.3, Game.LAYER_WORLD, [get_rid()])
	if not get_world_3d().direct_space_state.intersect_ray(q).is_empty():
		received -= 14.0
	var perceived := received - Visibility.noise_floor_db
	if asleep:
		# Only a real noise wakes a sleeping man.
		if perceived < 20.0:
			return
		_set_asleep(false)
		_bark_cd = 0.0
		bark("curious")
	if perceived <= 4.0:
		return
	# Hearing gives only a rough location, and the further away the worse it is.
	var err := clampf(d * 0.12, 0.5, 12.0)
	var guess := pos + Vector3(randf_range(-err, err), 0, randf_range(-err, err))
	if loudness >= 110.0:
		# A gunshot or a whistle. Something is wrong; go and find out, fast.
		raise_town(1, "shots")
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
	var prev := state
	state = s
	_state_t = 0.0
	if s == State.CHALLENGE or s == State.INSPECT:
		if not _papers_checkers.has(self):
			_papers_checkers.append(self)
	else:
		_papers_checkers.erase(self)
	match s:
		State.ALERTED:
			_fire_t = randf_range(0.55, 0.95)   # reaction time before the first aimed shot
			bark("curfew" if Game.curfew_active() and prev != State.INSPECT else "alerted")
			_raise_alarm()
		State.SEARCH:
			_wait = randf_range(18.0, 32.0)
			bark("search")
		State.CURIOUS:
			_wait = randf_range(2.5, 4.5)
			bark("curious")
		State.SUSPICIOUS:
			bark("suspicious_seen" if _can_see_player else "suspicious")
		State.PATROL:
			if prev == State.SEARCH or prev == State.SUSPICIOUS:
				bark("calm")
		State.CHALLENGE:
			_warned = false
			_warn_t = 0.0
			bark("challenge")
		State.INSPECT:
			if _question == "parole":
				pass
			elif _player.health < 60.0 or Game.curfew_active() or town_alert >= 2:
				bark("inspect")
				_question = "none"
			else:
				bark("inspect")
				_ask("where" if _player.papers.get("zone_pass", false) else "pass_q")


## Raise the town's alert. The level hears about it and changes the night accordingly.
func raise_town(level: int, reason: String) -> void:
	if level <= town_alert:
		return
	town_alert = level
	get_tree().call_group("level", "on_town_alert", level, reason)


func _raise_alarm() -> void:
	get_tree().call_group("level", "on_alarm")
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

	var in_grace := _turned_away_t < TURN_BACK_GRACE
	if checkpoint and in_grace and _zone_violation() and _turned_away_t > TURN_BACK_GRACE - 2.5 \
			and _turned_away_t - delta <= TURN_BACK_GRACE - 2.5:
		_bark_cd = 0.0
		bark("warning")
	# He remembers turning you back for a minute and just watches rather than asking again.
	if checkpoint and _player.disguise != "" and _can_see_player and state == State.PATROL \
			and global_position.distance_to(_player.global_position) < 9.0 and _bark_cd <= 0.0 and randf() < 0.02:
		bark("greet" if _player.disguise == "kriegsmarine" else "greet_army")
	if checkpoint and _player.disguise != "" and state in [State.PATROL, State.CURIOUS, State.SUSPICIOUS] and not hostile \
			and _can_see_player and _player_in_challenge_zone() \
			and Game.clock_minutes >= 20.0 * 60.0 and Game.clock_minutes > _cleared_until and _turned_away_t > 30.0 \
			and global_position.distance_to(_player.global_position) < 7.0:
		_question = "parole"
		_enter(State.INSPECT)
		_ask("parole")
		if _player.busy < 1.0:
			_player.busy = 11.0
	if checkpoint and _player.disguise == "" and _turned_away_t > 60.0 and state in [State.PATROL, State.CURIOUS, State.SUSPICIOUS] \
			and _can_see_player and not hostile and (_player_in_challenge_zone() or _zone_violation()):
		_enter(State.CHALLENGE)

	match state:
		State.CHALLENGE:
			if hostile and suspicion >= 1.0:
				_enter(State.ALERTED)
			elif _zone_violation() and global_position.distance_to(_player.global_position) > 3.0 and _state_t > 2.0:
				if not _warned:
					_warned = true
					_bark_cd = 0.0
					bark("warning")
				_warn_t += delta
				if _warn_t > 2.5:
					suspicion = 1.3
					_enter(State.ALERTED)
			elif not _player_in_challenge_zone() and not _zone_violation() and _state_t > 3.0:
				_turned_away_t = 0.0
				_enter(State.PATROL)
			elif fmod(_state_t, 9.0) < delta and _state_t > 1.0:
				_bark_cd = 0.0
				bark("challenge")
		State.INSPECT:
			# A plain look at the papers takes a few seconds; a question waits for its answer.
			var waiting := _question != "" and _question != "none" and _answer < 0 and _state_t < 11.0
			if _state_t > 3.5 and not waiting:
				if _question == "none":
					_question = ""
				_papers_verdict()
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


func _set_asleep(on: bool) -> void:
	asleep = on
	if _model:
		# Lying on his back in bed; standing up again when he wakes.
		_model.rotation = Vector3(-PI * 0.5 if on else 0.0, PI, 0.0)
		_model.position = Vector3(0, 0.62, 0.9) if on else Vector3.ZERO
	if _rifle and on:
		_rifle.visible = false
	elif _rifle:
		_rifle.visible = true


func _active_routine() -> Dictionary:
	if town_alert >= 2:
		return {}   # nobody takes a cigarette break with the town on alert
	var m := fposmod(Game.clock_minutes, 1440.0)
	for r: Dictionary in schedule:
		if m >= float(r["from"]) and m < float(r["to"]):
			return r
	return {}


## Is this guard away from his post on a routine right now (for the level and tests)?
func on_routine() -> bool:
	return not _active_routine().is_empty()


func _physics_process(delta: float) -> void:
	if state == State.DEAD:
		_update_death(delta)
		return
	_state_t += delta
	_combat_t += delta
	_update_chat(delta)
	_turned_away_t += delta
	_bark_cd = maxf(_bark_cd - delta, 0.0)
	_whistle_cd = maxf(_whistle_cd - delta, 0.0)
	_perceive_t -= delta
	if _perceive_t <= 0.0:
		_perceive_t = 0.1
		_perceive()
	_body_check_t -= delta
	if _body_check_t <= 0.0:
		_body_check_t = 0.4
		_check_bodies()
	_think(delta)
	if _update_phone_call(delta):
		_animate(delta)
		return

	var desired_speed := 0.0
	var face_dir := Vector3.ZERO
	match state:
		State.PATROL:
			_look_yaw = sin(_state_t * 0.35) * 0.45 if _wait > 0.0 else move_toward(_look_yaw, 0.0, delta)
			var routine := _active_routine()
			if routine.is_empty() and asleep:
				_set_asleep(false)
			if not routine.is_empty():
				# A routine by the clock: a smoke at the café, the walk down for the relief, bed.
				if asleep or _move_toward_point(routine["pos"], walk_speed, delta):
					face_dir = Vector3.FORWARD.rotated(Vector3.UP, deg_to_rad(float(routine.get("yaw", 0.0))))
					_look_yaw = sin(_state_t * 0.25) * 0.3 if not asleep else 0.0
					if routine.get("sleep", false) and not asleep:
						_set_asleep(true)
			elif patrol_points.is_empty():
				pass
			elif _wait > 0.0:
				_wait -= delta
			elif _move_toward_point(patrol_points[_patrol_i], walk_speed * (1.35 if town_alert >= 2 else 1.0), delta):
				_patrol_i = (_patrol_i + 1) % patrol_points.size()
				_wait = randf_range(3.0, 7.0) if patrol_points.size() > 1 else 9999.0
			if patrol_points.size() <= 1 and _wait > 0.0:
				face_dir = Vector3.FORWARD.rotated(Vector3.UP, _home_yaw)
			if checkpoint and _turned_away_t < TURN_BACK_GRACE + 4.0 and _can_see_player:
				face_dir = _player.global_position - global_position   # watching you go
		State.CURIOUS:
			_look_yaw = move_toward(_look_yaw, 0.0, delta * 2.0)
			face_dir = target_pos - global_position
		State.CHALLENGE, State.INSPECT:
			_look_yaw = move_toward(_look_yaw, 0.0, delta * 2.0)
			face_dir = _player.global_position - global_position
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
	_update_footsteps(delta)


var _stride := 0.0


## Boots on the ground, placed in the world so you can hear which way he is and roughly how far: heavier
## and quicker when he runs, the surface under him, and the clink of kit with every other step.
func _update_footsteps(_delta: float) -> void:
	var hs := Vector2(velocity.x, velocity.z).length()
	if hs < 0.3 or not is_on_floor():
		return
	var running := hs > 2.6
	_stride += hs * _delta
	var stride_len := 1.15 if running else 0.78
	if _stride < stride_len:
		return
	_stride -= stride_len
	var surface := "cobble"
	var q := PhysicsRayQueryParameters3D.create(global_position + Vector3.UP * 0.3, global_position + Vector3.DOWN * 0.6, Game.LAYER_WORLD, [get_rid()])
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	if not hit.is_empty():
		surface = ImpactFX.surface_of(hit.collider, hit.position)
	var key := "footsteps/%s_%s" % [surface, "run" if running else "walk"]
	if surface in ["cobble", "stone"] and SoundLib.has_sound("footsteps/npc_hobnail_cobble"):
		key = "footsteps/npc_hobnail_cobble"
	elif not SoundLib.has_sound(key):
		key = "footsteps/cobble_%s" % ("run" if running else "walk")
	# Hobnailed jackboots are louder than the player's shoes.
	SoundLib.play_3d(key, global_position + Vector3.UP * 0.05, 3.0 if running else -1.0, 55.0, 0.07, 2.5)


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
	_play_rifle_report(muzzle)
	Hearing.expose(167.0, _player.camera.global_position.distance_to(muzzle), false)
	Game.emit_noise(muzzle, 167.0, self)
	_flash(muzzle)
	ImpactFX.spawn_muzzle_smoke(get_tree().current_scene, muzzle, dir, Vector3.ZERO)

	var space := get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(eye, eye + shot * 400.0, Game.LAYER_WORLD | Game.LAYER_PLAYER, [get_rid()])
	var hit := space.intersect_ray(q)
	var end: Vector3 = eye + shot * 400.0 if hit.is_empty() else hit.position
	if hit.is_empty() or hit.collider != _player:
		_bullet_snap(eye, end)
	if hit.is_empty():
		return
	if hit.collider == _player:
		var head_h := _player.head.global_position.y
		var dmg := rifle_damage * (5.0 if hit.position.y > head_h - 0.14 else 1.0)
		_player.take_hit(dmg, hit.position, shot, self)
	else:
		ImpactFX.spawn(get_tree().current_scene, hit.position, hit.normal, shot, ImpactFX.surface_of(hit.collider, hit.position))


## The shot as the player hears it: the near report, or a distant thump beyond about 150 m,
## then the bolt being worked. Falls back to a pitched-down pistol shot if the rifle sounds don't exist yet.
func _play_rifle_report(muzzle: Vector3) -> void:
	var d := _player.camera.global_position.distance_to(muzzle)
	if d > 150.0 and SoundLib.has_sound("weapons/rifle_distant"):
		SoundLib.play_3d("weapons/rifle_distant", muzzle, 10.0, 2000.0, 0.04, 60.0)
	elif SoundLib.has_sound("weapons/kar98k_shot"):
		SoundLib.play_3d("weapons/kar98k_shot", muzzle, 6.0, 1200.0, 0.03, 18.0)
	else:
		var bang := SoundLib.play_3d("weapons/p38_shot", muzzle, 6.0, 900.0, 0.03, 18.0)
		bang.pitch_scale = 0.72
	var tail := SoundLib.play_3d("weapons/tail_street", muzzle, 2.0, 900.0, 0.03, 18.0)
	tail.pitch_scale = 0.8
	if SoundLib.has_sound("weapons/kar98k_bolt"):
		get_tree().create_timer(randf_range(0.55, 0.8), false).timeout.connect(func() -> void:
			if state != State.DEAD:
				SoundLib.play_3d("weapons/kar98k_bolt", global_position + Vector3.UP * 1.3, 0.0, 60.0, 0.05, 3.0))


## A miss that passes close to your head cracks past your ear.
func _bullet_snap(from: Vector3, to: Vector3) -> void:
	var head := _player.camera.global_position
	var seg := to - from
	var length := seg.length()
	if length < 0.01:
		return
	var t := clampf((head - from).dot(seg / length), 0.0, length)
	var miss := head.distance_to(from + seg / length * t)
	if miss < 2.5 and t > 3.0:
		var key := "weapons/bullet_snap" if SoundLib.has_sound("weapons/bullet_snap") else "impacts/ricochet"
		SoundLib.play_2d(key, lerpf(4.0, -6.0, miss / 2.5), Game.BUS_WORLD, 0.06)
		Hearing.expose(150.0, maxf(miss, 0.3), false)


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
	# Anything from the collar up is a headshot, and a headshot kills.
	if local_y > 1.42:
		health = 0.0
	else:
		health -= damage
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


func _die(quiet := false) -> void:
	_died_quietly = quiet
	get_tree().call_group("level", "on_guard_died", self, quiet)
	_papers_checkers.erase(self)
	state = State.DEAD
	_state_t = 0.0
	collision_layer = 0
	collision_mask = Game.LAYER_WORLD
	_shape.set_deferred("disabled", true)
	velocity = Vector3.ZERO
	add_to_group("bodies")
	_drop_rifle()
	SoundLib.play_3d("footsteps/cobble_run", global_position, -6.0 if quiet else 6.0, 40.0, 0.1, 3.0)


## The rifle leaves his hands as a real object that clatters to the ground (and can be picked up later).
func _drop_rifle() -> void:
	if _rifle == null or not is_instance_valid(_rifle):
		return
	var rb := RigidBody3D.new()
	rb.name = "DroppedKar98k"
	rb.collision_layer = Game.LAYER_DEBRIS
	rb.collision_mask = Game.LAYER_WORLD
	rb.mass = 4.1
	rb.continuous_cd = true
	rb.set_meta("weapon", "kar98k")
	# Sentries carry five in the magazine; whether one is chambered depends on the man.
	rb.set_meta("rounds", 5 if randf() < 0.7 else 4)
	rb.set_meta("chambered", randf() < 0.6)
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(0.07, 0.14, 1.15) if _model else Vector3(0.07, 1.1, 0.12)
	cs.shape = box
	cs.position = Vector3(0, -0.1, 0)
	rb.add_child(cs)
	var xf := _rifle.global_transform
	get_tree().current_scene.add_child(rb)
	rb.global_transform = xf
	_rifle.get_parent().remove_child(_rifle)
	rb.add_child(_rifle)
	_rifle.transform = Transform3D.IDENTITY
	rb.linear_velocity = -global_basis.z * randf_range(0.3, 1.2) + Vector3.UP * 0.5
	rb.angular_velocity = Vector3(randf_range(-3, 3), randf_range(-2, 2), randf_range(-3, 3))
	rb.add_to_group("dropped_weapons")
	_rifle = null
	rb.contact_monitor = true
	rb.max_contacts_reported = 1
	var clattered := [false]
	rb.body_entered.connect(func(_b: Node) -> void:
		if not clattered[0]:
			clattered[0] = true
			SoundLib.play_3d("impacts/impact_wood", rb.global_position, -2.0, 40.0, 0.1, 2.0)
			Game.emit_noise(rb.global_position, 60.0, null))


func is_dead() -> bool:
	return state == State.DEAD


## What's in his pouches. A rifleman carries rifle clips; a Feldgendarm has his pistol magazines too.
func take_loot() -> Dictionary:
	if searched:
		return {}
	searched = true
	var loot := {"7.92x57": 5 * randi_range(2, 4), "cigarettes": randf() < 0.6, "paybook": true}
	if model_variant == "feldgendarm":
		loot["7.92x57"] = 10
		loot["p38_mag"] = 1
	if carries_key:
		loot["cabinet_key"] = true
	return loot


## His greatcoat and cap. Clean if he was taken quietly, holed and bloody if he was shot.
func take_coat() -> float:
	coat_taken = true
	return 0.85 if _died_quietly else 0.7


## Sent by headquarters after a call: run to the trouble and search.
func dispatch_to(pos: Vector3) -> void:
	target_pos = pos
	alertness = 1.5
	_combat_t = 0.0
	_enter(State.SEARCH)
	_wait = randf_range(60.0, 90.0)


## Returns true while the call is taking over his movement.
func _update_phone_call(delta: float) -> bool:
	if phone_position == Vector3.INF or _call == "done":
		return false
	if _call == "":
		if (state == State.SEARCH or state == State.ALERTED) and not _can_see_player:
			_call = "going"
		else:
			return false
	if _can_see_player and state == State.ALERTED:
		return false   # a threat in front of him comes first
	var to := phone_position - global_position
	to.y = 0.0
	if _call == "going":
		if _move_toward_point(phone_position, run_speed, delta):
			_call = "calling"
			_call_t = 0.0
			_bark_cd = 0.0
			bark("phone")
		_finish_move(delta)
		return true
	# Calling: stand at the box with the handset.
	_call_t += delta
	velocity.x = move_toward(velocity.x, 0.0, delta * 8.0)
	velocity.z = move_toward(velocity.z, 0.0, delta * 8.0)
	if _call_t > 5.0:
		_call = "done"
		_bark_cd = 0.0
		if phone_line_ok:
			bark("phone_ok")
			raise_town(3, "call")
			get_tree().call_group("level", "call_reinforcements", target_pos)
		else:
			bark("phone_dead")
			_whistle_cd = 0.0
			_raise_alarm()
	_finish_move(delta)
	return true


func _finish_move(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= _gravity * delta
	else:
		velocity.y = 0.0
	move_and_slide()


## A takedown is possible from close behind, or when he isn't aware of you at all.
func can_be_taken_down_by(p: Node3D) -> bool:
	if state == State.DEAD or state == State.ALERTED:
		return false
	var to_p := p.global_position - global_position
	to_p.y = 0.0
	if to_p.length() > 1.4:
		return false
	if asleep:
		return true
	var behind := (-global_basis.z).angle_to(to_p.normalized()) > deg_to_rad(105.0)
	return behind or (not _can_see_player and suspicion < 0.5)


## The SOE way: from behind, quick and close. Quiet, but not silent: a scuffle carries a few metres.
func silent_kill(attacker: Node3D) -> void:
	if state == State.DEAD:
		return
	health = 0.0
	if attacker:
		_face(global_position - attacker.global_position, 1.0, 100.0)
	_die(true)
	Game.emit_noise(global_position + Vector3.UP, 50.0, attacker)


## The point at the body's chest, wherever it's lying.
func body_center() -> Vector3:
	return global_position + global_basis.z * 0.9 * clampf(_death_t / 0.8, 0.0, 1.0) + Vector3.UP * 0.25


## Pull the body so its shoulders follow `shoulder_target`, with the head end toward whoever is dragging.
func drag_toward(shoulder_target: Vector3, puller: Vector3, delta: float) -> void:
	var to_puller := puller - global_position
	to_puller.y = 0.0
	if to_puller.length() > 0.1:
		rotation.y = rotate_toward(rotation.y, atan2(to_puller.x, to_puller.z), delta * 3.0)
	var desired := shoulder_target - global_basis.z * 1.4
	desired.y = global_position.y
	global_position = global_position.lerp(desired, 1.0 - exp(-5.0 * delta))


func _check_bodies() -> void:
	if Debug.peaceful():
		return
	var eye := _eye_pos()
	var look := (-global_basis.z).rotated(Vector3.UP, _look_yaw)
	var space := get_world_3d().direct_space_state
	for b in get_tree().get_nodes_in_group("bodies"):
		if b == self or not (b is Guard) or (b as Guard).discovered:
			continue
		var g := b as Guard
		var bp := g.body_center()
		if bp.y < -0.75:
			continue   # under the water
		var to := bp - eye
		var light_f := clampf(Visibility.light_level(get_world_3d(), bp, [g.get_rid()]) / 0.5, 0.12, 2.5)
		# A body on the ground is harder to make out than a man standing up.
		if to.length() > view_distance * clampf(light_f, 0.2, 1.0) * 0.75:
			continue
		if rad_to_deg(look.angle_to(Vector3(to.x, 0, to.z).normalized())) > fov_deg * 0.5:
			continue
		var q := PhysicsRayQueryParameters3D.create(eye, bp, Game.LAYER_WORLD, [get_rid(), g.get_rid()])
		if not space.intersect_ray(q).is_empty():
			continue
		g.discovered = true
		_bark_cd = 0.0
		bark("body")
		raise_town(2, "body")
		target_pos = bp
		alertness = 1.5
		_combat_t = 0.0
		_raise_alarm()
		_enter(State.SEARCH)
		return


func _update_death(delta: float) -> void:
	_death_t += delta
	if _model:
		_play("Death", 0.12)
		if _anim:
			_anim.speed_scale = 1.0
		if dragged_by == null and not is_on_floor():
			velocity.y -= _gravity * delta
			move_and_slide()
		return
	if dragged_by:
		_body.rotation.x = deg_to_rad(84.0)
		_body.position = Vector3(0, 0.12, 0.9)
		return
	var t := clampf(_death_t / 0.8, 0.0, 1.0)
	var e := t * t
	_body.rotation.x = lerpf(0.0, deg_to_rad(84.0), e)
	_body.position.y = lerpf(0.0, 0.12, e)
	_body.position.z = lerpf(0.0, 0.9, e)
	if not is_on_floor():
		velocity.y -= _gravity * delta
		move_and_slide()


# --- animation ---------------------------------------------------------------------------------

func _animate_model(delta: float) -> void:
	var spd := Vector2(velocity.x, velocity.z).length()
	var aiming := state == State.ALERTED and _can_see_player
	var want := "Idle"
	if aiming:
		want = "AimRifle"
	elif spd > 2.6:
		want = "Run"
	elif spd > 0.25:
		want = "Walk"
	elif state == State.SEARCH or state == State.CURIOUS:
		want = "LookAround"
	_play(want, 0.3)
	if _anim:
		if want == "Walk":
			_anim.speed_scale = clampf(spd / 1.3, 0.6, 1.6)
		elif want == "Run":
			_anim.speed_scale = clampf(spd / 4.0, 0.7, 1.4)
		else:
			_anim.speed_scale = 1.0
	# The rifle comes off the shoulder into his hands to aim, and goes back after.
	if _rifle and is_instance_valid(_rifle):
		var socket_name := "RifleSocket_Hands" if aiming else "RifleSocket_Shoulder"
		if _rifle.get_parent() and String(_rifle.get_parent().name) != socket_name:
			var sock := _model.find_child(socket_name, true, false)
			if sock:
				_rifle.reparent(sock, false)
				_rifle.transform = Transform3D.IDENTITY
	if _torch_mount:
		_torch.global_position = _torch_mount.global_position
	_aim_torch(delta)


func _animate(delta: float) -> void:
	if _model:
		_animate_model(delta)
		return
	var spd := Vector2(velocity.x, velocity.z).length()
	_walk_phase += spd * delta * 2.4
	var amt := clampf(spd / 1.3, 0.0, 1.6)
	var swing := sin(_walk_phase) * 0.42 * amt
	_leg_l.rotation.x = swing
	_leg_r.rotation.x = -swing
	_body.position.y = absf(sin(_walk_phase)) * 0.025 * amt
	_head.rotation.y = lerp_angle(_head.rotation.y, _look_yaw, 1.0 - exp(-5.0 * delta))
	if _rifle == null:
		return
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
	_aim_torch(delta)


## The torch points where he's looking, and at you once he's interested.
func _aim_torch(delta: float) -> void:
	var torch_target := 0.0
	if state in [State.CURIOUS, State.SUSPICIOUS, State.ALERTED, State.CHALLENGE, State.INSPECT] and _player:
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
