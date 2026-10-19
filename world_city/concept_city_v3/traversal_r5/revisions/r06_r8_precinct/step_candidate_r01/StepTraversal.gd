extends Node3D
## Independent physics harness. No visuals, infinite floor, pathfinding, or point snapping.
const RD = preload("res://RenderData.gd")
const RADIUS := 0.3
const HEIGHT := 1.8
const SPEED := 4.0
const WAYPOINT_TOLERANCE := 0.075
const GRAVITY := 9.8
var options: Dictionary = {}
var prepared: Dictionary
var report: Dictionary = {"schema":"riverstone.registered_r5.capsule_results.v1", "status":"loading", "engine":"Godot CharacterBody3D / GodotPhysics3D", "routes":[], "errors":[]}
var body: CharacterBody3D
var routes: Array = []
var route_index := -1
var route: Dictionary
var result: Dictionary
var waypoint_index := 1
var stage := "loading"
var settle_frames := 0
var still_frames := 0
var no_floor_streak := 0
var route_frames := 0
var target_frame_budget := 0
var previous_position := Vector3.ZERO
var last_progress_position := Vector3.ZERO
var started_ms := Time.get_ticks_msec()
var simulation_frames := 0
var shapes: Dictionary = {}
var box_count := 0
var triangle_count := 0
var triangle_asset_count := 0
var world: Node3D
var route_triangle_count := 0
var route_asset_count := 0

func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--"):
			var pair := arg.substr(2).split("=",true,1)
			options[pair[0]]=pair[1] if pair.size()>1 else "true"
	var path: String = str(options.get("prepared",ProjectSettings.globalize_path("res://prepared.json")))
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary: abort("Invalid prepared JSON "+path); return
	prepared=parsed
	report.prepared_sha256=FileAccess.get_sha256(path)
	report.prepared_path=path
	report.engine_version=Engine.get_version_info()
	report.source_hashes=prepared.sources
	report.assumptions=prepared.assumptions
	report.coverage=prepared.coverage
	report.settings={"radius_m":RADIUS,"height_m":HEIGHT,"speed_mps":SPEED,"waypoint_tolerance_m":WAYPOINT_TOLERANCE,"physics_hz":Engine.physics_ticks_per_second,"gravity_mps2":GRAVITY,"floor_snap_length_m":.2,"safe_margin_m":.001,"no_visual_offset_in_physics":true}
	report.implementation_hashes=prepared.implementation_hashes
	for source in prepared.sources.values():
		if FileAccess.get_sha256(str(source.path)) != str(source.sha256): abort("Manifest changed before physics: "+str(source.path));return
	for source in prepared.implementation_hashes:
		if FileAccess.get_sha256(str(prepared.repo_root)+"/"+str(source)) != str(prepared.implementation_hashes[source]): abort("Harness changed before physics: "+str(source));return
	body=CharacterBody3D.new();body.name="GenericCapsule_0p3r_1p8h"
	body.collision_layer=4;body.collision_mask=3;body.safe_margin=.001
	body.floor_snap_length=.2;body.floor_max_angle=deg_to_rad(45)
	var capsule := CapsuleShape3D.new();capsule.radius=RADIUS;capsule.height=HEIGHT
	var collision := CollisionShape3D.new();collision.shape=capsule;body.add_child(collision);add_child(body)
	var selected: PackedStringArray=str(options.get("routes","")).split(",",false)
	for item in prepared.routes:
		if selected.is_empty() or str(item.id) in selected:routes.append(item)
	report.collision_world={"infinite_ground_plane":false,"route_local_worlds":true,"building_collision_policy":"actual_scene_boxes_and_native_cached_meshes","triangle_winding":"common RenderData quad order; exact City.gd a,c,b scene-triangle order","architecture":"unchanged completed-scene triangles plus actual native cached quads; no height resampling or step-up"}
	call_deferred("next_route")

func build_route_collision() -> void:
	if is_instance_valid(world):world.free()
	shapes.clear();world=Node3D.new();add_child(world)
	route_triangle_count=0;route_asset_count=0
	var keys: Dictionary={}
	for id in route.placement_ids:keys[prepared.placements[id].asset_key]=true
	for key in keys:
		var asset: Dictionary=prepared.assets[key]
		var path: String=str(prepared.repo_root)+"/"+str(asset.render_path)
		var vertices:=PackedVector3Array()
		if str(asset.get("collision_format",""))=="source_grade_proxy_triangles" or str(asset.get("collision_format",""))=="actual_scene_triangles":
			if FileAccess.get_sha256(path)!=asset.render_sha256:abort("Source proxy hash changed: "+str(key));return
			var data: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(path))
			for triangle in data.triangles:
				for vertex in triangle:vertices.append(RD.vector(vertex))
		else:
			var read: Dictionary=RD.read(path)
			if read.has("error"):abort(str(read.error));return
			if read.sha256!=asset.render_sha256:abort("Compiled render hash changed: "+str(key));return
			for group in read.data.groups:
				for quad in group.quads:
					for index in RD.TRIANGLE_ORDER:vertices.append(RD.vector(quad[index]))
		var shape:=ConcavePolygonShape3D.new();shape.backface_collision=false;shape.set_faces(vertices)
		shapes[key]=shape;route_triangle_count+=vertices.size()/3;route_asset_count+=1
	for id in route.placement_ids:
		var placement: Dictionary=prepared.placements[id]
		var static_body:=StaticBody3D.new();static_body.name="Infra_"+str(id).replace(":","_")
		static_body.set_meta("source_id",str(id));static_body.set_meta("category",str(placement.category))
		static_body.collision_layer=int(placement.collision_layer);static_body.collision_mask=0
		var basis:=Basis(Vector3.UP,deg_to_rad(float(placement.get("yaw_deg",0))))
		if placement.has("transform") and placement.transform.has("basis"):
			var rows: Array=placement.transform.basis
			basis=Basis(RD.vector(rows[0]),RD.vector(rows[1]),RD.vector(rows[2])).transposed()
		static_body.transform=Transform3D(basis,RD.vector(placement.position_m))
		var collision:=CollisionShape3D.new();collision.shape=shapes[placement.asset_key]
		static_body.add_child(collision);world.add_child(static_body)
	for id in route.building_ids:
		var building: Dictionary=prepared.buildings[id]
		var static_body:=StaticBody3D.new();static_body.name="Building_"+str(id)
		static_body.set_meta("source_id",str(id));static_body.set_meta("category","building_envelope")
		static_body.collision_layer=int(building.get("collision_layer",3));static_body.collision_mask=0
		static_body.position=RD.vector(building.position_m);static_body.rotation.y=float(building.yaw_rad)
		for bounds in building.boxes:
			var lo:=RD.vector(bounds.min);var hi:=RD.vector(bounds.max)
			var shape:=BoxShape3D.new();shape.size=hi-lo
			var collision:=CollisionShape3D.new();collision.shape=shape;collision.position=(lo+hi)*.5
			static_body.add_child(collision);box_count+=1
		world.add_child(static_body)
	result.collision_world={"collision_assets":route_asset_count,"collision_triangles":route_triangle_count,"placements":route.placement_ids.size(),"buildings":route.building_ids.size()}
	print("COLLISION_WORLD_READY "+str(route.id)+" "+JSON.stringify(result.collision_world))

func spawn_on_actual_ground() -> void:
	var point:=RD.vector(route.points[0])
	var ray:=PhysicsRayQueryParameters3D.create(Vector3(point.x,point.y+.45,point.z),Vector3(point.x,point.y-2.0,point.z),1)
	var hit:=get_world_3d().direct_space_state.intersect_ray(ray)
	result.spawn_ground_ray_hit=not hit.is_empty()
	if not hit.is_empty():
		point.y=hit.position.y
		result.spawn_ground_id=str(hit.collider.get_meta("source_id","unknown"))
		result.spawn_ground_category=str(hit.collider.get_meta("category","unknown"))
		result.spawn_surface_y_m=point.y
	# Sole within-case initialization. No later position assignments or snaps.
	body.position=point+Vector3(0,HEIGHT*.5+.06,0)
	body.velocity=Vector3.ZERO;stage="settling";settle_frames=0

func _physics_process(delta: float) -> void:
	if stage=="loading" or stage=="finished":return
	simulation_frames+=1
	if stage=="world_settle":
		settle_frames+=1
		if settle_frames>=3: spawn_on_actual_ground()
		return
	if stage=="settling":
		body.velocity=Vector3(0,body.velocity.y-GRAVITY*delta,0)
		body.move_and_slide();settle_frames+=1
		if settle_frames>=45:
			result.spawn_position=vec(body.position)
			result.spawn_on_floor=body.is_on_floor()
			result.min_feet_y_m=body.position.y-HEIGHT*.5;result.max_feet_y_m=body.position.y-HEIGHT*.5
			if not body.is_on_floor():finish_route("spawn_not_grounded");return
			stage="walking";previous_position=body.position;last_progress_position=body.position
		return
	if stage!="walking":return
	var target := RD.vector(route.points[waypoint_index]);target.y=body.position.y
	var offset := target-body.position
	if offset.length()<=WAYPOINT_TOLERANCE:
		result.waypoints_reached+=1
		result.waypoint_reached_frames.append({"index":waypoint_index,"walk_physics_frame":route_frames,"error_m":offset.length(),"position":vec(body.position)})
		result.max_waypoint_error_m=maxf(result.max_waypoint_error_m,offset.length())
		waypoint_index+=1
		if waypoint_index>=route.points.size():finish_route("reached");return
		target=RD.vector(route.points[waypoint_index]);target.y=body.position.y;offset=target-body.position
	body.velocity.x=offset.normalized().x*minf(SPEED,offset.length()/delta)
	body.velocity.z=offset.normalized().z*minf(SPEED,offset.length()/delta)
	body.velocity.y=-.25 if body.is_on_floor() else body.velocity.y-GRAVITY*delta
	candidate_stair_move(delta,offset)
	if stage=="finished":return
	route_frames+=1
	result.physics_frames=route_frames
	result.distance_walked_m+=Vector2(body.position.x-previous_position.x,body.position.z-previous_position.z).length()
	previous_position=body.position
	var feet_y: float=body.position.y-HEIGHT*.5
	result.min_feet_y_m=minf(result.min_feet_y_m,feet_y)
	result.max_feet_y_m=maxf(result.max_feet_y_m,feet_y)
	var start := RD.vector(route.points[waypoint_index-1]);var goal := RD.vector(route.points[waypoint_index])
	var p := Vector2(body.position.x,body.position.z);var a := Vector2(start.x,start.z);var b := Vector2(goal.x,goal.z)
	var ab := b-a;var t := clampf((p-a).dot(ab)/maxf(ab.length_squared(),.00001),0,1)
	result.max_centerline_error_m=maxf(result.max_centerline_error_m,p.distance_to(a+ab*t))
	if not body.is_on_floor():
		result.not_on_floor_frames+=1;no_floor_streak+=1
		result.max_not_on_floor_streak=maxi(result.max_not_on_floor_streak,no_floor_streak)
	else: no_floor_streak=0
	var ray := PhysicsRayQueryParameters3D.create(body.position,body.position-Vector3(0,HEIGHT*.5+.3,0),1)
	var floor_hit := get_world_3d().direct_space_state.intersect_ray(ray)
	if floor_hit.is_empty():result.ground_ray_miss_frames+=1
	else:
		var support_id: String=str(floor_hit.collider.get_meta("source_id","unknown"))
		var category: String=str(floor_hit.collider.get_meta("category","unknown"))
		result.ground_support_categories[category]=int(result.ground_support_categories.get(category,0))+1
		if str(route.kind)=="fine_interior" and category!="source_grade_proxy":result.non_fine_support_frames+=1
		if route_frames%30==0 or route_frames==1:
			result.position_samples.append({"frame":route_frames,"capsule_center":vec(body.position),"ground_y_m":floor_hit.position.y,"support_id":support_id,"support_category":category})
	for index in body.get_slide_collision_count():
		var collision := body.get_slide_collision(index)
		if absf(collision.get_normal().y)<.7:
			var collider=collision.get_collider()
			var id: String=str(collider.get_meta("source_id",collider.name)) if collider else "unknown"
			result.obstacle_contact_ids[id]=int(result.obstacle_contact_ids.get(id,0))+1
			if result.obstacle_contact_samples.size()<24 and (result.obstacle_contact_samples.is_empty() or route_frames%5==0):
				result.obstacle_contact_samples.append({"collider_id":id,"frame":route_frames,"position":vec(collision.get_position()),"normal":vec(collision.get_normal()),"capsule_center":vec(body.position),"target":route.points[waypoint_index]})
	if Vector2(body.position.x-last_progress_position.x,body.position.z-last_progress_position.z).length()>=.1:
		last_progress_position=body.position;still_frames=0
	else:still_frames+=1
	if feet_y < float(route.get("minimum_allowed_feet_y_m", -10.0)) or no_floor_streak>30: finish_route("ground_lost");return
	if still_frames>=120:finish_route("blocked");return
	if route_frames>=target_frame_budget:finish_route("timeout");return

func next_route() -> void:
	stage="loading"
	route_index+=1
	if route_index>=routes.size():finish_suite();return
	route=routes[route_index];route_frames=0;settle_frames=0;waypoint_index=1;still_frames=0;no_floor_streak=0
	result={"id":route.id,"kind":route.kind,"status":"running","waypoints_total":route.points.size(),"waypoints_reached":1,"waypoint_reached_frames":[],"physics_frames":0,"distance_expected_m":route.length_m,"distance_walked_m":0.,"max_waypoint_error_m":0.,"max_centerline_error_m":0.,"min_feet_y_m":0.,"max_feet_y_m":0.,"not_on_floor_frames":0,"max_not_on_floor_streak":0,"ground_ray_miss_frames":0,"obstacle_contact_ids":{},"obstacle_contact_samples":[],"source_road_ids":route.source_road_ids,"within_route_teleports":0,"ground_support_categories":{},"non_fine_support_frames":0,"position_samples":[],"test_scope":route.test_scope}
	if route.has("expected_failure"):result.expected_failure=route.expected_failure
	target_frame_budget=ceili(float(route.length_m)/SPEED*60*2)+600
	print("ROUTE_START "+str(route.id))
	build_route_collision()
	if stage=="finished":return
	stage="world_settle";settle_frames=0

func finish_route(status: String) -> void:
	result.status=status
	result.clearance_warning=not result.obstacle_contact_ids.is_empty() and not route.has("expected_failure")
	result.end_position=vec(body.position)
	result.failed_target_index=waypoint_index if status!="reached" else null
	result.failed_target=route.points[waypoint_index] if status!="reached" else null
	result.settle_physics_frames=settle_frames
	result.simulated_walk_seconds=float(route_frames)/float(Engine.physics_ticks_per_second)
	result.pass=status==str(route.expected_failure) if route.has("expected_failure") else status=="reached" and int(result.ground_ray_miss_frames)==0 and int(result.not_on_floor_frames)==0 and int(result.non_fine_support_frames)==0
	if route.has("expected_contact_id"):
		result.expected_contact_id=route.expected_contact_id
		result.pass=result.pass and result.obstacle_contact_ids.has(str(route.expected_contact_id))
	report.routes.append(result)
	print("ROUTE_RESULT "+JSON.stringify(result))
	write_report()
	stage="loading";call_deferred("next_route")

func finish_suite() -> void:
	stage="finished"
	var passed := 0;var positive := 0;var negative := 0;var frames := 0;var groundloss := 0
	var max_error := 0.;var max_waypoint_error := 0.;var distance := 0.
	var contact_routes: Array=[]
	for r in report.routes:
		if r.pass:passed+=1
		if r.has("expected_failure"):negative+=1
		else:
			positive+=1;groundloss+=int(r.not_on_floor_frames)
			if not r.obstacle_contact_ids.is_empty():contact_routes.append({"id":r.id,"obstacle_contact_ids":r.obstacle_contact_ids,"max_centerline_error_m":r.max_centerline_error_m})
			max_error=maxf(max_error,r.max_centerline_error_m)
			max_waypoint_error=maxf(max_waypoint_error,r.max_waypoint_error_m)
			frames+=int(r.physics_frames);distance+=float(r.distance_walked_m)
	report.status="pass" if passed==report.routes.size() else "fail"
	report.summary={"cases":report.routes.size(),"passed":passed,"positive_routes":positive,"positive_routes_with_contact":contact_routes,"negative_controls":negative,"positive_walk_physics_frames":frames,"simulation_physics_frames":simulation_frames,"distance_walked_m":distance,"positive_not_on_floor_frames":groundloss,"max_centerline_error_m":max_error,"max_waypoint_error_m":max_waypoint_error,"wall_clock_ms":Time.get_ticks_msec()-started_ms}
	write_report();print("SUITE_RESULT "+JSON.stringify(report.summary));get_tree().quit(0 if report.status=="pass" else 2)

func write_report() -> void:
	var path: String=str(options.get("report",ProjectSettings.globalize_path("res://evidence/traversal_results.json")))
	var file:=FileAccess.open(path,FileAccess.WRITE)
	if file:file.store_string(JSON.stringify(report,"  ")+"\n")

func abort(message: String) -> void:
	push_error(message);report.status="error";report.errors.append(message);write_report();stage="finished";get_tree().quit(1)
func vec(value: Vector3) -> Array:return [value.x,value.y,value.z]

const MAX_STEP := 0.18
func step_event(kind: String, info: Dictionary) -> void:
	if not result.has("step_events"):result.step_events=[]
	info.kind=kind;info.frame=route_frames;info.position=vec(body.position)
	result.step_events.append(info)

func candidate_stair_move(delta: float, offset: Vector3) -> void:
	var was_grounded:=body.is_on_floor()
	var horizontal:=Vector3(body.velocity.x,0,body.velocity.z)*delta
	if was_grounded and horizontal.length()>0:
		var blocked:=KinematicCollision3D.new()
		if body.test_move(body.global_transform,horizontal,blocked,.001) and blocked.get_normal().y<.95:
			var up:=Vector3.UP*MAX_STEP
			var raised:=body.global_transform;raised.origin+=up
			var advanced:=raised;advanced.origin+=horizontal
			var landing:=KinematicCollision3D.new()
			var reason:=""
			if body.test_move(body.global_transform,up,null,.001):reason="headroom"
			elif body.test_move(raised,horizontal,null,.001):reason="forward_obstacle"
			elif not body.test_move(advanced,-up,landing,.001):reason="no_landing"
			elif landing.get_normal().y<cos(body.floor_max_angle):reason="landing_not_floor"
			elif landing.get_position().y-(body.position.y-HEIGHT*.5)>MAX_STEP+.001:reason="surface_overheight"
			elif up.y+landing.get_travel().y>MAX_STEP+.001:reason="body_overheight"
			if reason=="":
				var before:=body.position
				var actual_up=body.move_and_collide(up)
				if actual_up!=null:abort("Up sweep changed between query and movement");return
				var actual_forward=body.move_and_collide(horizontal)
				if actual_forward!=null:abort("Forward sweep changed between query and movement");return
				var actual_down=body.move_and_collide(-up)
				if actual_down==null:abort("Landing vanished between query and movement");return
				body.velocity=Vector3(0,-.25,0);body.move_and_slide()
				step_event("step_up",{"delta_xyz_m":vec(body.position-before),"landing_normal":vec(actual_down.get_normal()),"landing_point":vec(actual_down.get_position()),"full_capsule_sweeps":3})
				return
			elif route_frames%15==0:step_event("rejected_up",{"reason":reason})
	body.move_and_slide()
	if was_grounded and not body.is_on_floor() and body.velocity.y<=0:
		var down:=Vector3.DOWN*MAX_STEP
		var landing:=KinematicCollision3D.new()
		if body.test_move(body.global_transform,down,landing,.001) and landing.get_normal().y>=cos(body.floor_max_angle):
			var surface_drop:=body.position.y-HEIGHT*.5-landing.get_position().y
			if surface_drop<=MAX_STEP+.001:
				var before:=body.position;var actual=body.move_and_collide(down)
				if actual==null:abort("Step-down landing vanished");return
				body.velocity=Vector3(0,-.25,0);body.move_and_slide()
				step_event("step_down",{"delta_xyz_m":vec(body.position-before),"landing_normal":vec(actual.get_normal()),"landing_point":vec(actual.get_position()),"surface_drop_m":surface_drop,"full_capsule_sweeps":1})
