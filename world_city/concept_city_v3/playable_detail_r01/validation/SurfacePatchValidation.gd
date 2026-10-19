extends SceneTree
const Patch=preload("res://SurfacePatchMesh.gd")
const SurfaceWorld=preload("res://CityWorldSurfaces.gd")
var checks: Array=[]
func check(name: String,value: bool,details: Variant=null) -> void:
	checks.append({"case":name,"pass":value,"details":details})
func _init() -> void:
	call_deferred("run")
func run() -> void:
	var front: Array=[[-2,-1,0],[2,-1,0],[2,3,0],[-2,3,0]]
	var f:=Patch.rectangular_face(front)
	check("proper_basis_front",f.n==Vector3.FORWARD*-1 and is_equal_approx(Basis(f.u,f.v,f.n).determinant(),1))
	var patches:=Patch.full_patches(f,Vector3(0,1,2),10)
	check("negative_world_grid_exact_16",patches.size()==16,patches.size())
	var contained:=true;var safe:=true
	for p in patches:
		for corner in [Vector3.ZERO,Vector3(1,0,0),Vector3(0,1,0),Vector3(1,1,0)]:
			var point: Vector3=p.transform*corner
			contained=contained and point.x>=-2.00001 and point.x<=2.00001 and point.y>=-1.00001 and point.y<=3.00001
			safe=safe and is_equal_approx(point.z,.0375)
	check("patches_inside_actual_source_quad",contained)
	check("explicit_visual_offset_00375",safe)
	var too_small:=Patch.rectangular_face([[0,0,0],[.5,0,0],[.5,2,0],[0,2,0]])
	check("narrow_door_trim_not_covered",too_small.is_empty())
	var side:=Patch.rectangular_face([[0,0,0],[0,2,0],[0,2,2],[0,0,2]])
	check("side_basis_preserves_winding",not side.is_empty() and is_equal_approx(Basis(side.u,side.v,side.n).determinant(),1))
	var diagonal:=Patch.rectangular_face([[0,0,0],[1,0,1],[1,2,1],[0,2,0]])
	check("non_axis_face_explicitly_rejected",diagonal.is_empty())
	check("outside_near_radius_has_zero_modules",Patch.full_patches(f,Vector3(0,1,30),10).is_empty())
	var edge:=Patch.rectangular_face([[-.5,-.25,.12345],[.5,-.25,.12345],[.5,.75,.12345],[-.5,.75,.12345]],.25)
	var trims:=Patch.trimmed_patches(edge,Vector3(0,0,2),10)
	var area:=0.0;var edge_safe:=true
	for trim in trims:
		area+=trim.size.x*trim.size.y
		for corner in [Vector3.ZERO,Vector3(trim.size.x,0,0),Vector3(0,trim.size.y,0),Vector3(trim.size.x,trim.size.y,0)]:
			var point: Vector3=trim.transform*corner
			edge_safe=edge_safe and point.x>=-.50001 and point.x<=.50001 and point.y>=-.25001 and point.y<=.75001 and absf(point.z-.16095)<.00001
	check("negative_quarter_trims_exact_area",trims.size()==4 and absf(area-1)<.00001,{"count":trims.size(),"area":area})
	check("nonquarter_plane_preserved_without_rounding",edge_safe)
	var invalid:=edge.duplicate();invalid.low=Vector2(-.49,-.25)
	check("nonquarter_uv_edges_fail_closed",Patch.trimmed_patches(invalid,Vector3(0,0,2),10).is_empty())
	edge.kind="ashlar";edge.material="stone";edge.number=0
	var other:=edge.duplicate();other.number=987
	check("seed_independent_of_quad_split",SurfaceWorld.surface_seed_token("wall",edge,trims[0])==SurfaceWorld.surface_seed_token("wall",other,trims[0]))
	other.plane+=.00001
	check("distinct_exact_planes_have_distinct_seeds",SurfaceWorld.surface_seed_token("wall",edge,trims[0])!=SurfaceWorld.surface_seed_token("wall",other,trims[0]))
	var exclusions: Array=[{"min":[-.61,.2,-.1],"max":[.61,1.8,.1]}]
	var pieces:=Patch.subtract_feature_regions(f,exclusions);var remaining:=0.0;var trimmed_area:=0.0
	var clear:=true;var retained_inside:=true
	for piece in pieces:
		remaining+=piece.area
		for patch in Patch.trimmed_patches(piece,Vector3(0,1,2),10):
			trimmed_area+=patch.size.x*patch.size.y
			clear=clear and not SurfaceWorld.patch_intersects_regions(patch,exclusions)
			for point in [patch.transform.origin,patch.transform*Vector3(patch.size.x,patch.size.y,0)]:retained_inside=retained_inside and point.x>=-2.00001 and point.x<=2.00001 and point.y>=-1.00001 and point.y<=3.00001
	check("feature_envelope_rounds_outward_and_area_conserved",absf(remaining-13)<.00001,remaining)
	check("trim_library_exactly_covers_surviving_area",absf(trimmed_area-remaining)<.00001,trimmed_area)
	check("actual_feature_opening_not_refilled",clear)
	check("trimmed_feature_pieces_stay_in_source_face",retained_inside)
	var behind:=Patch.subtract_feature_regions(f,[{"min":[-1,0,1],"max":[1,2,2]}])
	check("different_support_plane_not_subtracted",behind.size()==1 and absf(behind[0].area-16)<.00001)

	var world:=SurfaceWorld.new();root.add_child(world)
	var problem:=world.configure("res://generated/tile_r01/index.json",ProjectSettings.globalize_path("res://../../.."),true)
	check("surface_catalog_source_binding",problem.is_empty(),problem)
	if problem.is_empty():
		var module_id: String=world.surface_catalog.by_kind.ashlar[0]
		var mesh:=world._surface_module(module_id)
		check("actual_common_module_loaded",mesh!=null)
		var arrays: Array=mesh.surface_get_arrays(0)
		var legal:=true
		for point in arrays[Mesh.ARRAY_VERTEX]:legal=legal and point.z>=-.037501 and point.z<=.000001
		check("safe_module_actual_vertex_envelope",legal)
		check("mesh_shared_by_identity",world._surface_module(module_id).get_rid()==mesh.get_rid())
		var edge_id: String=world.surface_catalog.by_kind_trim.ashlar.w2_h2_x2_y2[0]
		var edge_mesh:=world._surface_module(edge_id)
		check("actual_trim_common_mesh_loaded",edge_mesh!=null)
		var size_ok:=true
		for point in edge_mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]:size_ok=size_ok and point.x>=-.00001 and point.x<=.50001 and point.y>=-.00001 and point.y<=.50001 and point.z>=-.037501 and point.z<=.000001
		check("actual_trim_extent_not_scaled",size_ok)
		check("actual_trim_mesh_cache_shared",world._surface_module(edge_id).get_rid()==edge_mesh.get_rid())
	var report={"schema":"riverstone.surface_patch.tests.v1","checks":checks,"all_pass":checks.all(func(c):return c.pass),"scope":"Actual common voxel module rendering adapter plus containment and binding fixtures; city traversal and visual review remain separate"}
	var out:=ProjectSettings.globalize_path("res://../near_detail_r01/city_upgrade/surface_patch_validation.json")
	var file:=FileAccess.open(out,FileAccess.WRITE);file.store_string(JSON.stringify(report,"  ")+"\n");print(JSON.stringify(report));quit(0 if report.all_pass else 2)
