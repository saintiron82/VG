extends SceneTree
const POLICY = preload("res://RoadSurfaceSource.gd")
var failures: Array = []
var oracle_cases: Array = []
func require_pass(condition: bool, message: String) -> void:
	if not condition: failures.append(message)
func source_face(vertices: Array, plane: Array, index: int) -> Dictionary:
	return {"vertices_xyz_m": vertices, "plane_y_xz_m": plane, "tile_id": "synthetic_fixture", "face_index": index, "owners": [0], "material": "road"}
func rectangle(x0: float, z0: float, x1: float, z1: float, height: float = 0.0) -> Array:
	var a := Vector3(x0,height,z0); var b := Vector3(x1,height,z0); var c := Vector3(x1,height,z1); var d := Vector3(x0,height,z1)
	return [source_face([a,c,b],[0.0,0.0,height],0),source_face([a,d,c],[0.0,0.0,height],1)]
func circle_ring(inner: float, outer: float) -> Array:
	var faces: Array = []
	for i in 32:
		var a := TAU * float(i) / 32.0; var b := TAU * float(i+1) / 32.0
		var p := Vector3(0.5+cos(a)*inner,0,0.5+sin(a)*inner)
		var q := Vector3(0.5+cos(a)*outer,0,0.5+sin(a)*outer)
		var r := Vector3(0.5+cos(b)*outer,0,0.5+sin(b)*outer)
		var s := Vector3(0.5+cos(b)*inner,0,0.5+sin(b)*inner)
		faces.append(source_face([p,r,q],[0.0,0.0,0.0],i*2))
		faces.append(source_face([p,s,r],[0.0,0.0,0.0],i*2+1))
	return faces
func gather_near(policy: RefCounted, original: Dictionary, root: String, observer: Vector3, radius: float) -> Dictionary:
	var owners: Dictionary = {}; var faces: Array = []; var truncated := false
	for x in range(floori((observer.x-radius)/64.0),floori((observer.x+radius)/64.0)+1):
		for z in range(floori((observer.z-radius)/64.0),floori((observer.z+radius)/64.0)+1):
			var id := "%d_%d" % [x,z]
			if not original.tiles.has(id): continue
			owners[id] = true
			for owner in original.tiles[id].dependency_owner_tiles: owners[owner] = true
	var ordered: Array = owners.keys(); ordered.sort()
	for id in ordered:
		var binary := FileAccess.get_file_as_bytes(root.path_join(original.tiles[id].terrain_path))
		var result: Dictionary = policy.near_faces_for_tile(id,binary,observer,radius,4096)
		require_pass(not result.has("error"),"nearby loaded-owner source query " + id)
		faces.append_array(result.get("faces",[])); truncated = truncated or result.get("truncated",false)
	return {"faces":faces,"truncated":truncated,"owner_tiles_loaded":ordered.size()}
func check_modules(policy: RefCounted, planned: Dictionary, faces: Array, observer: Vector3, radius: float, label: String) -> void:
	require_pass(not planned.has("error"),label+" valid plan: "+str(planned.get("error","")))
	require_pass(planned.candidate_checks<=256 and planned.modules.size()<=120 and planned.grid_slots_visited<=4096,label+" actual hard work bounds")
	for module in planned.modules:
		var transform: Transform3D = module.transform
		require_pass(absf(transform.basis.determinant()-1.0)<0.000001,label+" proper unit transform")
		require_pass(not module.collision_change and module.maximum_visual_collision_difference_m==0.0375,label+" collision unchanged and offset bounded")
		require_pass(not module.source_owner_indices.is_empty() and not module.source_face_refs.is_empty(),label+" source owner and face provenance")
		require_pass(module.seed in [41873,41879,41887],label+" deterministic approved seed family")
		var corners: Array = [transform*Vector3(0,0,-0.0375),transform*Vector3(1,0,-0.0375),transform*Vector3(1,1,-0.0375),transform*Vector3(0,1,-0.0375)]
		var contributors: Array = []
		for face in faces:
			if module.source_face_refs.has([face.tile_id,face.face_index]): contributors.append(face)
		var serialized_corners: Array = []
		for point in corners: serialized_corners.append([point.x,point.y,point.z])
		var serialized_faces: Array = []
		for face in contributors:
			var points: Array = []
			for point in face.vertices_xyz_m: points.append([point.x,point.y,point.z])
			serialized_faces.append({"vertices_xyz_m":points,"plane_y_xz_m":module.original_plane_y_xz_m,"tile_id":face.tile_id,"face_index":face.face_index})
		oracle_cases.append({"label":label,"corners_xyz_m":serialized_corners,"contributing_faces":serialized_faces,"seed":module.seed,"owners":module.source_owner_indices})
		for point in corners:
			require_pass(Vector2(point.x-observer.x,point.z-observer.z).length()<=radius+0.00002,label+" circular observer radius")
func signature(planned: Dictionary) -> String:
	var values: Array = []
	for module in planned.modules: values.append([module.seed,module.transform,module.original_plane_y_xz_m,module.source_face_refs,module.source_owner_indices])
	return str(values)
func _initialize() -> void:
	var root := ProjectSettings.globalize_path("res://../../..")
	var selected: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://../near_detail_r01/city_upgrade/road_surfaces/generated/source_index.json"))
	var original_path: String = root.path_join(selected.source_tile_index.path)
	var original: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(original_path))
	var policy := POLICY.new()
	require_pass(policy.configure(selected,original,FileAccess.get_sha256(original_path)),"source identity configuration")
	var binary := FileAccess.get_file_as_bytes(root.path_join(original.tiles["1_0"].terrain_path))
	var queried: Dictionary = policy.near_faces_for_tile("1_0",binary,Vector3(90,4.9,20),8.0,4096)
	require_pass(not queried.has("error") and queried.faces.size()>0,"actual market tile query")
	var bad := binary.duplicate();bad[0] = (int(bad[0])+1)%256
	require_pass(policy.near_faces_for_tile("1_0",bad,Vector3.ZERO).has("error"),"corrupted original BIN rejected")
	var corners: Array = [Vector3(0,0,0),Vector3(1,0,0),Vector3(1,0,1),Vector3(0,0,1)]
	require_pass(policy.footprint_supported(corners,rectangle(0,0,1,1)),"complete two-triangle support")
	var hole := rectangle(0,0,.49,1)+rectangle(.51,0,1,1)
	var step := rectangle(0,0,.5,1)+rectangle(.5,0,1,1,.1)
	require_pass(not policy.footprint_supported(corners,hole),"2 cm hole remains unfilled")
	require_pass(not policy.footprint_supported(corners,step),"different step heights never combined")
	var observer := Vector3(.5,0,.5)
	var full: Dictionary = policy.plan_local_modules(rectangle(0,0,1,1),observer,2.0)
	require_pass(full.modules.size()==1,"one full supported 1 m square planned")
	check_modules(policy,full,rectangle(0,0,1,1),observer,2.0,"synthetic square")
	require_pass(policy.plan_local_modules(hole,observer,2.0).modules.is_empty(),"planner never fills 2 cm water slit")
	require_pass(policy.plan_local_modules(step,observer,2.0).modules.is_empty(),"planner never bridges 10 cm step")
	var annulus := circle_ring(.35,2.6)
	var circular: Dictionary = policy.plan_local_modules(annulus,observer,3.5)
	require_pass(circular.modules.size()>0,"finite circular source admits safe interior squares")
	check_modules(policy,circular,annulus,observer,3.5,"circular water-hole terrain")
	for module in circular.modules:
		var local: Vector3 = module.transform.affine_inverse()*observer
		require_pass(not(local.x>0 and local.x<1 and local.y>0 and local.y<1),"circular water hole remains uncovered")
	require_pass(policy.plan_local_modules([],observer,10.01).has("error"),"radius >10 m rejected")
	require_pass(policy.plan_local_modules([],observer,2,257).has("error"),"candidate limit cannot be increased")
	require_pass(policy.plan_local_modules([],observer,2,256,121).has("error"),"module limit cannot be increased")
	var capped: Dictionary = policy.plan_local_modules(rectangle(-4,-4,4,4),observer,3.0,1,120)
	require_pass(capped.truncated and capped.candidate_checks==1 and capped.reason=="candidate_check_budget","candidate proof cap enforced in execution")
	var fragmented: Array = []
	for i in 160: fragmented.append_array(rectangle(float(i)/160.0,0,float(i+1)/160.0,1))
	var support_capped: Dictionary = policy.plan_local_modules(fragmented,observer,2.0)
	require_pass(support_capped.truncated and support_capped.modules.is_empty() and support_capped.support_budget_rejections>0,"support proof overflow fails closed")
	var excessive: Array = []; excessive.resize(4097)
	require_pass(policy.plan_local_modules(excessive,observer,2).has("error"),"global face list cannot be passed")
	var transform := policy.rigid_frame([.1,.05,4.0])
	require_pass(absf(transform.basis.determinant()-1.0)<.000001,"proper rotation slope frame")
	var cases: Array = []
	for site in [["market",Vector3(90,4.9,20)],["upper_sloped_road",Vector3(-240,12.5,-85)],["south_country_road",Vector3(140,2,600)]]:
		var nearby := gather_near(policy,original,root,site[1],10.0)
		var plan: Dictionary = policy.plan_local_modules(nearby.faces,site[1],10.0)
		require_pass(not nearby.truncated and plan.modules.size()>0,site[0]+" actual nearby source yields modules")
		check_modules(policy,plan,nearby.faces,site[1],10.0,site[0])
		var elapsed: Array = [plan.elapsed_usec]
		for attempt in 4:
			var repeat: Dictionary = policy.plan_local_modules(nearby.faces,site[1],10.0)
			require_pass(signature(plan)==signature(repeat),site[0]+" deterministic replay")
			elapsed.append(repeat.elapsed_usec)
		elapsed.sort()
		var slopes := 0
		for module in plan.modules:
			if Vector2(module.original_plane_y_xz_m[0],module.original_plane_y_xz_m[1]).length()>.00001: slopes+=1
		cases.append({"site":site[0],"observer_xyz_m":[site[1].x,site[1].y,site[1].z],"radius_m":10,"source_faces":nearby.faces.size(),"loaded_owner_tiles":nearby.owner_tiles_loaded,"modules":plan.modules.size(),"sloped_modules":slopes,"candidate_checks":plan.candidate_checks,"grid_slots_visited":plan.grid_slots_visited,"plane_groups":plan.plane_group_count,"truncated":plan.truncated,"reason":plan.reason,"support_budget_rejections":plan.support_budget_rejections,"planner_median_ms":float(elapsed[2])/1000.0,"planner_max_ms":float(elapsed[-1])/1000.0,"timing_repeats":5})
	var output := {"status":"PASS" if failures.is_empty() else "FAIL","failures":failures,"actual_market_tile_faces":queried.get("faces",[]).size(),"actual_planner_cases":cases,"synthetic_water_hole_modules":circular.modules.size(),"headless_only":true,"whole_city_coverage_pass":false}
	var file := FileAccess.open("res://../near_detail_r01/city_upgrade/native_access_detail_r01/validation/reviewer_r01/road_existing_regression.json",FileAccess.WRITE);file.store_string(JSON.stringify(output,"  ")+"\n");file.close()
	var oracle := FileAccess.open("res://../near_detail_r01/city_upgrade/native_access_detail_r01/validation/reviewer_r01/road_oracle_cases.json",FileAccess.WRITE)
	oracle.store_string(JSON.stringify({"schema":"riverstone.public_paving.headless_oracle.v1","cases":oracle_cases})+"\n");oracle.close()
	print(JSON.stringify(output));quit(0 if failures.is_empty() else 1)
