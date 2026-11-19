extends Control
## Front end: the title (logo over fog and rain), a short typed intro, then the mission briefing as an
## authentic-looking SOE operation instruction you page through. Ends by loading the mission.

const MISSION := "res://scenes/levels/village_test.tscn"
const INK := Color(0.1, 0.09, 0.12)
const STAMP_RED := Color(0.62, 0.08, 0.06, 0.82)

## The operation instruction, page by page. Typed in the house style of the period.
const PAGES := [
	{"head": "MOST SECRET", "body": """SPECIAL OPERATIONS EXECUTIVE
F  SECTION



OPERATION INSTRUCTION No. 31


Circuit:        LAPIDARY
To:             Organiser LAPIDARY ("TAILLEUR")
Via:            Courier, by hand
Date:           14th February 1944



Copy No. 1 of 1.
To be read, memorised and destroyed.""", "note": ""},
	{"head": "MOST SECRET", "body": """1.  SITUATION.

    (a) Your W/T operator has not come up on any
        schedule since the 11th inst. We must
        assume he has been taken. Treat anything
        he may know as compromised.

    (b) The coastal strip around PLOUZENNEC is a
        zone interdite. Entry requires a German
        Ausweis. Curfew is 2200 to 0500 hours
        and is strictly enforced.

    (c) A checkpoint controls the road from the
        bourg into the harbour zone. Telephone
        lines from it run up the main street.""", "note": "trust no one you don't have to"},
	{"head": "MOST SECRET", "body": """2.  TASK.

    (a) A Kriegsmarine signals post occupies the
        HOTEL DE LA PLAGE on the seafront.

    (b) You will obtain the current KEY SHEETS
        held at that post.

    (c) It is of the FIRST IMPORTANCE that the
        enemy should not learn the material has
        been compromised. Photograph or copy
        rather than remove. Leave no trace.

    (d) First you must get past the checkpoint
        into the zone. Use the means at hand.""", "note": "naval keys are printed in ink that runs in water. keep them dry."},
	{"head": "MOST SECRET", "body": """3.  EXTRACTION.

    (a) If the B.B.C. French service broadcasts

        "LE CHAT DE LA VOISINE A MANGÉ LES POMMES"

        a boat will lie off the ANSE DE KERLO
        at 0230 hours.

    (b) Signal the letter K by torch, seaward.
        Do not signal unless you are certain.

    (c) Should you be taken, hold for 48 hours.



                                         F.""", "note": "Good luck.  - F."},
]

var _stage := "title"
var _page := 0
var _font_type: SystemFont
var _font_hand: SystemFont
var _font_logo: SystemFont
var _root_title: Control
var _root_intro: Control
var _root_doc: Control
var _intro_label: Label
var _intro_lines := ["Bretagne occupée.  Février 1944.", "The coast is a forbidden zone.",
	"Three days ago, your wireless operator vanished.", "London has one more task for you."]
var _intro_i := 0
var _intro_t := 0.0
var _press: Label
var _page_nodes: Array[Control] = []
var _wind: AudioStreamPlayer
var _updater: Updater
var _logo: LogoAnimation
var _title_extras: Array = []
var _update_label: Label


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if Debug.active():
		get_tree().change_scene_to_file.call_deferred(MISSION)
		return
	_font_type = SystemFont.new()
	_font_type.font_names = PackedStringArray(["Courier New", "Courier", "Liberation Mono", "monospace"])
	_font_hand = SystemFont.new()
	_font_hand.font_names = PackedStringArray(["Ink Free", "Segoe Script", "Comic Sans MS", "Courier New"])
	_font_logo = SystemFont.new()
	_font_logo.font_names = PackedStringArray(["Stencil", "Impact", "Arial Black", "Courier New"])
	_build_title()
	_build_intro()
	_build_document()
	_show("title")
	_build_updater()
	_wind = AudioStreamPlayer.new()
	_wind.stream = SoundLib.pick("ambience/wind_gusts_loop")
	_wind.bus = Game.BUS_WORLD
	_wind.volume_db = SoundLib.gain("ambience/wind_gusts_loop") - 4.0
	add_child(_wind)
	_wind.play()
	get_tree().create_timer(1.5).timeout.connect(func() -> void:
		SoundLib.play_2d("ambience/church_bell_toll", -6.0))
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--doc-shot="):
			var page_n := int(arg.split("=")[1])
			_show("doc")
			_turn_to(page_n)
			get_tree().create_timer(2.0).timeout.connect(func() -> void:
				get_viewport().get_texture().get_image().save_png("user://doc_%d.png" % page_n)
				print("DOC SHOT ", ProjectSettings.globalize_path("user://doc_%d.png" % page_n))
				get_tree().quit())
	if OS.get_cmdline_user_args().has("--logo-shots"):
		for at: float in [3.0, 6.9, 9.2, 14.0]:
			get_tree().create_timer(at).timeout.connect(func() -> void:
				var path := "user://logo_%04.1f.png" % at
				get_viewport().get_texture().get_image().save_png(path)
				print("LOGO SHOT ", ProjectSettings.globalize_path(path)))
		get_tree().create_timer(14.5).timeout.connect(get_tree().quit)
	if OS.get_cmdline_user_args().has("--title-shot"):
		get_tree().create_timer(2.5).timeout.connect(func() -> void:
			get_viewport().get_texture().get_image().save_png("user://title.png")
			print("TITLE SHOT ", ProjectSettings.globalize_path("user://title.png"))
			get_tree().quit())


func _label(text: String, font: Font, size: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_override("font", font)
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l


func _full(c: Control) -> Control:
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return c


# --- title -------------------------------------------------------------------------------------

func _build_title() -> void:
	_root_title = _full(Control.new())
	add_child(_root_title)
	var bg := _full(ColorRect.new()) as ColorRect
	var fog := ShaderMaterial.new()
	fog.shader = Shader.new()
	fog.shader.code = """shader_type canvas_item;
float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float n(vec2 p){vec2 i=floor(p);vec2 f=fract(p);vec2 u=f*f*(3.0-2.0*f);return mix(mix(h(i),h(i+vec2(1,0)),u.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),u.x),u.y);}
float fbm(vec2 p){float v=0.0;float a=0.5;for(int i=0;i<5;i++){v+=n(p)*a;p*=2.0;a*=0.5;}return v;}
void fragment(){
	vec2 uv=UV*vec2(1.8,1.0);
	float t=TIME*0.03;
	float f=fbm(uv*3.0+vec2(t,t*0.4))*0.6+fbm(uv*6.0-vec2(t*1.6,0.0))*0.4;
	vec3 sky=mix(vec3(0.015,0.02,0.035),vec3(0.07,0.08,0.1),UV.y*0.6+f*0.5);
	float rain=step(0.996,h(floor(vec2(UV.x*420.0,UV.y*14.0-TIME*22.0))))*0.18;
	float vig=smoothstep(1.2,0.3,length(UV-vec2(0.5,0.55)));
	COLOR=vec4((sky+rain)*vig,1.0);
}"""
	bg.material = fog
	_root_title.add_child(bg)

	var col := VBoxContainer.new()
	col.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	col.offset_left = -700
	col.offset_right = 700
	col.offset_top = -400
	col.offset_bottom = 400
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 6)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root_title.add_child(col)

	var sign := _label("ACHTUNG  ·  SPERRGEBIET  ·  ZONE INTERDITE", _font_type, 18, Color(0.75, 0.2, 0.15))
	sign.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(sign)
	_logo = LogoAnimation.new(_font_logo)
	col.add_child(_logo)
	_logo.finished.connect(_on_logo_finished)
	var wire := BarbedWire.new()
	wire.custom_minimum_size = Vector2(1100, 36)
	col.add_child(wire)
	var sub := _label("Bretagne  ·  février 1944", _font_type, 24, Color(0.62, 0.6, 0.55))
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(sub)

	_press = _label("Press any key", _font_type, 18, Color(0.7, 0.68, 0.62))
	_press.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_press.offset_top = -120
	_press.offset_bottom = -90
	_press.offset_left = -300
	_press.offset_right = 300
	_press.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_root_title.add_child(_press)
	# Everything but the logo waits until the ink has been revealed.
	_title_extras = [sign, wire, sub, _press]
	for c: Control in _title_extras:
		c.modulate.a = 0.0


func _on_logo_finished() -> void:
	for c: Control in _title_extras:
		create_tween().tween_property(c, "modulate:a", 1.0, 1.4)


## Version in the corner, and a quiet update check. Patches download in the background and the game restarts
## itself to apply them (Boot loads them first thing).
func _build_updater() -> void:
	var ver := _label("v" + Boot.version, _font_type, 14, Color(0.5, 0.48, 0.44))
	ver.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	ver.offset_left = -220
	ver.offset_top = -40
	ver.offset_right = -24
	ver.offset_bottom = -16
	ver.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	add_child(ver)
	_update_label = _label("", _font_type, 14, Color(0.6, 0.57, 0.5))
	_update_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	_update_label.offset_left = 24
	_update_label.offset_top = -40
	_update_label.offset_right = 900
	_update_label.offset_bottom = -16
	add_child(_update_label)
	_updater = Updater.new()
	add_child(_updater)
	_updater.status.connect(func(t: String) -> void: _update_label.text = t)
	_updater.restart_ready.connect(func() -> void:
		get_tree().create_timer(1.5).timeout.connect(func() -> void:
			OS.set_restart_on_exit(true, OS.get_cmdline_args())
			get_tree().quit()))
	if not OS.has_feature("editor"):
		_updater.check_and_install()


# --- intro -------------------------------------------------------------------------------------

func _build_intro() -> void:
	_root_intro = _full(ColorRect.new())
	(_root_intro as ColorRect).color = Color.BLACK
	add_child(_root_intro)
	_intro_label = _label("", _font_type, 30, Color(0.82, 0.79, 0.72))
	_intro_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	_intro_label.offset_left = -800
	_intro_label.offset_right = 800
	_intro_label.offset_top = -40
	_intro_label.offset_bottom = 40
	_intro_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_root_intro.add_child(_intro_label)


# --- document ----------------------------------------------------------------------------------

func _build_document() -> void:
	_root_doc = _full(ColorRect.new())
	(_root_doc as ColorRect).color = Color(0.09, 0.06, 0.045)   # a dark wooden desk under a lamp
	add_child(_root_doc)
	var lamp := _full(ColorRect.new()) as ColorRect
	var lm := ShaderMaterial.new()
	lm.shader = Shader.new()
	lm.shader.code = """shader_type canvas_item;
void fragment(){ float d=length((UV-vec2(0.5,0.42))*vec2(1.0,1.4)); COLOR=vec4(1.0,0.75,0.45,0.0)+vec4(0.0,0.0,0.0,smoothstep(0.25,0.95,d)*0.85); COLOR.rgb=vec3(0.0); }"""
	lamp.material = lm
	for i in PAGES.size():
		var page := _make_page(i)
		_root_doc.add_child(page)
		_page_nodes.append(page)
	_root_doc.add_child(lamp)
	var hint := _label("Click or Space: next page   ·   ←: back   ·   Esc: skip", _font_type, 15, Color(0.6, 0.56, 0.5))
	hint.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	hint.offset_top = -50
	hint.offset_bottom = -25
	hint.offset_left = -400
	hint.offset_right = 400
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_root_doc.add_child(hint)


func _make_page(i: int) -> Control:
	var data: Dictionary = PAGES[i]
	var page := Control.new()
	page.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	page.offset_left = -390
	page.offset_right = 390
	page.offset_top = -500
	page.offset_bottom = 500
	page.pivot_offset = Vector2(390, 500)
	page.rotation = deg_to_rad([-1.2, 0.8, -0.5, 1.0][i % 4])
	page.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var paper := ColorRect.new()
	paper.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var pm := ShaderMaterial.new()
	pm.shader = load("res://shaders/paper.gdshader")
	pm.set_shader_parameter("seed", float(i) * 3.7 + 1.0)
	pm.set_shader_parameter("fold", 0.48 + 0.04 * i)
	pm.set_shader_parameter("ring_pos", Vector2(0.75 - 0.12 * (i % 2), 0.84 - 0.5 * float(i == 2)))
	paper.material = pm
	paper.mouse_filter = Control.MOUSE_FILTER_IGNORE
	page.add_child(paper)

	var head := _label(data["head"], _font_type, 24, INK)
	head.position = Vector2(0, 38)
	head.size = Vector2(780, 30)
	head.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	page.add_child(head)
	var body := _label(data["body"], _font_type, 19, INK)
	body.position = Vector2(64, 110)
	body.size = Vector2(660, 760)
	page.add_child(body)
	var foot := _label("%d / %d" % [i + 1, PAGES.size()], _font_type, 16, INK)
	foot.position = Vector2(0, 945)
	foot.size = Vector2(780, 24)
	foot.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	page.add_child(foot)
	var stamp := _label("MOST SECRET" if i == 0 else "SECRET", _font_logo, 46 if i == 0 else 34, STAMP_RED)
	stamp.position = Vector2(400 if i == 0 else 520, 700 if i == 0 else 760)
	stamp.rotation = deg_to_rad(-14.0 if i == 0 else 8.0)
	page.add_child(stamp)
	if i == 0:
		var ref := _label("F/31/LAP", _font_type, 16, INK)
		ref.position = Vector2(560, 84)
		page.add_child(ref)
	if data["note"] != "":
		var note := _label(data["note"], _font_hand, 24, Color(0.12, 0.2, 0.48, 0.9))
		note.position = Vector2(110, 860 if i != 3 else 800)
		note.rotation = deg_to_rad(-3.0)
		page.add_child(note)
	page.visible = false
	return page


# --- flow --------------------------------------------------------------------------------------

func _show(stage: String) -> void:
	_stage = stage
	_root_title.visible = stage == "title"
	_root_intro.visible = stage == "intro"
	_root_doc.visible = stage == "doc"
	if stage == "intro":
		_intro_i = 0
		_intro_t = 0.0
	if stage == "doc":
		_turn_to(0)


func _turn_to(i: int) -> void:
	_page = i
	for k in _page_nodes.size():
		_page_nodes[k].visible = k == i
	var p := _page_nodes[i]
	p.modulate.a = 0.0
	create_tween().tween_property(p, "modulate:a", 1.0, 0.35)
	SoundLib.play_2d("player/cloth_wool_move", -8.0, Game.BUS_WORLD, 0.15)


func _begin_mission() -> void:
	_stage = "loading"
	var fade := _full(ColorRect.new()) as ColorRect
	fade.color = Color(0, 0, 0, 0)
	add_child(fade)
	var tw := create_tween()
	tw.tween_property(fade, "color:a", 1.0, 1.2)
	tw.tween_callback(func() -> void: get_tree().change_scene_to_file(MISSION))


func _advance() -> void:
	match _stage:
		"title":
			if _logo and not _logo.is_done():
				_logo.skip()
				return
			_show("intro")
		"intro":
			_show("doc")
		"doc":
			if _page < PAGES.size() - 1:
				_turn_to(_page + 1)
			else:
				_begin_mission()


func _input(event: InputEvent) -> void:
	if _stage == "loading":
		return
	if event.is_action_pressed("pause"):
		_begin_mission()
		return
	var pressed: bool = (event is InputEventKey and event.pressed and not event.echo) \
		or (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT)
	if not pressed:
		return
	if _stage == "doc" and event is InputEventKey and (event.keycode == KEY_LEFT or event.keycode == KEY_BACKSPACE):
		if _page > 0:
			_turn_to(_page - 1)
		return
	_advance()


func _process(delta: float) -> void:
	if _stage == "title":
		if _logo and _logo.is_done() and _press.modulate.a > 0.4:
			_press.modulate.a = 0.45 + 0.4 * sin(Time.get_ticks_msec() / 600.0)
	elif _stage == "intro":
		_intro_t += delta
		var line: String = _intro_lines[_intro_i]
		var shown := int(_intro_t * 28.0)
		_intro_label.text = line.substr(0, shown)
		if _intro_t > line.length() / 28.0 + 2.2:
			_intro_i += 1
			_intro_t = 0.0
			if _intro_i >= _intro_lines.size():
				_show("doc")
