extends RefCounted
## Pure read-only source selector. Parent owns rendering/LOD and existing collision.
## Configure once, pass original loaded BIN per tile, request <=12 m around actor.
var selection: Dictionary = {}
var source_index: Dictionary = {}
var error := ""

func configure(policy: Dictionary, original_index: Dictionary, original_index_sha256: String) -> bool:
	if policy.get("schema", "") != "riverstone.public_paving.source_index.v1":
		error = "Unsupported public paving source index"; return false
	if policy.get("source_tile_index", {}).get("sha256", "") != original_index_sha256:
		error = "Paving/source tile index identity mismatch"; return false
	selection = policy; source_index = original_index
	return true

func _sha256(data: PackedByteArray) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_SHA256); context.update(data)
	return context.finish().hex_encode()

func near_faces_for_tile(tile_id: String, binary: PackedByteArray, observer: Vector3, radius_m: float = 10.0, maximum_faces: int = 4096) -> Dictionary:
	if selection.is_empty() or radius_m <= 0 or radius_m > 12 or maximum_faces < 1 or maximum_faces > 20000:
		return {"error": "Bounded configured source query required", "faces": []}
	if not selection.tiles.has(tile_id): return {"error": "Unknown owner tile", "faces": []}
	var record: Dictionary = selection.tiles[tile_id]
	if binary.size() != int(record.face_count) * 88 or _sha256(binary) != record.source_binary_sha256:
		return {"error": "Original source BIN identity mismatch", "faces": []}
	var result: Array = []
	for run in record.eligible_face_runs:
		for index in range(int(run[0]), int(run[1])):
			var offset := index * 88
			var vertices: Array[Vector3] = []
			for i in range(3):
				vertices.append(Vector3(binary.decode_double(offset + i * 24), binary.decode_double(offset + i * 24 + 8), binary.decode_double(offset + i * 24 + 16)))
			var low := Vector2(INF, INF); var high := Vector2(-INF, -INF)
			var nearest_height := INF
			for point in vertices:
				low = low.min(Vector2(point.x, point.z)); high = high.max(Vector2(point.x, point.z))
				nearest_height = minf(nearest_height, absf(point.y - observer.y))
			if high.x < observer.x - radius_m or low.x > observer.x + radius_m or high.y < observer.z - radius_m or low.y > observer.z + radius_m or nearest_height > 3.0: continue
			# Retain exactly the same decoded runtime Vector3 vertices. Compute their
			# plane in scalar float64: Vector3 cross is float32 in standard Godot,
			# and cancellation on source slivers can violate the strict 1e-5 m
			# plane/vertex proof even for these unchanged original vertices.
			var ux := float(vertices[1].x) - float(vertices[0].x)
			var uy := float(vertices[1].y) - float(vertices[0].y)
			var uz := float(vertices[1].z) - float(vertices[0].z)
			var vx := float(vertices[2].x) - float(vertices[0].x)
			var vy := float(vertices[2].y) - float(vertices[0].y)
			var vz := float(vertices[2].z) - float(vertices[0].z)
			var nx := uy * vz - uz * vy
			var ny := uz * vx - ux * vz
			var nz := ux * vy - uy * vx
			if ny <= 0.0: continue # Source slivers must never create downward paving.
			var grade := sqrt(nx * nx + nz * nz) / ny
			if grade > float(selection.policy.maximum_grade): continue
			var a := -nx / ny; var b := -nz / ny
			var c := float(vertices[0].y) - a * float(vertices[0].x) - b * float(vertices[0].z)
			var normal := Vector3(nx, ny, nz)
			var material_index := int(binary.decode_u32(offset + 76))
			if str(source_index.material_ids[material_index]) not in ["road", "space_civic"]:
				return {"error": "Non-public material in selected source face", "faces": []}
			result.append({"tile_id": tile_id, "face_index": index, "owners": run[2], "vertices_xyz_m": vertices, "plane_y_xz_m": [a, b, c], "normal": normal.normalized(), "material": source_index.material_ids[material_index]})
			if result.size() >= maximum_faces: return {"faces": result, "truncated": true, "whole_city_coverage_pass": false}
	return {"faces": result, "truncated": false, "whole_city_coverage_pass": false}

func rigid_frame(plane: Array) -> Transform3D:
	var normal := Vector3(-float(plane[0]), 1, -float(plane[1])).normalized()
	var right := Vector3(1, float(plane[0]), 0).normalized()
	var tangent := normal.cross(right)
	return Transform3D(Basis(right, tangent, normal), Vector3(0, float(plane[2]), 0))

func _area(polygon: Array) -> float:
	var total := 0.0
	for i in polygon.size():
		var a: Vector2 = polygon[i]; var b: Vector2 = polygon[(i + 1) % polygon.size()]
		total += a.x * b.y - b.x * a.y
	return total * 0.5

func _halfplane(subject: Array, a: Vector2, b: Vector2, orientation: float, keep_inside: bool) -> Array:
	if subject.is_empty(): return []
	var result: Array = []; var previous: Vector2 = subject[-1]
	var pd := orientation * (b - a).cross(previous - a)
	for value in subject:
		var current: Vector2 = value
		var cd := orientation * (b - a).cross(current - a)
		var previous_inside := pd >= 0 if keep_inside else pd <= 0
		var current_inside := cd >= 0 if keep_inside else cd <= 0
		if previous_inside != current_inside and absf(pd - cd) > 1e-12:
			result.append(previous.lerp(current, pd / (pd - cd)))
		if current_inside: result.append(current)
		previous = current; pd = cd
	return result

func _subtract(subject: Array, cover: Array) -> Array:
	var inside: Array = subject; var outside: Array = []
	var orientation := 1.0 if _area(cover) > 0 else -1.0
	for i in cover.size():
		if inside.is_empty(): break
		var a: Vector2 = cover[i]; var b: Vector2 = cover[(i + 1) % cover.size()]
		var piece := _halfplane(inside, a, b, orientation, false)
		if absf(_area(piece)) > 1e-10: outside.append(piece)
		inside = _halfplane(inside, a, b, orientation, true)
	return outside

func footprint_supported(corners: Array, faces: Array, plane_tolerance_m: float = 0.00001) -> bool:
	if corners.size() != 4 or faces.is_empty(): return false
	var plane: Array = faces[0].plane_y_xz_m
	var subject: Array = []
	for value in corners:
		var point: Vector3 = value
		if absf(point.y - float(plane[0]) * point.x - float(plane[1]) * point.z - float(plane[2])) > plane_tolerance_m: return false
		subject.append(Vector2(point.x, point.z))
	var remaining: Array = [subject]
	for face in faces:
		var cover: Array = []; var same_plane := true
		for value in face.vertices_xyz_m:
			var point: Vector3 = value
			if absf(point.y - float(plane[0]) * point.x - float(plane[1]) * point.z - float(plane[2])) > plane_tolerance_m: same_plane = false; break
			cover.append(Vector2(point.x, point.z))
		if not same_plane: continue
		var next: Array = []
		for piece in remaining: next.append_array(_subtract(piece, cover))
		remaining = next
		if remaining.is_empty(): return true
	var area := 0.0
	for piece in remaining: area += absf(_area(piece))
	return area <= 1e-8

## Bounded observer-local planner. Pass only nearby verified faces returned by
## near_faces_for_tile for already-loaded tiles/dependency owners. No tile IO,
## global index traversal, mesh duplication, scaling or collider creation here.
## The Transform3D maps a safe 1 m XY/+Z master onto its original source plane,
## then translates +0.0375 m along its unit normal. Its back remains on source.
func plan_local_modules(faces: Array, observer: Vector3, radius_m: float = 10.0, maximum_candidates: int = 256, maximum_modules: int = 120) -> Dictionary:
	var started := Time.get_ticks_usec()
	var result := {"modules": [], "truncated": false, "reason": "", "candidate_checks": 0, "grid_slots_visited": 0, "input_face_count": faces.size(), "plane_group_count": 0, "support_budget_rejections": 0, "whole_city_coverage_pass": false, "collision_change": false}
	if not observer.is_finite() or not is_finite(radius_m) or radius_m <= 0.0 or radius_m > 10.0 or maximum_candidates < 1 or maximum_candidates > 256 or maximum_modules < 1 or maximum_modules > 120 or faces.size() > 4096:
		result.error = "Finite observer, radius <= 10 m, <= 4096 nearby faces, <= 256 candidates and <= 120 modules required"
		return _finish_local_plan(result, started)
	var groups: Dictionary = {}
	for face in faces:
		if not face is Dictionary or not face.has_all(["vertices_xyz_m", "plane_y_xz_m", "tile_id", "face_index", "owners"]) or face.vertices_xyz_m.size() != 3 or face.plane_y_xz_m.size() != 3 or face.owners.is_empty():
			result.error = "Only complete verified source-face records are accepted"; result.modules = []
			return _finish_local_plan(result, started)
		var plane: Array = face.plane_y_xz_m
		if not is_finite(float(plane[0])) or not is_finite(float(plane[1])) or not is_finite(float(plane[2])) or Vector2(float(plane[0]), float(plane[1])).length() > 0.25:
			result.error = "Invalid or excessive source grade"; return _finish_local_plan(result, started)
		var low := Vector2(INF, INF); var high := Vector2(-INF, -INF); var distance := INF
		for value in face.vertices_xyz_m:
			if not value is Vector3 or not value.is_finite():
				result.error = "Finite original Vector3 source vertices required"; return _finish_local_plan(result, started)
			var point: Vector3 = value
			if absf(point.y - float(plane[0]) * point.x - float(plane[1]) * point.z - float(plane[2])) > 0.00001:
				result.error = "Source plane/vertex mismatch"; return _finish_local_plan(result, started)
			low = low.min(Vector2(point.x, point.z)); high = high.max(Vector2(point.x, point.z))
			distance = minf(distance, point.distance_squared_to(observer))
		var normal: Vector3 = (face.vertices_xyz_m[1] - face.vertices_xyz_m[0]).cross(face.vertices_xyz_m[2] - face.vertices_xyz_m[0])
		if normal.y <= 0.0:
			result.error = "Degenerate/downward source face"; return _finish_local_plan(result, started)
		if high.x < observer.x - radius_m or low.x > observer.x + radius_m or high.y < observer.z - radius_m or low.y > observer.z + radius_m: continue
		# Quantization only groups candidates. Exact plane checks below never average
		# these planes or let a nearby different level contribute support.
		var key := "%.7f/%.7f/%.6f" % [0.0 if float(plane[0]) == 0.0 else float(plane[0]), 0.0 if float(plane[1]) == 0.0 else float(plane[1]), 0.0 if float(plane[2]) == 0.0 else float(plane[2])]
		if not groups.has(key): groups[key] = {"plane": plane, "faces": [], "distance": distance, "key": key}
		groups[key].faces.append({"source": face, "low": low, "high": high})
		groups[key].distance = minf(float(groups[key].distance), distance)
	var ordered: Array = groups.values()
	ordered.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a.key < b.key if a.distance == b.distance else a.distance < b.distance)
	result.plane_group_count = ordered.size()
	for group in ordered:
		var frame := rigid_frame(group.plane)
		var inverse := frame.affine_inverse()
		var observer_local: Vector3 = inverse * observer
		var low := Vector2(INF, INF); var high := Vector2(-INF, -INF)
		for record in group.faces:
			for point in record.source.vertices_xyz_m:
				var local: Vector3 = inverse * point
				low = low.min(Vector2(local.x, local.y)); high = high.max(Vector2(local.x, local.y))
		# Proper rotations preserve distance; sqrt(1+grade^2) conservatively
		# covers the projection of the requested XZ disk onto this slope plane.
		var local_radius := radius_m * sqrt(1.0 + 0.25 * 0.25)
		low = low.max(Vector2(observer_local.x - local_radius, observer_local.y - local_radius))
		high = high.min(Vector2(observer_local.x + local_radius, observer_local.y + local_radius))
		if high.x - low.x < 1.0 or high.y - low.y < 1.0: continue
		# The finite plane bbox is pruned before any grid enumeration. Each
		# per-plane list has at most 22 x 22 entries at the supported radius.
		var grid: Array = []
		for ix in range(ceili(low.x - 0.00001), floori(high.x - 1.0 + 0.00001) + 1):
			for iy in range(ceili(low.y - 0.00001), floori(high.y - 1.0 + 0.00001) + 1):
				if result.grid_slots_visited >= 4096:
					result.truncated = true; result.reason = "grid_slot_budget"; return _finish_local_plan(result, started)
				result.grid_slots_visited += 1
				grid.append({"x": ix, "y": iy, "distance": Vector2(float(ix)+0.5-observer_local.x, float(iy)+0.5-observer_local.y).length_squared()})
		grid.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return (a.x < b.x if a.x != b.x else a.y < b.y) if a.distance == b.distance else a.distance < b.distance)
		for cell in grid:
			var ix: int = cell.x; var iy: int = cell.y
			var corners: Array = [frame * Vector3(ix, iy, 0), frame * Vector3(ix + 1, iy, 0), frame * Vector3(ix + 1, iy + 1, 0), frame * Vector3(ix, iy + 1, 0)]
			var inside := true
			var patch_low := Vector2(INF, INF); var patch_high := Vector2(-INF, -INF)
			for point in corners:
				var xz := Vector2(point.x, point.z)
				if xz.distance_squared_to(Vector2(observer.x, observer.z)) > radius_m * radius_m: inside = false; break
				patch_low = patch_low.min(xz); patch_high = patch_high.max(xz)
			if not inside: continue
			if result.candidate_checks >= maximum_candidates:
				result.truncated = true; result.reason = "candidate_check_budget"; return _finish_local_plan(result, started)
			result.candidate_checks += 1
			var support := _supported_local_patch(corners, group, patch_low, patch_high)
			if support.get("budget_exceeded", false): result.support_budget_rejections += 1; result.truncated = true
			if not support.supported: continue
			var anchor: Vector3 = frame * Vector3(ix, iy, 0.0375)
			# Negative grid coordinates use positive modulo for stable variants.
			var seed_index := posmod(ix * 17 + iy * 31, 3)
			result.modules.append({"kind": "paving", "variant_family": "safe_offset_r01", "seed": [41873, 41879, 41887][seed_index], "width_m": 1.0, "height_m": 1.0, "trim_offset_m": Vector2.ZERO, "transform": Transform3D(frame.basis, anchor), "original_plane_y_xz_m": group.plane.duplicate(), "source_owner_indices": support.owners, "source_face_refs": support.refs, "maximum_visual_collision_difference_m": 0.0375, "collision_change": false})
			if result.modules.size() >= maximum_modules:
				result.truncated = true; result.reason = "module_budget"; return _finish_local_plan(result, started)
	if result.support_budget_rejections > 0: result.reason = "support_proof_budget"
	return _finish_local_plan(result, started)

func _finish_local_plan(result: Dictionary, started: int) -> Dictionary:
	result.elapsed_usec = Time.get_ticks_usec() - started
	return result

## All contributors are exact coplanar source triangles. AABB only prunes;
## finite polygon-union subtraction proves the entire square is supported.
## Work limits fail closed: no approximate or partially proved square is emitted.
func _supported_local_patch(corners: Array, group: Dictionary, low: Vector2, high: Vector2) -> Dictionary:
	var answer := {"supported": false, "owners": [], "refs": [], "budget_exceeded": false}
	var plane: Array = group.plane
	var origin := Vector2(corners[0].x, corners[0].z)
	var subject: Array = []
	for point in corners:
		if absf(point.y - float(plane[0]) * point.x - float(plane[1]) * point.z - float(plane[2])) > 0.00001: return answer
		subject.append([float(point.x) - float(origin.x), float(point.z) - float(origin.y)])
	var remaining: Array = [subject]
	var covers := 0
	for record in group.faces:
		if record.high.x < low.x or record.low.x > high.x or record.high.y < low.y or record.low.y > high.y: continue
		var cover: Array = []; var same_plane := true
		for point in record.source.vertices_xyz_m:
			if absf(point.y - float(plane[0]) * point.x - float(plane[1]) * point.z - float(plane[2])) > 0.00001: same_plane = false; break
			cover.append([float(point.x) - float(origin.x), float(point.z) - float(origin.y)])
		if not same_plane: continue
		covers += 1
		if covers > 256: answer.budget_exceeded = true; return answer
		answer.refs.append([record.source.tile_id, record.source.face_index])
		for owner in record.source.owners:
			if not answer.owners.has(owner): answer.owners.append(owner)
		var next: Array = []
		for piece in remaining:
			next.append_array(_subtract64(piece, cover))
			if next.size() > 512: answer.budget_exceeded = true; return answer
		remaining = next
		if remaining.is_empty(): answer.supported = true; answer.owners.sort(); return answer
	var uncovered := 0.0
	for piece in remaining: uncovered += absf(_polygon_area64(piece))
	answer.supported = covers > 0 and uncovered <= 1e-8
	answer.owners.sort()
	return answer

## Float64 scalar clipping is intentional: Vector2 interpolation is float32 in
## standard Godot builds and can split shared source edges into false slivers.
func _polygon_area64(polygon: Array) -> float:
	var area := 0.0
	for i in polygon.size():
		var a: Array = polygon[i]; var b: Array = polygon[(i + 1) % polygon.size()]
		area += float(a[0]) * float(b[1]) - float(b[0]) * float(a[1])
	return area * 0.5

func _halfplane64(subject: Array, a: Array, b: Array, orientation: float, keep_inside: bool) -> Array:
	if subject.is_empty(): return []
	var result: Array = []; var previous: Array = subject[-1]
	var ex := float(b[0]) - float(a[0]); var ey := float(b[1]) - float(a[1])
	var pd := orientation * (ex * (float(previous[1]) - float(a[1])) - ey * (float(previous[0]) - float(a[0])))
	for current in subject:
		var cd := orientation * (ex * (float(current[1]) - float(a[1])) - ey * (float(current[0]) - float(a[0])))
		var previous_inside := pd >= 0 if keep_inside else pd <= 0
		var current_inside := cd >= 0 if keep_inside else cd <= 0
		if previous_inside != current_inside and absf(pd - cd) > 1e-15:
			var t := pd / (pd - cd)
			result.append([float(previous[0]) + (float(current[0]) - float(previous[0])) * t, float(previous[1]) + (float(current[1]) - float(previous[1])) * t])
		if current_inside: result.append(current)
		previous = current; pd = cd
	return result

func _subtract64(subject: Array, cover: Array) -> Array:
	var inside: Array = subject; var outside: Array = []
	var orientation := 1.0 if _polygon_area64(cover) > 0 else -1.0
	for i in cover.size():
		if inside.is_empty(): break
		var a: Array = cover[i]; var b: Array = cover[(i + 1) % cover.size()]
		var piece := _halfplane64(inside, a, b, orientation, false)
		if absf(_polygon_area64(piece)) > 1e-12: outside.append(piece)
		inside = _halfplane64(inside, a, b, orientation, true)
	return outside
