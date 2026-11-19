// The title written in invisible ink. A faint wet sheen trails behind the nib and dries away in a second.
// Later, heat from a lighter flame passing beneath the paper scorches the letters brown, column by column.
shader_type canvas_item;

uniform vec2 label_size = vec2(1200.0, 170.0);
uniform float write_x = 0.0;          // pen position across the text, 0..1
uniform float write_duration = 3.6;   // seconds the whole line took to write
uniform float reveal_x = -0.3;        // flame position across the text, 0..1
uniform float reveal_width = 0.11;
uniform vec4 scorch : source_color = vec4(0.33, 0.15, 0.045, 1.0);
uniform vec4 wet : source_color = vec4(0.62, 0.66, 0.7, 1.0);

varying vec2 lp;

float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float n(vec2 p) {
	vec2 i = floor(p); vec2 f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
	return mix(mix(h(i), h(i + vec2(1, 0)), u.x), mix(h(i + vec2(0, 1)), h(i + vec2(1, 1)), u.x), u.y);
}

void vertex() {
	lp = VERTEX;
}

void fragment() {
	float glyph = texture(TEXTURE, UV).a * COLOR.a;
	float x = lp.x / label_size.x;
	float since = (write_x - x) * write_duration;
	float sheen = step(0.0, since) * exp(-max(since, 0.0) * 2.4) * (0.6 + 0.4 * n(lp * 0.4));
	// Scorching is patchy: thicker strokes and fibres brown first.
	float grain = n(lp * 0.06) * 0.07 + n(lp * 0.9) * 0.025;
	float heat = smoothstep(0.0, reveal_width, reveal_x - x + grain);
	vec3 burnt = scorch.rgb * (0.75 + 0.5 * n(lp * 0.25));
	vec3 col = mix(wet.rgb, burnt, step(0.001, heat));
	float a = glyph * max(sheen * 0.17, heat * 0.92);
	COLOR = vec4(col, a);
}
