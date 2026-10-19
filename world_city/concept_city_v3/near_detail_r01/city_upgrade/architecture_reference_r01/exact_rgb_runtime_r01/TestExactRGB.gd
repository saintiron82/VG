extends SceneTree
const Adapter = preload("ExactRGBRenderData.gd")
const Fixtures = preload("Fixtures.gd")
var checks := 0
var failures: Array = []
func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition: failures.append(message); push_error(message)
func _initialize() -> void:
	var rd: Script = Fixtures.load_rd(ProjectSettings.globalize_path(get_script().resource_path))
	var data: Dictionary = Fixtures.render_data()
	# Include a non-axis-aligned face so normal packing is checked too.
	data.groups[5].quads.append([[0,0,-0.2],[0.8,0,-0.2],[0.8,0.8,0.4],[0,0.8,0.4]])
	var source_text := JSON.stringify(data)
	var base: Node3D = rd.build(data)
	var result: Dictionary = Adapter.build(data, 2, Fixtures.exact_ids(data), rd)
	check(not result.has("error"), "valid fixture builds")
	if result.has("error"): quit(2); return
	var root: Node3D = result.node
	check(root.get_child_count() == 2, "one original mesh plus one appended mesh")
	check(result.original_group_nodes[0] == root.get_child(0), "prefix node index preserved")
	check(not result.original_group_nodes.has(1), "empty original group skip matches RenderData")
	var original: Array = base.get_child(0).mesh.surface_get_arrays(0)
	var preserved: Array = root.get_child(0).mesh.surface_get_arrays(0)
	check(original[Mesh.ARRAY_VERTEX] == preserved[Mesh.ARRAY_VERTEX], "prefix positions unchanged")
	check(original[Mesh.ARRAY_NORMAL] == preserved[Mesh.ARRAY_NORMAL], "prefix normals unchanged")
	check(base.get_child(0).mesh.surface_get_material(0).albedo_color == root.get_child(0).mesh.surface_get_material(0).albedo_color, "prefix material color unchanged")
	var raw_ranges: Array = []
	var raw: Array = Adapter.triangle_arrays(data, range(2, data.groups.size()), rd, raw_ranges)
	var packed: Array = result.batch_node.mesh.surface_get_arrays(0)
	for range_info in result.report.group_vertex_ranges:
		var old_node: MeshInstance3D = base.get_child(int(range_info.group_index) - 1)
		var old: Array = old_node.mesh.surface_get_arrays(0)
		var expected: Color = old_node.mesh.surface_get_material(0).albedo_color
		for offset in int(range_info.vertex_count):
			var at: int = int(range_info.first_vertex) + offset
			check(packed[Mesh.ARRAY_VERTEX][at] == old[Mesh.ARRAY_VERTEX][offset], "identical triangle position %s" % at)
			check(packed[Mesh.ARRAY_NORMAL][at] == old[Mesh.ARRAY_NORMAL][offset], "identical triangle normal %s" % at)
			check(raw[Mesh.ARRAY_COLOR][at] == expected, "exact CPU source color %s" % at)
			check(packed[Mesh.ARRAY_COLOR][at].to_rgba32() == expected.to_rgba32(), "exact GPU RGB8 bytes %s" % at)
	var material: StandardMaterial3D = result.batch_node.mesh.surface_get_material(0)
	check(material.vertex_color_use_as_albedo and material.vertex_color_is_srgb, "explicit sRGB vertex albedo flags")
	check(material.albedo_color == Color.WHITE and material.roughness == 1.0 and material.metallic_specular == 0.0, "matches original lighting properties")
	var other: Dictionary = Adapter.build(data, 2, Fixtures.exact_ids(data), rd)
	var other_material: StandardMaterial3D = other.batch_node.mesh.surface_get_material(0)
	check(material != other_material, "no shared cross-house material resource")
	check(result.batch_node.mesh != other.batch_node.mesh, "no shared cross-house mesh resource")
	material.albedo_color = Color.RED
	check(other_material.albedo_color == Color.WHITE, "editing one house cannot recolor another")
	check(JSON.stringify(data) == source_text, "source remains byte-for-byte JSON identical")
	var alpha: Dictionary = data.duplicate(true)
	alpha.materials.exact_0 = "#12345680"
	check(Adapter.build(alpha, 2, Fixtures.exact_ids(alpha), rd).has("error"), "transparent exact group rejected by default")
	var fallback: Dictionary = Adapter.build(alpha, 2, Fixtures.exact_ids(alpha), rd, "keep_groups")
	check(fallback.report.transparent_fallback_groups == [2], "explicit transparent fallback reported")
	check(fallback.original_group_nodes[2].mesh.surface_get_material(0).transparency == BaseMaterial3D.TRANSPARENCY_ALPHA, "fallback keeps alpha material")
	var floats: Dictionary = data.duplicate(true)
	floats.materials.exact_0 = [0.12345, 0.2, 0.3]
	check(Adapter.build(floats, 2, Fixtures.exact_ids(floats), rd).has("error"), "non-RGB8 input rejected instead of rounded")
	check(Adapter.build(data, -1, [], rd).has("error"), "invalid boundary rejected")
	check(Adapter.build(data, 2, ["missing"], rd).has("error"), "unknown material rejected")
	var partial: Dictionary = Adapter.build(data, 2, ["exact_0"], rd)
	check(partial.report.batched_group_count == 1 and partial.report.unbatched_appended_groups.size() == 7, "only selected suffix material is batched")
	check(partial.original_group_nodes.has(3), "unselected appended group remains independently mapped")
	var unchanged: Dictionary = Adapter.build(data, data.groups.size(), Fixtures.exact_ids(data), rd)
	check(unchanged.batch_node == null and unchanged.node.get_child_count() == base.get_child_count(), "all-prefix input has no batch and unchanged node count")
	var many: Array = []
	for i in 3345: many.append("#%06x" % i)
	var many_data: Dictionary = Fixtures.render_data(many)
	var many_result: Dictionary = Adapter.build(many_data, 2, Fixtures.exact_ids(many_data), rd)
	check(not many_result.has("error") and many_result.report.batched_group_count == 3345, "3345 unique RGB groups accepted without palette cap")
	check(many_result.node.get_child_count() == 2 and many_result.batch_node.mesh.get_surface_count() == 1, "3345 appended groups become one surface")
	var report := {"engine": Engine.get_version_info(), "checks": checks, "failures": failures, "passed": failures.is_empty(), "gpu_pixels_verified": false, "note": "Headless geometry/RGB8 tests only; run ColorDiagnostic on actual renderer."}
	var path := ProjectSettings.globalize_path("res://headless_tests.json")
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "  ")); file.close()
	print(JSON.stringify(report))
	base.free(); root.free(); other.node.free(); fallback.node.free(); partial.node.free(); unchanged.node.free(); many_result.node.free()
	quit(0 if failures.is_empty() else 1)
