// Cold winter sea and river water: near-black body, slow wind ripples, sky and lamp reflections.
shader_type spatial;
render_mode blend_mix, depth_draw_opaque, cull_back, diffuse_burley, specular_schlick_ggx;

uniform vec3 deep_color : source_color = vec3(0.012, 0.022, 0.026);
uniform vec3 shallow_color : source_color = vec3(0.04, 0.055, 0.05);
uniform float wave_scale = 0.08;
uniform float wave_speed = 0.35;
uniform vec2 flow = vec2(0.0, 0.0);
uniform float roughness_base : hint_range(0.0, 1.0) = 0.06;

varying vec3 world_pos;

float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float n2(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(h21(i), h21(i + vec2(1, 0)), u.x), mix(h21(i + vec2(0, 1)), h21(i + vec2(1, 1)), u.x), u.y);
}
float waves(vec2 p, float t) {
	float v = 0.0;
	v += n2(p * 1.0 + vec2(t * 0.6, t * 0.4)) * 0.5;
	v += n2(p * 2.3 - vec2(t * 0.9, -t * 0.5)) * 0.3;
	v += n2(p * 5.1 + vec2(-t * 1.3, t * 1.1)) * 0.2;
	return v;
}

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

void fragment() {
	float t = TIME * wave_speed;
	vec2 p = world_pos.xz * wave_scale + flow * TIME;
	float e = 0.05;
	float c = waves(p, t);
	float dx = waves(p + vec2(e, 0.0), t) - c;
	float dz = waves(p + vec2(0.0, e), t) - c;
	vec3 n = normalize(vec3(-dx * 3.0, 1.0, -dz * 3.0));
	NORMAL = normalize((VIEW_MATRIX * vec4(n, 0.0)).xyz);
	ALBEDO = mix(deep_color, shallow_color, c * 0.4);
	ROUGHNESS = roughness_base + c * 0.05;
	METALLIC = 0.0;
	SPECULAR = 0.6;
}
