extends RefCounted
## Stable per-operation tone aliases. No geometry, texture, per-cell randomness or mutable palette edits.
const RD=preload("res://RenderData.gd")
static func resolve(slot: String,materials: Dictionary,palette: Dictionary,aliases: Array) -> Variant:
	for alias in aliases:
		if str(alias.get("material_id",""))!=slot:continue
		var base:=str(alias.get("base_material_id",""))
		if not materials.has(base):return null
		var value: Variant=RD.color_value(palette.get(base,materials[base]))
		var multiplier: Variant=alias.get("luminance_multiplier")
		if value==null or not (multiplier is int or multiplier is float) or not is_finite(float(multiplier)) or float(multiplier)<.8 or float(multiplier)>1.2:return null
		var color: Color=value
		var linear:=color.srgb_to_linear()
		linear.r=clampf(linear.r*float(multiplier),0,1)
		linear.g=clampf(linear.g*float(multiplier),0,1)
		linear.b=clampf(linear.b*float(multiplier),0,1)
		color=linear.linear_to_srgb()
		return [color.r,color.g,color.b,color.a]
	return palette.get(slot,materials.get(slot))
