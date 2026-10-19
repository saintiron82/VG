extends RefCounted
## Candidate-only pure selection helper. The parent owns production integration.
## Metadata is an exact rectangular partition of the proved cell footprint.
static func score(pose: Transform3D, placement: Dictionary, module: Dictionary, observer: Vector3, fade_end_m: float, stable_key: String) -> Dictionary:
	var local := pose.affine_inverse() * observer
	var trim: Dictionary = module.trim
	var rects: Array = placement.get("visibility_footprint_rects_xy_m", [[0.0, 0.0, float(trim.width_m), float(trim.height_m)]])
	var z: Array = placement.get("visibility_local_z_bounds_m", [-0.0375, 0.0])
	var nearest := INF
	var nearest_corner := INF
	var farthest_corner := 0.0
	for rect in rects:
		var lo := Vector3(float(rect[0]), float(rect[1]), float(z[0]))
		var hi := Vector3(float(rect[2]), float(rect[3]), float(z[1]))
		var closest := Vector3(clampf(local.x, lo.x, hi.x), clampf(local.y, lo.y, hi.y), clampf(local.z, lo.z, hi.z))
		nearest = minf(nearest, local.distance_squared_to(closest))
		for x in [lo.x, hi.x]:
			for y in [lo.y, hi.y]:
				for zz in [lo.z, hi.z]:
					var distance := local.distance_squared_to(Vector3(x, y, zz))
					nearest_corner = minf(nearest_corner, distance)
					farthest_corner = maxf(farthest_corner, distance)
	var center := Vector3(float(trim.width_m)*0.5, float(trim.height_m)*0.5, (float(z[0])+float(z[1]))*0.5)
	return {"visible": nearest < fade_end_m*fade_end_m, "distance_squared": nearest, "nearest_corner_squared": nearest_corner, "farthest_corner_squared": farthest_corner, "center_distance_squared": local.distance_squared_to(center), "stable_key": stable_key}
static func less(a: Dictionary, b: Dictionary) -> bool:
	if a.distance_squared != b.distance_squared: return a.distance_squared < b.distance_squared
	if a.center_distance_squared != b.center_distance_squared: return a.center_distance_squared < b.center_distance_squared
	return str(a.stable_key) < str(b.stable_key)
