extends "res://Traversal.gd"
## Post-motion observation only. Inherited controller receives identical inputs.
func _physics_process(delta: float) -> void:
	var was_walking:=stage=="walking"
	super._physics_process(delta)
	if not was_walking:return
	if not result.has("support_trace"):result.support_trace=[]
	if not body.is_on_floor():
		var ray:=PhysicsRayQueryParameters3D.create(body.position,body.position-Vector3(0,4,0),1)
		var hit:=get_world_3d().direct_space_state.intersect_ray(ray)
		var item: Dictionary={"walk_frame":route_frames,"capsule_center":vec(body.position),"velocity":vec(body.velocity),"long_ray_hit":not hit.is_empty()}
		if not hit.is_empty():
			item.ground_xyz_m=vec(hit.position);item.feet_gap_m=body.position.y-HEIGHT*.5-hit.position.y;item.source_id=str(hit.collider.get_meta("source_id","unknown"))
		result.support_trace.append(item)
		write_report()
