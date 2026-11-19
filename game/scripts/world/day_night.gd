class_name DayNight
extends Node
## Moves the light through the evening as the clock runs: blue hour, late dusk, then a moonless winter night.
## Lerps the sky, sun, fog, exposure, and the ambient light level the AI uses for sight.
## Keyframes are by minute of the day. Before the first one or after the last, the nearest key holds.

var env: Environment
var sun: DirectionalLight3D

const KEYS := [
	{"t": 1040.0, "top": Color(0.11, 0.15, 0.26), "horizon": Color(0.62, 0.58, 0.62), "sun": 1.2,
		"exposure": 1.6, "ambient": 0.28, "fog": Color(0.36, 0.38, 0.44)},                       # 17:20
	{"t": 1060.0, "top": Color(0.085, 0.115, 0.2), "horizon": Color(0.5, 0.48, 0.55), "sun": 0.9,
		"exposure": 1.7, "ambient": 0.2, "fog": Color(0.32, 0.34, 0.4)},                         # 17:40 (start)
	{"t": 1110.0, "top": Color(0.03, 0.042, 0.078), "horizon": Color(0.17, 0.17, 0.22), "sun": 0.3,
		"exposure": 2.0, "ambient": 0.12, "fog": Color(0.15, 0.16, 0.2)},                        # 18:30
	{"t": 1160.0, "top": Color(0.009, 0.012, 0.022), "horizon": Color(0.04, 0.045, 0.06), "sun": 0.0,
		"exposure": 2.4, "ambient": 0.065, "fog": Color(0.055, 0.06, 0.075)},                    # 19:20 (night)
]


func _process(_delta: float) -> void:
	if env == null:
		return
	var t := Game.clock_minutes
	if t < 600.0:
		t += 1440.0   # small hours count as late night
	var a: Dictionary = KEYS[0]
	var b: Dictionary = KEYS[0]
	var f := 0.0
	if t <= KEYS[0]["t"]:
		a = KEYS[0]
		b = a
	elif t >= KEYS[KEYS.size() - 1]["t"]:
		a = KEYS[KEYS.size() - 1]
		b = a
	else:
		for i in KEYS.size() - 1:
			if t >= KEYS[i]["t"] and t < KEYS[i + 1]["t"]:
				a = KEYS[i]
				b = KEYS[i + 1]
				f = (t - float(a["t"])) / (float(b["t"]) - float(a["t"]))
				break
	var sky := env.sky.sky_material as ProceduralSkyMaterial
	if sky:
		sky.sky_top_color = (a["top"] as Color).lerp(b["top"], f)
		sky.sky_horizon_color = (a["horizon"] as Color).lerp(b["horizon"], f)
		sky.ground_horizon_color = sky.sky_horizon_color * 0.65
	env.tonemap_exposure = lerpf(a["exposure"], b["exposure"], f)
	env.fog_light_color = (a["fog"] as Color).lerp(b["fog"], f)
	var sun_energy := lerpf(a["sun"], b["sun"], f)
	if sun:
		sun.light_energy = sun_energy
		sun.visible = sun_energy > 0.01
	Visibility.ambient = lerpf(a["ambient"], b["ambient"], f)
