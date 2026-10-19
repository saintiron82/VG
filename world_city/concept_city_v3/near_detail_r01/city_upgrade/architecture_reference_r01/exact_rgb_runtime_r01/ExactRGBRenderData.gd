extends RefCounted
## Optional runtime-only batching. Pass the existing D/RenderData.gd Script as rd.
## Input data, material IDs, source colors and world-space geometry stay untouched.

static func build(data: Dictionary, original_group_count: int, exact_material_ids: Array, rd: Script, transparency_policy: String = "reject") -> Dictionary:
	if rd == null: return {"error": "RenderData.gd dependency is required"}
	var problem: String = rd.validate(data)
	if not problem.is_empty(): return {"error": problem}
	if original_group_count < 0 or original_group_count > data.groups.size():
		return {"error": "original_group_count is outside source groups"}
	if transparency_policy not in ["reject", "keep_groups"]:
		return {"error": "transparency_policy must be reject or keep_groups"}
	var selected: Dictionary = {}
	for id in exact_material_ids:
		if not id is String or not data.materials.has(id): return {"error": "Unknown exact material ID: " + str(id)}
		selected[id] = true
	# Never batch prefix groups, including empty groups; their existing node mapping survives.
	var batched: Array = []
	var ordinary: Array = []
	var transparent: Array = []
	var quad_count := 0
	for gi in range(original_group_count, data.groups.size()):
		var group: Dictionary = data.groups[gi]
		if not selected.has(group.material):
			ordinary.append(gi)
			continue
		var color: Color = rd.color_value(data.materials[group.material])
		if color.a != 1.0:
			if transparency_policy == "reject":
				return {"error": "Transparent exact material rejected: " + group.material, "group_index": gi}
			transparent.append(gi)
			ordinary.append(gi)
			continue
		# Exact source-image RGB is 8-bit sRGB. Reject, never round arbitrary floats.
		if not is_rgb8(color): return {"error": "Exact material is not RGB8: " + group.material, "group_index": gi}
		batched.append(gi)
		quad_count += group.quads.size()
	var prefix: Dictionary = data.duplicate()
	prefix.groups = data.groups.slice(0, original_group_count)
	var asset: Node3D = rd.build(prefix)
	var group_nodes: Dictionary = {}
	var child_index := 0
	for gi in original_group_count:
		if data.groups[gi].quads.is_empty(): continue
		group_nodes[gi] = asset.get_child(child_index)
		child_index += 1
	var original_mesh_nodes := child_index
	# Rigid parts remain precisely as rd.build creates them. They are never merged.
	for gi in ordinary:
		var before := asset.get_child_count()
		rd._add_groups(asset, [data.groups[gi]], data.materials, Vector3.ZERO)
		if asset.get_child_count() > before: group_nodes[gi] = asset.get_child(before)
	var ranges: Array = []
	var batch_node: MeshInstance3D = null
	if quad_count > 0:
		var arrays: Array = triangle_arrays(data, batched, rd, ranges)
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		mesh.surface_set_material(0, make_material())
		batch_node = MeshInstance3D.new()
		batch_node.name = "ExactRGBAppendedOpaque"
		batch_node.mesh = mesh
		asset.add_child(batch_node)
	var report := {"original_group_count": original_group_count, "preserved_original_mesh_nodes": original_mesh_nodes,
		"batched_group_count": batched.size(), "batched_quads": quad_count, "batch_surfaces": 1 if quad_count > 0 else 0,
		"unbatched_appended_groups": ordinary, "transparent_fallback_groups": transparent, "group_vertex_ranges": ranges,
		"color_encoding": "unchanged RGB8 sRGB; vertex_color_use_as_albedo=true; vertex_color_is_srgb=true",
		"pitch_applied": false, "source_mutated": false, "palette_cap": null}
	asset.set_meta("exact_rgb_batch_report", report)
	return {"node": asset, "batch_node": batch_node, "original_group_nodes": group_nodes, "report": report}

static func is_rgb8(color: Color) -> bool:
	# Float32 representation of byte / 255 is accepted; arbitrary precision colors are not.
	for channel in [color.r, color.g, color.b]:
		if absf(channel * 255.0 - roundf(channel * 255.0)) > 0.00002: return false
	return true

static func make_material() -> StandardMaterial3D:
	# New resource for every asset: changing one house cannot recolor another.
	var material := StandardMaterial3D.new()
	material.albedo_color = Color.WHITE
	material.vertex_color_use_as_albedo = true
	material.vertex_color_is_srgb = true
	material.roughness = 1.0
	material.metallic_specular = 0.0
	material.transparency = BaseMaterial3D.TRANSPARENCY_DISABLED
	return material

static func triangle_arrays(data: Dictionary, group_indices: Array, rd: Script, ranges: Array) -> Array:
	var count := 0
	for gi in group_indices: count += data.groups[gi].quads.size() * 6
	var vertices := PackedVector3Array()
	var normals := PackedVector3Array()
	var colors := PackedColorArray()
	vertices.resize(count); normals.resize(count); colors.resize(count)
	var at := 0
	for gi in group_indices:
		var group: Dictionary = data.groups[gi]
		var color: Color = rd.color_value(data.materials[group.material])
		var first := at
		for quad in group.quads:
			# Same world-space conversion, normal expression and winding as D/RenderData.gd.
			var normal: Vector3 = (rd.vector(quad[1]) - rd.vector(quad[0])).cross(rd.vector(quad[2]) - rd.vector(quad[0])).normalized()
			for index in rd.TRIANGLE_ORDER:
				vertices[at] = rd.vector(quad[index])
				normals[at] = normal
				colors[at] = color
				at += 1
		ranges.append({"group_index": gi, "material_id": group.material, "first_vertex": first, "vertex_count": at - first})
	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_NORMAL] = normals
	arrays[Mesh.ARRAY_COLOR] = colors
	return arrays
