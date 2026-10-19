extends RefCounted
const COLORS := ["#000000", "#ffffff", "#01070b", "#123456", "#7f8081", "#b4753c", "#36a47e", "#ed6b4f"]

static func render_data(palette: Array = COLORS) -> Dictionary:
	var materials := {"roof": "#645044", "empty_original": "#eeeeee"}
	var groups: Array = [{"material": "roof", "quads": [quad(-2.0)]}, {"material": "empty_original", "quads": []}]
	for i in palette.size():
		var id := "exact_%s" % i
		materials[id] = palette[i]
		groups.append({"material": id, "quads": [quad(float(i) * 1.1)]})
	return {"schema": "riverstone.voxel.render.v1", "pitch": 0.013, "grid_origin": [99, 80, -42],
		"bounds": {"min": [-3,-1,-1], "max": [maxf(10, palette.size() * 1.1 + 1),2,1]}, "materials": materials, "groups": groups,
		"source_id": "exact_rgb_fixture", "master_hash": "fixture-no-master"}

static func quad(x: float, y: float = 0.0) -> Array:
	return [[x,y,0.0],[x+0.8,y,0.0],[x+0.8,y+0.8,0.0],[x,y+0.8,0.0]]

static func exact_ids(data: Dictionary) -> Array:
	var ids: Array = []
	for group in data.groups.slice(2): ids.append(group.material)
	return ids

static func load_rd(script_path: String) -> Script:
	var source := script_path.get_base_dir().path_join("../../../../playable_detail_r01/RenderData.gd").simplify_path()
	for token in OS.get_cmdline_user_args():
		if token.begins_with("--rd="): source = token.substr(5)
	return load(source) as Script
