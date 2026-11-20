class_name Journal
extends Control
## The agent's own notes: a folded, crumpled sheet in pencil-and-ink handwriting. Two halves: the things to do,
## and Intel (what's been seen, heard, read). Done tasks get crossed out by hand, a stroke drawn across them the
## next time the sheet is looked at. J shows and hides it.

const PAGE := Vector2(1180, 790)
const INK := Color(0.1, 0.12, 0.24, 0.92)

var title := ""
var tasks: Array[Dictionary] = []     # {id, text, done, cross (0..1 drawn), seed}
var intel: PackedStringArray = PackedStringArray()
var _fresh_intel := {}
var _paper: ColorRect
var _ink: InkLayer
var _scratch: AudioStreamPlayer
var _pen_t := 0.0


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	offset_left = -PAGE.x * 0.5
	offset_right = PAGE.x * 0.5
	offset_top = -PAGE.y * 0.5
	offset_bottom = PAGE.y * 0.5
	pivot_offset = PAGE * 0.5
	rotation = deg_to_rad(-1.4)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var shadow := ColorRect.new()
	shadow.color = Color(0, 0, 0, 0.45)
	shadow.position = Vector2(14, 18)
	shadow.size = PAGE
	shadow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(shadow)
	_paper = ColorRect.new()
	_paper.size = PAGE
	_paper.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var m := ShaderMaterial.new()
	m.shader = load("res://shaders/journal_paper.gdshader")
	m.set_shader_parameter("aspect", Vector2(PAGE.x / PAGE.y, 1.0))
	_paper.material = m
	add_child(_paper)
	_ink = InkLayer.new()
	_ink.journal = self
	_ink.size = PAGE
	add_child(_ink)
	_scratch = AudioStreamPlayer.new()
	_scratch.stream = SoundLib.pick("ui/pen_scratch_loop")
	_scratch.volume_db = -14.0
	add_child(_scratch)
	visible = false


func add_task(id: String, text: String) -> void:
	for t in tasks:
		if t["id"] == id:
			return
	tasks.append({"id": id, "text": text, "done": false, "cross": 0.0, "seed": float(tasks.size() * 7 + 3)})
	_ink.queue_redraw()


## Mark a task done. Its crossing-out is drawn by hand next time the journal is open.
func complete(id: String) -> bool:
	for t in tasks:
		if t["id"] == id and not t["done"]:
			t["done"] = true
			_ink.queue_redraw()
			return true
	return false


func is_done(id: String) -> bool:
	for t in tasks:
		if t["id"] == id:
			return t["done"]
	return false


## Something learned. Key hints in parentheses are left out: the journal is the agent's notes, not a manual.
func add_intel(text: String) -> bool:
	var clean := RegEx.create_from_string("\\s*\\((?:Space|[A-Z]|[A-Z]/[A-Z])\\)").sub(text, "", true).strip_edges()
	if clean == "" or intel.has(clean):
		return false
	intel.append(clean)
	_fresh_intel[clean] = true
	_ink.queue_redraw()
	return true


func toggle() -> void:
	visible = not visible
	if visible:
		_ink.queue_redraw()
	else:
		_fresh_intel.clear()


func _process(delta: float) -> void:
	if not visible:
		_scratch.stop()
		return
	# Cross out one finished task at a time, at the speed of a hand.
	var drawing := false
	for t in tasks:
		if t["done"] and t["cross"] < 1.0:
			t["cross"] = minf(1.0, t["cross"] + delta / 0.7)
			drawing = true
			break
	if drawing and not _scratch.playing:
		_scratch.play()
	elif not drawing and _scratch.playing:
		_scratch.stop()
	if drawing:
		_ink.queue_redraw()


## The handwriting and pen strokes, drawn over the paper.
class InkLayer:
	extends Control
	var journal: Journal
	var _hand: SystemFont
	var _hand_bold: SystemFont

	func _init() -> void:
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		_hand = SystemFont.new()
		_hand.font_names = PackedStringArray(["Ink Free", "Segoe Print", "Segoe Script", "Comic Sans MS"])
		_hand_bold = SystemFont.new()
		_hand_bold.font_names = _hand.font_names
		_hand_bold.font_weight = 700

	func _h(i: float) -> float:
		return fract(sin(i * 12.9898 + 78.233) * 43758.5453)

	func fract(x: float) -> float:
		return x - floorf(x)

	## Word-wrap to a width.
	func _wrap(text: String, width: float, fs: int) -> PackedStringArray:
		var lines := PackedStringArray()
		var cur := ""
		for w in text.split(" ", false):
			var t := w if cur == "" else cur + " " + w
			if _hand.get_string_size(t, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x > width and cur != "":
				lines.append(cur)
				cur = w
			else:
				cur = t
		if cur != "":
			lines.append(cur)
		return lines

	## A line of handwriting: each line sits a little off level and drifts, as written on the knee.
	func _write(pos: Vector2, text: String, fs: int, seed: float, col: Color, font: Font = null) -> float:
		var f := font if font else _hand
		var rot := (_h(seed) - 0.5) * 0.02
		draw_set_transform(pos, rot, Vector2.ONE)
		draw_string(f, Vector2.ZERO, text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, col)
		draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
		return f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x

	## A hand-drawn stroke across a line of text: quick, slightly rising, a little wavy, and thicker in the
	## middle where the pen presses. Drawn only as far as `t` (0..1) so it can be animated.
	func _cross(a: Vector2, b: Vector2, t: float, seed: float) -> void:
		if t <= 0.0:
			return
		var pts := PackedVector2Array()
		var n := 26
		var rise := (_h(seed + 1.0) - 0.35) * 7.0
		var ph := _h(seed + 2.0) * TAU
		for i in n + 1:
			var u := float(i) / n
			if u > t:
				break
			var p := a.lerp(b, u)
			p.y += rise * (u - 0.5) + sin(u * 7.0 + ph) * 1.6 + sin(u * 19.0 + ph * 2.0) * 0.6
			pts.append(p)
		for i in pts.size() - 1:
			var u2 := float(i) / n
			var w := lerpf(1.4, 2.8, sin(u2 * PI))
			draw_line(pts[i], pts[i + 1], INK, w, true)
		# A second, quicker return stroke on some lines, as people do.
		if _h(seed + 3.0) < 0.45 and t >= 1.0:
			var back := PackedVector2Array()
			for i in n + 1:
				var u3 := float(i) / n
				var p2 := b.lerp(a, u3) + Vector2(0, 3.0 + sin(u3 * 5.0 + ph) * 1.4)
				back.append(p2)
			draw_polyline(back, Color(INK, 0.75), 1.3, true)

	func _draw() -> void:
		var j := journal
		var fs := 25
		var col_w := Journal.PAGE.x * 0.5 - 120.0
		var lh := fs * 1.32
		# Shrink the hand if there's a lot written, so it all fits on the sheet.
		for attempt in 5:
			var need := 0
			for s in j.intel:
				need += _wrap(s, col_w - 24.0, fs).size()
			if 150.0 + need * lh + j.intel.size() * 6.0 < Journal.PAGE.y - 40.0:
				break
			fs -= 2
			lh = fs * 1.32
		var left := Vector2(110, 82)
		_write(left, j.title, fs + 2, 1.0, INK)
		# To do.
		var y := left.y + 70.0
		var hw := _write(Vector2(left.x, y), "To do", fs + 4, 2.0, INK, _hand_bold)
		draw_line(Vector2(left.x, y + 8), Vector2(left.x + hw + 10, y + 5), INK, 1.6, true)
		y += lh + 10.0
		for t in j.tasks:
			var lines := _wrap(String(t["text"]), col_w - 30.0, fs)
			_write(Vector2(left.x, y), "-", fs, t["seed"], INK)
			for li in lines.size():
				var wpx := _write(Vector2(left.x + 24, y + li * lh), lines[li], fs, t["seed"] + li, INK)
				if t["done"]:
					var share := 1.0 / lines.size()
					var local := clampf((float(t["cross"]) - li * share) / share, 0.0, 1.0)
					_cross(Vector2(left.x + 18, y + li * lh - fs * 0.3), Vector2(left.x + 30 + wpx, y + li * lh - fs * 0.34),
						local, t["seed"] * 3.0 + li)
			y += lines.size() * lh + 12.0
		# Intel, on the other half of the fold.
		var rx := Journal.PAGE.x * 0.5 + 44.0
		var ry := left.y + 70.0
		var iw := _write(Vector2(rx, ry), "Intel", fs + 4, 5.0, INK, _hand_bold)
		draw_line(Vector2(rx, ry + 8), Vector2(rx + iw + 10, ry + 6), INK, 1.6, true)
		ry += lh + 10.0
		for k in j.intel.size():
			var s: String = j.intel[k]
			var fresh: bool = j._fresh_intel.has(s)
			var c := Color(0.32, 0.12, 0.08, 0.92) if fresh else INK
			_write(Vector2(rx, ry), "-", fs, 40.0 + k, c)
			var lines2 := _wrap(s, col_w - 24.0, fs)
			for li in lines2.size():
				_write(Vector2(rx + 22, ry + li * lh), lines2[li], fs, 40.0 + k + li * 0.37, c)
			ry += lines2.size() * lh + 6.0
