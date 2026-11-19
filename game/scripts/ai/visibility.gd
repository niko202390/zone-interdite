class_name Visibility
extends RefCounted
## How lit a point in the world is, as the AI sees it. The level sets an ambient base for the time
## of day; point lights, spotlights (guards' torches) and muzzle flashes add to it where they reach
## and aren't blocked. Also holds the world's background noise floor (rain and wind mask footsteps).

## Light level that dusk ambience alone gives (open sky, no lamps).
static var ambient := 0.2
## Background noise (dB SPL) that quiet sounds have to rise above to be heard.
static var noise_floor_db := 34.0
## Set by the level once its navigation mesh has finished baking.
static var nav_ready := false
## Areas where simply being seen is enough to be challenged (e.g. a checkpoint), as world-space AABBs.
static var restricted_zones: Array[AABB] = []

static var _lights: Array = []


static func register_light(light: Light3D) -> void:
	if not _lights.has(light):
		_lights.append(light)


## Called when a level loads. Lights don't need clearing; freed ones are pruned as they're found.
static func reset() -> void:
	restricted_zones.clear()
	nav_ready = false


static func in_restricted_zone(pos: Vector3) -> bool:
	for z in restricted_zones:
		if z.has_point(pos):
			return true
	return false


## Roughly 0.2 in open dusk, around 0.5 near a lit window, and 1.5 or more in a torch beam or muzzle flash.
static func light_level(world: World3D, pos: Vector3, exclude: Array[RID] = []) -> float:
	var level := ambient
	var space := world.direct_space_state
	var i := _lights.size() - 1
	while i >= 0:
		var entry: Variant = _lights[i]
		if not is_instance_valid(entry):
			_lights.remove_at(i)
			i -= 1
			continue
		i -= 1
		var light := entry as Light3D
		if not light.is_visible_in_tree() or light.light_energy <= 0.01:
			continue
		var lp := light.global_position
		var to := pos - lp
		var d := to.length()
		var reach: float
		var cone := 1.0
		if light is OmniLight3D:
			reach = (light as OmniLight3D).omni_range
		elif light is SpotLight3D:
			var spot := light as SpotLight3D
			reach = spot.spot_range
			var ang := rad_to_deg((-light.global_basis.z).angle_to(to))
			if ang > spot.spot_angle:
				continue
			cone = 1.0 - smoothstep(spot.spot_angle * 0.6, spot.spot_angle, ang)
		else:
			continue
		if d >= reach:
			continue
		var q := PhysicsRayQueryParameters3D.create(lp, pos, Game.LAYER_WORLD, exclude)
		var hit := space.intersect_ray(q)
		if not hit.is_empty() and hit.position.distance_to(pos) > 0.3:
			continue
		var falloff := pow(1.0 - d / reach, 2.0)
		level += light.light_energy * falloff * cone * 0.35
	return level
