class_name ProcTex
extends RefCounted
## Small textures and meshes generated in code (from scratch) and cached.

static var _cache := {}


## A bullet strike. On granite and stone it's a dark pit inside a ring of freshly chipped, lighter stone.
## On wood it's a darker splintered hole.
static func bullet_hole(kind: String) -> ImageTexture:
	var key := "hole_" + kind
	if _cache.has(key):
		return _cache[key]
	var size := 128
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(key)
	var c := Vector2(size, size) * 0.5
	var lobes: Array[float] = []
	for i in 9:
		lobes.append(rng.randf_range(0.75, 1.3))
	var wood := kind == "wood"
	var soft := kind == "mud" or kind == "grass"
	for y in size:
		for x in size:
			var d := Vector2(x, y) - c
			var r := d.length() / (size * 0.5)
			var ang := atan2(d.y, d.x)
			var li := int(floor((ang + PI) / TAU * lobes.size())) % lobes.size()
			var lobe := lobes[li]
			var n := rng.randf_range(-0.06, 0.06)
			var col := Color(0, 0, 0, 0)
			var hole_r := 0.12
			var chip_r := (0.42 if not soft else 0.3) * lobe
			if r < hole_r + n * 0.5:
				col = Color(0.02, 0.018, 0.016, 1.0)
			elif r < chip_r + n:
				var t := (r - hole_r) / maxf(chip_r - hole_r, 0.001)
				if wood:
					col = Color(0.16, 0.1, 0.06, 0.95 * (1.0 - t * 0.6))
				elif soft:
					col = Color(0.06, 0.05, 0.04, 0.9 * (1.0 - t))
				else:
					var v := lerpf(0.72, 0.5, t) + n
					col = Color(v, v * 0.97, v * 0.93, 0.9 * (1.0 - t * t))
			elif r < chip_r * 1.25 and not soft:
				var t2 := (r - chip_r) / (chip_r * 0.25)
				col = Color(0.08, 0.075, 0.07, 0.35 * (1.0 - t2))
			img.set_pixel(x, y, col)
	img.generate_mipmaps()
	var tex := ImageTexture.create_from_image(img)
	_cache[key] = tex
	return tex


## Soft round particle sprite.
static func soft_dot() -> ImageTexture:
	if _cache.has("dot"):
		return _cache["dot"]
	var size := 64
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	for y in size:
		for x in size:
			var r := (Vector2(x, y) - Vector2(size, size) * 0.5).length() / (size * 0.5)
			var a := clampf(1.0 - r, 0.0, 1.0)
			img.set_pixel(x, y, Color(1, 1, 1, a * a))
	img.generate_mipmaps()
	var tex := ImageTexture.create_from_image(img)
	_cache["dot"] = tex
	return tex


## Muzzle flash: a hot core with irregular spikes.
static func flash_star() -> ImageTexture:
	if _cache.has("flash"):
		return _cache["flash"]
	var size := 128
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	var rng := RandomNumberGenerator.new()
	rng.seed = 1943
	var spikes: Array[float] = []
	for i in 7:
		spikes.append(rng.randf() * TAU)
	for y in size:
		for x in size:
			var d := Vector2(x, y) - Vector2(size, size) * 0.5
			var r := d.length() / (size * 0.5)
			var ang := atan2(d.y, d.x)
			var spike := 0.0
			for s in spikes:
				var da := absf(wrapf(ang - s, -PI, PI))
				spike = maxf(spike, exp(-da * da * 160.0) * (1.0 - r))
			var core := exp(-r * r * 18.0)
			var v := clampf(core + spike * 0.9, 0.0, 1.0)
			img.set_pixel(x, y, Color(1.0, lerpf(0.55, 0.95, core), lerpf(0.25, 0.8, core), v))
	img.generate_mipmaps()
	var tex := ImageTexture.create_from_image(img)
	_cache["flash"] = tex
	return tex


## A 9×19 mm brass case.
static func casing_mesh() -> Mesh:
	if _cache.has("casing"):
		return _cache["casing"]
	var m := CylinderMesh.new()
	m.top_radius = 0.0048
	m.bottom_radius = 0.0049
	m.height = 0.019
	m.radial_segments = 12
	m.rings = 1
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.78, 0.58, 0.28)
	mat.metallic = 1.0
	mat.roughness = 0.32
	m.material = mat
	_cache["casing"] = m
	return m


## A flat-colour texture, used when a generated asset is missing.
static func flat(color: Color) -> ImageTexture:
	var key := "flat_" + color.to_html()
	if _cache.has(key):
		return _cache[key]
	var img := Image.create(4, 4, false, Image.FORMAT_RGBA8)
	img.fill(color)
	var tex := ImageTexture.create_from_image(img)
	_cache[key] = tex
	return tex
