class_name FilmIntro
extends Control
## The pre-rendered photoreal title film (tools/blender/intro), played full screen with its sounds cued from
## intro_cues.json. When it ends, or is skipped, the final frame stays as the title backdrop.
## Same small API as LogoAnimation: finished, skip(), is_done().

signal finished

const VIDEO := "res://assets/video/intro.ogv"
const FINAL := "res://assets/video/intro_final.png"
const CUES := "res://assets/video/intro_cues.json"

var _video: VideoStreamPlayer
var _still: TextureRect
var _done := false
var _t := 0.0
var _cues := {}
var _fired := {}
var _scratch: AudioStreamPlayer
var _flame: AudioStreamPlayer


static func available() -> bool:
	return ResourceLoader.exists(VIDEO) and ResourceLoader.exists(FINAL)


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	var black := ColorRect.new()
	black.color = Color.BLACK
	black.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	black.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(black)
	_still = TextureRect.new()
	_still.texture = load(FINAL)
	_still.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_still.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_still.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_still.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_still.modulate.a = 0.0
	add_child(_still)
	_video = VideoStreamPlayer.new()
	_video.stream = load(VIDEO)
	_video.expand = true
	_video.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_video.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_video)
	_video.finished.connect(_finish)
	if FileAccess.file_exists(CUES):
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(CUES))
		if parsed is Dictionary:
			_cues = parsed
	_scratch = _loop("ui/pen_scratch_loop", -10.0)
	_flame = _loop("ui/flame_loop", -6.0)
	_video.play()


func _loop(key: String, vol: float) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.stream = SoundLib.pick(key)
	p.volume_db = vol
	add_child(p)
	return p


func _at(name: String) -> bool:
	if not _cues.has(name) or _fired.has(name):
		return false
	if _t >= float(_cues[name]):
		_fired[name] = true
		return true
	return false


func _process(delta: float) -> void:
	if _done:
		return
	_t += delta
	if _at("pen_start"):
		_scratch.play()
	if _at("pen_end"):
		_scratch.stop()
	if _at("lid_open"):
		SoundLib.play_2d("ui/lighter_open", -2.0, &"Master")
	if _at("strike"):
		SoundLib.play_2d("ui/lighter_strike", -2.0, &"Master")
	if _at("flame_on"):
		_flame.play()
	if _at("flame_off"):
		_flame.stop()
	if _at("lid_close"):
		SoundLib.play_2d("ui/lighter_close", -2.0, &"Master")


func skip() -> void:
	_finish()


func is_done() -> bool:
	return _done


func _finish() -> void:
	if _done:
		return
	_done = true
	_scratch.stop()
	_flame.stop()
	_video.stop()
	_video.visible = false
	_still.modulate.a = 1.0
	finished.emit()
