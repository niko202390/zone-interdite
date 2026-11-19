class_name GroundMask
extends RefCounted
## Where open ground is grass and where it's mud. Mirrors the noise in shaders/ground.gdshader
## so footsteps and impacts match what you see. Keep the two in sync.

const SCALE := 0.045


static func _hash(p: Vector2) -> float:
	var h := sin(p.dot(Vector2(127.1, 311.7))) * 43758.5453
	return h - floorf(h)


static func _vnoise(p: Vector2) -> float:
	var i := p.floor()
	var f := p - i
	var u := f * f * (Vector2(3.0, 3.0) - 2.0 * f)
	var a := _hash(i)
	var b := _hash(i + Vector2(1, 0))
	var c := _hash(i + Vector2(0, 1))
	var d := _hash(i + Vector2(1, 1))
	return lerpf(lerpf(a, b, u.x), lerpf(c, d, u.x), u.y)


static func fbm(p: Vector2) -> float:
	var v := 0.0
	var amp := 0.5
	for i in 4:
		v += _vnoise(p) * amp
		p = p * 2.03 + Vector2(17.0, 9.0)
		amp *= 0.5
	return v / 0.9375


## 1 = grass, 0 = mud.
static func grassiness(pos: Vector3) -> float:
	return smoothstep(0.42, 0.58, fbm(Vector2(pos.x, pos.z) * SCALE))


static func surface_at(pos: Vector3) -> String:
	return "grass" if grassiness(pos) > 0.5 else "mud"
