extends SceneTree
const Current=preload("res://RoadSurfaceSource.gd")
const Old=preload("res://../near_detail_r01/city_upgrade/native_access_detail_r01/validation/reviewer_r01/RoadSurfaceSource.before.gd")
const BASE="res://../near_detail_r01/city_upgrade/native_access_detail_r01/validation/reviewer_r01/"
func residual(face: Dictionary) -> float:
	var worst:=0.0;var p: Array=face.plane_y_xz_m
	for v in face.vertices_xyz_m:worst=maxf(worst,absf(float(v.y)-float(p[0])*float(v.x)-float(p[1])*float(v.z)-float(p[2])))
	return worst
func _init() -> void:
	var repo:=ProjectSettings.globalize_path("res://../../..")
	var index: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://generated/tile_r01/index.json"))
	var config: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://road_catalog.json"))
	var policy: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(repo.path_join(config.policy_path)))
	var previous:=Old.new();var current:=Current.new()
	previous.configure(policy,index,config.source_city_index_sha256);current.configure(policy,index,config.source_city_index_sha256)
	var captured: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://../near_detail_r01/city_upgrade/native_access_detail_r01/evidence/actual_r01/stair_before.json"))
	var obs: Array=captured.observer;var observer:=Vector3(obs[0],obs[1],obs[2])
	var owners: Dictionary={}
	for x in range(floori((observer.x-12)/64),floori((observer.x+12)/64)+1):
		for z in range(floori((observer.z-12)/64),floori((observer.z+12)/64)+1):
			var id:="%d_%d"%[x,z]
			if index.tiles.has(id):
				owners[id]=true
				for owner in index.tiles[id].dependency_owner_tiles:owners[owner]=true
	var ids:=owners.keys();ids.sort();var old_faces: Array=[];var new_faces: Array=[];var bad: Array=[];var vertices_identical:=true;var max_old:=0.0;var max_new:=0.0
	for id in ids:
		var binary:=FileAccess.get_file_as_bytes(repo.path_join(index.tiles[id].terrain_path))
		var a: Dictionary=previous.near_faces_for_tile(id,binary,observer,12,4096)
		var b: Dictionary=current.near_faces_for_tile(id,binary,observer,12,4096)
		old_faces.append_array(a.faces);new_faces.append_array(b.faces)
		if a.faces.size()!=b.faces.size():vertices_identical=false
		for i in mini(a.faces.size(),b.faces.size()):
			vertices_identical=vertices_identical and a.faces[i].vertices_xyz_m==b.faces[i].vertices_xyz_m and a.faces[i].face_index==b.faces[i].face_index
			var ra:=residual(a.faces[i]);var rb:=residual(b.faces[i]);max_old=maxf(max_old,ra);max_new=maxf(max_new,rb)
			if ra>0.00001:bad.append({"tile":id,"face_index":a.faces[i].face_index,"old_plane":a.faces[i].plane_y_xz_m,"new_plane":b.faces[i].plane_y_xz_m,"old_residual_m":ra,"new_residual_m":rb,"vertices_unchanged":a.faces[i].vertices_xyz_m==b.faces[i].vertices_xyz_m})
	var old_plan: Dictionary=previous.plan_local_modules(old_faces,observer,10,256,120)
	var new_plan: Dictionary=current.plan_local_modules(new_faces,observer,10,256,120)
	var tests:={"same_source_vertices_and_refs":vertices_identical,"prior_mismatch_reproduced":old_plan.get("error","")=="Source plane/vertex mismatch","new_strict_plane_bound":max_new<=0.00001,"fixed_plan_no_error":not new_plan.has("error"),"same_hard_caps":new_plan.modules.size()<=120 and new_plan.candidate_checks<=256}
	var report:={"tests":tests,"all_pass":tests.values().all(func(v):return v),"observer":obs,"owner_tiles":ids,"old_face_count":old_faces.size(),"new_face_count":new_faces.size(),"old_max_residual_m":max_old,"new_max_residual_m":max_new,"old_error":old_plan.get("error",""),"new_error":new_plan.get("error",""),"new_modules":new_plan.modules.size(),"bad_faces":bad,"current_selector_sha256":FileAccess.get_sha256("res://RoadSurfaceSource.gd"),"previous_selector_sha256":FileAccess.get_sha256(BASE+"RoadSurfaceSource.before.gd")}
	var name:="road_plane_after.json" if OS.get_cmdline_user_args().has("--after") else "road_plane_before.json"
	var f:=FileAccess.open(BASE+name,FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 3)
