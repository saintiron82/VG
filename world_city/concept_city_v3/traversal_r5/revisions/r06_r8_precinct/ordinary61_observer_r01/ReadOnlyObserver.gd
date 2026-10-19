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
	var event := {"event":"post_step_contact_or_support_event", "case":case_id, "walk_physics_frame":frame, "engine_physics_frame":Engine.get_physics_frames(), "controller_simulation_frame":controller.simulation_frames, "stage":controller.stage, "waypoint_index":controller.waypoint_index, "capsule_center":vec(body.position), "feet_y_m":body.position.y-.9, "velocity_readback":vec(body.velocity), "on_floor":body.is_on_floor(), "original_ground_ray_miss_total":misses, "original_ground_ray_miss_delta":miss_delta, "all_slide_contacts":contacts, "observer_repeat_support_ray":{"from":vec(body.position), "to":vec(ray_to), "collision_mask":1, "result":ray_result}}
	output.store_line(JSON.stringify(event))
	output.flush()
