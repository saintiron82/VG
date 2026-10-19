extends SceneTree
## Real selected source poses; LOD/collision identity, not movement replay.
const World=preload("res://CityWorldSurfaces.gd")
var rows: Array=[]
func _init() -> void:call_deferred("run")
func collision_snapshot(node: Node) -> Array:
	var out: Array=[]
	for child in node.get_children():
		if child is CollisionShape3D:out.append([child.get_instance_id(),child.shape.get_instance_id(),str(child.global_transform),child.disabled])
		out.append_array(collision_snapshot(child))
	return out
func run() -> void:
	var base:="res://../near_detail_r01/city_upgrade/evidence/"
	var records: Array=JSON.parse_string(FileAccess.get_file_as_string(base+"changed_asset_poses_r01.json"))
	for pose in records:
		var world:=World.new();root.add_child(world)
		var problem:=world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),true)
		var owner:=Node3D.new();world.add_child(owner)
		var added: bool=problem.is_empty() and world._add_native(owner,pose)
		var before:=collision_snapshot(owner);var key: String=pose.asset_key
		var tr: Transform3D=world._pose(pose);var observer: Vector3=tr*Vector3(0,1.7,7)
		world.update_near_detail(observer,1)
		var record: Dictionary=world.detail_records.get(pose.id,{})
		var active: bool=not record.is_empty() and record.fine!=null and is_instance_valid(record.fine.get_ref())
		var tests:={"source_pose_added":added,"source_colliders_exist":not before.is_empty(),"fine_active":active,"same_collision_near":before==collision_snapshot(owner),"native_cache_used":world.detail_cache.has(key),"no_runtime_error":world.error.is_empty()}
		if active:tests.same_pose=record.fine.get_ref().transform.is_equal_approx(tr)
		world.update_near_detail(observer+Vector3(300,0,0),1)
		tests.far_restores_coarse=record.fine==null and record.coarse.get_ref().visible
		tests.same_collision_far=before==collision_snapshot(owner)
		world._evict(key) # Budget fault injection must exercise cold load, not reuse a previously resident cache.
		world.detail_catalog.cache_budget_vertex_normal_bytes=1;world.update_near_detail(observer,1)
		tests.low_budget_keeps_coarse=record.fine==null and record.coarse.get_ref().visible
		world.detail_catalog.cache_budget_vertex_normal_bytes=100663296;world.update_near_detail(observer,1)
		tests.budget_restored_fine=record.fine!=null
		tests.same_collision_reload=before==collision_snapshot(owner)
		rows.append({"asset":key,"placement_id":pose.id,"tests":tests,"all_pass":tests.values().all(func(v):return v),"state":world.debug_state()})
		world.free()
	var report:={"all_pass":rows.all(func(row):return row.all_pass),"assets":rows,"scope":"Actual source placement LOD/budget and collision node/shape/transform identity. Not capsule traversal, interior accessibility or final art acceptance."}
	var f:=FileAccess.open(base+"changed_assets_lod_r02.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 3)
