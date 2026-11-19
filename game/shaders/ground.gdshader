// Open ground: wet mud blended with matted winter grass. The noise mask mirrors
// scripts/world/ground_mask.gd so footstep sounds match the visuals. Keep them in sync.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform sampler2D mud_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D mud_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D mud_orm : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_albedo : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D grass_orm : hint_default_white, filter_linear_mipmap_anisotropic, repeat_enable;
uniform float tile_size = 2.0;
uniform float mask_scale = 0.045;
uniform float wetness : hint_range(0.0, 1.0) = 0.65;

varying vec3 world_pos;

float hash12(vec2 p) {
	return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float vnoise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = p - i;
	vec2 u = f * f * (3.0 - 2.0 * f);
	float a = hash12(i);
	float b = hash12(i + vec2(1.0, 0.0));
	float c = hash12(i + vec2(0.0, 1.0));
	float d = hash12(i + vec2(1.0, 1.0));
	return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p) {
	float v = 0.0;
	float amp = 0.5;
	for (int i = 0; i < 4; i++) {
		v += vnoise(p) * amp;
		p = p * 2.03 + vec2(17.0, 9.0);
		amp *= 0.5;
	}
	return v / 0.9375;
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	vec2 uv = world_pos.xz / tile_size;
	// A second, rotated sample breaks up obvious tiling.
	vec2 uv2 = mat2(vec2(0.8, -0.6), vec2(0.6, 0.8)) * uv * 0.37 + vec2(0.31, 0.77);
	float grass = smoothstep(0.42, 0.58, fbm(world_pos.xz * mask_scale));
	float detail = fbm(world_pos.xz * 0.6);

	vec3 mud_a = mix(texture(mud_albedo, uv).rgb, texture(mud_albedo, uv2).rgb, 0.35);
	vec3 grass_a = mix(texture(grass_albedo, uv).rgb, texture(grass_albedo, uv2).rgb, 0.35);
	vec3 alb = mix(mud_a, grass_a, grass);
	vec3 orm = mix(texture(mud_orm, uv).rgb, texture(grass_orm, uv).rgb, grass);
	vec3 nrm = mix(texture(mud_normal, uv).rgb, texture(grass_normal, uv).rgb, grass);

	// Wet ground is darker and glossier, mud more than grass, with puddle-ish patches in the low noise.
	float wet = wetness * mix(1.0, 0.45, grass);
	float puddle = (1.0 - grass) * smoothstep(0.17, 0.11, detail) * wetness;
	ALBEDO = alb * mix(1.0, 0.6, wet) * mix(1.0, 0.7, puddle);
	// Wet earth is a soft sheen, not a mirror; only real puddles get glossy.
	ROUGHNESS = mix(mix(orm.g, max(orm.g * 0.75, 0.45), wet), 0.12, puddle);
	METALLIC = 0.0;
	AO = orm.r;
	NORMAL_MAP = mix(nrm, vec3(0.5, 0.5, 1.0), puddle);
}
