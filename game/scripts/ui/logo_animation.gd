class_name LogoAnimation
extends Control
## The animated title. A pen writes ZONE INTERDITE in invisible ink. A wartime petrol lighter is flicked open
## and held beneath the paper, and the flame's heat scorches the words into view.
## About 12 seconds; skip() jumps to the end.

signal finished

const W := 1400.0
const H := 560.0
const PAPER := Rect2(50, 40, 1300, 360)
const TEXT := Rect2(100, 170, 1200, 170)
const LENGTH := 12.0

var _t := 0.0
var _done := false
var _font: Font
var _paper: ColorRect
var _label: Label
var _glow: ColorRect
var _glow_mat: ShaderMaterial
var _ink: ShaderMaterial
var _pen: PenDraw
var _lighter: LighterDraw
var _scratch: AudioStreamPlayer
var _flame_snd: AudioStreamPlayer
var _cues := {}
var _reveal := -0.3


func _init(font: Font) -> void:
	_font = font


func _ready() -> void:
	custom_minimum_size = Vector2(W, H)
	size = Vector2(W, H)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	# Behind the paper: the lighter, so its flame and chimney are hidden by the sheet once it's beneath.
	_lighter = LighterDraw.new()
	add_child(_lighter)
	_lighter.position = Vector2(TEXT.position.x - 40.0, PAPER.end.y + 700.0)
	_lighter.visible = false
	_paper = ColorRect.new()
	_paper.position = PAPER.position
	_paper.size = PAPER.size
	_paper.pivot_offset = PAPER.size * 0.5
	_paper.rotation = deg_to_rad(-1.2)
	var pm := ShaderMaterial.new()
	pm.shader = load("res://shaders/paper.gdshader")
	pm.set_shader_parameter("seed", 7.0)
	pm.set_shader_parameter("fold", 0.3)
	pm.set_shader_parameter("ring_pos", Vector2(0.9, 0.2))
	_paper.material = pm
	_paper.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_paper.modulate = Color(0, 0, 0, 1)
	add_child(_paper)
	_label = Label.new()
	_label.text = "ZONE INTERDITE"
	_label.add_theme_font_override("font", _font)
	_label.add_theme_font_size_override("font_size", 132)
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_label.position = TEXT.position
	_label.size = TEXT.size
	_label.pivot_offset = PAPER.size * 0.5 - (TEXT.position - PAPER.position)
	_label.rotation = _paper.rotation
	_ink = ShaderMaterial.new()
	_ink.shader = load("res://shaders/logo_reveal.gdshader")
	_ink.set_shader_parameter("label_size", TEXT.size)
	_label.material = _ink
	_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_label)
	_glow = ColorRect.new()
	_glow.position = PAPER.position
	_glow.size = PAPER.size
	_glow_mat = ShaderMaterial.new()
	_glow_mat.shader = Shader.new()
	_glow_mat.shader.code = """shader_type canvas_item;
render_mode blend_add;
uniform vec2 center = vec2(0.5, 0.75);
uniform float strength = 0.0;
void fragment() {
	vec2 d = (UV - center) * vec2(3.6, 1.0);
	float g = exp(-dot(d, d) * 6.0);
	COLOR = vec4(vec3(1.0, 0.5, 0.17) * g * strength, 1.0);
}"""
	_glow.material = _glow_mat
	_glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_glow)
	_pen = PenDraw.new()
	add_child(_pen)
	_pen.position = Vector2(TEXT.position.x - 120, TEXT.position.y - 260)
	_scratch = _player("ui/pen_scratch_loop", -10.0)
	_flame_snd = _player("ui/flame_loop", -6.0)


func _player(key: String, vol: float) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.stream = SoundLib.pick(key)
	p.volume_db = vol
	add_child(p)
	return p


func _cue(name: String, at: float) -> bool:
	if _t >= at and not _cues.has(name):
		_cues[name] = true
		return true
	return false


func skip() -> void:
	_t = LENGTH


func is_done() -> bool:
	return _done


## Where along the text (0..1) a horizontal position in this control is.
func _text_x(px: float) -> float:
	return (px - TEXT.position.x) / TEXT.size.x


func _process(delta: float) -> void:
	if _done:
		return
	_t += delta
	var t := _t
	# 0-1: fade up on the paper in the dark.
	var dim := clampf(t / 1.0, 0.0, 1.0) * 0.42
	# 1-4.6: the pen writes.
	var write := clampf((t - 1.0) / 3.6, 0.0, 1.0)
	if _cue("scratch_on", 1.0):
		_scratch.play()
	if _cue("scratch_off", 4.6):
		_scratch.stop()
	_ink.set_shader_parameter("write_x", write)
	var nib := Vector2(TEXT.position.x + write * TEXT.size.x, TEXT.position.y + TEXT.size.y * 0.62 + sin(t * 17.0) * 9.0 + sin(t * 5.3) * 6.0)
	if t < 1.0:
		_pen.position = _pen.position.lerp(Vector2(TEXT.position.x, nib.y - 30.0), 1.0 - exp(-delta * 4.0))
	elif t < 4.6:
		_pen.position = nib
	else:
		_pen.position = _pen.position.lerp(Vector2(W + 300.0, -260.0), 1.0 - exp(-delta * 2.5))
	_pen.modulate.a = clampf(1.0 - (t - 4.8) / 0.5, 0.0, 1.0)
	# 5.4: the lighter rises below the paper; 6.1 lid flicked open; 6.5 struck.
	var below := Vector2(TEXT.position.x - 40.0, PAPER.end.y + 160.0)
	var beneath_y := TEXT.position.y + TEXT.size.y * 0.8 + 70.0
	_lighter.visible = t >= 5.3 and t < 11.9
	if t >= 5.4 and t < 7.0:
		_lighter.position = _lighter.position.lerp(below, 1.0 - exp(-delta * 6.0))
	if _cue("open", 6.1):
		SoundLib.play_2d("ui/lighter_open", -2.0, &"Master")
	_lighter.lid = clampf((t - 6.1) / 0.09, 0.0, 1.0) * (1.0 - clampf((t - 11.55) / 0.09, 0.0, 1.0))
	if _cue("strike", 6.45):
		SoundLib.play_2d("ui/lighter_strike", -2.0, &"Master")
	var lit := t >= 6.7 and t < 11.4
	_lighter.flame = move_toward(_lighter.flame, 1.0 if lit else 0.0, delta * 4.0)
	if _cue("flame_on", 6.7):
		_flame_snd.play()
	if _cue("flame_off", 11.4):
		_flame_snd.stop()
	# 7-11: held beneath the sheet and drawn slowly along under the words.
	var sweep := clampf((t - 7.4) / 3.6, 0.0, 1.0)
	if t >= 7.0 and t < 11.0:
		var target := Vector2(TEXT.position.x - 40.0 + sweep * (TEXT.size.x + 80.0), beneath_y + sin(t * 2.3) * 8.0)
		_lighter.position = _lighter.position.lerp(target, 1.0 - exp(-delta * (5.0 if t < 7.4 else 3.0)))
	elif t >= 11.0:
		_lighter.position = _lighter.position.lerp(Vector2(_lighter.position.x, PAPER.end.y + 420.0), 1.0 - exp(-delta * 3.0))
	if _cue("close", 11.55):
		SoundLib.play_2d("ui/lighter_close", -2.0, &"Master")
	var flame_tip := _lighter.position + Vector2(0, -34.0 - 70.0 * _lighter.flame)
	var under_paper := flame_tip.y < PAPER.end.y
	var reveal := _text_x(flame_tip.x) if (t >= 7.0 and under_paper and _lighter.flame > 0.5) else -1.0
	_reveal = maxf(_reveal, reveal)
	_ink.set_shader_parameter("reveal_x", _reveal)
	var flicker := 0.85 + 0.1 * sin(t * 23.0) + 0.05 * sin(t * 41.0)
	_glow_mat.set_shader_parameter("strength", (0.9 * flicker if under_paper else 0.15) * _lighter.flame)
	_glow_mat.set_shader_parameter("center", (flame_tip - PAPER.position) / PAPER.size)
	var warm := _lighter.flame * 0.25
	_paper.modulate = Color(dim + warm, dim + warm * 0.7, dim + warm * 0.4)
	if t >= LENGTH:
		_finish()


func _finish() -> void:
	_done = true
	_ink.set_shader_parameter("write_x", 1.0)
	_ink.set_shader_parameter("reveal_x", 1.3)
	_glow_mat.set_shader_parameter("strength", 0.0)
	_lighter.visible = false
	_pen.visible = false
	_scratch.stop()
	_flame_snd.stop()
	_paper.modulate = Color(0.5, 0.47, 0.42)
	finished.emit()


## A fountain pen: black barrel, gold band, a two-tone nib. The nib tip is at the origin.
class PenDraw:
	extends Node2D

	func _draw() -> void:
		draw_set_transform(Vector2.ZERO, deg_to_rad(-38.0), Vector2.ONE)
		draw_colored_polygon(PackedVector2Array([Vector2(0, 0), Vector2(26, -6), Vector2(30, 0), Vector2(26, 6)]), Color(0.78, 0.68, 0.42))
		draw_line(Vector2(3, 0), Vector2(22, 0), Color(0.2, 0.17, 0.1), 1.2)
		draw_rect(Rect2(28, -7, 16, 14), Color(0.04, 0.04, 0.045))
		draw_rect(Rect2(44, -9, 190, 18), Color(0.06, 0.055, 0.06))
		draw_rect(Rect2(44, -9, 190, 3), Color(0.16, 0.15, 0.16))
		draw_rect(Rect2(150, -9, 8, 18), Color(0.72, 0.6, 0.32))
		draw_rect(Rect2(234, -8, 30, 16), Color(0.05, 0.05, 0.055))


## A WW2-era petrol lighter: black crackle case, brass chimney with vent holes, a hinged lid, and the flame.
## The origin is the top of the case (the hinge line); the chimney and flame rise above it.
class LighterDraw:
	extends Node2D
	var lid := 0.0
	var flame := 0.0
	var _t := 0.0

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()

	func _draw() -> void:
		var case_col := Color(0.075, 0.075, 0.08)
		draw_rect(Rect2(-36, 0, 72, 110), case_col)
		draw_rect(Rect2(-36, 0, 5, 110), Color(0.17, 0.17, 0.18))
		draw_rect(Rect2(-36, 0, 72, 3), Color(0.2, 0.2, 0.21))
		draw_rect(Rect2(-24, -34, 48, 34), Color(0.56, 0.46, 0.25))
		for i in 3:
			for j in 2:
				draw_circle(Vector2(-14 + i * 14, -25 + j * 13), 3.4, Color(0.16, 0.12, 0.07))
		draw_circle(Vector2(18, -12), 8.0, Color(0.42, 0.4, 0.38))
		if flame > 0.02:
			var h := 72.0 * flame * (0.9 + 0.08 * sin(_t * 23.0) + 0.06 * sin(_t * 41.0))
			var sway := sin(_t * 6.7) * 5.0 + sin(_t * 13.1) * 2.0
			var outer := PackedVector2Array([Vector2(-10, -34), Vector2(-12, -34 - h * 0.35), Vector2(-7, -34 - h * 0.72),
				Vector2(sway, -34 - h), Vector2(7, -34 - h * 0.72), Vector2(12, -34 - h * 0.35), Vector2(10, -34)])
			draw_colored_polygon(outer, Color(1.0, 0.5, 0.12, 0.85))
			var inner := PackedVector2Array([Vector2(-5, -34), Vector2(-6, -34 - h * 0.3), Vector2(sway * 0.6, -34 - h * 0.62),
				Vector2(6, -34 - h * 0.3), Vector2(5, -34)])
			draw_colored_polygon(inner, Color(1.0, 0.86, 0.5, 0.95))
			draw_colored_polygon(PackedVector2Array([Vector2(-3, -34), Vector2(0, -44), Vector2(3, -34)]), Color(0.45, 0.6, 1.0, 0.7))
		# The lid swings open around the hinge on the right.
		draw_set_transform(Vector2(36, 0), -lid * 2.55, Vector2.ONE)
		draw_rect(Rect2(-72, -42, 72, 42), case_col)
		draw_rect(Rect2(-72, -42, 72, 3), Color(0.2, 0.2, 0.21))
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
