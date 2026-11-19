class_name DuskEnvironment
extends RefCounted
## Blue hour under winter overcast on the Breton coast: a last cold glow in the west, fog off the sea,
## and drizzle. This is where all the global look settings live.

static func apply(root: Node3D) -> Dictionary:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.085, 0.115, 0.2)
	sky_mat.sky_horizon_color = Color(0.5, 0.48, 0.55)
	sky_mat.sky_curve = 0.11
	sky_mat.ground_bottom_color = Color(0.02, 0.022, 0.026)
	sky_mat.ground_horizon_color = Color(0.32, 0.32, 0.36)
	sky_mat.ground_curve = 0.04
	sky_mat.sun_angle_max = 40.0
	sky_mat.sun_curve = 0.06
	sky_mat.energy_multiplier = 1.5

	var sky := Sky.new()
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_256

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_sky_contribution = 1.0
	env.ambient_light_energy = 1.6
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY

	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.7

	env.sdfgi_enabled = true
	env.sdfgi_use_occlusion = true
	env.sdfgi_cascades = 5
	env.sdfgi_min_cell_size = 0.18
	env.sdfgi_energy = 1.0

	env.ssao_enabled = true
	env.ssao_radius = 1.4
	env.ssao_intensity = 2.2
	env.ssil_enabled = true
	env.ssil_intensity = 0.8
	env.ssr_enabled = true
	env.ssr_max_steps = 48

	env.glow_enabled = true
	env.glow_intensity = 0.55
	env.glow_strength = 0.9
	env.glow_bloom = 0.04
	env.glow_hdr_threshold = 1.1

	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_light_color = Color(0.32, 0.34, 0.4)
	env.fog_light_energy = 1.0
	env.fog_density = 0.016
	env.fog_sky_affect = 0.55
	env.fog_aerial_perspective = 0.4
	env.fog_height = 4.0
	env.fog_height_density = 0.05

	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.02
	env.volumetric_fog_albedo = Color(0.75, 0.77, 0.82)
	env.volumetric_fog_emission = Color(0.01, 0.012, 0.018)
	env.volumetric_fog_length = 80.0
	env.volumetric_fog_anisotropy = 0.4
	env.volumetric_fog_ambient_inject = 0.35
	env.volumetric_fog_sky_affect = 0.25

	env.adjustment_enabled = true
	env.adjustment_saturation = 0.8
	env.adjustment_contrast = 1.06

	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	we.environment = env
	root.add_child(we)

	# There's no sun disc, just the last low cold light from the west-south-west.
	var sun := DirectionalLight3D.new()
	sun.name = "LastLight"
	sun.rotation_degrees = Vector3(-8.0, -110.0, 0.0)
	sun.light_color = Color(0.66, 0.66, 0.8)
	sun.light_energy = 0.9
	sun.light_angular_distance = 3.0
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 90.0
	sun.directional_shadow_blend_splits = true
	sun.sky_mode = DirectionalLight3D.SKY_MODE_LIGHT_ONLY
	root.add_child(sun)

	return {"environment": env, "sun": sun, "world_environment": we}
