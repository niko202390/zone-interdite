// Aged wartime paper: yellowed stock, fibre grain, foxing spots, a fold crease, darkened edges and a
// faint coffee ring. Drawn under the typed text of the briefing pages.
shader_type canvas_item;

uniform vec4 base : source_color = vec4(0.86, 0.81, 0.68, 1.0);
uniform float seed = 1.0;
uniform float fold = 0.5;
uniform vec2 ring_pos = vec2(0.78, 0.82);

float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7)) + seed * 17.0) * 43758.5453); }
float n(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(h(i), h(i + vec2(1, 0)), u.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) { float v = 0.0; float a = 0.5; for (int i = 0; i < 5; i++) { v += n(p) * a; p *= 2.1; a *= 0.5; } return v; }

void fragment() {
	vec2 uv = UV;
	vec3 c = base.rgb;
	c *= 0.93 + 0.1 * fbm(uv * vec2(9.0, 12.0));                 // mottling
	c *= 0.97 + 0.03 * n(uv * vec2(900.0, 40.0));                // fibre grain
	float edge = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
	c *= mix(0.72, 1.0, smoothstep(0.0, 0.09, edge + 0.02 * fbm(uv * 30.0)));   // handled, darkened edges
	float fox = smoothstep(0.72, 0.8, fbm(uv * 14.0 + 3.0));
	c = mix(c, c * vec3(0.78, 0.64, 0.45), fox * 0.5);          // foxing
	float crease = exp(-pow((uv.y - fold) * 260.0, 2.0));
	c *= 1.0 - 0.18 * crease;
	c += vec3(0.03) * exp(-pow((uv.y - fold - 0.006) * 260.0, 2.0));
	float r = length((uv - ring_pos) * vec2(1.0, 1.35));
	float ring = smoothstep(0.012, 0.0, abs(r - 0.085)) * (0.5 + 0.5 * n(uv * 60.0));
	c = mix(c, c * vec3(0.7, 0.55, 0.38), ring * 0.45);
	COLOR = vec4(c, 1.0);
}
