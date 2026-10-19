extends SceneTree
## Actual composed asset at its source city pose; no artificial geometry fixtures.
## This checks cache/LOD/collision identity, not city traversal or visual approval.
const World=preload("res://CityWorldSurfaces.gd")
const KEY="registered_port_long_loading_shed"
const OUT="res://../near_detail_r01/city_upgrade/evidence/facility_runtime_r01"
var checks: Array=[]
func _init() -> void:call_deferred("run")
func check(name: String,value: bool,details: Variant=null) -> void:checks.append({"case":name,"pass":value,"details":details})
func collisions(node: Node) -> Array:
	var result: Array=[]
	for child in node.get_children():
		if child is CollisionShape3D:result.append({"node":child.get_instance_id(),"shape":child.shape.get_instance_id(),"pose":str(child.global_transform),"disabled":child.disabled})
		result.append_array(collisions(child))
	return result
func run() -> void:
	var world:=World.new();root.add_child(world)
	check("configure_current_source",world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),true).is_empty())
	var records: Array=JSON.parse_string(FileAccess.get_file_as_string(OUT+"/actual_port_placements.json"))
	var pose: Dictionary=records[0].pose
	var owner:=Node3D.new();world.add_child(owner)
	check("load_actual_source_pose",world._add_native(owner,pose),pose)
	var before:=collisions(owner)
	check("source_collisions_present",not before.is_empty(),before.size())
	var tr: Transform3D=world._pose(pose);var observer: Vector3=tr*Vector3(0,2,9)
	var time:=Time.get_ticks_usec()
	world.update_near_detail(observer,1.0)
	var near_time:=(Time.get_ticks_usec()-time)/1000.0
	var record: Dictionary=world.detail_records[pose.id]
	var active: bool=record.fine!=null and is_instance_valid(record.fine.get_ref())
	check("actual_composed_fine_activates",active,world.error)
	check("one_verified_native_asset_cached",world.detail_cache.size()==1 and world.detail_cache.has(KEY),world.debug_state().near_detail)
	check("collision_nodes_shapes_poses_unchanged_near",before==collisions(owner))
	check("source_coarse_hidden_only_after_success",active and not record.coarse.get_ref().visible)
	if active:
		check("actual_fine_pose_identical",record.fine.get_ref().transform.is_equal_approx(tr))
		check("native_cache_geometry_bytes",world.detail_cached_bytes==18062208,world.detail_cached_bytes)
		var entry: Dictionary=world.detail_catalog.assets[KEY]
		check("twenty_windows_plus_four_interfaces_bound",entry.window_regions.size()==20 and entry.surface_exclusion_regions.size()==24)
		var inspected:=0;var rejected:=0;var outside:=0
		for face in world._surface_faces_for(KEY):
			for patch in World.Patch.full_patches(face,Vector3(0,3,9),30):
				inspected+=1
				var expected: bool=World.patch_intersects_regions(patch,entry.surface_exclusion_regions)
				var actual: bool=world._patch_intersects_active_window(str(pose.id),patch)
				if expected:rejected+=1
				else:outside+=1
				if expected!=actual:check("actual_patch_exclusion_mismatch",false,patch)
		check("actual_facade_patches_exercised",inspected>0 and rejected>0 and outside>0,{"inspected":inspected,"excluded":rejected,"retained":outside})
		var exact_regions: Array=world.surface_feature_regions.get(KEY,[]).duplicate(true)
		for region in exact_regions:
			for axis in 3:region.min[axis]+=.0001;region.max[axis]-=.0001
		var cropped_count:=0;var conflicts:=0
		for face in world._surface_faces_for_owner(str(pose.id),KEY):
			for patch in World.Patch.trimmed_patches(face,Vector3(0,3,9),30):
				cropped_count+=1
				if World.patch_intersects_regions(patch,exact_regions):conflicts+=1
		check("source_feature_trim_contract_loaded",exact_regions.size()==24)
		check("trimmed_actual_facade_never_overlays_window_or_interface",cropped_count>0 and conflicts==0,{"cropped_patches":cropped_count,"positive_overlap_conflicts":conflicts})
	var revision:=world.detail_revision
	world.update_near_detail(observer+Vector3(300,0,0),1.0)
	check("far_restores_original_mesh",record.fine==null and record.coarse.get_ref().visible)
	check("collision_nodes_shapes_poses_unchanged_far",before==collisions(owner))
	check("lod_revision_notifies_wall_overlay",world.detail_revision>revision)
	world._evict(KEY);world.detail_catalog.cache_budget_vertex_normal_bytes=1
	world.update_near_detail(observer,1.0)
	check("insufficient_budget_keeps_original_visible",record.fine==null and record.coarse.get_ref().visible and world.detail_cache.is_empty())
	world.detail_catalog.cache_budget_vertex_normal_bytes=100663296
	world.update_near_detail(observer,1.0)
	check("budget_restore_reactivates_verified_asset",record.fine!=null and world.detail_cache.has(KEY))
	check("collision_identity_survives_reload",before==collisions(owner))
	var report:={"scope":"Headless actual composed facility at exact source pose. LOD, shared cache and collision identity only; no GUI image or traversal claim.","all_pass":checks.all(func(c):return c.pass),"checks":checks,"initial_activation_cpu_ms":near_time,"render_fps_measured":false,"source_city_index_sha256":world.index_sha256,"state":world.debug_state()}
	var f:=FileAccess.open(OUT+"/actual_port_lod_validation.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 2)
