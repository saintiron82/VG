extends Node3D
const World=preload("res://CityWorldDetail.gd")
var checks: Array=[]
func check(name: String,passed: bool,details: Variant=null) -> void:
	checks.append({"case":name,"pass":passed,"details":details})
func _ready() -> void:
	var world:=World.new();add_child(world)
	var problem:=world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),true)
	check("catalog_binding",problem.is_empty(),problem)
	var owner:=Node3D.new();world.add_child(owner)
	var key: String=world.detail_catalog.assets.keys()[0]
	var a: Dictionary={"id":"fixture_A","asset_key":key,"position_m":[0,0,0],"yaw_rad":0,"palette_override":{"slate":"a16b51"}}
	var b: Dictionary={"id":"fixture_B","asset_key":key,"position_m":[10,0,0],"yaw_rad":0,"palette_override":{"slate":"456171"}}
	check("add_same_asset_twice",world._add_native(owner,a) and world._add_native(owner,b))
	world.update_near_detail(Vector3(5,0,8),.3)
	check("one_shared_cache",world.detail_cache.size()==1 and world.detail_builds==1,world.debug_state().near_detail)
	var f1: Node3D=world.detail_records.fixture_A.fine.get_ref();var f2: Node3D=world.detail_records.fixture_B.fine.get_ref()
	check("shared_mesh_resource",f1.get_child(0).mesh.get_rid()==f2.get_child(0).mesh.get_rid())
	var slot_diff:=false
	for i in range(f1.get_child_count()):
		if str(f1.get_child(i).get_meta("material_slot",""))=="slate":slot_diff=f1.get_child(i).material_override.albedo_color!=f2.get_child(i).material_override.albedo_color
	check("palette_isolated_per_instance",slot_diff)
	world.update_near_detail(Vector3(500,0,500),.3)
	check("far_restores_coarse",world.detail_records.fixture_A.fine==null and world.detail_records.fixture_A.coarse.get_ref().visible)
	# Deliberately reduce budget below one geometry to verify graceful deferral.
	world._evict(key);world.detail_catalog.cache_budget_vertex_normal_bytes=1
	world.update_near_detail(Vector3(5,0,8),.3)
	check("budget_defers_without_hidden_coarse",world.detail_cache.size()==0 and world.detail_records.fixture_A.coarse.get_ref().visible and world.detail_deferred>0)
	world.detail_catalog.cache_budget_vertex_normal_bytes=100663296
	world.update_near_detail(Vector3(5,0,8),.3)
	check("rebuild_after_eviction",world.detail_builds==2 and world.detail_cache.size()==1)
	owner.queue_free();await get_tree().process_frame;await get_tree().process_frame
	world.update_near_detail(Vector3(500,0,500),.3)
	check("owner_unload_prunes_records",world.detail_records.is_empty())
	var report={"scope":"headless synthetic owner fixtures, not whole-city traversal","checks":checks,"all_pass":checks.all(func(c):return c.pass),"state":world.debug_state()}
	var path:=ProjectSettings.globalize_path("res://../near_detail_r01/city_upgrade/detail_cache_validation.json")
	var file:=FileAccess.open(path,FileAccess.WRITE);file.store_string(JSON.stringify(report,"\t"));print(JSON.stringify(report));get_tree().quit(0 if report.all_pass else 2)
