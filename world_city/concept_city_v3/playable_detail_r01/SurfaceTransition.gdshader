shader_type spatial;
render_mode diffuse_burley, specular_disabled;
// Actual common-compiled voxel relief remains intact near the observer.
// Fade material contrast toward the source before a narrow outer dither band.
// No vertex displacement, alpha sorting, wall replacement or collision change.
uniform vec3 detail_observer;
uniform float fade_start_m = 5.0;
uniform float fade_end_m = 9.0;
varying float detail_weight;
varying float edge_weight;
varying vec3 authored_albedo;

void vertex() {
	vec3 world_position = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float d = distance(world_position, detail_observer);
	detail_weight = 1.0 - smoothstep(fade_start_m, fade_end_m, d);
	edge_weight = 1.0 - smoothstep(max(fade_end_m - 0.6, fade_start_m), fade_end_m, d);
	authored_albedo = INSTANCE_CUSTOM.rgb;
}

void fragment() {
	float screen_noise = fract(52.9829189 * fract(dot(floor(FRAGCOORD.xy), vec2(0.06711056, 0.00583715))));
	if (edge_weight <= screen_noise) discard;
	ALBEDO = mix(authored_albedo, COLOR.rgb, detail_weight);
	ROUGHNESS = 1.0;
}
