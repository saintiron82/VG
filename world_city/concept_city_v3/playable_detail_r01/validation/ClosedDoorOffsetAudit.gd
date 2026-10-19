extends SceneTree
const World=preload("res://CityWorldSurfaces.gd")
var checks: Array=[]
func _init()->void:call_deferred("run")
func cast(space:Node3D,point:Vector3,normal:Vector3,exclude:Array[RID]=[])->Dictionary:
	var q:=PhysicsRayQueryParameters3D.create(point+normal*.4,point-normal*.3,1,exclude)
	var hit:=space.get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():return {"hit":false}
	return {"hit":true,"source_id":str(hit.collider.get_meta("source_id","")),"distance_to_leaf_m":hit.position.distance_to(point),"signed_outward_offset_m":(hit.position-point).dot(normal),"normal_alignment":hit.normal.dot(normal),"position":str(hit.position)}
func run()->void:
	var space:=Node3D.new();root.add_child(space)
	var world:=World.new();space.add_child(world)
	var problem:=world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),false)
	assert(problem.is_empty(),problem)
	var key:="ordinary_d4fcb5b21ffb18";var id:="d4_audit"
	var parent:=Node3D.new();world.add_child(parent)
	var pose:Dictionary={"id":id,"asset_key":key,"position_m":[2400,0,0],"yaw_rad":.71}
	assert(world._add_native(parent,pose))
	var base:Array[RID]=[];var repairs:Array[RID]=[]
	for child in parent.get_children():
		if child is StaticBody3D:
			if child.get_meta("source_id","")==id:base.append(child.get_rid())
			else:repairs.append(child.get_rid())
	assert(base.size()==1 and repairs.size()==1)
	var repair:Dictionary=world.detail_catalog.assets[key].collision_repairs[0]
	var tr:Transform3D=world._pose(pose)*world._local_transform(repair.get("transform",{}))
	var centre:Vector3=(World.RD.vector(repair.min)+World.RD.vector(repair.max))*.5
	centre.z=float(repair.max[2]);var point:=tr*centre;var normal:=tr.basis*Vector3(0,0,1)
	await physics_frame;await physics_frame
	var full:=cast(space,point,normal);var source_only:=cast(space,point,normal,repairs);var repair_only:=cast(space,point,normal,base)
	checks.append({"case":"exact_leaf_shape_exists","pass":repair_only.get("hit",false) and repair_only.distance_to_leaf_m<.001 and repair_only.normal_alignment>.999})
	checks.append({"case":"first_hit_unchanged_from_coarse_original","pass":full==source_only})
	checks.append({"case":"offset_is_original_body","pass":full.get("source_id","")==id and full.get("signed_outward_offset_m",-1)>0})
	var report:Dictionary={"schema":"riverstone.closed_door_offset_audit.v1","all_diagnostic_checks_pass":checks.all(func(x):return x.pass),"strict_exact_combined_collision_pass":false,"all_original_and_near_physical_surfaces_changed":false,"asset":key,"original_city_index_sha256":world.index_sha256,"full":full,"source_only":source_only,"repair_only":repair_only,"checks":checks,"limit":"The combined original 0.5 m sampled collider stops the ray about 0.16 m before the authored closed leaf. This predates near detail and is NOT an exact-door pass or traversable-interior test. No collision/source modification was made."}
	var out:=ProjectSettings.globalize_path("res://../near_detail_r01/city_upgrade/evidence/d4_closed_door_offset_r01.json")
	FileAccess.open(out,FileAccess.WRITE).store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_diagnostic_checks_pass else 2)
