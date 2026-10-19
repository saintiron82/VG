shader_type spatial;
render_mode diffuse_burley, specular_disabled;
// UV is in source-operation coordinates; no world-up or screen-space grain.
// UV2.x: 0 = unresolved base palette, 1 = fibers, 2 = end-grain.
uniform vec4 base_color : source_color = vec4(0.396, 0.275, 0.192, 1.0);
uniform sampler2D wood_fibers : filter_nearest_mipmap, repeat_enable;
uniform sampler2D wood_endgrain : filter_nearest_mipmap, repeat_disable;
uniform float grain_strength : hint_range(0.0, 0.5) = 0.32;
uniform float fade_start_m = 10.0;
uniform float fade_end_m = 28.0;
void fragment() {
 float mode = UV2.x;
 float fade = 1.0 - smoothstep(fade_start_m, fade_end_m, length(VERTEX));
 float tone = 0.5;
 if (mode > 1.5) { tone = texture(wood_endgrain, UV).r; }
 else if (mode > 0.5) { tone = texture(wood_fibers, UV).r; }
 float modulation = (tone - 0.5) * 2.0 * grain_strength * fade;
 // Wear is gentle along pale fibers; never modifies the palette hue or mesh.
 float wear = max(0.0, tone - 0.60) * UV2.y * fade;
 ALBEDO = base_color.rgb * (1.0 + modulation + wear);
 ROUGHNESS = 1.0;
 METALLIC = 0.0;
 SPECULAR = 0.0;
}
