class_name Terrain
extends RefCounted
## The land around the village: rolling bocage fields, a rise to the west (future cliffs), a fall to the sea in
## the north, and a river valley to the east, kept flat under the village street.
## height() is the single source of truth, shared by the visual mesh, the collision heightmap and object scattering.

const SIZE := 400.0          # metres, centred on the origin
const STEP := 2.0            # metres between height samples
const SEA_LEVEL := -1.4
const RIVER_X := 62.0


static func _hash(p: Vector2) -> float:
	var h := sin(p.dot(Vector2(127.1, 311.7))) * 43758.5453
	return h - floorf(h)


static func _noise(p: Vector2) -> float:
	var i := p.floor()
	var f := p - i
	var u := f * f * (Vector2(3, 3) - 2.0 * f)
	return lerpf(lerpf(_hash(i), _hash(i + Vector2(1, 0)), u.x), lerpf(_hash(i + Vector2(0, 1)), _hash(i + Vector2(1, 1)), u.x), u.y)


static func _fbm(p: Vector2) -> float:
	var v := 0.0
	var a := 0.5
	for i in 5:
		v += _noise(p) * a
		p = p * 2.07 + Vector2(31.0, 17.0)
		a *= 0.5
	return v / 0.96875


## 1 inside the village (kept flat at y = 0), fading to 0 over a soft margin.
static func village_mask(x: float, z: float) -> float:
	var dx := maxf(absf(x) - 22.0, 0.0)
	var dz := maxf(maxf(-75.0 - z, z - 64.0), 0.0)
	var street := 1.0 - smoothstep(0.0, 22.0, sqrt(dx * dx + dz * dz))
	# The harbour: a broad flat quayside ending at the quay wall (z 93), where it drops straight to the sea.
	var hx := maxf(absf(x) - 48.0, 0.0)
	var hz := maxf(40.0 - z, 0.0)
	var harbour := (1.0 - smoothstep(0.0, 16.0, sqrt(hx * hx + hz * hz))) * (1.0 - smoothstep(93.0, 95.0, z))
	# The square, the mairie and the churchyard to the east of the street.
	var ex := maxf(maxf(-x, x - 60.0), 0.0)
	var ez := maxf(absf(z) - 22.0, 0.0)
	var square := 1.0 - smoothstep(0.0, 14.0, sqrt(ex * ex + ez * ez))
	# The Le Goff farmyard to the south, where the mission begins.
	var farm := 1.0 - smoothstep(10.0, 24.0, Vector2(x + 16.0, z + 120.0).length())
	return maxf(maxf(street, harbour), maxf(square, farm))


static func river_center_x(z: float) -> float:
	return RIVER_X + sin(z * 0.021) * 9.0 + sin(z * 0.057) * 3.0


static func height(x: float, z: float) -> float:
	var p := Vector2(x, z)
	var h := (_fbm(p * 0.011) - 0.5) * 10.0 + (_fbm(p * 0.047 + Vector2(5, 9)) - 0.5) * 1.8
	# A broad rise to the west, where the cliffs and the strongpoint will go.
	h += 11.0 * exp(-(pow(x + 150.0, 2.0) / (2.0 * 55.0 * 55.0) + pow(z - 20.0, 2.0) / (2.0 * 110.0 * 110.0)))
	# The land falls away to the shore in the north.
	h -= smoothstep(66.0, 112.0, z) * (h + 4.5)
	# River valley in the east, widening toward the estuary.
	var width := lerpf(7.0, 22.0, smoothstep(-100.0, 100.0, z))
	var rd := absf(x - river_center_x(z)) / width
	var valley := exp(-rd * rd * 1.6)
	h = lerpf(h, minf(h, -2.2), valley)
	# Flat under the village.
	return lerpf(h, 0.0, village_mask(x, z))


static func build(root: Node3D, material: Material) -> StaticBody3D:
	var n := int(SIZE / STEP) + 1
	var half := SIZE * 0.5
	var heights := PackedFloat32Array()
	heights.resize(n * n)
	for j in n:
		for i in n:
			heights[j * n + i] = height(-half + i * STEP, -half + j * STEP)

	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for j in n:
		for i in n:
			var x := -half + i * STEP
			var z := -half + j * STEP
			var hl := heights[j * n + maxi(i - 1, 0)]
			var hr := heights[j * n + mini(i + 1, n - 1)]
			var hd := heights[maxi(j - 1, 0) * n + i]
			var hu := heights[mini(j + 1, n - 1) * n + i]
			st.set_normal(Vector3(hl - hr, 2.0 * STEP, hd - hu).normalized())
			st.set_uv(Vector2(x, z) / 2.0)
			st.add_vertex(Vector3(x, heights[j * n + i], z))
	for j in n - 1:
		for i in n - 1:
			var a := j * n + i
			st.add_index(a)
			st.add_index(a + 1)
			st.add_index(a + n)
			st.add_index(a + 1)
			st.add_index(a + n + 1)
			st.add_index(a + n)
	var mi := MeshInstance3D.new()
	mi.name = "TerrainMesh"
	mi.mesh = st.commit()
	mi.material_override = material
	root.add_child(mi)

	var body := StaticBody3D.new()
	body.name = "Ground"
	var cs := CollisionShape3D.new()
	var shape := HeightMapShape3D.new()
	shape.map_width = n
	shape.map_depth = n
	shape.map_data = heights
	cs.shape = shape
	cs.scale = Vector3(STEP, 1.0, STEP)
	body.add_child(cs)
	root.add_child(body)
	return body
