class_name Instruments
extends Control
## Hold Tab: the left wrist comes up with the watch, and the right hand brings out a brass pocket compass.
## The watch shows game time; the compass card swings and settles to magnetic north (+Z is north here).
## In the dark the dials are hard to read, but the luminous dots still glow.

var player: Node3D
var _show := 0.0
var _card := 0.0          # compass card rotation, radians
var _card_vel := 0.0
var _used := false
var _tick_t := 0.0
var _font: SystemFont
## Screenshot harness: hold them up without the key.
var force := false
signal first_used


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_font = SystemFont.new()
	_font.font_names = PackedStringArray(["Georgia", "Times New Roman", "serif"])


func heading_deg() -> float:
	if player == null:
		return 0.0
	var cam := get_viewport().get_camera_3d()
	var fwd := -cam.global_basis.z if cam else -player.global_basis.z
	return fposmod(rad_to_deg(atan2(fwd.x, fwd.z)), 360.0)


func is_shown() -> bool:
	return _show > 0.5


func _process(delta: float) -> void:
	var want := force or (Input.is_action_pressed("tools") and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED and not get_tree().paused)
	if want and not _used:
		_used = true
		first_used.emit()
	if Input.is_action_just_pressed("tools") and player and player.has_method("note") and Game.clock_minutes >= Game.CURFEW_START - 30 \
			and not Game.curfew_active():
		player.note("Curfew soon.", 2.0)
	_show = move_toward(_show, 1.0 if want else 0.0, delta / (0.28 if want else 0.2))
	# The card is a damped pendulum chasing north. Turning quickly sets it swinging.
	var target := deg_to_rad(heading_deg())
	var err := wrapf(target - _card, -PI, PI)
	_card_vel += (err * 26.0 - _card_vel * 5.5) * delta
	_card += _card_vel * delta
	_tick_t += delta
	visible = _show > 0.001
	if visible:
		queue_redraw()


func _light() -> float:
	return clampf(Visibility.ambient * 2.2 + 0.25, 0.25, 1.0)


func _draw() -> void:
	var s := smoothstep(0.0, 1.0, _show)
	var vp := get_viewport_rect().size
	var k := vp.y / 1080.0
	var lift := (1.0 - s) * 420.0 * k
	_draw_watch(Vector2(vp.x * 0.36, vp.y - 210.0 * k + lift), 118.0 * k, _light())
	_draw_compass(Vector2(vp.x * 0.64, vp.y - 200.0 * k + lift), 140.0 * k, _light())


func _draw_watch(c: Vector2, r: float, light: float) -> void:
	var tint := Color(light, light * 0.97, light * 0.92)
	# The forearm comes up from the bottom-left corner: wool coat sleeve, then the wrist with the strap across it.
	var ang := deg_to_rad(-38.0)
	draw_set_transform(c, ang, Vector2.ONE)
	var sleeve := Color(0.13, 0.11, 0.1) * tint
	draw_colored_polygon(PackedVector2Array([Vector2(-r * 6.0, -r * 1.9), Vector2(-r * 1.6, -r * 1.25), Vector2(-r * 1.5, r * 1.25),
		Vector2(-r * 6.0, r * 2.0)]), sleeve)
	draw_colored_polygon(PackedVector2Array([Vector2(-r * 1.7, -r * 1.3), Vector2(-r * 1.35, -r * 1.32), Vector2(-r * 1.3, r * 1.32),
		Vector2(-r * 1.65, r * 1.3)]), Color(0.17, 0.14, 0.12) * tint)
	draw_colored_polygon(PackedVector2Array([Vector2(-r * 1.4, -r * 0.95), Vector2(r * 1.6, -r * 0.85), Vector2(r * 1.7, r * 0.85),
		Vector2(-r * 1.4, r * 0.95)]), Color(0.36, 0.27, 0.21) * tint)
	draw_colored_polygon(PackedVector2Array([Vector2(r * 1.5, -r * 0.95), Vector2(r * 2.6, -r * 0.8), Vector2(r * 2.8, r * 0.75),
		Vector2(r * 1.6, r * 0.95)]), Color(0.1, 0.08, 0.07) * tint)
	var strap := Color(0.24, 0.14, 0.07) * tint
	draw_rect(Rect2(-r * 0.42, -r * 1.02, r * 0.84, r * 2.04), strap)
	draw_line(Vector2(-r * 0.34, -r * 1.0), Vector2(-r * 0.34, r * 1.0), Color(0.15, 0.09, 0.05) * tint, 1.0)
	draw_line(Vector2(r * 0.34, -r * 1.0), Vector2(r * 0.34, r * 1.0), Color(0.15, 0.09, 0.05) * tint, 1.0)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	# Case, bezel and crown.
	draw_circle(c + Vector2(r * 0.98, 0).rotated(deg_to_rad(-18.0)), r * 0.13, Color(0.5, 0.48, 0.44) * tint)
	draw_circle(c, r * 1.07, Color(0.2, 0.19, 0.18) * tint)
	draw_circle(c, r * 1.02, Color(0.62, 0.6, 0.56) * tint)
	draw_circle(c, r * 0.93, Color(0.36, 0.35, 0.33) * tint)
	# Dial: cream, aged.
	draw_circle(c, r * 0.9, Color(0.86, 0.82, 0.7) * tint)
	draw_circle(c + Vector2(-r * 0.25, -r * 0.3), r * 0.5, Color(1, 1, 1, 0.05 * light))
	for i in 60:
		var a := TAU * i / 60.0
		var d := Vector2(sin(a), -cos(a))
		var big := i % 5 == 0
		draw_line(c + d * r * (0.74 if big else 0.8), c + d * r * 0.86, Color(0.08, 0.07, 0.06) * tint, 2.4 if big else 1.0)
	var fs := int(r * 0.22)
	for n: int in [12, 3, 6, 9]:
		var a2 := TAU * n / 12.0
		var p := c + Vector2(sin(a2), -cos(a2)) * r * 0.58
		var t := str(n)
		var sz := _font.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs)
		draw_string(_font, p + Vector2(-sz.x * 0.5, sz.y * 0.32), t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0.08, 0.07, 0.06) * tint)
	# Radium dots: they glow regardless of the light.
	for i in 12:
		var a3 := TAU * i / 12.0
		draw_circle(c + Vector2(sin(a3), -cos(a3)) * r * 0.7, r * 0.035, Color(0.55, 0.85, 0.45, 0.35 + 0.4 * (1.0 - light)))
	# Hands.
	var m := Game.clock_minutes
	var hour_a := TAU * fposmod(m, 720.0) / 720.0
	var min_a := TAU * fposmod(m, 60.0) / 60.0
	var sec_a := TAU * floorf(fposmod(_tick_t, 60.0)) / 60.0
	_hand(c, hour_a, r * 0.46, r * 0.075, Color(0.06, 0.05, 0.05) * tint)
	_hand(c, min_a, r * 0.72, r * 0.05, Color(0.06, 0.05, 0.05) * tint)
	var sc := c + Vector2(0, r * 0.42)
	draw_arc(sc, r * 0.17, 0, TAU, 32, Color(0.2, 0.18, 0.15) * tint, 1.0)
	draw_line(sc, sc + Vector2(sin(sec_a), -cos(sec_a)) * r * 0.15, Color(0.5, 0.1, 0.06) * tint, 1.2)
	draw_circle(c, r * 0.05, Color(0.06, 0.05, 0.05) * tint)
	# Glass sheen.
	draw_arc(c, r * 0.84, deg_to_rad(200.0), deg_to_rad(260.0), 16, Color(1, 1, 1, 0.12 * light), r * 0.05)


func _hand(c: Vector2, a: float, length: float, width: float, col: Color) -> void:
	var d := Vector2(sin(a), -cos(a))
	var n := Vector2(-d.y, d.x)
	draw_colored_polygon(PackedVector2Array([c - d * length * 0.15 + n * width * 0.5, c + d * length * 0.7 + n * width,
		c + d * length, c + d * length * 0.7 - n * width, c - d * length * 0.15 - n * width * 0.5]), col)
	draw_circle(c + d * length * 0.72, width * 0.55, Color(0.55, 0.85, 0.45, 0.5))


func _draw_compass(c: Vector2, r: float, light: float) -> void:
	var tint := Color(light, light * 0.96, light * 0.88)
	# Held in a gloved hand, tilted towards the eye, so the round case reads as an ellipse.
	var squash := Vector2(1.0, 0.72)
	# The gloved hand under it, wrist coming up from the bottom-right.
	var glove := Color(0.11, 0.08, 0.06) * tint
	draw_set_transform(c, deg_to_rad(20.0), Vector2.ONE)
	draw_colored_polygon(PackedVector2Array([Vector2(-r * 0.7, r * 0.4), Vector2(r * 0.9, r * 0.3), Vector2(r * 1.6, r * 3.4),
		Vector2(-r * 0.2, r * 3.6)]), Color(0.13, 0.11, 0.1) * tint)
	draw_colored_polygon(PackedVector2Array([Vector2(-r * 1.0, r * 0.1), Vector2(r * 1.05, r * 0.05), Vector2(r * 0.95, r * 1.0),
		Vector2(-r * 0.75, r * 1.05)]), glove)
	draw_set_transform(c, 0.0, squash)
	draw_circle(Vector2(0, r * 0.12), r * 1.12, Color(0.05, 0.04, 0.03, 0.8))
	draw_circle(Vector2.ZERO, r * 1.1, Color(0.42, 0.32, 0.14) * tint)
	draw_circle(Vector2.ZERO, r * 1.03, Color(0.66, 0.52, 0.24) * tint)
	draw_circle(Vector2.ZERO, r * 0.95, Color(0.3, 0.23, 0.1) * tint)
	draw_circle(Vector2.ZERO, r * 0.9, Color(0.1, 0.09, 0.08) * tint)
	# The card rotates with the needle: north stays north while you turn.
	var rot := _card
	var fs := int(r * 0.2)
	for i in 72:
		var a := TAU * i / 72.0 - rot
		var d := Vector2(sin(a), -cos(a))
		var big := i % 9 == 0
		draw_line(d * r * (0.7 if big else 0.78), d * r * 0.86, Color(0.82, 0.78, 0.66) * tint, 2.0 if big else 1.0)
	for pair in [["N", 0.0], ["E", 90.0], ["S", 180.0], ["W", 270.0]]:
		var a2 := deg_to_rad(float(pair[1])) - rot
		var p := Vector2(sin(a2), -cos(a2)) * r * 0.55
		var t: String = pair[0]
		var sz := _font.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs)
		var col := Color(0.85, 0.3, 0.2) if t == "N" else Color(0.85, 0.8, 0.68)
		draw_string(_font, p + Vector2(-sz.x * 0.5, sz.y * 0.32), t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, col * tint)
	# Needle: red end north, luminous tip.
	var nd := Vector2(sin(-rot), -cos(-rot))
	var nn := Vector2(-nd.y, nd.x)
	draw_colored_polygon(PackedVector2Array([nd * r * 0.42, nn * r * 0.06, -nn * r * 0.06]), Color(0.75, 0.16, 0.1) * tint)
	draw_colored_polygon(PackedVector2Array([-nd * r * 0.42, nn * r * 0.06, -nn * r * 0.06]), Color(0.78, 0.76, 0.7) * tint)
	draw_circle(nd * r * 0.36, r * 0.03, Color(0.55, 0.85, 0.45, 0.35 + 0.45 * (1.0 - light)))
	draw_circle(Vector2.ZERO, r * 0.05, Color(0.66, 0.52, 0.24) * tint)
	# Lubber line: the way you're facing.
	draw_line(Vector2(0, -r * 0.9), Vector2(0, -r * 0.7), Color(0.55, 0.85, 0.45, 0.6), 3.0)
	draw_arc(Vector2.ZERO, r * 0.86, deg_to_rad(205.0), deg_to_rad(250.0), 16, Color(1, 1, 1, 0.1 * light), r * 0.05)
	# Fingers curled round the rim at the front, and a thumb at the side.
	for f in 4:
		var fx := -r * 0.62 + f * r * 0.36
		var fy := r * 0.98 - absf(f - 1.5) * r * 0.07
		draw_set_transform(c + Vector2(fx, fy * squash.y), deg_to_rad(-6.0 + f * 4.0), Vector2.ONE)
		draw_colored_polygon(PackedVector2Array([Vector2(-r * 0.15, r * 0.25), Vector2(-r * 0.16, -r * 0.08), Vector2(-r * 0.08, -r * 0.18),
			Vector2(r * 0.08, -r * 0.18), Vector2(r * 0.16, -r * 0.08), Vector2(r * 0.15, r * 0.25)]), glove)
	draw_set_transform(c + Vector2(-r * 1.06, r * 0.1), deg_to_rad(-25.0), Vector2.ONE)
	draw_colored_polygon(PackedVector2Array([Vector2(-r * 0.14, r * 0.55), Vector2(-r * 0.12, -r * 0.18), Vector2(0, -r * 0.27),
		Vector2(r * 0.12, -r * 0.18), Vector2(r * 0.14, r * 0.55)]), glove)
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
