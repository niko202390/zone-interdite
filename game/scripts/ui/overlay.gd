extends CanvasLayer
## Almost all the UI there is: a faint typewritten line for what the character feels or knows,
## the pause screen with settings, a controls card for playtesting, and the fade to black on death.

const CONTROLS := """WASD  move        Mouse wheel  walking pace        Shift  sprint
C  crouch        Space  jump        Q / E  lean
RMB  aim        LMB  fire        R  reload        T  check magazine
B  safety (decocks the hammer)        H  holster        F  interact / take down / papers        X  watch
F1  this card        F11  fullscreen        Esc  pause / settings        F10  quit"""

const INK := Color(0.86, 0.83, 0.76)

var _font: SystemFont
var _theme: Theme
var _note: Label
var _note_t := 0.0
var _hint: Label
var _hint_text := ""
var _subtitle: Label
var _subtitle_t := 0.0

var _pause: Control
var _help: Label
var _help_t := 10.0
var _fade: ColorRect
var _fade_target := 0.0
var _value_labels := {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 10
	_font = SystemFont.new()
	_font.font_names = PackedStringArray(["Courier New", "Courier", "Liberation Mono", "monospace"])
	_theme = Theme.new()
	_theme.default_font = _font
	_theme.default_font_size = 18
	_theme.set_color("font_color", "Label", INK)
	_theme.set_color("font_color", "CheckBox", INK)
	_theme.set_color("font_color", "OptionButton", INK)

	_fade = ColorRect.new()
	_fade.color = Color(0, 0, 0, 0)
	_fade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_fade)

	_note = _label(19)
	_note.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_note.offset_top = -120
	_note.offset_bottom = -80
	_note.offset_left = -700
	_note.offset_right = 700
	_note.modulate.a = 0.0
	add_child(_note)

	_hint = _label(16)
	_hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_hint.offset_top = 60
	_hint.offset_bottom = 90
	_hint.offset_left = -300
	_hint.offset_right = 300
	_hint.modulate.a = 0.0
	add_child(_hint)

	_subtitle = _label(20)
	_subtitle.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_subtitle.offset_top = -190
	_subtitle.offset_bottom = -130
	_subtitle.offset_left = -800
	_subtitle.offset_right = 800
	_subtitle.add_theme_color_override("font_color", Color(0.95, 0.9, 0.78))
	_subtitle.modulate.a = 0.0
	add_child(_subtitle)

	_help = _label(17)
	_help.text = CONTROLS
	_help.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_help.offset_top = 40
	_help.offset_bottom = 200
	_help.offset_left = -700
	_help.offset_right = 700
	add_child(_help)
	if Debug.active():
		_help_t = 0.0

	_build_pause()


func _label(size: int) -> Label:
	var l := Label.new()
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.add_theme_font_override("font", _font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", INK)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	l.add_theme_constant_override("outline_size", 5)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


# --- pause and settings ------------------------------------------------------------------------

func _build_pause() -> void:
	var bg := ColorRect.new()
	bg.color = Color(0.0, 0.0, 0.0, 0.78)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.mouse_filter = Control.MOUSE_FILTER_STOP
	bg.theme = _theme
	_pause = bg

	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	bg.add_child(center)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 14)
	center.add_child(col)

	var title := _label(40)
	title.text = "ZONE INTERDITE"
	col.add_child(title)
	var sub := _label(17)
	sub.text = "Paused.  Esc resumes."
	col.add_child(sub)

	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 24)
	grid.add_theme_constant_override("v_separation", 10)
	col.add_child(grid)

	_slider_row(grid, "Mouse sensitivity", 0.3, 3.0, 0.05, Settings.sensitivity / 0.0022,
		func(v: float) -> void: Settings.set_value("sensitivity", 0.0022 * v), "%.2fx")
	_slider_row(grid, "Field of view", 70.0, 110.0, 1.0, Settings.horizontal_fov(Settings.fov),
		func(v: float) -> void: Settings.set_value("fov", _vertical_fov(v)), "%d°")
	_slider_row(grid, "Master volume", 0.0, 100.0, 1.0, Settings.master_volume * 100.0,
		func(v: float) -> void: Settings.set_value("master_volume", v / 100.0), "%d")
	_slider_row(grid, "Effects volume", 0.0, 100.0, 1.0, Settings.effects_volume * 100.0,
		func(v: float) -> void: Settings.set_value("effects_volume", v / 100.0), "%d")
	_slider_row(grid, "Music volume", 0.0, 100.0, 1.0, Settings.music_volume * 100.0,
		func(v: float) -> void: Settings.set_value("music_volume", v / 100.0), "%d")

	var ql := _label(18)
	ql.text = "Graphics quality"
	ql.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	grid.add_child(ql)
	var opt := OptionButton.new()
	for p in Settings.PRESETS:
		opt.add_item(p)
	opt.selected = Settings.quality
	opt.custom_minimum_size = Vector2(320, 0)
	opt.item_selected.connect(func(i: int) -> void: Settings.set_value("quality", i))
	grid.add_child(opt)
	grid.add_child(Control.new())

	_check_row(grid, "Fullscreen", Settings.fullscreen, func(on: bool) -> void: Settings.set_value("fullscreen", on))
	_check_row(grid, "Vertical sync", Settings.vsync, func(on: bool) -> void: Settings.set_value("vsync", on))

	var controls := _label(16)
	controls.text = "\n" + CONTROLS
	col.add_child(controls)

	bg.visible = false
	add_child(bg)


func _slider_row(grid: GridContainer, text: String, lo: float, hi: float, step: float, value: float,
		on_change: Callable, fmt: String) -> void:
	var l := _label(18)
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	grid.add_child(l)
	var s := HSlider.new()
	s.min_value = lo
	s.max_value = hi
	s.step = step
	s.value = value
	s.custom_minimum_size = Vector2(320, 24)
	grid.add_child(s)
	var v := _label(18)
	v.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	v.custom_minimum_size = Vector2(80, 0)
	v.text = fmt % value
	grid.add_child(v)
	s.value_changed.connect(func(nv: float) -> void:
		v.text = fmt % nv
		on_change.call(nv))


func _check_row(grid: GridContainer, text: String, value: bool, on_toggle: Callable) -> void:
	var l := _label(18)
	l.text = text
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	grid.add_child(l)
	var c := CheckBox.new()
	c.button_pressed = value
	c.toggled.connect(on_toggle)
	grid.add_child(c)
	grid.add_child(Control.new())


static func _vertical_fov(horizontal_deg: float) -> float:
	return rad_to_deg(2.0 * atan(tan(deg_to_rad(horizontal_deg) * 0.5) * 9.0 / 16.0))


# --- runtime -----------------------------------------------------------------------------------

## Something said out loud, shown in German with a translation. When the player is half-deaf or too far
## away, only the fact that someone is shouting gets through.
func subtitle(german: String, english: String, muffled := false) -> void:
	if muffled:
		_subtitle.text = "[ muffled shouting ]"
	else:
		_subtitle.text = "«%s»\n(%s)" % [german, english] if german != english else "«%s»" % german
	_subtitle_t = 3.2


## A faint, context-only prompt just below the centre of the screen. An empty string hides it.
func hint(text: String) -> void:
	if text != "":
		_hint.text = text
	_hint_text = text


func note(text: String, seconds := 3.0) -> void:
	_note.text = text
	_note_t = seconds


## 0 = clear, 1 = black. Used for death and later for passing out / transitions.
func fade_to(alpha: float) -> void:
	_fade_target = alpha


func _input(event: InputEvent) -> void:
	if event.is_action_pressed("pause"):
		_set_paused(not get_tree().paused)
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("help"):
		_help_t = 0.0 if _help_t > 0.0 else 30.0
	elif event is InputEventMouseButton and event.is_pressed() and not get_tree().paused \
			and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and not Debug.active():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		get_viewport().set_input_as_handled()


func _set_paused(paused: bool) -> void:
	get_tree().paused = paused
	_pause.visible = paused
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if paused else Input.MOUSE_MODE_CAPTURED


func _process(delta: float) -> void:
	_note_t -= delta
	_note.modulate.a = move_toward(_note.modulate.a, 0.85 if _note_t > 0.0 else 0.0, delta * 2.5)
	_help_t -= delta
	_help.modulate.a = move_toward(_help.modulate.a, 0.8 if _help_t > 0.0 else 0.0, delta * 1.5)
	_fade.color.a = move_toward(_fade.color.a, _fade_target, delta * 0.6)
	_hint.modulate.a = move_toward(_hint.modulate.a, 0.55 if _hint_text != "" else 0.0, delta * 4.0)
	_subtitle_t -= delta
	_subtitle.modulate.a = move_toward(_subtitle.modulate.a, 0.95 if _subtitle_t > 0.0 else 0.0, delta * 3.0)
