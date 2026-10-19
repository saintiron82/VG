extends SceneTree
const World=preload("res://CityWorldSurfaces.gd")
var checks: Array=[]
var world: Node3D
const KEY="registered_port_long_loading_shed"
const OUT="res://../near_detail_r01/city_upgrade/evidence/facility_runtime_r01"
func check(name: String,value: bool,details: Variant=null) -> void:checks.append({"case":name,"pass":value,"details":details})
func _init() -> void:call_deferred("run")
func exercise(contract: Dictionary,entry: Dictionary) -> bool:
	var path:=OUT+"/contract_fixture_%02d.json" % checks.size()
	var f:=FileAccess.open(path,FileAccess.WRITE);f.store_string(JSON.stringify(contract));f.close()
	entry=entry.duplicate(true);entry.composed_manifest_path=ProjectSettings.globalize_path(path);entry.composed_manifest_sha256=FileAccess.get_sha256(path)
	world.composed_contracts.clear();world.error=""
	return world._validate_composed_contract(KEY,entry)
func run() -> void:
	world=World.new();root.add_child(world)
	check("actual_source_binding",world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),false).is_empty())
	var source: Dictionary=world.index.common_assets[KEY];var render: Dictionary=world._asset(KEY)
	var regions: Array=[{"id":"bounded_fixture","min":[-1.0,2.0,-6.25],"max":[1.0,4.0,-5.5]}]
	var entry:={"render_path":source.render_path,"sha256":source.render_sha256,"source_master_sha256":source.master_sha256,"geometry_estimated_bytes":World.RD.stats(render).quads*144,"window_regions":regions}
	var contract:={"schema":"riverstone.facility.composed_render.v1","asset_key":KEY,"source_master_sha256":source.master_sha256,"source_render_sha256":source.render_sha256,"render_sha256":source.render_sha256,"render_path":source.render_path,"output_quad_count":World.RD.stats(render).quads,"all_pass":true,"collision_reference_changed":false,"window_regions":regions}
	check("matching_verified_contract",exercise(contract,entry))
	for field in ["source_master_sha256","source_render_sha256","render_sha256","render_path","asset_key"]:
		var bad:=contract.duplicate(true);bad[field]="invalid"
		check("reject_"+field,not exercise(bad,entry))
	for field in ["all_pass","collision_reference_changed"]:
		var bad:=contract.duplicate(true);bad[field]=not bad[field]
		check("reject_"+field,not exercise(bad,entry))
	var bad:=contract.duplicate(true);bad.window_regions[0].max[0]=2.0
	check("reject_modified_window_region",not exercise(bad,entry))
	bad=contract.duplicate(true);bad.output_quad_count+=1
	check("reject_modified_quad_count",not exercise(bad,entry))
	var pose:=Transform3D(Basis.IDENTITY,Vector3(-.5,2.5,-6.0))
	var patch:={"transform":pose,"size":Vector2(1,1)}
	check("module_over_window_rejected",World.patch_intersects_regions(patch,regions))
	patch.transform.origin.x=2.0
	check("module_outside_window_preserved",not World.patch_intersects_regions(patch,regions))
	patch.transform.origin=Vector3(-2,2.5,-6)
	check("exact_window_boundary_conservatively_rejected",World.patch_intersects_regions(patch,regions))
	patch.transform.origin=Vector3(-2.1,2.5,-6)
	check("ten_centimeter_separation_preserved",not World.patch_intersects_regions(patch,regions))
	patch.transform=Transform3D(Basis(Vector3(0,0,1),Vector3.UP,Vector3(-1,0,0)),Vector3(.9,2.5,-6.2))
	check("side_facing_relief_also_rejected",World.patch_intersects_regions(patch,regions))
	var a:=entry.duplicate(true);a.composed_manifest_sha256="a";var b:=a.duplicate(true);b.composed_manifest_sha256="b"
	check("native_cache_composition_hash_binds_manifest",world.composition_contract_hash(a)!=world.composition_contract_hash(b))
	b=a.duplicate(true);b.window_regions[0].max[1]=5
	check("native_cache_composition_hash_binds_cavities",world.composition_contract_hash(a)!=world.composition_contract_hash(b))
	var bounded:=contract.duplicate(true);var bounded_entry:=entry.duplicate(true)
	var fine_bounds: Dictionary=source.bounds.duplicate(true);fine_bounds.max[1]+=.5
	var proof:={"source_master_sha256":source.master_sha256,"coarse_render_bounds":source.bounds.duplicate(true),"composed_render_bounds":fine_bounds.duplicate(true),"analytic_source_bounds":fine_bounds.duplicate(true),"outside_analytic_aabb_vertices":0,"reason":"Synthetic contract validator fixture only; not an authored asset proof."}
	bounded.bounds_contract=proof;bounded_entry.bounds_contract=proof.duplicate(true);bounded_entry.visual_bounds=fine_bounds
	check("declared_source_bounds_contract",exercise(bounded,bounded_entry))
	var wrong:=bounded.duplicate(true);var wrong_entry:=bounded_entry.duplicate(true)
	wrong.bounds_contract.outside_analytic_aabb_vertices=1;wrong_entry.bounds_contract=wrong.bounds_contract.duplicate(true)
	check("reject_analytic_bounds_overflow",not exercise(wrong,wrong_entry))
	wrong=bounded.duplicate(true);wrong_entry=bounded_entry.duplicate(true)
	wrong.bounds_contract.analytic_source_bounds.max[1]-=1.0;wrong_entry.bounds_contract=wrong.bounds_contract.duplicate(true)
	check("reject_fine_bounds_exceeding_analytic_source",not exercise(wrong,wrong_entry))
	wrong=bounded.duplicate(true);wrong_entry=bounded_entry.duplicate(true)
	wrong.bounds_contract.reason="";wrong_entry.bounds_contract=wrong.bounds_contract.duplicate(true)
	check("reject_undeclared_bound_revision_reason",not exercise(wrong,wrong_entry))
	wrong_entry=bounded_entry.duplicate(true);wrong_entry.visual_bounds.max[1]+=.05
	check("reject_visual_bounds_manifest_mismatch",not exercise(bounded,wrong_entry))
	check("native_hash_binds_new_visual_bounds",world.composition_contract_hash(bounded_entry)!=world.composition_contract_hash(wrong_entry))
	var report:={"all_pass":checks.all(func(c):return c.pass),"checks":checks,"scope":"Source-bound manifest gate and finite-region wall-overlay rejection; fixtures do not claim a generated facility is visually accepted."}
	var f:=FileAccess.open(OUT+"/runtime_contract_validation.json",FileAccess.WRITE);f.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 2)
