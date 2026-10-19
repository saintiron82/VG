extends SceneTree
const World=preload("res://CityWorldAccessDetail.gd")
func _init() -> void:call_deferred("run")
func collision_snapshot(node: Node) -> Array:
	var out: Array=[]
	for child in node.get_children():
		if child is CollisionShape3D:out.append([child.get_instance_id(),child.shape.get_instance_id(),str(child.global_transform),child.disabled])
		out.append_array(collision_snapshot(child))
	return out
func run() -> void:
	var base:=OS.get_environment("FAR_INTEGRATION_REPORT_DIR")+"/"
	if not FileAccess.file_exists(base+"access_poses16.json"):push_error("Missing explicit access pose source: "+base);quit(2);return
	var poses: Array=JSON.parse_string(FileAccess.get_file_as_string(base+"access_poses16.json"));var rows: Array=[]
	for pose in poses:
		var w:=World.new();root.add_child(w);var problem:=w.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),true)
		var owner:=Node3D.new();w.add_child(owner);var added: bool=problem.is_empty()and w._add_native(owner,pose);var before:=collision_snapshot(owner)
		var key: String=pose.asset_key;var source: Dictionary=w.access_assets[key];var local: Transform3D=w.access_pose(source.placements[0].transform);var observer: Vector3=w._pose(pose)*(local.origin+Vector3(.1,1.7,-.1))
		w.update_near_detail(observer,1)
		var tests:={"source_added":added,"no_runtime_error":w.error.is_empty(),"source_collision_mode_matches_contract":before.is_empty()==w.disabled.has(str(pose.id)),"near_detail_active":int(w.access_stats.active_modules)>0,"collision_near_identical":before==collision_snapshot(owner),"module_count_bounded":w.access_stats.active_modules<=120,"mesh_bytes_bounded":w.access_stats.geometry_estimated_bytes<=24000000}
		var proxy_verified:=true
		if w.disabled.has(str(pose.id)):
			proxy_verified=false
			for contract in w.index.collision_contracts:
				if contract.get("native_placement_id","")==str(pose.id) and contract.has("replacement_local_mesh"):
					var replacement: Dictionary=contract.replacement_local_mesh
					proxy_verified=FileAccess.get_sha256(w._path(replacement.path))==replacement.sha256 and contract.native_source.sha256==w.index.common_assets[key].render_sha256
				tests.declared_continuous_proxy_verified=proxy_verified
		var near: Dictionary=w.access_stats.duplicate(true)
		w.update_near_detail(observer+Vector3(100,0,0),1)
		tests.far_modules_zero=w.access_stats.active_modules==0;tests.far_mesh_evicted=w.access_meshes.is_empty();tests.collision_far_identical=before==collision_snapshot(owner)
		w.access_config.maximum_mesh_bytes=0;w.update_near_detail(observer,1)
		tests.budget_zero_keeps_original=w.access_stats.active_modules==0 and before==collision_snapshot(owner)
		w.access_config.maximum_mesh_bytes=24000000;w.access_last=Vector3(INF,INF,INF);w.update_near_detail(observer,1)
		tests.budget_restore=w.access_stats.active_modules>0
		owner.free();w.update_near_detail(observer,1)
		tests.owner_unload_clears_modules=w.access_stats.active_modules==0 and w.access_records.is_empty() and w.access_meshes.is_empty()
		rows.append({"asset":key,"tests":tests,"near_stats":near,"all_pass":tests.values().all(func(v):return v)})
		w.free()
	var report:={"all_pass":rows.size()==16 and rows.all(func(v):return v.all_pass),"assets":rows,"scope":"Exact native source poses; near/far resource bounds and original collision identity. Native stairs intentionally use an existing source-hash-bound continuous collision proxy; this isolated owner test verifies that contract, not physical support. Not capsule route replay or whole-city acceptance."}
	var destination:=OS.get_environment("NATIVE_ACCESS_VALIDATION_OUTPUT")
	if destination.is_empty():destination=base+"runtime_r02.json"
	var f:=FileAccess.open(destination,FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 3)
