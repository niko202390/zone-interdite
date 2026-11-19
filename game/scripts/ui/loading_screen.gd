class_name LoadingScreen
extends CanvasLayer
## Shown while a level builds itself: the place name, what's being laid out, and a thin progress line.
## set_progress() between build steps; finish() fades it away.

var _bar: ColorRect
var _bar_bg: ColorRect
var _step: Label
var _root: Control
var _shown := 0.0
var _target := 0.0
var _t := 0.0

const LINES := ["Rain off the Channel since noon.", "Curfew at ten.", "The coast is a forbidden zone.",
	"Papers are checked at the harbour road.", "Keep out of the light."]


func _init(title := "Plouzennec") -> void:
	layer = 100
	_root = Control.new()
	_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	var bg := ColorRect.new()
	bg.color = Color(0.012, 0.012, 0.016)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_root.add_child(bg)
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["Courier New", "Courier", "Liberation Mono", "monospace"])
	var name_l := _label(title, font, 56, Color(0.78, 0.75, 0.68))
	name_l.offset_top = -110
	name_l.offset_bottom = -40
	var sub := _label(LINES[randi() % LINES.size()], font, 24, Color(0.55, 0.53, 0.48))
	sub.offset_top = -40
	sub.offset_bottom = -10
	_step = _label("", font, 19, Color(0.5, 0.48, 0.44))
	_step.offset_top = 48
	_step.offset_bottom = 76
	_bar_bg = ColorRect.new()
	_bar_bg.color = Color(0.13, 0.12, 0.11)
	_bar_bg.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_bar_bg.offset_left = -340
	_bar_bg.offset_right = 340
	_bar_bg.offset_top = 30
	_bar_bg.offset_bottom = 32
	_root.add_child(_bar_bg)
	_bar = ColorRect.new()
	_bar.color = Color(0.72, 0.62, 0.42)
	_bar.position = Vector2.ZERO
	_bar.size = Vector2(0, 2)
	_bar_bg.add_child(_bar)


func _label(text: String, font: Font, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	l.offset_left = -700
	l.offset_right = 700
	_root.add_child(l)
	return l


func set_progress(fraction: float, step: String) -> void:
	_target = clampf(fraction, 0.0, 1.0)
	_shown = maxf(_shown, _target * 0.98)   # jump most of the way: frames are rare while building
	_step.text = step
	_apply()


func _apply() -> void:
	_bar.size = Vector2(_bar_bg.size.x * _shown, 2)


func _process(delta: float) -> void:
	_shown = move_toward(_shown, _target, delta * 0.5)
	_apply()
	_t += delta


func finish() -> void:
	set_progress(1.0, "")
	var tw := create_tween()
	tw.tween_interval(0.3)
	tw.tween_property(_root, "modulate:a", 0.0, 1.2)
	tw.tween_callback(queue_free)
