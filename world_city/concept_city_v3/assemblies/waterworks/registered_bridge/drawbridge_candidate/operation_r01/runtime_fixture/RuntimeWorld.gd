extends Node3D
## Reconstructed closed-world actor fixture. Real city population/nav integration is absent.
const Adapter=preload("../OperationAdapter.gd")
const Volumes=preload("../OperationSensorVolumes.gd")
const Controller=preload("../OperationController.gd")
const ACTOR_LAYER=2
const GATE_LAYER=4
var adapter
var contract={}
var volumes
var actors={}
var gate_bodies={}
var gates={}
var admission_acks={"road":{"closed":true,"generation":0},"navigation":{"closed":true,"generation":0}}
var gate_pending={}
var exit_permissions={"road":{},"navigation":{}}
var coverage_issues=[]
var gate_faults=[]
var actor_root: Node3D
var frame: Transform3D
var sequence=0
var last_output={}
var audit_log=[]
var coverage_query_limit=256
var trusted_actuator_feedback=true
var last_sensor_physics_frame=-1
var volume_signatures={}
func configure(contract_path: String,pack_path: String,viewer=null) -> bool:
	contract=JSON.parse_string(FileAccess.get_file_as_string(contract_path)); frame=Adapter.rigid(contract.bridge_to_world); adapter=Adapter.new()
	if not adapter.configure_from_files(contract_path,pack_path,viewer): return false
	actor_root=Node3D.new(); actor_root.name="RegisteredFixtureActors"; add_child(actor_root)
	volumes=Volumes.new(); add_child(volumes); volumes.configure(contract,ACTOR_LAYER)
	for family in volumes.regions:
		for a in volumes.regions[family]: volume_signatures[a.get_instance_id()]={"transform":a.global_transform,"size":a.get_child(0).shape.size}
	for kind in ["road","navigation"]:
		gates[kind]=[]
		for sign_value in [-1,1]:
			var body=StaticBody3D.new(); body.name=kind+"_admission_"+str(sign_value); body.collision_layer=GATE_LAYER; body.collision_mask=ACTOR_LAYER
			var cs=CollisionShape3D.new(); var shape=BoxShape3D.new(); shape.size=Vector3(0.5,7,17) if kind=="road" else Vector3(22,24,0.5); cs.shape=shape; body.add_child(cs); add_child(body)
			var center=Vector3(sign_value*20,6.5,0) if kind=="road" else Vector3(0,8,sign_value*45)
			body.transform=frame*Transform3D(Basis.IDENTITY,center); gates[kind].append({"body":body,"shape":cs,"center":center,"size":shape.size,"transform":body.transform}); gate_bodies[body.get_instance_id()]=body
	return true
func attach_mechanism(view) -> bool: return adapter.attach_mechanism(view)
func bridge_local_to_world() -> Transform3D: return frame
func _shape_signature(shape: Shape3D) -> Dictionary:
	if shape is CapsuleShape3D: return {"type":"capsule","radius":shape.radius,"height":shape.height}
	if shape is BoxShape3D: return {"type":"box","size":[shape.size.x,shape.size.y,shape.size.z]}
	return {}
func add_actor(ident: String,kind: String,origin: Vector3) -> CharacterBody3D:
	assert(not actors.has(ident)); var body=CharacterBody3D.new(); body.name=ident; body.collision_layer=ACTOR_LAYER; body.collision_mask=GATE_LAYER
	var cs=CollisionShape3D.new(); var bounds; var asset=""
	if kind=="pedestrian":
		var shape=CapsuleShape3D.new(); shape.radius=0.4; shape.height=1.8; cs.shape=shape; cs.position.y=0.9; bounds={"min":[-0.4,0,-0.4],"max":[0.4,1.8,0.4]}
	elif kind=="cart":
		var shape=BoxShape3D.new(); shape.size=Vector3(5,2.4,2.2); cs.shape=shape; cs.position.y=1.2; bounds={"min":[-2.5,0,-1.1],"max":[2.5,2.4,1.1]}
	else:
		assert(kind=="vessel"); asset="registered_port_rigged_barge_24m"; bounds=contract.vessel_catalog[asset].duplicate(true)
		var shape=BoxShape3D.new(); shape.size=Vector3(bounds.max[0]-bounds.min[0],bounds.max[1]-bounds.min[1],bounds.max[2]-bounds.min[2]); cs.shape=shape; cs.position=Vector3((bounds.max[0]+bounds.min[0])*0.5,(bounds.max[1]+bounds.min[1])*0.5,(bounds.max[2]+bounds.min[2])*0.5)
	body.add_child(cs); actor_root.add_child(body); body.transform=frame*Transform3D(Basis.IDENTITY,origin)
	actors[ident]={"body":body,"shape":cs,"kind":kind,"asset_key":asset,"bounds_local_m":bounds,"shape_signature":_shape_signature(cs.shape),"shape_transform":cs.transform}; return body
func pose(ident: String) -> Transform3D: return frame.affine_inverse()*actors[ident].body.global_transform
func move_actor(ident: String,delta_bridge: Vector3): return actors[ident].body.move_and_collide(frame.basis*delta_bridge)
func _bounds(ident: String) -> Dictionary: return Controller.transformed_box(actors[ident].bounds_local_m,Adapter.dict_transform(pose(ident)))
func _walk_bodies(node: Node,found: Dictionary):
	if node is PhysicsBody3D: found[node.get_instance_id()]=node
	for child in node.get_children(): _walk_bodies(child,found)
func _coverage() -> bool:
	coverage_issues.clear(); coverage_issues.append_array(gate_faults); var known={}; var tree_bodies={}; _walk_bodies(self,tree_bodies)
	for ident in actors:
		var a=actors[ident]
		if not is_instance_valid(a.body) or not is_instance_valid(a.shape) or not a.body.is_inside_tree(): coverage_issues.append("registry_missing_body:"+ident); continue
		known[a.body.get_instance_id()]=ident
		if a.body.get_parent()!=actor_root: coverage_issues.append("registry_body_outside_owned_root:"+ident)
		var expected_exceptions={}
		for kind in exit_permissions:
			if exit_permissions[kind].has(ident):
				for gate in gates[kind]: expected_exceptions[gate.body.get_instance_id()]=true
		var actual_exceptions={}
		for exception in a.body.get_collision_exceptions(): actual_exceptions[exception.get_instance_id()]=true
		if actual_exceptions!=expected_exceptions: coverage_issues.append("unowned_collision_exception:"+ident)
		if a.body.collision_layer!=ACTOR_LAYER or a.body.collision_mask!=GATE_LAYER: coverage_issues.append("actor_mask_mismatch:"+ident)
		if a.shape.disabled or a.shape.get_parent()!=a.body or a.body.get_child_count()!=1: coverage_issues.append("actor_shape_coverage_mismatch:"+ident)
		if _shape_signature(a.shape.shape)!=a.shape_signature or a.shape.transform!=a.shape_transform: coverage_issues.append("actor_shape_changed:"+ident)
		if not Controller.rigid_valid(Adapter.dict_transform(pose(ident))): coverage_issues.append("actor_scaled_or_invalid_transform:"+ident)
	for ident in tree_bodies:
		if not known.has(ident) and not gate_bodies.has(ident): coverage_issues.append("unregistered_physics_body:"+str(ident))
	for kind in gates:
		for gate in gates[kind]:
			if gate.body.transform!=gate.transform or gate.shape.shape.size!=gate.size or gate.body.collision_mask!=ACTOR_LAYER or not gate.body.get_collision_exceptions().is_empty(): coverage_issues.append("gate_geometry_or_mask_changed:"+kind)
	var exclude: Array[RID]=[]
	for b in gate_bodies.values(): exclude.append(b.get_rid())
	for family in volumes.regions:
		for area in volumes.regions[family]:
			var signature=volume_signatures[area.get_instance_id()]
			if area.global_transform!=signature.transform or area.get_child(0).shape.size!=signature.size or area.collision_mask!=ACTOR_LAYER: coverage_issues.append("sensor_volume_changed:"+family)
			var query=PhysicsShapeQueryParameters3D.new(); query.shape=area.get_child(0).shape; query.transform=area.global_transform; query.collision_mask=0xFFFFFFFF; query.exclude=exclude; query.collide_with_bodies=true; query.collide_with_areas=false
			var found=get_world_3d().direct_space_state.intersect_shape(query,coverage_query_limit)
			if found.size()>=coverage_query_limit: coverage_issues.append("physics_query_saturated:"+family)
			for item in found:
				if not known.has(item.collider_id): coverage_issues.append("unregistered_query_body:"+str(item.collider_id))
	return coverage_issues.is_empty()
func _inside_admission(ident: String,kind: String) -> bool:
	var envelope={"min":[-20.25,3,-8.5],"max":[20.25,10,8.5]} if kind=="road" else {"min":[-11,-4,-45.25],"max":[11,20,45.25]}
	return Controller.intersects(_bounds(ident),envelope)
func _refresh_exit_permissions():
	for kind in exit_permissions:
		for ident in exit_permissions[kind].keys():
			if not actors.has(ident) or not is_instance_valid(actors[ident].body): continue
			if not _inside_admission(ident,kind):
				for gate in gates[kind]: actors[ident].body.remove_collision_exception_with(gate.body)
				exit_permissions[kind].erase(ident); audit_log.append({"event":"full_actor_exited","id":ident,"route":kind,"sequence":sequence})
func _apply_admissions(commands: Dictionary):
	for kind in commands:
		var command=commands[kind]
		if gate_pending.has(kind) and gate_pending[kind].generation==command.generation: continue
		if admission_acks[kind].generation==command.generation and admission_acks[kind].closed==not command.enabled: continue
		if not command.enabled:
			for ident in actors:
				if not is_instance_valid(actors[ident].body): continue
				if (actors[ident].kind=="vessel")!=(kind=="navigation"): continue
				if _inside_admission(ident,kind):
					exit_permissions[kind][ident]=true
					for gate in gates[kind]: actors[ident].body.add_collision_exception_with(gate.body)
		for gate in gates[kind]: gate.shape.disabled=command.enabled
		gate_pending[kind]={"closed":not command.enabled,"generation":command.generation,"physics_frame":Engine.get_physics_frames()}; audit_log.append({"event":"admission_applied","route":kind,"closed":not command.enabled,"generation":command.generation,"egress_ids":exit_permissions[kind].keys()})
func _acknowledge_gates():
	gate_faults.clear()
	for kind in gates:
		if gate_pending.has(kind): continue
		for gate in gates[kind]:
			if gate.shape.disabled==admission_acks[kind].closed or gate.body.collision_layer!=GATE_LAYER: gate_faults.append("admission_physical_feedback_changed:"+kind)
	for kind in gate_pending.keys():
		var p=gate_pending[kind]
		if Engine.get_physics_frames()<=p.physics_frame: continue
		var agrees=true
		for gate in gates[kind]:
			if gate.shape.disabled==p.closed or gate.body.collision_layer!=GATE_LAYER: agrees=false
		if agrees: admission_acks[kind]={"closed":p.closed,"generation":p.generation}; gate_pending.erase(kind)
func _actuator_feedback() -> Dictionary:
	if not trusted_actuator_feedback: return {"leaves":"unknown","covers":"unknown","barriers":"unknown"}
	var p=adapter.actual_pose_parameters()
	return {"leaves":"seated_locked" if abs(p.leaf_angle_degrees)<0.000001 else ("open_locked" if abs(p.leaf_angle_degrees-90)<0.000001 else "moving"),"covers":"seated_locked" if abs(p.hinge_plate_progress)<0.000001 else ("stowed_locked" if abs(p.hinge_plate_progress-1)<0.000001 else "moving"),"barriers":"open_locked" if abs(p.barrier_angle_degrees-90)<0.000001 else ("closed_locked" if abs(p.barrier_angle_degrees)<0.000001 else "moving")}
func observe(now_ms: int) -> Dictionary:
	sequence+=1; _acknowledge_gates(); _refresh_exit_permissions(); var complete=_coverage(); var observations=[]
	if Engine.get_physics_frames()<=last_sensor_physics_frame: complete=false; coverage_issues.append("no_new_physics_observation")
	last_sensor_physics_frame=Engine.get_physics_frames()
	for ident in actors:
		var a=actors[ident]
		if not is_instance_valid(a.body) or not a.body.is_inside_tree(): continue
		var o={"id":ident,"kind":a.kind}
		if a.kind=="vessel": o.asset_key=a.asset_key; o.transform_bridge_local=Adapter.dict_transform(pose(ident))
		else: o.bounds_bridge_local_m=_bounds(ident)
		observations.append(o)
	return {"sequence":sequence,"timestamp_ms":now_ms,"complete":complete,"coverage_ids":contract.required_coverage_ids.duplicate(),"geometry_sha256":contract.geometry_pack.sha256,"observations":observations,"pending_navigation_admissions":[],"actuators":_actuator_feedback(),"admission_ack":admission_acks.duplicate(true),"emergency_stop":false}
func tick(now_ms: int,commands: Array=[]) -> Dictionary:
	var snapshot=observe(now_ms); last_output=adapter.tick(now_ms,snapshot,commands); _apply_admissions(last_output.controller.admission_commands)
	return {"operation":last_output.duplicate(true),"snapshot":snapshot,"coverage_issues":coverage_issues.duplicate(),"exit_permission_ids":{"road":exit_permissions.road.keys(),"navigation":exit_permissions.navigation.keys()}}

func tick_live(commands: Array=[]) -> Dictionary:
	return tick(Time.get_ticks_msec(),commands)
