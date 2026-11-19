extends CanvasLayer
## Almost all the UI there is: a faint typewritten line for what the character feels or knows,
## the pause screen, and a controls card for playtesting.

const CONTROLS := """WASD  move        Mouse wheel  walking pace        Shift  sprint
C  crouch        Space  jump        Q / E  lean
RMB  aim        LMB  fire        R  reload        T  check magazine
B  safety (decocks the hammer)        H  holster
F1  this card        F11  fullscreen        Esc  pause        F10  quit"""

var _font: SystemFont
var _note: Label
var _note_t := 0.0
var _pause: Control
var _help: Label
var _help_t := 10.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 10
	_font = SystemFont.new()
	_font.font_names = PackedStringArray(["Courier New", "Courier", "Liberation Mono", "monospace"])

	_note = _label(19, Color(0.86, 0.83, 0.76))
	_note.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_note.offset_top = -120
	_note.offset_bottom = -80
	_note.offset_left = -700
	_note.offset_right = 700
	_note.modulate.a = 0.0
	add_child(_note)

	_help = _label(17, Color(0.8, 0.78, 0.72))
	_help.text = CONTROLS
	_help.set_anchors_and_offsets_preset(Control.PRESET_CENTER_TOP)
	_help.offset_top = 40
	_help.offset_bottom = 200
	_help.offset_left = -700
	_help.offset_right = 700
	add_child(_help)
	if Debug.active():
		_help_t = 0.0

	_pause = ColorRect.new()
	(_pause as ColorRect).color = Color(0.0, 0.0, 0.0, 0.72)
	_pause.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_pause.mouse_filter = Control.MOUSE_FILTER_STOP
	var title := _label(42, Color(0.9, 0.86, 0.78))
	title.text = "ZONE INTERDITE"
	title.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	title.offset_top = -200
	title.offset_bottom = -140
	title.offset_left = -600
	title.offset_right = 600
	_pause.add_child(title)
	var body := _label(18, Color(0.82, 0.8, 0.74))
	body.text = "Paused.  Esc resumes.\n\n" + CONTROLS
	body.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	body.offset_top = -100
	body.offset_bottom = 140
	body.offset_left = -700
	body.offset_right = 700
	_pause.add_child(body)
	_pause.visible = false
	add_child(_pause)


func _label(size: int, color: Color) -> Label:
	var l := Label.new()
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.autowrap_mode = TextServer.AUTOWRAP_OFF
	l.add_theme_font_override("font", _font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	l.add_theme_constant_override("outline_size", 5)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func note(text: String, seconds := 3.0) -> void:
	_note.text = text
	_note_t = seconds


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
