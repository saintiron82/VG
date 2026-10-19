extends SceneTree
const Plain=preload("res://CityWorld.gd")
const Detailed=preload("res://CityWorldAccessDetail.gd")
const Patch=preload("res://SurfacePatchMesh.gd")
const BASE="res://../near_detail_r01/city_upgrade/native_access_detail_r01/validation/reviewer_r01/"
func _init() -> void:call_deferred("run")
func vlist(v: Vector3) -> Array:return [v.x,v.y,v.z]
func sha_bytes(bytes: PackedByteArray) -> String:
	var context:=HashingContext.new();context.start(HashingContext.HASH_SHA256);context.update(bytes);return context.finish().hex_encode()
func collision_snapshot(node: Node, identities: bool) -> Array:
	var out: Array=[]
	for child in node.get_children():
		if child is CollisionShape3D:
			var row: Dictionary={"source":str(child.get_parent().get_meta("source_id","")),"transform":str(child.global_transform),"disabled":child.disabled,"layer":child.get_parent().collision_layer,"mask":child.get_parent().collision_mask,"faces_sha256":sha_bytes(child.shape.get_faces().to_byte_array()),"backface_collision":child.shape.backface_collision}
			if identities:row.node_id=child.get_instance_id();row.shape_id=child.shape.get_instance_id()
			out.append(row)
		out.append_array(collision_snapshot(child,identities))
	out.sort_custom(func(a,b):return JSON.stringify(a)<JSON.stringify(b))
	return out
func sample(w: Node3D,pose: Dictionary,probes: Array) -> Array:
	var result: Array=[];var tr: Transform3D=w._pose(pose)
	for p in probes:
		var point: Vector3=tr*Plain.RD.vector(p.local)
		var q:=PhysicsRayQueryParameters3D.create(point+Vector3(0,1,0),point-Vector3(0,3,0),1)
		q.hit_back_faces=false
		var hit:=w.get_world_3d().direct_space_state.intersect_ray(q)
		var row: Dictionary={"name":p.name,"kind":p.kind,"source_point":vlist(point),"hit":not hit.is_empty()}
		if not hit.is_empty():row.position=vlist(hit.position);row.normal=vlist(hit.normal);row.source_id=str(hit.collider.get_meta("source_id",""));row.source_visual_minus_physics_m=point.y-hit.position.y
		result.append(row)
	return result
func summarize(samples: Array) -> Dictionary:
	var stats: Dictionary={};var max_above:=-INF;var max_below:=-INF
	for row in samples:
		if not stats.has(row.kind):stats[row.kind]={"total":0,"hit":0,"miss":0,"max_source_visual_above_physics_m":-INF,"max_physics_above_source_visual_m":-INF}
		var s: Dictionary=stats[row.kind];s.total+=1
		if row.hit:s.hit+=1;s.max_source_visual_above_physics_m=maxf(s.max_source_visual_above_physics_m,row.source_visual_minus_physics_m);s.max_physics_above_source_visual_m=maxf(s.max_physics_above_source_visual_m,-row.source_visual_minus_physics_m)
		else:s.miss+=1
	return stats
func winding(repo: String) -> Dictionary:
	var config: Dictionary=JSON.parse_string(FileAccess.get_file_as_string("res://native_access_catalog.json"))
	var cat: Dictionary=JSON.parse_string(FileAccess.get_file_as_string(repo.path_join(config.module_catalog_path)))
	var triangles:=0;var bad:=0;var degenerate:=0;var modules:=0
	for row in cat.modules:
		var r: Dictionary=Plain.RD.read(repo.path_join(row.render_path));var mesh:=Patch.module_mesh(r.data);var arrays:=mesh.surface_get_arrays(0);var vertices: PackedVector3Array=arrays[Mesh.ARRAY_VERTEX];var normals: PackedVector3Array=arrays[Mesh.ARRAY_NORMAL]
		modules+=1
		for i in range(0,vertices.size(),3):
			triangles+=1;var cross: Vector3=(vertices[i+1]-vertices[i]).cross(vertices[i+2]-vertices[i]);var n: Vector3=normals[i]
			if cross.length_squared()<1e-18:degenerate+=1
			elif cross.normalized().dot(n)>-.99999:bad+=1
	return {"modules":modules,"triangles":triangles,"wrong_clockwise_normal_triangles":bad,"degenerate_triangles":degenerate,"all_pass":modules==75 and bad==0 and degenerate==0,"backing_faces":"Intentionally omitted by common Patch.module_mesh; source mesh remains authoritative behind them."}
func run() -> void:
	var repo:=ProjectSettings.globalize_path("res://../../..")
	var poses: Array=JSON.parse_string(FileAccess.get_file_as_string("res://../near_detail_r01/city_upgrade/native_access_detail_r01/validation/poses.json"))
	var probes: Array=JSON.parse_string(FileAccess.get_file_as_string(BASE+"support_probes.json"));var rows: Array=[]
	var mesh_check:=winding(repo)
	for i in poses.size():
		var pose: Dictionary=poses[i];var observer: Vector3=Transform3D(Basis(Vector3.UP,pose.yaw_rad),Plain.RD.vector(pose.position_m))*Vector3(0,1.7,1)
		var plain:=Plain.new();root.add_child(plain);var err:=plain.configure("res://generated/tile_r01/index.json",repo,false)
		var loaded_original:=err.is_empty() and plain.ensure_region(observer,0)
		await physics_frame;await physics_frame
		var baseline:=sample(plain,pose,probes[i].probes);var original_shapes:=collision_snapshot(plain,false);var original_tiles:=plain.loaded.keys();original_tiles.sort();plain.free()
		await physics_frame
		var w:=Detailed.new();root.add_child(w);err=w.configure("res://generated/tile_r01/index.json",repo,true)
		var loaded_detail:=err.is_empty() and w.ensure_region(observer,0)
		await physics_frame;await physics_frame
		var before:=collision_snapshot(w,true);var detailed_shapes:=collision_snapshot(w,false);var initial:=sample(w,pose,probes[i].probes)
		w.update_near_detail(observer,1)
		await physics_frame
		var near:=sample(w,pose,probes[i].probes);var near_stats: Dictionary=w.access_stats.duplicate(true)
		var tests:={"original_ensure_region_loaded":loaded_original,"detail_ensure_region_loaded":loaded_detail,"runtime_no_error":w.error.is_empty(),"same_original_collider_geometry":original_shapes==detailed_shapes,"same_original_support_before_detail":baseline==initial,"near_active":int(w.access_stats.active_modules)>0,"near_all_support_unchanged":initial==near,"near_collision_node_shape_identity":before==collision_snapshot(w,true),"near_count_bound":int(w.access_stats.active_modules)<=120,"near_mesh_bytes_bound":int(w.access_stats.geometry_estimated_bytes)<=24000000}
		w.update_near_detail(observer+Vector3(1000,0,1000),1);await physics_frame
		tests.far_zero_and_evicted=w.access_stats.active_modules==0 and w.access_meshes.is_empty() and w.access_nodes.is_empty();tests.far_support_unchanged=initial==sample(w,pose,probes[i].probes);tests.far_collision_identity=before==collision_snapshot(w,true)
		w.access_config.maximum_mesh_bytes=0;w.update_near_detail(observer,1);await physics_frame
		tests.zero_budget_preserves_original=w.access_stats.active_modules==0 and initial==sample(w,pose,probes[i].probes) and before==collision_snapshot(w,true)
		w.access_config.maximum_mesh_bytes=24000000;w.access_last=Vector3(INF,INF,INF);w.update_near_detail(observer,1);tests.budget_restored=w.access_stats.active_modules>0
		var moved:=w.ensure_region(Vector3(0,0,0),0);await physics_frame;await process_frame
		w.update_near_detail(observer,1)
		tests.actual_owner_unload=moved and not w.access_records.has(str(pose.id));tests.stationary_observer_owner_unload_clears=w.access_nodes.is_empty() and w.access_meshes.is_empty() and w.access_stats.active_modules==0
		var detail_tiles:=w.loaded.keys();detail_tiles.sort()
		rows.append({"asset":pose.asset_key,"tests":tests,"all_pass":tests.values().all(func(v):return v),"original_loaded_tiles":original_tiles,"after_unload_loaded_tiles":detail_tiles,"original_shape_count":original_shapes.size(),"near_stats":near_stats,"support_summary":summarize(baseline),"baseline_samples":baseline,"scope":"Original CityWorld.ensure_region radius 0 plus all declared dependencies, compared to unchanged Detailed scene before/near/far/zero-budget. Rays are a source-support invariant check, not capsule locomotion or proof of arbitrary unsampled coverage."})
		w.free();await physics_frame
	var report:={"all_pass":mesh_check.all_pass and rows.size()==2 and rows.all(func(v):return v.all_pass),"mesh_winding":mesh_check,"assets":rows,"actual_walking_tested":false,"new_floor_or_collider_added":false}
	var f:=FileAccess.open(BASE+"scene_support.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n")
	for row in rows:print(JSON.stringify({"asset":row.asset,"tests":row.tests,"support_summary":row.support_summary,"near_stats":row.near_stats}))
	print(JSON.stringify({"all_pass":report.all_pass,"mesh_winding":mesh_check}));quit(0 if report.all_pass else 3)
