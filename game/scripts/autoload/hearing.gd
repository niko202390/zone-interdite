extends Node
## Simulates the player's hearing being damaged by loud noise.
##  - temporary: a temporary threshold shift. The world sounds muffled and quieter, and recovers over time.
##  - reflex: the acoustic reflex, a brief clamp-down straight after an impulse.
##  - tinnitus: a ringing tone that lags behind and fades more slowly than the muffling.
##  - permanent: a small share of every heavy dose never comes back.
## A deafened player can't hear footsteps, dogs or shouts, which is the gameplay cost of noise.

signal exposed(received_db: float)

## Exposure adds up: impulses are summed as energy in a short window, so one shot in the open passes,
## but rapid fire, firing indoors, or a rifle going off beside you does damage.
## Your own shots count for less: you know they're coming, and the ear's reflex is braced (playtest feedback).
const SHIFT_THRESHOLD_DB := 162.0
const SHIFT_RANGE_DB := 14.0
const WINDOW_TAU := 3.0
const OWN_SHOT_DB := -2.0
const STARTLE_DB := 6.0
const MIN_CUTOFF_HZ := 380.0
const MAX_CUTOFF_HZ := 20000.0

var temporary := 0.0
var permanent := 0.0
var tinnitus := 0.0
## Effects volume from Settings. It's applied here because this script owns the World bus level.
var effects_gain_db := 0.0
var _reflex := 0.0
var _energy := 0.0   # decaying sum of recent impulse energy (linear, relative to 1e15)

var _bus := -1
var _lowpass: AudioEffectLowPassFilter
var _tinnitus_player: AudioStreamPlayer


func _ready() -> void:
	_bus = AudioServer.get_bus_index(Game.BUS_WORLD)
	_lowpass = AudioServer.get_bus_effect(_bus, 0) as AudioEffectLowPassFilter
	_tinnitus_player = AudioStreamPlayer.new()
	_tinnitus_player.bus = Game.BUS_TINNITUS
	_tinnitus_player.volume_db = -80.0
	add_child(_tinnitus_player)
	# Defer so SoundLib can resolve the stream once the scene tree is up.
	_start_tinnitus.call_deferred()


func _start_tinnitus() -> void:
	_tinnitus_player.stream = SoundLib.pick("player/tinnitus_loop")
	_tinnitus_player.play()


## level_db: peak SPL at 1 m from the source. distance: metres from the listener's ear.
## enclosed: walls and ceiling close by reflect the impulse back, which adds several dB.
func expose(level_db: float, distance: float, enclosed := false, own := false) -> void:
	var received := level_db + linear_to_db(1.0 / maxf(distance, 1.0)) + (8.0 if enclosed else 0.0) \
		+ (OWN_SHOT_DB if own else STARTLE_DB)
	exposed.emit(received)
	_energy += pow(10.0, (received - 150.0) / 10.0)
	var cumulative := 150.0 + 10.0 * log(maxf(_energy, 1e-9)) / log(10.0)
	var dose := clampf((cumulative - SHIFT_THRESHOLD_DB) / SHIFT_RANGE_DB, 0.0, 1.0)
	if dose <= 0.0:
		return
	# Hold the effect back a moment so the impulse itself is heard at full force (the reflex has a real latency).
	get_tree().create_timer(0.07, false).timeout.connect(_apply_dose.bind(dose))


func _apply_dose(dose: float) -> void:
	temporary = clampf(temporary + dose * 0.42 * (1.0 - temporary * 0.5), 0.0, 1.0)
	permanent = minf(permanent + dose * dose * 0.004, 0.45)
	_reflex = maxf(_reflex, dose)
	tinnitus = maxf(tinnitus, minf(temporary * 1.1, 1.0))
	_tinnitus_player.pitch_scale = randf_range(0.93, 1.07)


## 0 = perfect hearing, 1 = nearly deaf. AI-facing systems can read this to decide what the player could hear.
func loss() -> float:
	return clampf(temporary + permanent, 0.0, 1.0)


func _process(delta: float) -> void:
	# Heavier shifts recover more slowly.
	var tau := 4.0 + 28.0 * temporary
	temporary = maxf(temporary - delta * (temporary / tau + 0.002), 0.0)
	_reflex = maxf(_reflex - delta * 4.0, 0.0)
	_energy *= exp(-delta / WINDOW_TAU)
	tinnitus = maxf(tinnitus - delta / (7.0 + 45.0 * tinnitus), temporary * 0.8)

	var l := loss()
	if _lowpass:
		_lowpass.cutoff_hz = MAX_CUTOFF_HZ * pow(MIN_CUTOFF_HZ / MAX_CUTOFF_HZ, pow(l, 0.8))
	AudioServer.set_bus_volume_db(_bus, effects_gain_db - 16.0 * l - 18.0 * _reflex)
	AudioServer.set_bus_volume_db(AudioServer.get_bus_index(Game.BUS_TINNITUS), effects_gain_db)
	_tinnitus_player.volume_db = linear_to_db(maxf(tinnitus, 0.0001)) - 4.0 + SoundLib.gain("player/tinnitus_loop")
