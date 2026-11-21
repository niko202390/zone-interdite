class_name Debrief
extends CanvasLayer
## London's report on the night: a typed F Section sheet that says how it went, not just whether.
## Any key (after a moment) calls `on_close`.

var text := ""
var verdict := ""
var on_close: Callable
var _t := 0.0
var _root: Control


func _init(body: String, verdict_line: String, close: Callable) -> void:
	text = body
	verdict = verdict_line
	on_close = close
	layer = 60
	process_mode = Node.PROCESS_MODE_ALWAYS


func _ready() -> void:
	_root = Control.new()
	_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.modulate.a = 0.0
	add_child(_root)
	var bg := ColorRect.new()
	bg.color = Color(0.02, 0.02, 0.025, 0.92)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.add_child(bg)
	var page := ColorRect.new()
	page.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	page.offset_left = -430
	page.offset_right = 430
	page.offset_top = -490
	page.offset_bottom = 440
	page.pivot_offset = Vector2(430, 465)
	page.rotation = deg_to_rad(0.8)
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/paper.gdshader")
	m.set_shader_parameter("seed", 11.0)
	m.set_shader_parameter("fold", 0.5)
	m.set_shader_parameter("ring_pos", Vector2(0.8, 0.86))
	page.material = m
	_root.add_child(page)
	var type := SystemFont.new()
	type.font_names = PackedStringArray(["Courier New", "Courier", "monospace"])
	var body := Label.new()
	body.text = text
	body.add_theme_font_override("font", type)
	body.add_theme_font_size_override("font_size", 19)
	body.add_theme_color_override("font_color", Color(0.1, 0.09, 0.12))
	body.position = Vector2(60, 60)
	body.size = Vector2(740, 760)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	page.add_child(body)
	var stamp := Label.new()
	stamp.text = verdict
	var bold := SystemFont.new()
	bold.font_names = PackedStringArray(["Stencil", "Impact", "Arial Black"])
	stamp.add_theme_font_override("font", bold)
	stamp.add_theme_font_size_override("font_size", 34)
	stamp.add_theme_color_override("font_color", Color(0.62, 0.08, 0.06, 0.85))
	stamp.position = Vector2(110, 780)
	stamp.rotation = deg_to_rad(-6.0)
	page.add_child(stamp)
	var hint := Label.new()
	hint.text = "Press any key"
	hint.add_theme_font_override("font", type)
	hint.add_theme_font_size_override("font_size", 16)
	hint.add_theme_color_override("font_color", Color(0.7, 0.68, 0.62))
	hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	hint.offset_top = -44
	hint.offset_left = -200
	hint.offset_right = 200
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_root.add_child(hint)
	create_tween().tween_property(_root, "modulate:a", 1.0, 1.5)
	SoundLib.play_2d("player/cloth_wool_move", -6.0)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _process(delta: float) -> void:
	_t += delta


func _input(event: InputEvent) -> void:
	if _t < 2.0:
		return
	var pressed: bool = (event is InputEventKey and event.pressed and not event.echo) \
		or (event is InputEventMouseButton and event.pressed)
	if pressed and on_close.is_valid():
		var cb := on_close
		on_close = Callable()
		get_viewport().set_input_as_handled()
		cb.call()
