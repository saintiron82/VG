extends Node3D
## Independent actual-city capsule check. All movement is the unchanged LilyController.
## Spawn is assigned once per case; waypoint coordinates only produce direction/speed input.
const CityWorld = preload("res://CityWorld.gd")
const LilyController = preload("res://character/runtime/LilyController.gd")
const DT := 1.0 / 60.0
var options: Dictionary = {}
var prepared: Dictionary = {}
var report: Dictionary = {}
var world: Node3D
var replay_data: Dictionary = {}
var out_dir := ""
var mode := "follow"
var selected := ""
var effective_repo_root := ""

func vector(a: Array) -> Vector3: return Vector3(float(a[0]),float(a[1]),float(a[2]))
func coords(p: Vector3) -> Array: return [p.x,p.y,p.z]
func xz_distance(a: Vector3,b: Vector3) -> float: return Vector2(a.x-b.x,a.z-b.z).length()
func write_json(path: String,value: Variant) -> void:
	var file := FileAccess.open(path,FileAccess.WRITE)
	if file == null: push_error("Cannot write "+path); return
	file.store_string(JSON.stringify(value,"  ")+"\n")

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair := arg.substr(2).split("=",true,1)
			options[pair[0]]=pair[1] if pair.size()>1 else "true"
	mode = str(options.get("mode","follow"))
	selected = str(options.get("case",""))
	out_dir = str(options.get("out",ProjectSettings.globalize_path("res://validation/evidence/run_r01")))
	if FileAccess.file_exists(out_dir.path_join("report.json")):
		push_error("Refusing evidence overwrite: "+out_dir);get_tree().quit(3);return
	DirAccess.make_dir_recursive_absolute(out_dir)
	DirAccess.make_dir_recursive_absolute(out_dir.path_join("source_snapshots"))
	for source_path in ["res://validation/LilyCityValidation.gd","res://CityWorld.gd","res://character/runtime/LilyController.gd","res://validation/cases.json"]:
		DirAccess.copy_absolute(ProjectSettings.globalize_path(source_path),out_dir.path_join("source_snapshots").path_join(str(source_path).get_file()))
	prepared = JSON.parse_string(FileAccess.get_file_as_string("res://validation/cases.json"))
	effective_repo_root=str(options.get("repo-root",prepared.repo_root)).trim_suffix("/")
	if mode == "replay": replay_data=JSON.parse_string(FileAccess.get_file_as_string(str(options.get("input",""))))
	report={"schema":"riverstone.lily_city.validation.v1","status":"running","mode":mode,"effective_repo_root":effective_repo_root,"physics_hz":Engine.physics_ticks_per_second,"engine":Engine.get_version_info(),"cases_sha256":FileAccess.get_sha256("res://validation/cases.json"),"controller_sha256":FileAccess.get_sha256("res://character/runtime/LilyController.gd"),"harness_sha256":FileAccess.get_sha256("res://validation/LilyCityValidation.gd"),"world_script_sha256":FileAccess.get_sha256("res://CityWorld.gd"),"tile_index_sha256":FileAccess.get_sha256("res://generated/tile_r01/index.json"),"cases":[],"errors":[],"limits":prepared.limitations,"test_input":"Closed-loop direction/speed route-following" if mode=="follow" else "Saved direction/speed frames through unchanged LilyController.load_replay", "position_assignments":"Exactly one spawn per independently named case; none during movement", "added_test_geometry":false,"npc_behavior_economy":false}
	if mode=="replay":
		for key in ["controller_sha256","tile_index_sha256","cases_sha256"]:
			if replay_data.get(key,"")!=report[key]:fail("Saved input binding mismatch: "+key);return
	if Engine.physics_ticks_per_second != 60: fail("Physics must be 60 Hz"); return
	if report.controller_sha256 != prepared.sources.lily_controller.sha256: fail("Controller is not byte-identical to approved source");return
	for key in prepared.sources:
		var source: Dictionary=prepared.sources[key]
		if FileAccess.get_sha256(effective_repo_root.path_join(source.path)) != source.sha256: fail("Changed case source "+key);return
	world=CityWorld.new();add_child(world)
	var error: String=world.configure("res://generated/tile_r01/index.json",effective_repo_root,false)
	if not error.is_empty():fail(error);return
	call_deferred("run_all")

func fail(message: String) -> void:
	report.errors.append(message);report.status="ERROR";write_json(out_dir.path_join("report.json"),report);push_error(message);get_tree().quit(2)

func nearest_distance(p: Vector3, points: Array) -> float:
	var best := INF
	var q := Vector2(p.x,p.z)
	for i in range(points.size()-1):
		var a := Vector2(points[i][0],points[i][2]);var b := Vector2(points[i+1][0],points[i+1][2]);var ab:=b-a
		var t:=clampf((q-a).dot(ab)/ab.length_squared(),0,1) if ab.length_squared()>0 else 0.0
		best=minf(best,q.distance_to(a+ab*t))
	return best

func run_all() -> void:
	var recorded: Dictionary={"schema":"riverstone.lily_city.saved_route_controls.v1","physics_hz":60,"cases_sha256":report.cases_sha256,"controller_sha256":report.controller_sha256,"tile_index_sha256":report.tile_index_sha256,"cases":{}}
	for case in prepared.cases:
		if not selected.is_empty() and str(case.id)!=selected:continue
		var result: Dictionary=await run_case(case)
		report.cases.append(result)
		if mode=="follow":recorded.cases[case.id]=result.input_replay
		print("LILY_CITY_CASE "+JSON.stringify({"id":case.id,"pass":result.get("pass",false),"reason":result.get("reason",""),"ticks":result.get("movement_ticks",0),"final":result.get("final_feet_m",[])}))
		write_json(out_dir.path_join("partial.json"),report)
		report.cases[-1].erase("input_replay")
	if mode=="follow":write_json(out_dir.path_join("recorded_inputs.json"),recorded)
	var passed: bool=not report.cases.is_empty()
	for result in report.cases:passed=passed and bool(result.get("pass",false))
	report.status="PASS" if passed else "FAIL"
	report.world_final=world.debug_state()
	write_json(out_dir.path_join("report.json"),report)
	print("LILY_CITY_VALIDATION "+JSON.stringify({"status":report.status,"mode":mode,"cases":report.cases.size(),"output":out_dir}))
	get_tree().quit(0 if passed else 1)

func run_case(case: Dictionary) -> Dictionary:
	var result: Dictionary={"id":case.id,"expect":case.expect,"pass":false,"reason":"","scope":case.scope,"spawn_position_assignments":1,"traversal_position_assignments":0,"collision_contacts":{},"wall_contacts":{},"first_wall_contacts":[],"streaming_cells":[],"support_source_ids":[],"movement_ticks":0,"ground_loss_frames":0,"ground_loss_max_streak":0,"max_centerline_error_m":0.0,"max_abs_delta_y_m":0.0,"trace":[]}
	var start:=vector(case.points[0])
	if not world.ensure_region(start,1):result.reason="world_region_failed";result.world=world.debug_state();return result
	await get_tree().physics_frame
	await get_tree().physics_frame
	var ray:=PhysicsRayQueryParameters3D.create(start+Vector3(0,.45,0),start-Vector3(0,2,0),1)
	var hit:=get_world_3d().direct_space_state.intersect_ray(ray)
	result.spawn_ray_hit=not hit.is_empty()
	if hit.is_empty():result.reason="spawn_ground_missing";return result
	result.spawn_surface_m=coords(hit.position);result.spawn_source_id=str(hit.collider.get_meta("source_id","unknown"))
	if float(hit.normal.y)<.6 or absf(float(hit.position.y)-start.y)>.35:result.reason="spawn_ground_not_source_height";return result
	var player: CharacterBody3D=LilyController.new()
	player.player_input_enabled=false;player.camera_enabled=false
	player.position=Vector3(start.x,hit.position.y+.04,start.z)
	add_child(player);player.set_physics_process(false)
	if not player.initialized:result.reason="character_not_ready: "+player.load_error;player.queue_free();return result
	var initial_debug: Dictionary=player.debug_state()
	result.capsule_radius_m=initial_debug.capsule_radius_m;result.capsule_height_m=initial_debug.capsule_height_m
	if absf(float(result.capsule_radius_m)-.23)>.000001 or absf(float(result.capsule_height_m)-1.72)>.000001:result.reason="wrong_capsule";player.queue_free();return result
	for _i in range(30):
		await get_tree().physics_frame
		player.set_control(Vector3.ZERO,0);player._physics_process(DT)
	result.settled_feet_m=coords(player.position);result.settled_grounded=player.is_on_floor()
	if not player.is_on_floor():result.reason="spawn_did_not_settle";player.queue_free();await get_tree().physics_frame;return result
	var frames: Array=[]
	var replay: Dictionary={}
	if mode=="replay":
		if not replay_data.get("cases",{}).has(case.id):result.reason="missing_saved_case";player.queue_free();return result
		replay=replay_data.cases[case.id]
		var error: String=player.load_replay(replay)
		if not error.is_empty():result.reason=error;player.queue_free();return result
	var waypoint:=1
	var budget:=int(ceil(float(case.length_m)/float(case.speed_mps)*60*2))+240
	if case.expect=="blocked":budget=int(case.duration_ticks)
	if mode=="replay":budget=int(replay.frames[-1].tick)+31
	var streak:=0;var blocked_streak:=0;var max_blocked_streak:=0
	var previous:=player.position
	var minimum_y:=player.position.y;var maximum_y:=player.position.y
	var contact_expected:=false
	var reached:=false
	var idle_tail:=0
	var stopped:=false
	for tick in range(budget):
		await get_tree().physics_frame
		if not world.ensure_region(player.position,1):result.reason="streaming_failure";break
		var cell: Array=[floori(player.position.x/64.0),floori(player.position.z/64.0)]
		if result.streaming_cells.is_empty() or result.streaming_cells[-1]!=cell:result.streaming_cells.append(cell)
		while waypoint<case.points.size() and xz_distance(player.position,vector(case.points[waypoint]))<=float(case.waypoint_tolerance_m):waypoint+=1
		if waypoint>=case.points.size():reached=true
		if mode=="follow":
			var direction:=Vector3.ZERO;var speed:=0.0
			if not reached:
				direction=vector(case.points[waypoint])-player.position;direction.y=0
				if bool(case.get("fixed_direction",false)):direction=vector(case.points[-1])-vector(case.points[0]);direction.y=0
				speed=minf(float(case.speed_mps),direction.length()*5.0) if case.expect=="reach" else float(case.speed_mps)
				direction=direction.normalized()
			frames.append({"tick":tick,"direction":coords(direction),"speed_mps":speed})
			player.set_control(direction,speed)
		player._physics_process(DT)
		var moved:=player.position-previous
		result.max_abs_delta_y_m=maxf(result.max_abs_delta_y_m,absf(moved.y))
		result.max_centerline_error_m=maxf(result.max_centerline_error_m,nearest_distance(player.position,case.points))
		minimum_y=minf(minimum_y,player.position.y);maximum_y=maxf(maximum_y,player.position.y)
		if not player.is_on_floor():streak+=1;result.ground_loss_frames+=1
		else:streak=0
		result.ground_loss_max_streak=maxi(result.ground_loss_max_streak,streak)
		if player.requested_speed>.1 and Vector2(moved.x,moved.z).length()/DT<.05:blocked_streak+=1
		else:blocked_streak=0
		max_blocked_streak=maxi(max_blocked_streak,blocked_streak)
		for i in player.get_slide_collision_count():
			var collision:=player.get_slide_collision(i)
			var collider:=collision.get_collider()
			var id:=str(collider.get_meta("source_id",collider.name))
			result.collision_contacts[id]=int(result.collision_contacts.get(id,0))+1
			if collision.get_normal().y>.6 and not id in result.support_source_ids:result.support_source_ids.append(id)
			if absf(collision.get_normal().y)<.4 and collision.get_normal().dot(player.requested_world_direction)<-.7:
				if not result.wall_contacts.has(id):result.first_wall_contacts.append({"source_id":id,"tick":tick,"normal":coords(collision.get_normal()),"point_m":coords(collision.get_position()),"input_direction":coords(player.requested_world_direction)})
				result.wall_contacts[id]=int(result.wall_contacts.get(id,0))+1
				if id in case.get("expected_obstacle_source_ids",[]):contact_expected=true
		result.movement_ticks=tick+1
		if tick%10==0 or not player.is_on_floor():result.trace.append({"tick":tick,"feet_m":coords(player.position),"velocity_mps":coords(player.velocity),"grounded":player.is_on_floor(),"waypoint_index":waypoint})
		previous=player.position
		if player.position.y<minimum_route_y(case.points)-2:result.reason="fell_below_route";break
		if case.expect=="reach" and mode=="follow":
			if reached:idle_tail+=1
			if idle_tail>=30:stopped=true;break
			if blocked_streak>=180:result.reason="blocked_for_3_seconds";break
	result.final_feet_m=coords(player.position)
	result.final_grounded=player.is_on_floor()
	result.final_height_error_m=absf(player.position.y-float(case.points[-1][1]))
	result.final_distance_to_target_m=xz_distance(player.position,vector(case.points[-1]))
	result.height_range_m=[minimum_y,maximum_y]
	result.max_blocked_streak=max_blocked_streak
	result.expected_obstacle_contact=contact_expected
	result.final_controller_state=player.debug_state()
	result.world=world.debug_state()
	result.reached_waypoints=waypoint
	if case.expect=="reach":
		result.pass=float(result.final_distance_to_target_m)<=.15 and player.is_on_floor() and streak==0 and float(result.final_height_error_m)<=.20 and float(result.max_centerline_error_m)<=.55 and int(result.ground_loss_max_streak)<=3 and result.reason.is_empty()
		if str(case.id)=="MARKET_TO_ADJACENT_SOUTH_STREET":result.pass=result.pass and result.streaming_cells.size()>=2
		if str(case.id).begins_with("R8_STAIR_CENTER"):
			var saw_contract:=false
			for id in result.support_source_ids:
				if str(id).begins_with("ExplicitCollisionContract_"):saw_contract=true
			result.real_stair_collision_contract_contact=saw_contract
			result.pass=result.pass and saw_contract and maximum_y-minimum_y>3.5
	else:
		result.pass=not reached and contact_expected and max_blocked_streak>=120 and player.is_on_floor() and result.reason.is_empty()
	if result.reason.is_empty():result.reason="reached_supported_target" if result.pass and case.expect=="reach" else ("correctly_blocked_by_original_native_obstacle" if result.pass else "acceptance_metrics_failed")
	if mode=="follow":
		if frames.is_empty() or float(frames[-1].speed_mps)>0:frames.append({"tick":int(result.movement_ticks),"direction":[0,0,0],"speed_mps":0.0})
		result.input_replay={"schema":"riverstone.character.input_replay.v1","physics_hz":60,"frames":frames}
	player.queue_free();await get_tree().physics_frame
	return result

func minimum_route_y(points: Array) -> float:
	var value:=INF
	for p in points:value=minf(value,float(p[1]))
	return value
