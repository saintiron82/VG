extends SceneTree
const Visual = preload("res://runtime/LilyVisual.gd")
const Player = preload("res://runtime/LilyController.gd")
var report := {"schema": "riverstone.character.fixture_report.v1", "checks": [], "failures": [], "physics": [], "visual_review": "not performed; headless fixtures only"}
var scene: Node3D

func _initialize() -> void:
	call_deferred("run")

func check(condition: bool, label: String) -> void:
	report.checks.append({"id":label,"pass":condition})
	if not condition: report.failures.append(label)

func resources(node: Node) -> Array:
	var out: Array = []
	if node is MeshInstance3D: out.append(node.mesh.get_rid().get_id())
	for child in node.get_children(): out.append_array(resources(child))
	return out

func _box(parent: Node3D, pos: Vector3, size: Vector3, angle := 0.0) -> void:
	var body := StaticBody3D.new()
	body.collision_layer=1;body.collision_mask=2;body.position=pos;body.rotation.x=angle
	var collision := CollisionShape3D.new();var shape := BoxShape3D.new();shape.size=size;collision.shape=shape
	body.add_child(collision);parent.add_child(body)

func fixture() -> Node3D:
	var result := Node3D.new();root.add_child(result);return result

func make_player(parent: Node3D, pos := Vector3(0,.04,0)) -> CharacterBody3D:
	var p := Player.new();p.player_input_enabled=false;p.camera_enabled=false;p.position=pos;parent.add_child(p)
	p.set_physics_process(false);return p

func frames(p: CharacterBody3D, count: int) -> void:
	for _i in range(count):
		await physics_frame
		p.simulate_control(1.0/60.0)

func dispose(node: Node) -> void:
	node.queue_free()
	await process_frame
	await physics_frame

func run() -> void:
	scene=fixture()
	var v := Visual.new();scene.add_child(v)
	check(v.load_character().is_empty(),"load_character")
	check(v.parts().size()==28,"28_separate_rigid_parts")
	var mesh_ids := resources(v)
	check(mesh_ids.size()==83,"83_material_mesh_groups")
	var nodes: Dictionary=v.parts()
	check(nodes.forearm_left.get_parent()==nodes.upper_arm_left,"elbow_parent_contract")
	check(nodes.eyelid_left.get_parent()==nodes.head,"face_parent_contract")
	v.set_locomotion(1.65);v.seek_motion(.2)
	check(not nodes.thigh_left.transform.is_equal_approx(v._rest.thigh_left) or not nodes.shin_left.transform.is_equal_approx(v._rest.shin_left),"walk_moves_actual_body_nodes")
	v.seek_motion(0);var initial: Transform3D=nodes.hand_left.global_transform
	v.seek_motion(8.0)
	check(nodes.hand_left.global_transform.is_equal_approx(initial),"ten_loops_no_transform_drift")
	v.seek_blink(0);var open_y: float=nodes.eyelid_left.position.y
	check(nodes.eyelid_left.position.z < v._rest.eyelid_left.origin.z-.15,"open_lids_retracted_inside_head")
	v.seek_blink(3.90)
	check(is_equal_approx(nodes.eyelid_left.position.y,open_y-.08),"blink_cover_translation")
	check(v.set_expression("happy"),"happy_expression_supported")
	check(not nodes.mouth_corner_left.transform.is_equal_approx(v._rest.mouth_corner_left),"mouth_corner_geometry_moves")
	check(v.set_expression("focused"),"focused_expression_supported")
	check(not v.set_expression("invalid"),"invalid_expression_rejected")
	for _i in range(240):v.advance(1.0/60)
	check(resources(v)==mesh_ids,"mesh_resources_unchanged_during_motion")
	# Record gait sole extents candidly; this is not foot IK or a visual pass.
	var foot_range := [INF,-INF]
	for i in range(33):
		v.seek_motion(float(i)*.8/32)
		var minimum := INF
		for id in ["foot_left","foot_right"]:
			var foot: Node3D=nodes[id]
			for mesh in foot.get_children():
				if mesh is MeshInstance3D:
					var bounds: AABB=mesh.mesh.get_aabb()
					for k in range(8):minimum=minf(minimum,(foot.global_transform*bounds.get_endpoint(k)).y)
		foot_range[0]=minf(foot_range[0],minimum);foot_range[1]=maxf(foot_range[1],minimum)
	report["gait_minimum_sole_y_range_m"]=foot_range
	check(foot_range[0]>-.011 and foot_range[1]<.011,"gait_sole_within_half_voxel_of_rest_plane")
	await dispose(scene)
	# Flat travel uses actual capsule movement; no route/position rewriting.
	scene=fixture();_box(scene,Vector3(0,-.2,0),Vector3(20,.4,20));var p:=make_player(scene)
	await frames(p,25);check(p.is_on_floor(),"flat_spawn_grounded")
	var lost: int=p.ground_loss_frames;var start: Vector3=p.position
	p.set_control(Vector3.FORWARD,1.65);await frames(p,120)
	check(p.position.distance_to(start)>3.0,"flat_capsule_walks_three_metres")
	check(p.ground_loss_frames==lost,"flat_walk_never_loses_floor")
	report.physics.append({"case":"flat","state":p.debug_state()})
	await dispose(scene)
	# 0.64 m vertical obstacle and 2 m wall cannot be silently jumped.
	scene=fixture();_box(scene,Vector3(0,-.2,0),Vector3(20,.4,20));_box(scene,Vector3(0,.32,2),Vector3(3,.64,.4));p=make_player(scene)
	await frames(p,25);p.set_control(Vector3.BACK,1.65);await frames(p,180)
	check(p.position.z<1.60 and p.position.y<.05,"vertical_obstacle_blocks_without_jump")
	check(p.blocked_frames>30,"blocked_input_is_observable")
	report.physics.append({"case":"obstacle","state":p.debug_state()})
	await dispose(scene)
	# Traversable authored slope, same rule as city stair collision proxies.
	scene=fixture();_box(scene,Vector3(0,-.2,-2),Vector3(8,.4,4.2))
	_box(scene,Vector3(0,.40,2),Vector3(3,.20,4.12),-atan(.25))
	_box(scene,Vector3(0,.90,6),Vector3(4,.20,4.0))
	p=make_player(scene,Vector3(0,.04,-1));await frames(p,25);p.set_control(Vector3.BACK,1.65);await frames(p,240)
	check(p.position.z>4.5 and p.position.y>.95,"authored_stair_ramp_traversal")
	check(p.is_on_floor(),"ramp_finishes_grounded")
	report.physics.append({"case":"ramp","state":p.debug_state()})
	await dispose(scene)
	# A finite ledge really falls. There is no implicit world floor or snap.
	scene=fixture();_box(scene,Vector3(0,-.2,0),Vector3(3,.4,3));p=make_player(scene)
	await frames(p,25);p.set_control(Vector3.BACK,1.65);await frames(p,150)
	check(p.position.y < -1 and not p.is_on_floor(),"finite_ledge_falls_no_hidden_floor")
	report.physics.append({"case":"ledge","state":p.debug_state()})
	await dispose(scene)
	# Replay refuses output positions; bounded controls reproduce input intent.
	scene=fixture();_box(scene,Vector3(0,-.2,0),Vector3(10,.4,10));p=make_player(scene)
	var replay := {"schema":"riverstone.character.input_replay.v1","physics_hz":60,"frames":[{"tick":0,"direction":[0,0,1],"speed_mps":1.65},{"tick":60,"direction":[0,0,0],"speed_mps":0.0}]}
	check(p.load_replay(JSON.parse_string(JSON.stringify(replay))).is_empty(),"serialized_input_replay_accepted")
	var bad_replay: Dictionary = replay.duplicate(true)
	bad_replay.frames[0]["position"] = [0, 50, 0]
	check(not p.load_replay(bad_replay).is_empty(),"replay_position_teleport_rejected")
	for _i in range(120):await physics_frame;p._physics_process(1.0/60.0)
	check(p.replay_index==2 and p.position.z>1.4 and p.position.z<1.9,"serialized_input_replay_walk_and_stop")
	check(not p.load_replay({"schema":"bad"}).is_empty(),"bad_replay_rejected")
	report.physics.append({"case":"replay","state":p.debug_state()})
	await dispose(scene)
	report["passed"]=report.failures.is_empty();report["check_count"]=report.checks.size()
	var out:=FileAccess.open("res://evidence/headless_r5.json",FileAccess.WRITE);out.store_string(JSON.stringify(report,"  ")+"\n");out.close()
	print(JSON.stringify({"passed":report.passed,"checks":report.check_count,"failures":report.failures,"gait_sole_y":foot_range}))
	quit(0 if report.passed else 1)
