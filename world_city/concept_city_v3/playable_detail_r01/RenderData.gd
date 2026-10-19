extends RefCounted
## Render adapter with optional immutable rigid-part layers. Geometry is produced offline.
## Quad coordinates are world units; pitch/origin are metadata, never applied again.

const SCHEMA := "riverstone.voxel.render.v1"
const TRIANGLE_ORDER := [0, 2, 1, 0, 3, 2] # Godot uses clockwise front faces.

static func finite_number(value: Variant) -> bool:
	return (value is int or value is float) and is_finite(float(value))

static func vector_ok(value: Variant) -> bool:
	return value is Array and value.size() == 3 and finite_number(value[0]) and finite_number(value[1]) and finite_number(value[2])

static func vector(value: Array) -> Vector3:
	return Vector3(float(value[0]), float(value[1]), float(value[2]))

static func color_value(value: Variant) -> Variant:
	if value is Dictionary:
		value = value.get("rgba", value.get("color", value.get("hex", null)))
	if value is String:
		var html: String = value if value.begins_with("#") else "#" + value
		return Color.html(html) if Color.html_is_valid(html) else null
	if value is Array and value.size() in [3, 4]:
		for channel in value:
			if not finite_number(channel) or float(channel) < 0.0 or float(channel) > 1.0:
				return null
		return Color(float(value[0]), float(value[1]), float(value[2]), float(value[3]) if value.size() == 4 else 1.0)
	return null

static func read(path: String) -> Dictionary:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		return {"error": "Cannot read %s: %s" % [path, error_string(FileAccess.get_open_error())]}
	var parser := JSON.new()
	var bytes := file.get_buffer(file.get_length())
	var decoded := bytes
	if path.ends_with(".gz"):
		# Bounded common-render transport; integrity is the original compressed bytes.
		decoded = bytes.decompress_dynamic(64*1024*1024, FileAccess.COMPRESSION_GZIP)
		if decoded.is_empty(): return {"error":"Invalid gzip or render exceeds 64 MiB: "+path}
	var status := parser.parse(decoded.get_string_from_utf8())
	if status != OK:
		return {"error": "JSON error in %s, line %s: %s" % [path, parser.get_error_line(), parser.get_error_message()]}
	if not parser.data is Dictionary:
		return {"error": "Render input must be an object: " + path}
	var data: Dictionary = parser.data
	var problem := validate(data)
	if not problem.is_empty():
		return {"error": path + ": " + problem}
	var hasher := HashingContext.new()
	hasher.start(HashingContext.HASH_SHA256)
	hasher.update(bytes)
	return {"data": data, "sha256": hasher.finish().hex_encode()}

static func validate(data: Dictionary) -> String:
	if data.get("schema") != SCHEMA:
		return "Expected %s; first convert compiled cells using common/render_data.py" % SCHEMA
	if not finite_number(data.get("pitch")) or float(data.pitch) <= 0.0:
		return "pitch must be finite and positive"
	if not vector_ok(data.get("grid_origin")):
		return "grid_origin must contain three finite numbers"
	var bounds: Variant = data.get("bounds")
	if not bounds is Dictionary or not vector_ok(bounds.get("min")) or not vector_ok(bounds.get("max")):
		return "bounds must contain world-space min/max XYZ"
	var low := vector(bounds.min)
	var high := vector(bounds.max)
	if low.x >= high.x or low.y >= high.y or low.z >= high.z:
		return "bounds must have positive extent in every axis"
	if not data.get("materials") is Dictionary or data.materials.is_empty():
		return "materials must be a nonempty map"
	for material_id in data.materials:
		if not material_id is String or color_value(data.materials[material_id]) == null:
			return "Invalid material color: " + str(material_id)
	if not data.get("groups") is Array:
		return "groups must be an array"
	var all_groups: Array = data.groups.duplicate()
	var seen_parts: Dictionary = {}
	if data.has("rigid_parts"):
		if not data.rigid_parts is Array: return "rigid_parts must be an array"
		for part in data.rigid_parts:
			if not part is Dictionary or not vector_ok(part.get("pivot_world")) or not part.get("groups") is Array or part.groups.is_empty(): return "rigid part requires pivot and groups"
			var selector: Variant = part.get("selector")
			if not selector is Dictionary or selector.size() != 2 or not selector.get("instance") is String or not selector.get("part") is String: return "rigid part requires instance+part selector"
			var key := JSON.stringify([selector.instance, selector.part])
			if seen_parts.has(key): return "duplicate rigid part selector"
			seen_parts[key] = true
			var rows: Variant = part.get("source_world_basis")
			if not rows is Array or rows.size() != 3: return "rigid part source basis required"
			for row in rows:
				if not vector_ok(row): return "finite source basis required"
			var basis := Basis(vector(rows[0]), vector(rows[1]), vector(rows[2])).transposed()
			if not (basis * basis.transposed()).is_equal_approx(Basis.IDENTITY) or not is_equal_approx(basis.determinant(), 1.0): return "rigid part source basis must be proper orthonormal rotation"
			all_groups.append_array(part.groups)
	var quads := 0
	var tolerance: float = maxf(0.000001, (high - low).length() * 0.000001)
	for group in all_groups:
		if not group is Dictionary or not data.materials.has(group.get("material")) or not group.get("quads") is Array:
			return "Each group must reference a known material and contain quads"
		for quad in group.quads:
			if not quad is Array or quad.size() != 4:
				return "Each quad needs four perimeter-ordered world-space corners"
			for corner in quad:
				if not vector_ok(corner):
					return "Quad corners must contain three finite numbers"
				var point := vector(corner)
				if point.x < low.x - tolerance or point.y < low.y - tolerance or point.z < low.z - tolerance or point.x > high.x + tolerance or point.y > high.y + tolerance or point.z > high.z + tolerance:
					return "Quad extends beyond declared world bounds"
			var first := vector(quad[0])
			var normal := (vector(quad[1]) - first).cross(vector(quad[2]) - first)
			if normal.length_squared() == 0.0:
				return "Degenerate quad"
			if absf(normal.normalized().dot(vector(quad[3]) - first)) > tolerance:
				return "Non-planar quad"
			quads += 1
	if quads == 0:
		return "No renderable quads"
	return ""

static func bounds_of(data: Dictionary) -> AABB:
	return AABB(vector(data.bounds.min), vector(data.bounds.max) - vector(data.bounds.min))

static func stats(data: Dictionary) -> Dictionary:
	var groups: Array = data.groups.duplicate()
	for part in data.get("rigid_parts", []): groups.append_array(part.groups)
	var quads := 0
	for group in groups: quads += group.quads.size()
	return {"quads": quads, "triangles": quads * 2, "groups": groups.size(), "cell_count": data.get("cell_count", null), "rigid_parts": data.get("rigid_parts", []).size()}

static func build(data: Dictionary) -> Node3D:
	var asset := Node3D.new()
	asset.name = "WorldSpaceVoxelAsset"
	asset.set_meta("source_id", data.get("source_id"))
	asset.set_meta("master_hash", data.get("master_hash"))
	_add_groups(asset, data.groups, data.materials, Vector3.ZERO)
	var bindings: Array = []
	for part in data.get("rigid_parts", []):
		var node := Node3D.new()
		node.position = vector(part.pivot_world)
		asset.add_child(node)
		_add_groups(node, part.groups, data.materials, node.position)
		bindings.append({"selector": part.selector, "node": node, "rest_transform": node.transform, "pivot_world": part.pivot_world, "source_world_basis": part.source_world_basis})
	asset.set_meta("rigid_parts", bindings)
	return asset

static func _add_groups(parent: Node3D, groups: Array, materials: Dictionary, origin: Vector3) -> void:
	for group in groups:
		if group.quads.is_empty(): continue
		var vertices := PackedVector3Array()
		var normals := PackedVector3Array()
		vertices.resize(group.quads.size() * 6)
		normals.resize(group.quads.size() * 6)
		var offset := 0
		for quad in group.quads:
			var normal := (vector(quad[1]) - vector(quad[0])).cross(vector(quad[2]) - vector(quad[0])).normalized()
			for index in TRIANGLE_ORDER:
				vertices[offset] = vector(quad[index]) - origin
				normals[offset] = normal
				offset += 1
		var arrays: Array = []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = vertices
		arrays[Mesh.ARRAY_NORMAL] = normals
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		var material := StandardMaterial3D.new()
		material.albedo_color = color_value(materials[group.material])
		material.roughness = 1.0
		material.metallic_specular = 0.0
		if material.albedo_color.a < 1.0: material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mesh.surface_set_material(0, material)
		var instance := MeshInstance3D.new()
		instance.mesh = mesh
		parent.add_child(instance)
