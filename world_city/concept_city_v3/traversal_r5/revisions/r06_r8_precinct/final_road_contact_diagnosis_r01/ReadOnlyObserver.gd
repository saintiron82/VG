extends Node
## Reads after the unchanged controller's priority-zero physics callback.
## No writes to controller, body, world, result, physics settings or acceptance.
var output: FileAccess
var previous_case := ""
var previous_frame := -1
var previous_misses := 0

func _ready() -> void:
	var path := ProjectSettings.globalize_path("res://evidence/observer_events.jsonl")
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--observer="): path = arg.substr(11)
	output = FileAccess.open(path, FileAccess.WRITE)
	if output:
		output.store_line(JSON.stringify({"event":"observer_ready", "observer_physics_priority":process_physics_priority, "controller_physics_priority":get_parent().process_physics_priority, "policy":"Post-controller reads only; repeat support ray is diagnostic, not the original saved local query."}))
		output.flush()

func vec(value: Vector3) -> Array:
	return [value.x,value.y,value.z]

func collider_info(collider) -> Dictionary:
	if not is_instance_valid(collider): return {"source_id":"unavailable"}
	return {"source_id":str(collider.get_meta("source_id",collider.name)), "category":str(collider.get_meta("category","unknown")), "instance_id":collider.get_instance_id()}

func _physics_process(_delta: float) -> void:
	var controller = get_parent()
	if not output or not is_instance_valid(controller.body) or controller.route.is_empty(): return
	var case_id := str(controller.route.id)
	if case_id != previous_case:
		previous_case = case_id
		previous_frame = -1
		previous_misses = 0
	var frame := int(controller.route_frames)
	if frame <= 0 or frame == previous_frame: return
	previous_frame = frame
	var body: CharacterBody3D = controller.body
	var misses := int(controller.result.get("ground_ray_miss_frames",0))
	var miss_delta := misses - previous_misses
	previous_misses = misses
	var contacts: Array = []
	for slide_index in body.get_slide_collision_count():
		var collision := body.get_slide_collision(slide_index)
		for contact_index in collision.get_collision_count():
			var contact := {"slide_index":slide_index, "contact_index":contact_index, "position":vec(collision.get_position(contact_index)), "normal":vec(collision.get_normal(contact_index)), "collider_shape_index":collision.get_collider_shape_index(contact_index), "collider":collider_info(collision.get_collider(contact_index)), "travel":vec(collision.get_travel()), "remainder":vec(collision.get_remainder()), "depth":collision.get_depth(), "face_index":null, "face_index_status":"KinematicCollision3D exposes a shape index, not a triangle face index."}
			contacts.append(contact)
	if miss_delta <= 0 and contacts.is_empty() and body.is_on_floor(): return
	var ray_to := body.position-Vector3(0,1.2,0)
	var ray := PhysicsRayQueryParameters3D.create(body.position,ray_to,1)
	var hit: Dictionary = controller.get_world_3d().direct_space_state.intersect_ray(ray)
	var ray_result: Dictionary = {"hit":not hit.is_empty()}
	if not hit.is_empty():
		ray_result.merge({"position":vec(hit.position), "normal":vec(hit.normal), "face_index":hit.get("face_index",null), "shape_index":hit.get("shape",null), "collider":collider_info(hit.get("collider"))})
	if miss_delta > 0 or not body.is_on_floor(): snapshot_nearby_shapes(controller, body.position, frame)
	var event := {"event":"post_step_contact_or_support_event", "case":case_id, "walk_physics_frame":frame, "engine_physics_frame":Engine.get_physics_frames(), "controller_simulation_frame":controller.simulation_frames, "stage":controller.stage, "waypoint_index":controller.waypoint_index, "capsule_center":vec(body.position), "feet_y_m":body.position.y-.9, "velocity_readback":vec(body.velocity), "on_floor":body.is_on_floor(), "original_ground_ray_miss_total":misses, "original_ground_ray_miss_delta":miss_delta, "all_slide_contacts":contacts, "observer_repeat_support_ray":{"from":vec(body.position), "to":vec(ray_to), "collision_mask":1, "result":ray_result}}
	output.store_line(JSON.stringify(event))
	output.flush()

func snapshot_nearby_shapes(controller, point: Vector3, frame: int) -> void:
	var records: Array = []
	for collider in controller.world.get_children():
		if not collider is StaticBody3D: continue
		for child in collider.get_children():
			if not child is CollisionShape3D or not child.shape is ConcavePolygonShape3D: continue
			var xf: Transform3D = child.global_transform
			var faces: PackedVector3Array = child.shape.get_faces()
			var nearby: Array = []
			for i in range(0,faces.size(),3):
				var a: Vector3 = xf*faces[i]
				var b: Vector3 = xf*faces[i+1]
				var c: Vector3 = xf*faces[i+2]
				if minf(a.x,minf(b.x,c.x)) > point.x+.1 or maxf(a.x,maxf(b.x,c.x)) < point.x-.1: continue
				if minf(a.z,minf(b.z,c.z)) > point.z+.1 or maxf(a.z,maxf(b.z,c.z)) < point.z-.1: continue
				if minf(a.y,minf(b.y,c.y)) > point.y or maxf(a.y,maxf(b.y,c.y)) < point.y-1.3: continue
				nearby.append({"face_index":i/3,"local_xyz_m":[vec(faces[i]),vec(faces[i+1]),vec(faces[i+2])],"world_xyz_float32_m":[vec(a),vec(b),vec(c)]})
			records.append({"collider":collider_info(collider),"basis_columns":[vec(xf.basis.x),vec(xf.basis.y),vec(xf.basis.z)],"origin":vec(xf.origin),"ray_from_in_collider_local":vec(xf.affine_inverse()*point),"ray_to_in_collider_local":vec(xf.affine_inverse()*(point-Vector3(0,1.2,0))),"nearby_faces":nearby})
	output.store_line(JSON.stringify({"event":"read_only_shapes_at_support_or_floor_event","case":str(controller.route.id),"walk_physics_frame":frame,"point":vec(point),"colliders":records}))
	output.flush()
