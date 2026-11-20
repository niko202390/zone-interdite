// A sheet torn from a cheap notebook, folded in four to fit an inside pocket, and crumpled.
// Fold lines are real creases: one side of each catches the light, the other falls into shadow.
// Crumple is a field of small creases lit from the lamp; edges are soft, frayed and grubby.
shader_type canvas_item;

uniform float seed = 3.0;
uniform vec2 light_dir = vec2(-0.6, -0.8);
uniform vec4 paper : source_color = vec4(0.83, 0.78, 0.66, 1.0);
uniform vec4 rule : source_color = vec4(0.45, 0.55, 0.7, 1.0);
uniform float rule_spacing = 0.043;
uniform vec2 aspect = vec2(1.45, 1.0);

float h(vec2 p) { return fract(sin(dot(p + seed, vec2(127.1, 311.7))) * 43758.5453); }
float n(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(h(i), h(i + vec2(1, 0)), u.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) { float v = 0.0; float a = 0.5; for (int i = 0; i < 5; i++) { v += a * n(p); p *= 2.03; a *= 0.5; } return v; }

// Crumple height: sharp ridges from folded noise at a few scales.
float crumple(vec2 p) {
	float r = 0.0;
	r += (1.0 - abs(fbm(p * 3.0) * 2.0 - 1.0)) * 0.6;
	r += (1.0 - abs(fbm(p * 7.0 + 4.0) * 2.0 - 1.0)) * 0.3;
	r += (1.0 - abs(fbm(p * 15.0 + 9.0) * 2.0 - 1.0)) * 0.1;
	return r;
}

void fragment() {
	vec2 uv = UV;
	vec2 p = uv * aspect;
	// Fold creases at the middle of each axis, slightly off true, as folded by hand.
	float fx = uv.x - (0.5 + 0.006 * sin(uv.y * 9.0 + seed));
	float fy = uv.y - (0.5 + 0.005 * sin(uv.x * 7.0 + seed * 2.0));
	// Height: crumple plus the tent of each fold.
	float e = 0.0015;
	float hc = crumple(p);
	float hx = crumple(p + vec2(e, 0.0));
	float hy = crumple(p + vec2(0.0, e));
	vec2 grad = vec2(hx - hc, hy - hc) / e;
	grad *= 0.012;
	grad.x += sign(fx) * exp(-abs(fx) / 0.012) * 0.55;
	grad.y += sign(fy) * exp(-abs(fy) / 0.012) * 0.45;
	float shade = clamp(1.0 + dot(grad, normalize(light_dir)) * 0.55, 0.62, 1.18);
	// Paper colour: fibres, foxing, and grime worked in along the folds and edges.
	vec3 col = paper.rgb * (0.94 + 0.08 * fbm(p * 40.0));
	col *= 1.0 - 0.10 * smoothstep(0.62, 0.8, fbm(p * 5.0 + 20.0));
	float crease = exp(-abs(fx) / 0.003) + exp(-abs(fy) / 0.003);
	col *= 1.0 - 0.16 * crease * (0.6 + 0.4 * n(p * 60.0));
	float edge = min(min(uv.x, 1.0 - uv.x) * aspect.x, min(uv.y, 1.0 - uv.y) * aspect.y);
	col *= mix(0.72, 1.0, smoothstep(0.0, 0.06, edge + 0.02 * fbm(p * 12.0)));
	// A faint ruled line every so often, mostly worn away.
	float ry = fract((uv.y - 0.08) / rule_spacing);
	float ruled = smoothstep(0.035, 0.0, abs(ry - 0.5) - 0.465) * step(0.08, uv.y) * 0.22;
	col = mix(col, rule.rgb, ruled * (0.5 + 0.5 * n(p * 8.0)));
	// The margin rule.
	col = mix(col, vec3(0.7, 0.35, 0.33), smoothstep(0.0025, 0.0, abs(uv.x - 0.075)) * 0.25);
	// A tea ring near one corner.
	float ring = length((uv - vec2(0.83, 0.82)) * aspect);
	col = mix(col, vec3(0.55, 0.4, 0.22), smoothstep(0.012, 0.0, abs(ring - 0.11 - 0.006 * n(uv * 40.0))) * 0.25);
	col *= shade;
	// Frayed edges.
	float fray = smoothstep(0.0, 0.008, edge - 0.004 * fbm(p * 60.0));
	COLOR = vec4(col, fray);
}
