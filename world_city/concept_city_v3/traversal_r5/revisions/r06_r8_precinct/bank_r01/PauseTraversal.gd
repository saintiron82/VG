extends "res://Traversal.gd"
## Input-only stop/restart probe. Inherited walking/collision code remains unchanged.
var paused_frames_left := 0
var paused_route := ""
var completed_pause_indices: Array = []

func _physics_process(delta: float) -> void:
	if stage != "walking":
		super._physics_process(delta)
		return
	if paused_route != str(route.id):
		paused_route=str(route.id);completed_pause_indices=[];paused_frames_left=0
		result.pause_events=[];result.pause_physics_frames=0;result.pause_drift_m=0.0
	var stops: Array=route.get("pause_points_xyz_m",[])
	if paused_frames_left==0:
		for i in stops.size():
			if i in completed_pause_indices:continue
			var p:=RD.vector(stops[i])
			if Vector2(body.position.x-p.x,body.position.z-p.z).length()<=WAYPOINT_TOLERANCE:
				completed_pause_indices.append(i);paused_frames_left=int(route.get("pause_frames",60))
				result.pause_events.append({"index":i,"phase":"stop","position":vec(body.position),"walk_frame":route_frames})
				break
	if paused_frames_left>0:
		var prior:=body.position
		body.velocity.x=0;body.velocity.z=0
		body.velocity.y=-.25 if body.is_on_floor() else body.velocity.y-GRAVITY*delta
		body.move_and_slide();simulation_frames+=1;result.pause_physics_frames+=1
		result.pause_drift_m+=Vector2(body.position.x-prior.x,body.position.z-prior.z).length()
		if not body.is_on_floor():result.not_on_floor_frames+=1
		var ray:=PhysicsRayQueryParameters3D.create(body.position,body.position-Vector3(0,HEIGHT*.5+.3,0),1)
		if get_world_3d().direct_space_state.intersect_ray(ray).is_empty():result.ground_ray_miss_frames+=1
		paused_frames_left-=1
		if paused_frames_left==0:
			result.pause_events.append({"phase":"restart","position":vec(body.position),"walk_frame":route_frames})
			previous_position=body.position
		return
	super._physics_process(delta)

func finish_route(status: String) -> void:
	result.required_stop_count=route.get("pause_points_xyz_m",[]).size()
	result.completed_stop_count=completed_pause_indices.size()
	if status=="reached" and completed_pause_indices.size()!=result.required_stop_count:
		status="required_stop_not_reached"
	super.finish_route(status)
