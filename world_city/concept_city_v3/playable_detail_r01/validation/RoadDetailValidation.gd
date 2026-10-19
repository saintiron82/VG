extends SceneTree
const World=preload("res://CityWorldRoadDetail.gd")
var checks: Array=[]
func check(name: String,value: bool,detail: Variant=null) -> void:checks.append({"case":name,"pass":value,"detail":detail})
func _init() -> void:call_deferred("run")
func floors(world: Node3D,observer: Vector3) -> Array:
	var results: Array=[]
	for x in [-2,0,2]:
		for z in [-2,0,2]:
			var origin:=observer+Vector3(x,3,z)
			var hit:=world.get_world_3d().direct_space_state.intersect_ray(PhysicsRayQueryParameters3D.create(origin,origin-Vector3(0,8,0),1))
			results.append({"position":str(hit.get("position")),"normal":str(hit.get("normal")),"id":str(hit.collider.get_meta("source_id","unknown")) if not hit.is_empty() else "none"})
	return results
func run() -> void:
	var world:=World.new();root.add_child(world)
	var problem:=world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),true)
	check("all_source_catalog_bindings",problem.is_empty(),problem)
	var position:=Vector3(98.41505784216918,4,48.75638652919374)
	if problem.is_empty():
		check("original_city_market_load",world.ensure_region(position,1),world.error)
		await physics_frame;await physics_frame
		var before:=floors(world,position)
		world.update_near_detail(position,1)
		await physics_frame;await physics_frame
		check("road_layer_runtime_has_no_error",world.error.is_empty(),world.error)
		check("actual_paving_resources_instanced",world.road_stats.active_modules>0,world.road_stats)
		check("bounded_active_modules",world.road_stats.active_modules<=120)
		check("bounded_binary_cache",world.road_stats.binary_cache_bytes<=12*1024*1024)
		check("original_floor_collision_unchanged",JSON.stringify(before)==JSON.stringify(floors(world,position)),before)
		var builds:=JSON.stringify(world.road_stats)
		world.update_near_detail(position,.6)
		check("stationary_observer_reuses_placement",JSON.stringify(world.road_stats)==builds)
		var shared:=true
		for key in world.road_nodes:
			shared=shared and world.road_nodes[key].multimesh.mesh.get_rid()==world._surface_module(key).get_rid()
		check("multimesh_uses_shared_common_mesh",shared)
	var report={"schema":"riverstone.road_detail.integration_tests.v1","all_pass":checks.all(func(c):return c.pass),"checks":checks,"scope":"Actual source-coordinate market, real common modules and unchanged nine floor collision samples; not rendered visual acceptance or whole city traversal"}
	var file:=FileAccess.open(ProjectSettings.globalize_path("res://../near_detail_r01/city_upgrade/road_runtime_validation.json"),FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 2)
