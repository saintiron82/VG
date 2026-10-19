extends SceneTree
const World=preload("res://CityWorldSurfaces.gd")
var checks: Array=[]
func _init() -> void:call_deferred("run")
func run() -> void:
	var space:=Node3D.new();root.add_child(space)
	var world:=World.new();space.add_child(world)
	var error:=world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),false)
	checks.append({"case":"all_catalog_bindings","pass":error.is_empty(),"error":error})
	var targets: Array=[];var i:=0
	if error.is_empty():
		for key in world.detail_catalog.assets:
			var position:=Vector3(i*100,0,0);i+=1
			var owner:=Node3D.new();world.add_child(owner)
			var placement: Dictionary={"id":"entry_fixture_"+key,"asset_key":key,"position_m":[position.x,0,0],"yaw_rad":.71}
			var added:=world._add_native(owner,placement)
			checks.append({"case":"source_collision_plus_closed_contract_"+key,"pass":added})
			for repair in world.detail_catalog.assets[key].get("collision_repairs",[]):
				var tr: Transform3D=world._pose(placement)*world._local_transform(repair.get("transform",{}))
				var centre: Vector3=(World.RD.vector(repair.min)+World.RD.vector(repair.max))*.5
				centre.z=float(repair.max[2]);var front:=tr*centre;var normal:=tr.basis*Vector3(0,0,1)
				targets.append({"id":key+"/"+str(repair.id),"point":front,"normal":normal})
	await physics_frame;await physics_frame
	for target in targets:
		var query:=PhysicsRayQueryParameters3D.create(target.point+target.normal*.4,target.point-target.normal*.3,1)
		var hit:=space.get_world_3d().direct_space_state.intersect_ray(query)
		var pass_hit: bool=not hit.is_empty() and hit.position.distance_to(target.point)<.001 and hit.normal.dot(target.normal)>.999
		checks.append({"case":"exact_closed_leaf_ray_"+target.id,"pass":pass_hit,"hit_position":str(hit.get("position")),"expected_position":str(target.point)})
	var report={"schema":"riverstone.near_entry.tests.v1","all_pass":checks.all(func(c):return c.pass),"checks":checks,"closed_doors_tested":targets.size(),"scope":"Exact authored closed leaves under rotated source poses. No open interiors, automatic stairs or whole-city character traversal claim."}
	var path:=ProjectSettings.globalize_path("res://../near_detail_r01/city_upgrade/near_entry_validation.json")
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with("--output="):path=argument.trim_prefix("--output=")
	var file:=FileAccess.open(path,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 2)
