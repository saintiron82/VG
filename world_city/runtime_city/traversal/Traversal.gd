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
var report: Dictionary = {"schema":"riverstone.city.capsule_results.v1", "status":"loading", "engine":"Godot CharacterBody3D / GodotPhysics3D", "routes":[], "errors":[]}
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
var negative_phase := false

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
	call_deferred("build_collision_world")

func build_collision_world() -> void:
	for key in prepared.assets:
		var asset: Dictionary = prepared.assets[key]
		var read: Dictionary = RD.read(str(prepared.repo_root)+"/"+str(asset.render_path))
		if read.has("error"): abort(str(read.error)); return
		if read.sha256 != asset.render_sha256: abort("Compiled render hash changed: "+key);return
		var vertices := PackedVector3Array()
		for group in read.data.groups:
			for quad in group.quads:
				for index in RD.TRIANGLE_ORDER: vertices.append(RD.vector(quad[index]))
		var shape := ConcavePolygonShape3D.new()
		shape.backface_collision=false
		shape.set_faces(vertices)
		shapes[key]=shape
		triangle_count+=vertices.size()/3
		triangle_asset_count+=1
	for placement in prepared.placements:
		var static_body := StaticBody3D.new()
		static_body.name="Infra_"+str(placement.id).replace(":","_")
		static_body.set_meta("source_id",str(placement.id))
		static_body.set_meta("category",str(placement.category))
		static_body.collision_layer=int(placement.collision_layer)
		static_body.collision_mask=0
		var basis := Basis(Vector3.UP,deg_to_rad(float(placement.get("yaw_deg",0))))
		if placement.has("transform") and placement.transform.has("basis"):
			var rows: Array=placement.transform.basis
			basis=Basis(RD.vector(rows[0]),RD.vector(rows[1]),RD.vector(rows[2])).transposed()
		static_body.transform=Transform3D(basis,RD.vector(placement.position_m))
		var collision := CollisionShape3D.new();collision.shape=shapes[placement.asset_key]
		static_body.add_child(collision);add_child(static_body)
	for building in prepared.buildings:
		var static_body := StaticBody3D.new()
		static_body.name="Building_"+str(building.id)
		static_body.set_meta("source_id",str(building.id));static_body.set_meta("category","building_envelope")
		static_body.collision_layer=2;static_body.collision_mask=0
		static_body.position=RD.vector(building.position_m)
		static_body.rotation.y=float(building.yaw_rad)
		for bounds in building.boxes:
			var lo := RD.vector(bounds.min);var hi := RD.vector(bounds.max)
			var shape := BoxShape3D.new();shape.size=hi-lo
			var collision := CollisionShape3D.new();collision.shape=shape;collision.position=(lo+hi)*.5
			static_body.add_child(collision);box_count+=1
		add_child(static_body)
	body=CharacterBody3D.new();body.name="GenericCapsule_0p3r_1p8h"
	body.collision_layer=4;body.collision_mask=3;body.safe_margin=.001
	body.floor_snap_length=.2;body.floor_max_angle=deg_to_rad(45)
	var capsule := CapsuleShape3D.new();capsule.radius=RADIUS;capsule.height=HEIGHT
	var collision := CollisionShape3D.new();collision.shape=capsule;body.add_child(collision);add_child(body)
	var filter_text: String=str(options.get("routes",""))
	var selected: PackedStringArray=filter_text.split(",",false)
	for item in prepared.routes:
		if selected.is_empty() or str(item.id) in selected:routes.append(item)
	if str(options.get("negative-controls","true"))=="true":
		routes.append({"id":"NEGATIVE_RIVER_HAS_NO_INFINITE_FLOOR","kind":"negative_control","points":[[-700,0,490],[-698,0,490]],"length_m":2.,"source_road_ids":[],"expected_failure":"spawn_not_grounded"})
		routes.append({"id":"NEGATIVE_CASTLE_WALL_IS_SOLID","kind":"negative_control","points":[[-440,0,-325],[-440,0,-345]],"length_m":20.,"source_road_ids":[],"expected_failure":"blocked"})
	report.collision_world={"infrastructure_instances":prepared.placements.size(),"building_instances":prepared.buildings.size(),"building_box_shapes":box_count,"unique_exact_render_shapes":triangle_asset_count,"unique_exact_triangles":triangle_count,"infinite_ground_plane":false,"building_collision_policy":"conservative_envelope_minus_explicit_openings"}
	report.load_ms=Time.get_ticks_msec()-started_ms
	print("COLLISION_WORLD_READY "+JSON.stringify(report.collision_world))
	stage="world_settle";settle_frames=0

func _physics_process(delta: float) -> void:
	if stage=="loading" or stage=="finished":return
	simulation_frames+=1
	if stage=="world_settle":
		settle_frames+=1
		if settle_frames>=3: next_route()
		return
	if stage=="settling":
		body.velocity=Vector3(0,body.velocity.y-GRAVITY*delta,0)
		body.move_and_slide();settle_frames+=1
		if settle_frames>=45:
			result.spawn_position=vec(body.position)
			result.spawn_on_floor=body.is_on_floor()
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
	body.move_and_slide()
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
	if feet_y < -.35 or no_floor_streak>30: finish_route("ground_lost");return
	if still_frames>=120:finish_route("blocked");return
	if route_frames>=target_frame_budget:finish_route("timeout");return

func next_route() -> void:
	route_index+=1
	if route_index>=routes.size():finish_suite();return
	route=routes[route_index];route_frames=0;settle_frames=0;waypoint_index=1;still_frames=0;no_floor_streak=0
	result={"id":route.id,"kind":route.kind,"status":"running","waypoints_total":route.points.size(),"waypoints_reached":1,"waypoint_reached_frames":[],"physics_frames":0,"distance_expected_m":route.length_m,"distance_walked_m":0.,"max_waypoint_error_m":0.,"max_centerline_error_m":0.,"min_feet_y_m":0.,"max_feet_y_m":0.,"not_on_floor_frames":0,"max_not_on_floor_streak":0,"ground_ray_miss_frames":0,"obstacle_contact_ids":{},"obstacle_contact_samples":[],"source_road_ids":route.source_road_ids,"within_route_teleports":0}
	if route.has("expected_failure"):result.expected_failure=route.expected_failure
	target_frame_budget=ceili(float(route.length_m)/SPEED*60*2)+600
	# This is the only body position assignment: permitted independent-case reset.
	body.position=RD.vector(route.points[0])+Vector3(0,HEIGHT*.5+.06,0)
	body.velocity=Vector3.ZERO;stage="settling"
	print("ROUTE_START "+str(route.id))

func finish_route(status: String) -> void:
	result.status=status
	result.clearance_warning=not result.obstacle_contact_ids.is_empty() and not route.has("expected_failure")
	result.end_position=vec(body.position)
	result.failed_target_index=waypoint_index if status!="reached" else null
	result.failed_target=route.points[waypoint_index] if status!="reached" else null
	result.settle_physics_frames=settle_frames
	result.simulated_walk_seconds=float(route_frames)/float(Engine.physics_ticks_per_second)
	result.pass=status==str(route.expected_failure) if route.has("expected_failure") else status=="reached" and int(result.ground_ray_miss_frames)==0 and int(result.not_on_floor_frames)==0
	report.routes.append(result)
	print("ROUTE_RESULT "+JSON.stringify(result))
	write_report()
	next_route()

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
