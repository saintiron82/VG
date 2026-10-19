extends "res://Traversal.gd"
## Separate kinematic fixture. The inherited native collider builder and source
## checks are unchanged. No movement controller, vehicle or suspension model.
var fixture: Dictionary
var cart_shape: BoxShape3D
var cart_stage := "loading"
var cart_settle := 0
var cart_case_index := -1
var cart_routes: Array = []
var poses: Array = []
var pose_index := 0
var previous_transform := Transform3D.IDENTITY
var previous_valid := false
var case_started := 0
var report_started := 0

func _ready() -> void:
	super._ready()
	if report.status == "error": return
	body.collision_layer = 0
	body.collision_mask = 0
	fixture = prepared.cart_fixture
	cart_shape = BoxShape3D.new()
	cart_shape.size = Vector3(float(fixture.width_m), float(fixture.overall_height_m) - float(fixture.ground_clearance_m), float(fixture.length_m))
	for r in routes:
		if bool(r.get("cart_test", true)): cart_routes.append(r)
		elif str(r.id) in ["NEGATIVE_ACTUAL_SOLID_WALL", "NEGATIVE_UNBRIDGED_RIVER"]:
			var control: Dictionary = r.duplicate(true)
			control["cart_control"] = "wall_overlap" if str(r.id) == "NEGATIVE_ACTUAL_SOLID_WALL" else "gap_support"
			cart_routes.append(control)
	report = {"schema":"riverstone.r9.rigid_cart_clearance.v1", "status":"loading", "engine":"GodotPhysics3D native shape casts and four-point ray support", "engine_version":Engine.get_version_info(), "prepared_path":str(options.get("prepared")), "prepared_sha256":FileAccess.get_sha256(str(options.get("prepared"))), "sources":prepared.sources, "implementation_hashes":prepared.implementation_hashes, "fixture":fixture, "routes":[], "errors":[], "limits":["Kinematic rigid envelope, not suspension, wheel rolling, traction, steering feasibility or vehicle dynamics.", "Continuous straight translation swept against exact native colliders. Turning/ground-orientation changes use a conservative rotation-envelope inflation.", "Four support raycasts per pose are bounded discrete samples, not a continuous wheel-contact theorem.", "Body envelope begins at the explicit 0.15 m underbody clearance and ends at 2.2 m overall height; wheels are four support points."]}
	report_started = Time.get_ticks_msec()

func next_route() -> void:
	cart_stage = "loading"
	cart_case_index += 1
	if cart_case_index >= cart_routes.size():
		finish_suite()
		return
	route = cart_routes[cart_case_index]
	result = {"id":route.id, "status":"running", "pass":false, "source_road_ids":route.source_road_ids, "test_scope":route.test_scope, "samples":0, "support_rays":0, "translation_casts":0, "conservative_rotation_casts":0, "max_support_plane_residual_m":0.0, "min_support_normal_y":1.0, "max_step_orientation_deg":0.0, "max_rotation_envelope_inflation_m":0.0, "support_ids":{}, "pose_samples":[], "first_failure":null, "full_route_length_m":route.length_m}
	build_route_collision()
	if stage == "finished": return
	poses = create_poses(route.points)
	result.planned_poses = poses.size()
	pose_index = 0
	previous_valid = false
	cart_settle = 0
	case_started = Time.get_ticks_msec()
	cart_stage = "settling"
	print("CART_ROUTE_START " + str(route.id) + " poses=" + str(poses.size()))

func create_poses(points: Array) -> Array:
	var out: Array = []
	var previous_yaw := 0.0
	for i in range(points.size() - 1):
		var a := RD.vector(points[i])
		var b := RD.vector(points[i + 1])
		var d := b - a
		var horizontal := Vector2(d.x, d.z)
		if horizontal.length() < 0.00001: continue
		var yaw := atan2(d.x, d.z)
		if i > 0:
			var angle := wrapf(yaw - previous_yaw, -PI, PI)
			var turn_steps := maxi(1, ceili(absf(angle) / deg_to_rad(float(fixture.maximum_orientation_increment_deg))))
			for k in range(1, turn_steps + 1):
				out.append({"point":a, "yaw":previous_yaw + angle * float(k) / float(turn_steps), "phase":"turn", "source_segment":i})
		var steps := maxi(1, ceili(horizontal.length() / float(fixture.maximum_sample_translation_m)))
		for k in range(0 if i == 0 else 1, steps + 1):
			out.append({"point":a.lerp(b, float(k) / float(steps)), "yaw":yaw, "phase":"translation", "source_segment":i})
		previous_yaw = yaw
	return out

func _physics_process(_delta: float) -> void:
	if cart_stage == "loading" or cart_stage == "finished": return
	if cart_stage == "settling":
		cart_settle += 1
		if cart_settle >= 3:
			if route.has("cart_control"):
				run_cart_control()
				return
			cart_stage = "testing"
		return
	# Read-only native physics queries; batching does not alter engine state.
	for _batch in range(12):
		if pose_index >= poses.size():
			finish_cart_route("clear_supported")
			return
		var p: Dictionary = poses[pose_index]
		var sample := support_pose(p)
		if sample.has("failure"):
			result.first_failure = sample
			finish_cart_route(str(sample.failure))
			return
		var transform: Transform3D = sample.transform
		var query := PhysicsShapeQueryParameters3D.new()
		query.shape = cart_shape
		query.transform = transform
		query.collision_mask = 3
		query.margin = 0.001
		var collisions := get_world_3d().direct_space_state.intersect_shape(query, 16)
		if not collisions.is_empty():
			result.first_failure = {"failure":"envelope_overlap", "pose_index":pose_index, "point":vec(p.point), "phase":p.phase, "source_segment":p.source_segment, "collider_ids":hit_ids(collisions), "cart_transform":xform_dict(transform), "support":sample.support}
			finish_cart_route("envelope_overlap")
			return
		if previous_valid:
			var orientation_angle := previous_transform.basis.get_rotation_quaternion().angle_to(transform.basis.get_rotation_quaternion())
			result.max_step_orientation_deg = maxf(result.max_step_orientation_deg, rad_to_deg(orientation_angle))
			var inflation := cart_shape.size.length() * sin(orientation_angle * 0.5)
			# Every intermediate rotated corner is within this radius of the
			# previous orientation. Isotropic box expansion bounds that sphere.
			var swept := BoxShape3D.new()
			swept.size = cart_shape.size + Vector3.ONE * (2.0 * inflation)
			query.shape = swept
			query.transform = previous_transform
			query.motion = transform.origin - previous_transform.origin
			var expanded_initial := get_world_3d().direct_space_state.intersect_shape(query, 16)
			if not expanded_initial.is_empty():
				result.first_failure = {"failure":"conservative_rotation_envelope_overlap", "pose_index":pose_index, "point":vec(p.point), "phase":p.phase, "source_segment":p.source_segment, "collider_ids":hit_ids(expanded_initial), "orientation_change_deg":rad_to_deg(orientation_angle), "inflation_m":inflation, "support":sample.support}
				finish_cart_route("conservative_rotation_envelope_overlap")
				return
			var fraction := get_world_3d().direct_space_state.cast_motion(query)
			result.translation_casts += 1
			if inflation > 0.000001: result.conservative_rotation_casts += 1
			result.max_rotation_envelope_inflation_m = maxf(result.max_rotation_envelope_inflation_m, inflation)
			if fraction.size() != 2 or fraction[0] < 0.99999:
				result.first_failure = {"failure":"swept_envelope_blocked", "pose_index":pose_index, "point":vec(p.point), "phase":p.phase, "source_segment":p.source_segment, "safe_unsafe_fractions":Array(fraction), "cart_transform":xform_dict(transform), "inflation_m":inflation, "support":sample.support}
				finish_cart_route("swept_envelope_blocked")
				return
		previous_transform = transform
		previous_valid = true
		result.samples += 1
		if pose_index % 40 == 0 or pose_index == poses.size()-1:
			result.pose_samples.append({"index":pose_index, "point":vec(p.point), "phase":p.phase, "source_segment":p.source_segment, "cart_transform":xform_dict(transform), "support":sample.support})
		pose_index += 1

func support_pose(p: Dictionary) -> Dictionary:
	var point: Vector3 = p.point
	var yaw_basis := Basis(Vector3.UP, float(p.yaw))
	var half_track := float(fixture.support_track_m) * 0.5
	var half_base := float(fixture.support_wheelbase_m) * 0.5
	var local_points := [Vector3(-half_track, 0, -half_base),Vector3(half_track, 0, -half_base),Vector3(-half_track, 0, half_base),Vector3(half_track, 0, half_base)]
	var support: Array = []
	var heights: Array[float] = []
	for local in local_points:
		var foot: Vector3 = point + yaw_basis * local
		var q := PhysicsRayQueryParameters3D.create(foot + Vector3.UP * 0.75, foot - Vector3.UP * 1.5, 1)
		var hit := get_world_3d().direct_space_state.intersect_ray(q)
		result.support_rays += 1
		if hit.is_empty(): return {"failure":"support_missing", "pose_index":pose_index, "point":vec(point), "phase":p.phase, "source_segment":p.source_segment, "missing_support_index":support.size(), "support":support}
		var normal: Vector3 = hit.normal
		var id := str(hit.collider.get_meta("source_id", "unknown"))
		support.append({"position":vec(hit.position), "normal":vec(normal), "source_id":id})
		heights.append(float(hit.position.y))
		result.min_support_normal_y = minf(result.min_support_normal_y, normal.y)
		result.support_ids[id] = int(result.support_ids.get(id, 0)) + 1
		if normal.y < cos(deg_to_rad(30.0)): return {"failure":"support_slope_over_30deg", "pose_index":pose_index, "point":vec(point), "support":support}
	var middle := (heights[0] + heights[1] + heights[2] + heights[3]) * 0.25
	var slope_x := ((heights[1] + heights[3]) - (heights[0] + heights[2])) / (4.0 * half_track)
	var slope_z := ((heights[2] + heights[3]) - (heights[0] + heights[1])) / (4.0 * half_base)
	var residual := 0.0
	for i in range(4): residual = maxf(residual, absf(heights[i] - (middle + slope_x * local_points[i].x + slope_z * local_points[i].z)))
	result.max_support_plane_residual_m = maxf(result.max_support_plane_residual_m, residual)
	if residual > float(fixture.support_plane_residual_max_m): return {"failure":"four_supports_nonplanar", "pose_index":pose_index, "point":vec(point), "phase":p.phase, "residual_m":residual, "support":support}
	var x := (yaw_basis.x + Vector3.UP * slope_x).normalized()
	var z_hint := yaw_basis.z + Vector3.UP * slope_z
	var normal := z_hint.cross(x).normalized()
	var z := x.cross(normal).normalized()
	var basis := Basis(x, normal, z)
	var center := Vector3(point.x, middle, point.z) + normal * (float(fixture.ground_clearance_m) + cart_shape.size.y * 0.5)
	return {"transform":Transform3D(basis, center), "support":support, "support_plane_residual_m":residual}

func run_cart_control() -> void:
	var point := (RD.vector(route.points[0]) + RD.vector(route.points[-1])) * 0.5
	var delta := RD.vector(route.points[-1]) - RD.vector(route.points[0])
	var yaw := atan2(delta.x, delta.z)
	result.control_mode = route.cart_control
	result.control_point = vec(point)
	if str(route.cart_control) == "wall_overlap":
		var q := PhysicsShapeQueryParameters3D.new()
		q.shape = cart_shape
		q.collision_mask = 3
		q.transform = Transform3D(Basis(Vector3.UP, yaw), point + Vector3.UP * (float(fixture.ground_clearance_m) + cart_shape.size.y * 0.5))
		var hits := get_world_3d().direct_space_state.intersect_shape(q, 16)
		var ids := hit_ids(hits)
		result.control_contact_ids = ids
		result.expected_contact_id = route.expected_contact_id
		result.control_scope = "Source-exact native solid wall envelope-intersection control. No cart route/support claim on the small isolated wall fixture."
		finish_cart_route("expected_native_wall_collision" if str(route.expected_contact_id) in ids else "negative_wall_not_detected")
	else:
		var sample := support_pose({"point":point, "yaw":yaw, "phase":"negative_gap", "source_segment":0})
		result.control_support = sample
		result.control_scope = "Source-exact finite unbridged river-gap four-point support query at midpoint of the original negative-control route."
		finish_cart_route("expected_gap_support_absence" if sample.get("failure", "") == "support_missing" else "negative_gap_not_detected")

func hit_ids(hits: Array) -> Array:
	var out: Array = []
	for hit in hits: out.append(str(hit.collider.get_meta("source_id", "unknown")))
	return out

func xform_dict(t: Transform3D) -> Dictionary:
	return {"position_m":vec(t.origin), "basis_columns":[vec(t.basis.x),vec(t.basis.y),vec(t.basis.z)]}

func finish_cart_route(status: String) -> void:
	result.status = status
	result.pass = status == "clear_supported" or status == "expected_native_wall_collision" or status == "expected_gap_support_absence"
	result.elapsed_ms = Time.get_ticks_msec() - case_started
	report.routes.append(result)
	print("CART_ROUTE_RESULT " + JSON.stringify(result))
	write_report()
	cart_stage = "loading"
	call_deferred("next_route")

func finish_suite() -> void:
	cart_stage = "finished"
	var passed := 0
	var samples := 0
	var casts := 0
	var rays := 0
	for r in report.routes:
		if r.pass: passed += 1
		samples += int(r.samples)
		casts += int(r.translation_casts)
		rays += int(r.support_rays)
	report.status = "pass" if passed == report.routes.size() and passed > 0 else "fail"
	report.summary = {"cases":report.routes.size(), "passed":passed, "supported_clear_poses":samples, "native_shape_sweeps":casts, "ground_support_rays":rays, "elapsed_ms":Time.get_ticks_msec()-report_started}
	write_report()
	print("CART_SUITE_RESULT " + JSON.stringify(report.summary))
	get_tree().quit(0 if report.status == "pass" else 2)
